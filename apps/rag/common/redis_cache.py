"""Redis Cache for Cumulative Query Data Storage

Environment Variables (Requirements 3.3):
- REDIS_URL: Full Redis connection URL (production, e.g., redis://host:port/db)
- REDIS_HOST: Redis host (development, default: redis)
- REDIS_PORT: Redis port (development, default: 6379)
"""
import redis
import json
import os

# =============================================================================
# 대화 히스토리 캐시 (최근 5개 질문/답변)
# =============================================================================
MAX_CONVERSATION_HISTORY = 5  # 최근 5개 질문만 유지


def save_conversation_turn(session_id: str, question: str, answer: str, ttl: int = 86400):
    """
    대화 턴 저장 (최근 5개만 유지)
    
    Args:
        session_id: 세션 ID
        question: 사용자 질문
        answer: 챗봇 응답 (요약본)
        ttl: 캐시 유지 시간 (기본 24시간)
    """
    try:
        r = get_redis_client()
        key = f"conversation:{session_id}"
        
        # 기존 히스토리 로드
        existing = r.get(key)
        history = json.loads(existing) if existing else []
        
        # 새 턴 추가
        history.append({
            "question": question,
            "answer": answer[:500] if answer else ""  # 답변은 500자로 제한
        })
        
        # 최근 5개만 유지
        history = history[-MAX_CONVERSATION_HISTORY:]
        
        r.setex(key, ttl, json.dumps(history, ensure_ascii=False))
        print(f"[ConversationCache] ✓ Saved turn ({len(history)}/{MAX_CONVERSATION_HISTORY})")
    except Exception as e:
        print(f"[ConversationCache] ✗ Save failed: {e}")


def get_conversation_history(session_id: str) -> list:
    """
    대화 히스토리 조회 (최근 5개)
    
    Returns:
        [{"question": "...", "answer": "..."}, ...]
    """
    try:
        r = get_redis_client()
        key = f"conversation:{session_id}"
        data = r.get(key)
        if data:
            history = json.loads(data)
            print(f"[ConversationCache] ✓ Loaded {len(history)} turns")
            return history
        print(f"[ConversationCache] No history for session")
        return []
    except Exception as e:
        print(f"[ConversationCache] ✗ Load failed: {e}")
        return []


def clear_conversation_history(session_id: str):
    """대화 히스토리 삭제"""
    try:
        r = get_redis_client()
        r.delete(f"conversation:{session_id}")
        print(f"[ConversationCache] ✓ Cleared history")
    except Exception as e:
        print(f"[ConversationCache] ✗ Clear failed: {e}")


def get_redis_client():
    """Get Redis client with support for both REDIS_URL and individual env vars.
    
    In production (AWS ElastiCache), use REDIS_URL.
    In development (Docker), use REDIS_HOST and REDIS_PORT.
    """
    redis_url = os.getenv("REDIS_URL")
    
    if redis_url:
        # Production: Use REDIS_URL (e.g., redis://elasticache-endpoint:6379/0)
        return redis.from_url(redis_url, decode_responses=True)
    else:
        # Development: Use individual environment variables
        return redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0,
            decode_responses=True
        )

def save_search_context(session_id: str, property_ids: list, facility_type: str = None, graph_results: list = None, ttl: int = 7200):
    """
    검색 결과를 누적하여 저장 (Q1 + Q2 + Q3... 모든 데이터 누적)
    
    핵심 로직: 
    - 기존 accumulated_results에 새 데이터를 **병합** (덮어쓰기 X)
    - 모든 시설 필드가 누적됨
    """
    try:
        r = get_redis_client()
        key = f"search:{session_id}"
        
        # 1. 기존 데이터 로드
        existing_data = r.get(key)
        if existing_data:
            existing = json.loads(existing_data)
        else:
            existing = {"property_ids": [], "facility_types": [], "accumulated_results": {}}
        
        existing_accumulated = existing.get("accumulated_results", {})
        existing_facility_types = existing.get("facility_types", [])
        
        # 2. 새 결과를 기존에 병합 (기존 데이터 유지 + 새 필드 추가)
        for result in (graph_results or []):
            if not isinstance(result, dict):
                continue
            prop_id = str(result.get("id") or result.get("p.id") or "")
            if not prop_id:
                continue
            
            if prop_id in existing_accumulated:
                # 기존 데이터 유지, 새 값이 있으면 추가 (빈 값은 덮어쓰지 않음)
                merged = existing_accumulated[prop_id].copy()
                for key_name, value in result.items():
                    # 새 값이 유효하고, 기존에 없거나 빈 값일 때만 업데이트
                    if value and value != [] and value != 0 and value != "":
                        existing_val = merged.get(key_name)
                        if not existing_val or existing_val == [] or existing_val == 0:
                            merged[key_name] = value
                        # id, address는 항상 최신으로 유지
                        elif key_name in ["id", "address"]:
                            merged[key_name] = value
                existing_accumulated[prop_id] = merged
            else:
                existing_accumulated[prop_id] = result.copy()
        
        # 3. 시설 타입 누적
        if facility_type and facility_type not in existing_facility_types:
            existing_facility_types.append(facility_type)
        
        # 4. 저장
        data = {
            "property_ids": property_ids,
            "facility_types": existing_facility_types,
            "accumulated_results": existing_accumulated
        }
        r.setex(key, ttl, json.dumps(data))
        
        # 디버그 로그
        sample_id = next(iter(existing_accumulated.keys()), None)
        if sample_id:
            sample_fields = list(existing_accumulated[sample_id].keys())
            print(f"[RedisCache] ✓ Saved {len(property_ids)} IDs, facilities: {existing_facility_types}")
            print(f"[RedisCache] DEBUG: Sample fields: {sample_fields}")
    except Exception as e:
        print(f"[RedisCache] ✗ Save failed: {e}")

def get_search_context(session_id: str) -> dict:
    """저장된 검색 컨텍스트 조회"""
    try:
        r = get_redis_client()
        key = f"search:{session_id}"
        data = r.get(key)
        if data:
            context = json.loads(data)
            print(f"[RedisCache] ✓ Loaded {len(context.get('property_ids', []))} IDs, facilities: {context.get('facility_types', [])}")
            return context
        print(f"[RedisCache] No cached context for session")
        return {}
    except Exception as e:
        print(f"[RedisCache] ✗ Load failed: {e}")
        return {}

def get_accumulated_results(session_id: str) -> dict:
    """누적된 결과를 ID별 dict로 반환"""
    context = get_search_context(session_id)
    return context.get("accumulated_results", {})

def get_property_ids(session_id: str) -> list:
    context = get_search_context(session_id)
    return context.get("property_ids", [])

def clear_cache(session_id: str):
    """캐시 삭제"""
    try:
        r = get_redis_client()
        r.delete(f"search:{session_id}")
        print(f"[RedisCache] ✓ Cleared cache")
    except Exception as e:
        print(f"[RedisCache] ✗ Clear failed: {e}")


# =============================================================================
# 위치 기반 Neo4j 결과 캐싱 (Plan 4: 응답 속도 최적화)
# =============================================================================
# 동일 위치 검색 시 Neo4j 쿼리를 스킵하여 응답 시간 대폭 단축
# TTL: 24시간 (위치 데이터는 자주 변경되지 않음)

import hashlib

def normalize_location(location: str) -> str:
    """위치명 정규화 (역, 대, 학교 등 접미사 제거)"""
    if not location:
        return ""
    # 접미사 제거
    normalized = location.replace("역", "").replace("대학교", "").replace("학교", "")
    return normalized.strip().lower()

def get_location_cache_key(location: str, facility_type: str = "default") -> str:
    """위치+시설 기반 캐시 키 생성"""
    normalized = normalize_location(location)
    key_str = f"{normalized}:{facility_type}"
    hash_suffix = hashlib.md5(key_str.encode()).hexdigest()[:8]
    return f"neo4j:loc:{hash_suffix}"

def save_location_cache(location: str, facility_type: str, results: list, ttl: int = 86400):
    """
    위치 기반 Neo4j 검색 결과 캐싱
    
    Args:
        location: 위치명 (예: "홍대입구", "강남")
        facility_type: 시설 타입 (예: "convenience", "safety")
        results: Neo4j 검색 결과 리스트
        ttl: 캐시 유지 시간 (기본 24시간)
    """
    if not location or not results:
        return
    
    try:
        r = get_redis_client()
        key = get_location_cache_key(location, facility_type)
        
        # 결과를 JSON으로 직렬화
        data = {
            "location": location,
            "facility_type": facility_type,
            "results": results,
            "count": len(results)
        }
        r.setex(key, ttl, json.dumps(data, default=str))
        
        print(f"[LocationCache] ✓ Saved {len(results)} results for '{location}:{facility_type}' (TTL: {ttl//3600}h)")
    except Exception as e:
        print(f"[LocationCache] ✗ Save failed: {e}")

def get_location_cache(location: str, facility_type: str = "default") -> list | None:
    """
    위치 기반 Neo4j 검색 결과 조회
    
    Args:
        location: 위치명
        facility_type: 시설 타입
    
    Returns:
        캐시된 결과 리스트 (없으면 None)
    """
    if not location:
        return None
    
    try:
        r = get_redis_client()
        key = get_location_cache_key(location, facility_type)
        
        data = r.get(key)
        if data:
            cached = json.loads(data)
            results = cached.get("results", [])
            print(f"[LocationCache] ✓ Cache HIT for '{location}:{facility_type}' ({len(results)} results)")
            return results
        
        print(f"[LocationCache] Cache MISS for '{location}:{facility_type}'")
        return None
    except Exception as e:
        print(f"[LocationCache] ✗ Load failed: {e}")
        return None

def clear_location_cache(location: str = None, facility_type: str = None):
    """
    위치 캐시 삭제
    
    Args:
        location: 특정 위치만 삭제 (None이면 전체)
        facility_type: 특정 시설만 삭제
    """
    try:
        r = get_redis_client()
        
        if location and facility_type:
            # 특정 위치+시설 삭제
            key = get_location_cache_key(location, facility_type)
            r.delete(key)
            print(f"[LocationCache] ✓ Cleared '{location}:{facility_type}'")
        else:
            # 전체 위치 캐시 삭제
            keys = r.keys("neo4j:loc:*")
            if keys:
                r.delete(*keys)
            print(f"[LocationCache] ✓ Cleared all location caches ({len(keys)} keys)")
    except Exception as e:
        print(f"[LocationCache] ✗ Clear failed: {e}")


# =============================================================================
# 멀티턴 대화 조건 수집 캐시
# =============================================================================
# 세션별로 수집 중인 조건 (위치, 거래유형, 스타일)을 저장

def save_collected_conditions(session_id: str, conditions: dict, ttl: int = 3600):
    """
    수집된 조건 저장 (1시간 유지)
    
    Args:
        session_id: 세션 ID
        conditions: {
            "location": "홍대역",
            "deal_type": "월세",
            "style": ["풀옵션", "채광좋음"],
            "price_info": {"max_deposit": 1000, "max_rent": 50}
        }
        ttl: 캐시 유지 시간 (기본 1시간)
    """
    try:
        r = get_redis_client()
        key = f"conditions:{session_id}"
        r.setex(key, ttl, json.dumps(conditions, ensure_ascii=False))
        print(f"[ConditionsCache] ✓ Saved conditions: {list(conditions.keys())}")
    except Exception as e:
        print(f"[ConditionsCache] ✗ Save failed: {e}")


def get_collected_conditions(session_id: str) -> dict:
    """
    수집된 조건 조회
    
    Returns:
        저장된 조건 dict (없으면 빈 dict)
    """
    try:
        r = get_redis_client()
        key = f"conditions:{session_id}"
        data = r.get(key)
        if data:
            conditions = json.loads(data)
            print(f"[ConditionsCache] ✓ Loaded conditions: {list(conditions.keys())}")
            return conditions
        print(f"[ConditionsCache] No conditions for session")
        return {}
    except Exception as e:
        print(f"[ConditionsCache] ✗ Load failed: {e}")
        return {}


def clear_collected_conditions(session_id: str):
    """조건 초기화 (검색 완료 후)"""
    try:
        r = get_redis_client()
        r.delete(f"conditions:{session_id}")
        print(f"[ConditionsCache] ✓ Cleared conditions")
    except Exception as e:
        print(f"[ConditionsCache] ✗ Clear failed: {e}")
