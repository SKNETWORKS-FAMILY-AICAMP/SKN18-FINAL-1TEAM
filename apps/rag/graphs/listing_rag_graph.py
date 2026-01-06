from typing import List
from langgraph.graph import StateGraph, END
from common.state import RAGState
from nodes import sql_search_node, vector_search_node, generate_node, neo4j_search_node, es_search_node, query_analyzer_node, soft_filter_rerank_node

def create_rag_graph():
    """
    RAG 그래프 생성 (순차적 파이프라인 + 검색 전략 분기 + 멀티턴 인터럽트)
    
    검색 전략:
    1. neo4j_only: Neo4j → SQL (위치/시설 기반)
    2. keyword_only: ES Keyword → SQL (가격/타입 기반)
    3. neo4j_keyword: Neo4j → ES Keyword → SQL (위치 + 가격)
    4. keyword_vector: ES Keyword → Vector Rerank → SQL (가격 + 소프트 필터)
    5. full: Neo4j → ES Keyword → Vector Rerank → SQL (복합 조건)
    
    흐름:
    query_analyzer → [조건 완성?] → Yes: [전략별 파이프라인] → sql_search → generate
                       ↓ No
                    interrupt_response → END (후속 질문 반환)
    """
    workflow = StateGraph(RAGState)
    
    # ==================================================================
    # 노드 등록
    # ==================================================================
    workflow.add_node("query_analyzer", query_analyzer_node.analyze)
    
    # 멀티턴 인터럽트 응답 노드
    workflow.add_node("interrupt_response", interrupt_response_node)
    
    # 검색 노드들 (순차 실행)
    workflow.add_node("neo4j_search", neo4j_search_node.search)
    workflow.add_node("es_keyword_search", es_keyword_search_node)
    workflow.add_node("vector_rerank", soft_filter_rerank_node.rerank)  # 벡터 재정렬
    
    # 최종 처리 노드들
    workflow.add_node("sql_search", sql_search_node.search)
    workflow.add_node("generate", generate_node.generate)
    
    # ==================================================================
    # 엣지 정의
    # ==================================================================
    
    # 진입점
    workflow.set_entry_point("query_analyzer")
    
    # query_analyzer → 조건 완성 여부 체크 → 검색 전략 분기 OR 인터럽트
    def route_after_analyzer(state: RAGState) -> str:
        """
        조건 완성 여부에 따른 분기:
        - 조건 미완성: interrupt_response → 후속 질문 반환
        - 조건 완성: 검색 전략에 따라 분기
        """
        conversation_complete = state.get("conversation_complete", False)
        
        if not conversation_complete:
            # 조건 미완성 → 인터럽트
            print(f"[Router] ❓ 조건 미완성 → 인터럽트 응답")
            return "interrupt"
        
        # 조건 완성 → 검색 전략 분기
        strategy = state.get("search_strategy", "neo4j_keyword")
        print(f"[Router] 🎯 조건 완성, 검색 전략: {strategy}")
        
        if strategy == "neo4j_only":
            return "neo4j_only"
        elif strategy == "keyword_only":
            return "keyword_only"
        elif strategy == "neo4j_keyword":
            return "neo4j_keyword"
        elif strategy == "keyword_vector":
            return "keyword_vector"
        elif strategy == "full":
            return "full"
        else:
            return "neo4j_keyword"
    
    workflow.add_conditional_edges(
        "query_analyzer",
        route_after_analyzer,
        {
            "interrupt": "interrupt_response",
            "neo4j_only": "neo4j_search",
            "keyword_only": "es_keyword_search",
            "neo4j_keyword": "neo4j_search",
            "keyword_vector": "es_keyword_search",
            "full": "neo4j_search"
        }
    )
    
    # interrupt_response → END (후속 질문 반환하고 종료)
    workflow.add_edge("interrupt_response", END)
    
    # 각 전략별 후속 라우팅
    def route_after_neo4j(state: RAGState) -> str:
        """Neo4j 검색 후 라우팅"""
        strategy = state.get("search_strategy", "neo4j_keyword")
        
        if strategy == "neo4j_only":
            return "sql_search"
        elif strategy in ["neo4j_keyword", "full"]:
            return "es_keyword_search"
        else:
            return "sql_search"
    
    workflow.add_conditional_edges(
        "neo4j_search",
        route_after_neo4j,
        {
            "sql_search": "sql_search",
            "es_keyword_search": "es_keyword_search"
        }
    )
    
    def route_after_keyword(state: RAGState) -> str:
        """ES Keyword 검색 후 라우팅"""
        strategy = state.get("search_strategy", "neo4j_keyword")
        
        if strategy in ["keyword_vector", "full"]:
            return "vector_rerank"
        else:
            return "sql_search"
    
    workflow.add_conditional_edges(
        "es_keyword_search",
        route_after_keyword,
        {
            "sql_search": "sql_search",
            "vector_rerank": "vector_rerank"
        }
    )
    
    # vector_rerank → sql_search
    workflow.add_edge("vector_rerank", "sql_search")
    
    # sql_search → generate
    workflow.add_edge("sql_search", "generate")
    
    return workflow.compile()


def es_keyword_search_node(state: RAGState) -> RAGState:
    """
    ES 키워드 기반 검색/재정렬 노드
    
    - 이전 단계 결과가 있으면: 가격/타입 조건으로 재정렬 (결과 유지)
    - 이전 단계 결과가 없으면: 새 검색
    """
    hard_filters = state.get("hard_filters", {})
    existing_results = state.get("graph_results", [])
    
    print(f"\n{'='*60}")
    print(f"[ES Keyword] 🔍 가격/타입 기반 검색")
    print(f"[ES Keyword] 📋 하드 필터: {hard_filters}")
    print(f"[ES Keyword] 📊 기존 결과: {len(existing_results)}개")
    print(f"{'='*60}\n")
    
    # 기존 결과가 있고, 가격/타입 필터가 없으면 스킵
    has_price_filter = hard_filters.get("max_deposit") or hard_filters.get("max_rent") or hard_filters.get("min_deposit")
    has_type_filter = hard_filters.get("building_type") or hard_filters.get("deal_type")
    
    if existing_results and not has_price_filter and not has_type_filter:
        print(f"[ES Keyword] ⏭️ 가격/타입 필터 없음 - 기존 결과 유지")
        return state
    
    try:
        from elasticsearch import Elasticsearch
        import os
        
        es_host = os.getenv("ELASTICSEARCH_HOST", "elasticsearch")
        es_port = os.getenv("ELASTICSEARCH_PORT", "9200")
        es_url = f"http://{es_host}:{es_port}"
        es_index = os.getenv("ES_INDEX_NAME", "realestate_listings")
        
        es = Elasticsearch(hosts=[es_url], request_timeout=30)
        
        # bool 쿼리 빌드
        must_clauses = []
        filter_clauses = []
        
        # 기존 결과가 있으면 해당 ID들만 필터링
        if existing_results:
            existing_ids = [str(r.get("id", "")) for r in existing_results if r.get("id")]
            if existing_ids:
                filter_clauses.append({"terms": {"land_num": existing_ids}})
        
        # 가격/타입 필터 적용 (기존 결과가 있으면 더 관대하게)
        building_type = hard_filters.get("building_type")
        if building_type and not existing_results:  # 새 검색일 때만 building_type 필터
            filter_clauses.append({"term": {"building_type": building_type}})
        
        # ★★★ 거래 유형은 항상 적용 (사용자가 명시적으로 선택한 조건) ★★★
        deal_type = hard_filters.get("deal_type")
        if deal_type:
            filter_clauses.append({"term": {"deal_type": deal_type}})
            print(f"[ES Keyword] 🏠 거래유형 필터 적용: {deal_type}")
        
        # 보증금 범위 (항상 적용)
        max_deposit = hard_filters.get("max_deposit")
        min_deposit = hard_filters.get("min_deposit")
        if max_deposit or min_deposit:
            deposit_range = {"range": {"deposit": {}}}
            if max_deposit:
                deposit_range["range"]["deposit"]["lte"] = max_deposit
            if min_deposit:
                deposit_range["range"]["deposit"]["gte"] = min_deposit
            filter_clauses.append(deposit_range)
        
        # 월세 범위 (항상 적용)
        max_rent = hard_filters.get("max_rent")
        if max_rent:
            filter_clauses.append({"range": {"monthly_rent": {"lte": max_rent}}})
        
        # 키워드 검색 (위치 등) - 기존 결과가 없을 때만
        if not existing_results:
            location = hard_filters.get("location")
            if location:
                must_clauses.append({
                    "multi_match": {
                        "query": location,
                        "fields": ["address^3", "search_text^2"],
                        "type": "best_fields"
                    }
                })
        
        # 쿼리 빌드
        query = {
            "bool": {
                "must": must_clauses if must_clauses else [{"match_all": {}}],
                "filter": filter_clauses if filter_clauses else []
            }
        }
        
        response = es.search(
            index=es_index,
            query=query,
            size=50,
            _source=["land_num", "address", "search_text", "deposit", "monthly_rent", "building_type", "deal_type"]
        )
        
        # 결과 파싱
        results = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            results.append({
                "id": source.get("land_num", hit["_id"]),
                "address": source.get("address", ""),
                "search_text": source.get("search_text", ""),
                "deposit": source.get("deposit", 0),
                "monthly_rent": source.get("monthly_rent", 0),
                "total_score": hit["_score"],
                "source": "es_keyword"
            })
        
        print(f"[ES Keyword] ✅ {len(results)}개 매물 발견")
        
        # 결과가 있으면 업데이트, 없으면 기존 결과 유지!
        if results:
            state["graph_results"] = results
        elif existing_results:
            print(f"[ES Keyword] ⚠️ ES 결과 0개 - 기존 Neo4j 결과 {len(existing_results)}개 유지")
            # 기존 결과 유지 (state["graph_results"] 변경하지 않음)
        else:
            state["graph_results"] = []
        
    except Exception as e:
        print(f"[ES Keyword] ❌ 검색 실패: {e}")
        # 실패 시 기존 결과 유지
    
    return state


def interrupt_response_node(state: RAGState) -> RAGState:
    """
    멀티턴 인터럽트 응답 노드
    
    조건이 미완성일 때 호출되어, pending_question을 answer로 설정하고 종료.
    프론트엔드에서 이를 받아 사용자에게 추가 질문을 표시.
    """
    pending_question = state.get("pending_question", "")
    missing = state.get("missing_conditions", [])
    collected = state.get("collected_conditions", {})
    
    print(f"\n{'='*60}")
    print(f"[Interrupt] ❓ 조건 수집 인터럽트")
    print(f"[Interrupt] 📦 수집된 조건: {collected}")
    print(f"[Interrupt] ❌ 누락 조건: {missing}")
    print(f"{'='*60}\n")
    
    # 후속 질문을 answer로 설정
    state["answer"] = pending_question
    
    # 검색은 실행하지 않음 (빈 결과)
    state["graph_results"] = []
    state["sql_results"] = []
    
    return state


