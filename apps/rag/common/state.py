from typing import TypedDict, List, Optional, Dict, Any

class RAGState(TypedDict):
    question: str
    session_id: Optional[str]  # 세션 ID
    
    # 캐시 관련 (후속 질문 필터링)
    cached_property_ids: Optional[List[str]]  # Q1에서 저장된 매물 ID
    use_cache: Optional[bool]  # 캐시 사용 여부
    filter_source: Optional[str]  # "neo4j:safety", "neo4j:convenience", "postgres" 등
    price_conditions: Optional[Dict[str, int]]  # 가격 조건: deposit_max, rent_max 등
    
    # 누적 검색 컨텍스트 (Q1+Q2+Q3... 모든 이전 결과)
    accumulated_results: Optional[Dict[str, Dict]]  # {property_id: {merged_data}}
    
    # =====================================================================
    # Query Analyzer 결과 (하드/소프트 필터 분리)
    # =====================================================================
    hard_filters: Optional[Dict[str, Any]]  # 고정 조건 (위치, 가격, 건물타입 등)
    # 예: {"location": "홍대입구", "deal_type": "월세", "max_rent": 50, "building_type": "원룸", "facilities": ["subway", "convenience"]}
    
    soft_filters: Optional[List[str]]  # 감성 선호 (깨끗한, 럭셔리한 등) - 없을 수 있음
    # 예: ["깨끗한", "럭셔리한", "가성비좋은", "조용한"]
    
    search_strategy: Optional[str]  # "neo4j" | "es_keyword" | "hybrid"
    # neo4j: 위치+시설 기반, es_keyword: 가격+타입 기반, hybrid: 복합
    
    # 기존 필드
    query_type: Optional[str]
    sql_results: Optional[List]
    vector_results: Optional[List]
    graph_results: Optional[List]
    graph_summary: Optional[str]  # Neo4j 결과의 LLM 요약
    answer: Optional[str]
    
    # ES 하이브리드 검색 관련 (Requirements 6.2, 6.3)
    es_scores: Optional[Dict[str, float]]  # ES 검색 점수 {property_id: score}
    
    # 벡터 검색 관련 (Requirements 3.1, 3.2, 3.3, 3.4)
    vector_scores: Optional[Dict[str, float]]  # 벡터 검색 점수 {property_id: score}

    # 검색 진행 상황 (Requirements: Dynamic Progress Messages)
    search_steps: Optional[List[str]]  # ["홍대입구 근처 검색 중", "편의점 찾는 중", ...]
    requested_facilities: Optional[List[str]]  # ["convenience", "safety", ...]

    # =====================================================================
    # 멀티턴 대화 상태 (조건 수집 인터럽트)
    # =====================================================================
    pending_question: Optional[str]  # 사용자에게 보낼 추가 질문
    missing_conditions: Optional[List[str]]  # 누락된 조건 ["location", "deal_type", "style"]
    collected_conditions: Optional[Dict[str, Any]]  # 지금까지 수집된 조건
    conversation_complete: Optional[bool]  # 모든 조건 수집 완료 여부

