"""
Classify Node - 질문 분류 및 캐시 무효화 결정

핵심 로직:
- gpt-5-nano로 후속 질문 vs 새 질문 분류 (< 1초)
- 세션의 위치 비교로 캐시 무효화 결정
- 최근 5개 대화 히스토리 기반 판단
"""
from common.state import RAGState
from common.redis_cache import get_redis_client, get_conversation_history
import json
import os
import time


def classify(state: RAGState) -> RAGState:
    """
    질문 분류 및 캐시 무효화 결정
    
    1. gpt-5-nano로 후속 질문 여부 판단
    2. 새 질문에서 위치 추출 / 세션의 기존 위치와 비교
    3. 위치가 바뀌면 cached_property_ids 초기화 → 새 검색
    """
    question = state.get("question", "")
    session_id = state.get("session_id", "")
    cached_ids = state.get("cached_property_ids", [])
    
    # 기본값 설정
    state["query_type"] = "graph_search"
    state["is_followup"] = False
    
    # 세션 ID가 없으면 그대로 반환
    if not session_id:
        return state
    
    # 1. 대화 히스토리 로드 (최근 5개)
    conversation_history = get_conversation_history(session_id)
    
    # 2. gpt-5-nano로 의도 분류 (히스토리가 있을 때만)
    if conversation_history:
        start_time = time.time()
        is_followup = classify_intent_with_llm(question, conversation_history)
        elapsed = time.time() - start_time
        print(f"[Classify] LLM intent classification: is_followup={is_followup} ({elapsed:.2f}s)")
        state["is_followup"] = is_followup
        
        # 후속 질문이 아니면 캐시 무효화
        if not is_followup:
            print(f"[Classify] ⚡ New topic detected → CLEAR CACHE")
            state["cached_property_ids"] = []
            state["accumulated_results"] = {}
            _clear_session_location(session_id)
            return state
    
    # 3. 현재 질문에서 위치 추출
    try:
        from nodes.neo4j_search_node import extract_location
        current_location, location_type = extract_location(question)
    except Exception as e:
        print(f"[Classify] Location extraction failed: {e}")
        current_location = ""
        location_type = ""
    
    print(f"[Classify] Current location: '{current_location}' (type: {location_type})")
    
    # 4. 위치가 감지되면 세션의 기존 위치와 비교
    if current_location:
        cached_location = _get_session_location(session_id)
        print(f"[Classify] Cached location: '{cached_location}'")
        
        if cached_location and cached_location != current_location:
            # 위치가 바뀜 → 캐시 무효화
            print(f"[Classify] ⚡ Location changed: '{cached_location}' → '{current_location}' → CLEAR CACHE")
            state["cached_property_ids"] = []
            state["accumulated_results"] = {}
            state["is_followup"] = False
            _save_session_location(session_id, current_location)
        elif not cached_location:
            # 첫 검색 → 위치 저장
            print(f"[Classify] 📍 First search, saving location: '{current_location}'")
            _save_session_location(session_id, current_location)
        else:
            # 위치가 같음 → 후속 질문 (캐시 유지)
            print(f"[Classify] ✓ Same location, keeping cache ({len(cached_ids)} IDs)")
    
    return state


def classify_intent_with_llm(question: str, history: list) -> bool:
    """
    gpt-5-nano를 사용하여 후속 질문 여부 판단
    
    Args:
        question: 현재 질문
        history: 최근 5개 대화 히스토리 [{"question": ..., "answer": ...}, ...]
    
    Returns:
        True: 이전 대화를 참조하는 후속 질문
        False: 새로운 주제의 질문
    """
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # 히스토리를 간단한 형식으로 변환
        history_text = ""
        for i, turn in enumerate(history[-3:], 1):  # 최근 3개만 사용 (속도 최적화)
            history_text += f"Q{i}: {turn['question'][:100]}\n"
            history_text += f"A{i}: {turn['answer'][:100]}...\n\n"
        
        prompt = f"""최근 대화:
{history_text}

현재 질문: {question}

이 질문이 위 대화의 맥락을 참조하는 후속 질문인지 판단하세요.
후속 질문 예시: "더 싼 거 없어?", "그 중에서 넓은 건?", "첫번째 매물 자세히"
새 질문 예시: "홍대 원룸 추천해줘", "강남역 근처 오피스텔"

답변 형식 (한 단어만):
- 후속질문
- 새질문"""

        response = client.chat.completions.create(
            model="gpt-4.1-nano",  # gpt-5-nano 사용 (중요!)
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0
        )
        
        result = response.choices[0].message.content.strip()
        print(f"[Classify] LLM response: '{result}'")
        
        return "후속" in result or "followup" in result.lower()
        
    except Exception as e:
        print(f"[Classify] LLM classification failed: {e}")
        # 실패 시 규칙 기반 폴백
        return _fallback_intent_detection(question)


def _fallback_intent_detection(question: str) -> bool:
    """LLM 실패 시 규칙 기반 후속 질문 감지"""
    followup_keywords = [
        "더", "그 중", "그중", "저것", "이것", "그거", "첫번째", "두번째",
        "위에", "아래", "방금", "말한", "추천한", "보여준", "싼", "비싼",
        "넓은", "좁은", "가까운", "먼", "좋은", "저렴한"
    ]
    return any(kw in question for kw in followup_keywords)


def _get_session_location(session_id: str) -> str:
    """세션의 저장된 위치 조회"""
    try:
        r = get_redis_client()
        key = f"session_loc:{session_id}"
        return r.get(key) or ""
    except Exception:
        return ""


def _save_session_location(session_id: str, location: str, ttl: int = 86400):
    """세션의 위치 저장 (24시간 유지)"""
    try:
        r = get_redis_client()
        key = f"session_loc:{session_id}"
        r.setex(key, ttl, location)
    except Exception as e:
        print(f"[Classify] Failed to save location: {e}")


def _clear_session_location(session_id: str):
    """세션의 위치 삭제"""
    try:
        r = get_redis_client()
        r.delete(f"session_loc:{session_id}")
    except Exception:
        pass
