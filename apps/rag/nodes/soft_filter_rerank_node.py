"""
Soft Filter Rerank Node - 소프트 필터 기반 재정렬

하드 필터로 검색된 결과를 소프트 필터(감성 선호)로 재정렬합니다.
소프트 필터가 없으면 이 노드는 스킵됩니다.

소프트 필터 예시:
- 깨끗한, 럭셔리한, 가성비좋은, 조용한, 채광좋은, 신축, 넓은, 아늑한

처리 방식:
- 소프트 필터 키워드를 벡터 임베딩
- 매물의 style_tags, search_text와 유사도 계산
- 유사도 점수로 결과 재정렬
"""
import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# libs 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from common.state import RAGState

logger = logging.getLogger(__name__)

# 임베딩 서비스 싱글톤
_embedding_service = None


def get_embedding_service():
    """EmbeddingService 싱글톤 인스턴스 반환"""
    global _embedding_service
    if _embedding_service is None:
        from libs.clients.embedding_service import EmbeddingService
        _embedding_service = EmbeddingService.get_instance()
    return _embedding_service


def soft_filter_rerank(state: RAGState) -> RAGState:
    """
    소프트 필터 기반 재정렬 노드
    
    - 소프트 필터가 없으면 그대로 반환 (스킵)
    - 소프트 필터가 있으면 벡터 유사도로 재정렬
    """
    soft_filters = state.get("soft_filters", [])
    graph_results = state.get("graph_results", [])
    
    # 소프트 필터가 없으면 스킵
    if not soft_filters:
        print("[SoftFilterRerank] ⏭️ 소프트 필터 없음 - 스킵")
        return state
    
    # 결과가 없으면 스킵
    if not graph_results:
        print("[SoftFilterRerank] ⏭️ 검색 결과 없음 - 스킵")
        return state
    
    print(f"\n{'='*60}")
    print(f"[SoftFilterRerank] 🎨 소프트 필터 재정렬 시작")
    print(f"[SoftFilterRerank] 필터: {soft_filters}")
    print(f"[SoftFilterRerank] 대상: {len(graph_results)}개 매물")
    print(f"{'='*60}\n")
    
    try:
        # 소프트 필터 키워드를 하나의 쿼리로 결합
        soft_query = " ".join(soft_filters)
        
        # 벡터 유사도 계산 (ES 활용)
        reranked_results = _rerank_with_vector_similarity(
            soft_query=soft_query,
            results=graph_results
        )
        
        state["graph_results"] = reranked_results
        print(f"[SoftFilterRerank] ✅ 재정렬 완료: {len(reranked_results)}개")
        
    except Exception as e:
        print(f"[SoftFilterRerank] ❌ 재정렬 실패: {e}, 원본 순서 유지")
        logger.error(f"[SoftFilterRerank] Error: {e}")
    
    return state


def _rerank_with_vector_similarity(
    soft_query: str,
    results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    소프트 필터 쿼리로 벡터 유사도 계산 후 재정렬
    
    ES의 style_tags, search_text를 기반으로 유사도 계산
    """
    from elasticsearch import Elasticsearch
    
    # ES 클라이언트 가져오기
    es_host = os.getenv("ELASTICSEARCH_HOST", "elasticsearch")
    es_port = os.getenv("ELASTICSEARCH_PORT", "9200")
    es_url = f"http://{es_host}:{es_port}"
    
    es = Elasticsearch(hosts=[es_url], request_timeout=30)
    
    # 소프트 쿼리 임베딩 생성
    service = get_embedding_service()
    soft_embedding = service.embed_text(soft_query)
    
    if not soft_embedding:
        print("[SoftFilterRerank] ⚠️ 임베딩 생성 실패, 원본 순서 유지")
        return results
    
    # 현재 결과의 ID 추출
    result_ids = [str(r.get("id", "")) for r in results if r.get("id")]
    
    if not result_ids:
        return results
    
    try:
        # ES kNN 검색으로 유사도 점수 계산 (결과 필터링)
        es_index = os.getenv("ES_INDEX_NAME", "realestate_listings")
        
        response = es.search(
            index=es_index,
            knn={
                "field": "embedding",
                "query_vector": soft_embedding,
                "k": len(result_ids),
                "num_candidates": len(result_ids) * 3,
                "filter": {
                    "terms": {"land_num": result_ids}
                }
            },
            size=len(result_ids),
            _source=["land_num"]
        )
        
        # ES 결과로 유사도 점수 매핑
        soft_scores = {}
        for hit in response["hits"]["hits"]:
            land_num = hit["_source"].get("land_num")
            if land_num:
                soft_scores[str(land_num)] = hit["_score"]
        
        # 결과에 소프트 필터 점수 추가
        for result in results:
            prop_id = str(result.get("id", ""))
            result["soft_filter_score"] = soft_scores.get(prop_id, 0)
            
            # 최종 점수 계산: 기존 점수 60% + 소프트 필터 점수 40%
            base_score = result.get("total_score", 0) or result.get("combined_score", 0) or 0
            soft_score = result["soft_filter_score"]
            
            # 점수 정규화 (소프트 스코어)
            max_soft = max(soft_scores.values()) if soft_scores else 1
            normalized_soft = soft_score / max_soft if max_soft > 0 else 0
            
            result["final_score"] = base_score * 0.6 + normalized_soft * base_score * 0.4
        
        # 최종 점수로 재정렬
        results.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        
        print(f"[SoftFilterRerank] 📊 상위 3개 소프트 점수: {[(r.get('id'), r.get('soft_filter_score', 0)) for r in results[:3]]}")
        
    except Exception as e:
        print(f"[SoftFilterRerank] ⚠️ ES 검색 실패: {e}, 원본 순서 유지")
        logger.error(f"[SoftFilterRerank] ES error: {e}")
    
    return results


def should_rerank(state: RAGState) -> bool:
    """소프트 필터 재정렬이 필요한지 확인 (라우팅용)"""
    soft_filters = state.get("soft_filters", [])
    return bool(soft_filters) and len(soft_filters) > 0


# 그래프 노드 진입점
def rerank(state: RAGState) -> RAGState:
    """그래프 노드 진입점"""
    return soft_filter_rerank(state)
