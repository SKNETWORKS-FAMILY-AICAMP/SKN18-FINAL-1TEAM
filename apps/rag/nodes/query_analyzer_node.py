"""
Query Analyzer Node - OpenAI 기반 하드/소프트 필터 분석 + 세션 위치 관리

사용자 질문을 분석하여:
1. 하드 필터 추출 (위치, 가격, 건물타입, 시설 등)
2. 소프트 필터 추출 (깨끗한, 럭셔리한 등 - 없을 수 있음)
3. 검색 전략 결정 (neo4j | es_keyword | hybrid)
4. 캐시된 대화와의 관련성 판단 → 관련 있으면 컨텍스트로 활용
5. 세션 위치 저장/비교 (Redis) → 위치 변경 시 캐시 무효화
"""
import os
import json
import time
from typing import Dict, List, Any, Optional
from common.state import RAGState
from common.redis_cache import get_conversation_history, get_redis_client, clear_collected_conditions


def analyze_query(state: RAGState) -> RAGState:
    """
    OpenAI를 사용하여 사용자 질문을 하드/소프트 필터로 분류
    + 캐시된 대화 컨텍스트와의 관련성 판단
    + Redis 세션 위치 저장/비교
    + 멀티턴 조건 수집 인터럽트
    
    Returns:
        state with hard_filters, soft_filters, search_strategy, use_cached_context populated
    """
    question = state.get("question", "")
    session_id = state.get("session_id", "")
    
    if not question:
        return state
    
    print(f"\n{'='*60}")
    print(f"[QueryAnalyzer] 🔍 질문 분석 시작: {question}")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    
    # 기본값 설정
    state["query_type"] = "graph_search"
    state["is_followup"] = False
    state["conversation_complete"] = False
    
    # 이전에 수집된 조건 로드
    collected = state.get("collected_conditions") or {}
    print(f"[QueryAnalyzer] 📦 기존 수집 조건: {list(collected.keys())}")
    
    # 최근 대화 히스토리 로드 (내부적으로 5개 제한됨)
    conversation_history = []
    if session_id:
        conversation_history = get_conversation_history(session_id)
        print(f"[QueryAnalyzer] 📚 대화 히스토리: {len(conversation_history)}개")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # OpenAI로 필터 분석 + 캐시 관련성 판단
        analysis = _analyze_with_openai(client, question, conversation_history)
        
        elapsed = time.time() - start_time
        print(f"[QueryAnalyzer] ⏱️ 분석 완료: {elapsed:.2f}s")
        
        # 상태 업데이트
        state["hard_filters"] = analysis.get("hard_filters", {})
        state["soft_filters"] = analysis.get("soft_filters", [])
        state["search_strategy"] = analysis.get("search_strategy", "hybrid")
        
        # 캐시 관련성 판단 결과
        use_cached_context = analysis.get("use_cached_context", False)
        cached_context_reason = analysis.get("cached_context_reason", "")
        state["use_cache"] = use_cached_context
        state["is_followup"] = use_cached_context
        
        # 현재 위치 추출
        current_location = state["hard_filters"].get("location", "")
        
        # 세션 위치 비교 및 관리
        if session_id and current_location:
            cached_location = _get_session_location(session_id)
            print(f"[QueryAnalyzer] 📍 현재 위치: '{current_location}', 캐시 위치: '{cached_location}'")
            
            if cached_location and cached_location != current_location:
                # 위치가 바뀜 → 캐시 무효화 + collected_conditions 초기화
                print(f"[QueryAnalyzer] ⚡ 위치 변경 감지: '{cached_location}' → '{current_location}' → 전체 초기화")
                state["cached_property_ids"] = []
                state["accumulated_results"] = {}
                state["is_followup"] = False
                state["use_cache"] = False
                # ★★★ collected_conditions도 초기화 ★★★
                collected = {}
                state["collected_conditions"] = {}
                if session_id:
                    clear_collected_conditions(session_id)
            elif not cached_location:
                # 첫 검색 → 위치 저장
                print(f"[QueryAnalyzer] 📍 첫 검색, 위치 저장: '{current_location}'")
            
            # 현재 위치 저장
            _save_session_location(session_id, current_location)
        
        # ★★★ LLM 기반 조건 변경 의도 감지 ★★★
        change_intent = analysis.get("condition_change_intent")
        if change_intent and change_intent != "null":
            print(f"[QueryAnalyzer] 🔄 조건 변경 요청 감지 (LLM): {change_intent}")
            # 해당 조건을 초기화하고 다시 질문
            if change_intent == "deal_type":
                collected.pop("deal_type", None)
                state["collected_conditions"] = collected
            elif change_intent == "location":
                collected.pop("location", None)
                state["collected_conditions"] = collected
            elif change_intent == "style":
                collected.pop("style", None)
                state["collected_conditions"] = collected
        
        # 로그 출력
        print(f"[QueryAnalyzer] 📋 하드 필터: {json.dumps(state['hard_filters'], ensure_ascii=False)}")
        print(f"[QueryAnalyzer] 🎨 소프트 필터: {state['soft_filters']}")
        print(f"[QueryAnalyzer] 🎯 검색 전략: {state['search_strategy']}")
        print(f"[QueryAnalyzer] 💾 후속 질문: {state['is_followup']}")
        
        # 가격 조건을 price_conditions에도 동기화 (기존 호환성)
        _sync_price_conditions(state)
        
        # =====================================================================
        # 멀티턴 조건 수집: 기존 조건과 병합 + 누락 체크
        # =====================================================================
        merged_conditions = _merge_conditions(collected, state["hard_filters"], state["soft_filters"])
        
        # ★ 스타일 폴백: 스타일 질문 상태에서 OpenAI가 스타일 추출 실패 시
        # 사용자 응답 전체를 스타일로 사용 (위치+거래유형은 있는데 스타일만 없을 때)
        if (collected.get("location") and collected.get("deal_type") 
            and not merged_conditions.get("style") 
            and not state["soft_filters"]
            and question.strip()):
            # 사용자 응답을 스타일로 처리
            user_style = question.strip()
            merged_conditions["style"] = [user_style]
            print(f"[QueryAnalyzer] 🔄 스타일 폴백: 사용자 응답 '{user_style}'를 스타일로 사용")
        
        state["collected_conditions"] = merged_conditions
        
        # 필수 조건 누락 체크
        missing = _check_missing_conditions(merged_conditions)
        state["missing_conditions"] = missing
        
        if missing:
            # 인터럽트: 첫 번째 누락 조건에 대한 질문 생성
            pending_q = _generate_followup_question(missing[0], merged_conditions)
            state["pending_question"] = pending_q
            state["conversation_complete"] = False
            print(f"[QueryAnalyzer] ❓ 누락 조건: {missing} → 인터럽트 질문 생성")
        else:
            state["pending_question"] = None
            state["conversation_complete"] = True
            print(f"[QueryAnalyzer] ✅ 모든 조건 수집 완료 → 검색 실행")
            
            # ★★★ 핵심: 수집된 조건을 hard_filters/soft_filters에 동기화 ★★★
            # 멀티턴에서 수집된 조건이 실제 검색에 반영되도록 함
            _sync_collected_to_filters(state, merged_conditions)
        
    except Exception as e:
        print(f"[QueryAnalyzer] ❌ OpenAI 분석 실패: {e}, 규칙 기반 폴백 사용")
        _fallback_analysis(state, question)
        
        # 폴백에서도 조건 체크
        merged_conditions = _merge_conditions(collected, state.get("hard_filters", {}), state.get("soft_filters", []))
        state["collected_conditions"] = merged_conditions
        missing = _check_missing_conditions(merged_conditions)
        state["missing_conditions"] = missing
        
        if missing:
            state["pending_question"] = _generate_followup_question(missing[0], merged_conditions)
            state["conversation_complete"] = False
        else:
            state["pending_question"] = None
            state["conversation_complete"] = True
            # 폴백에서도 수집된 조건 동기화
            _sync_collected_to_filters(state, merged_conditions)
    
    return state


# =============================================================================
# Redis 세션 위치 관리
# =============================================================================

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
        print(f"[QueryAnalyzer] 위치 저장 실패: {e}")


def _clear_session_location(session_id: str):
    """세션의 위치 삭제"""
    try:
        r = get_redis_client()
        r.delete(f"session_loc:{session_id}")
    except Exception:
        pass




def _analyze_with_openai(client, question: str, history: List[Dict] = None) -> Dict[str, Any]:
    """OpenAI API를 사용하여 질문 분석 + 검색 전략 결정"""
    
    # 대화 히스토리 포맷팅
    history_text = ""
    if history and len(history) > 0:
        history_text = "\n\n이전 대화 (최근 5개):\n"
        for i, turn in enumerate(history[-5:], 1):
            q = turn.get('question', '')[:80]
            a = turn.get('answer', '')[:100]
            history_text += f"Q{i}: {q}\nA{i}: {a}...\n"
    
    prompt = f"""사용자의 부동산 검색 질문을 분석하여 JSON 형식으로 반환하세요.
{history_text}
현재 질문: "{question}"

다음 형식으로 JSON만 반환하세요 (다른 텍스트 없이):
{{
    "hard_filters": {{
        "location": "지하철역 또는 지역명 (없으면 빈 문자열)",
        "deal_type": "월세|전세|매매|단기임대 (없으면 빈 문자열)",
        "building_type": "원룸|투룸|오피스텔|아파트|빌라 (없으면 빈 문자열)",
        "max_deposit": 보증금 상한 만원 단위 숫자 (없으면 null),
        "min_deposit": 보증금 하한 만원 단위 숫자 (없으면 null),
        "max_rent": 월세 상한 만원 단위 숫자 (없으면 null),
        "max_size": 평수 상한 숫자 (없으면 null),
        "max_distance": 역까지 도보 분 숫자 (없으면 null),
        "facilities": ["subway", "convenience", "safety", "hospital", "park", "university"] 중 필요한 것들
    }},
    "soft_filters": ["사용자가 원하는 스타일/분위기/선호도 키워드 - 정확한 태그명이 아니어도 됨 (예: 햇살좋은, 밝은, 아늑한, 조용한, 깔끔한, 넓은 등), 없으면 빈 배열"],
    "search_strategy": "neo4j_only|keyword_only|neo4j_keyword|keyword_vector|full",
    "use_cached_context": true 또는 false,
    "cached_context_reason": "관련성 판단 이유 (한 줄)",
    "condition_change_intent": "location|deal_type|style|null (사용자가 이미 설정한 조건을 변경하려는 의도가 있으면 해당 조건명, 없으면 null)"
}}

검색 전략 결정 규칙:
- "neo4j_only": 위치 + 시설(치안, 편의점, 공원 등)만 있고 가격/타입 없음
- "keyword_only": 가격 + 건물타입 + 거래타입만 있고 위치/시설 없음
- "neo4j_keyword": 위치/시설 + 가격/타입 모두 있음 (가장 일반적)
- "keyword_vector": 가격/타입 + 소프트 필터(깨끗한, 럭셔리한 등) 있음
- "full": 위치/시설 + 가격/타입 + 소프트 필터 모두 있음

캐시 관련성 판단 규칙:
- use_cached_context = true: 이전 대화의 후속 질문 (예: "더 싼 거", "그 중에서")
- use_cached_context = false: 새로운 위치/조건 언급
- 이전 대화가 없으면 항상 false

조건 변경 의도 감지 규칙:
- 사용자가 "아니 월세 말고 전세", "전세로 바꿔줘", "다른 지역으로" 등 이미 설정된 조건을 변경하려는 표현을 사용하면 해당 조건 타입 반환
- "location": 위치 변경 요청 (예: "다른 지역으로", "강남 말고 홍대로")
- "deal_type": 거래 유형 변경 요청 (예: "월세 말고 전세", "전세로 바꿔줘", "아니 매매로")
- "style": 스타일 조건 변경 요청 (예: "다른 스타일로", "조건 바꿔")
- 변경 의도가 없으면 null"""

    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
        temperature=0
    )
    
    result_text = response.choices[0].message.content.strip()
    
    # JSON 파싱 (```json``` 블록 제거)
    if result_text.startswith("```"):
        result_text = result_text.split("```")[1]
        if result_text.startswith("json"):
            result_text = result_text[4:]
    
    result = json.loads(result_text)
    return result


def _fallback_analysis(state: RAGState, question: str) -> None:
    """OpenAI 실패 시 규칙 기반 분석"""
    import re
    
    hard_filters: Dict[str, Any] = {
        "location": "",
        "deal_type": "",
        "building_type": "",
        "max_deposit": None,
        "max_rent": None,
        "facilities": []
    }
    soft_filters: List[str] = []
    
    # 위치 추출 (기존 neo4j_search_node 패턴 재사용)
    location_pattern = r"(홍대|강남|신촌|이태원|잠실|여의도|명동|역삼|선릉|삼성|건대|왕십리|성수|합정|망원|연남|마포|용산|영등포|구로|노원|송파|동작|서초|강서|양천|은평|독산|금천|시흥|가산)"
    location_match = re.search(location_pattern, question)
    if location_match:
        hard_filters["location"] = location_match.group(1)
    
    # 역 패턴 추출
    station_pattern = r"(\w+역)"
    station_match = re.search(station_pattern, question)
    if station_match and not hard_filters["location"]:
        hard_filters["location"] = station_match.group(1).replace("역", "")
    
    # 거래 타입
    if "월세" in question:
        hard_filters["deal_type"] = "월세"
    elif "전세" in question:
        hard_filters["deal_type"] = "전세"
    elif "매매" in question or "매물" in question:
        hard_filters["deal_type"] = "매매"
    
    # 건물 타입
    if "원룸" in question:
        hard_filters["building_type"] = "원룸"
    elif "투룸" in question or "2룸" in question:
        hard_filters["building_type"] = "투룸"
    elif "오피스텔" in question:
        hard_filters["building_type"] = "오피스텔"
    elif "아파트" in question:
        hard_filters["building_type"] = "아파트"
    elif "빌라" in question:
        hard_filters["building_type"] = "빌라"
    
    # 가격 추출
    deposit_pattern = r"보증금\s*(\d+)"
    deposit_match = re.search(deposit_pattern, question)
    if deposit_match:
        hard_filters["max_deposit"] = int(deposit_match.group(1))
    
    rent_pattern = r"월세\s*(\d+)"
    rent_match = re.search(rent_pattern, question)
    if rent_match:
        hard_filters["max_rent"] = int(rent_match.group(1))
    
    # 시설 키워드
    facility_keywords = {
        "subway": ["역세권", "지하철", "역 ", "역근처"],
        "convenience": ["편의점", "편세권", "마트"],
        "safety": ["치안", "안전", "cctv", "경찰"],
        "hospital": ["병원", "의원", "약국"],
        "park": ["공원", "산책", "녹지"],
        "university": ["대학", "학교", "캠퍼스"]
    }
    
    for facility, keywords in facility_keywords.items():
        if any(kw in question.lower() for kw in keywords):
            hard_filters["facilities"].append(facility)
    
    # 소프트 필터 추출
    soft_keywords = ["깨끗", "럭셔리", "가성비", "조용", "채광", "신축", "넓은", "아늑", "예쁜", "모던", "깔끔"]
    for kw in soft_keywords:
        if kw in question:
            soft_filters.append(kw)
    
    # 검색 전략 결정 (새 전략 체계)
    has_location = bool(hard_filters["location"]) or bool(hard_filters["facilities"])
    has_price_type = bool(hard_filters["deal_type"]) or bool(hard_filters["max_deposit"]) or bool(hard_filters["max_rent"])
    has_soft = bool(soft_filters)
    
    if has_location and has_price_type and has_soft:
        search_strategy = "full"
    elif has_location and has_price_type:
        search_strategy = "neo4j_keyword"
    elif has_price_type and has_soft:
        search_strategy = "keyword_vector"
    elif has_location:
        search_strategy = "neo4j_only"
    elif has_price_type:
        search_strategy = "keyword_only"
    else:
        search_strategy = "neo4j_keyword"  # 기본값
    
    state["hard_filters"] = hard_filters
    state["soft_filters"] = soft_filters
    state["search_strategy"] = search_strategy


def _sync_price_conditions(state: RAGState) -> None:
    """하드 필터의 가격 조건을 price_conditions에 동기화 (기존 호환성 유지)"""
    hard_filters = state.get("hard_filters", {})
    price_conditions = state.get("price_conditions", {}) or {}
    
    if hard_filters.get("max_deposit"):
        price_conditions["deposit_max"] = hard_filters["max_deposit"]
    if hard_filters.get("min_deposit"):
        price_conditions["deposit_min"] = hard_filters["min_deposit"]
    if hard_filters.get("max_rent"):
        price_conditions["rent_max"] = hard_filters["max_rent"]
    
    if price_conditions:
        state["price_conditions"] = price_conditions


# 단축 함수 (그래프 노드용)
def analyze(state: RAGState) -> RAGState:
    """그래프 노드 진입점"""
    return analyze_query(state)


# =============================================================================
# 멀티턴 조건 수집 헬퍼 함수
# =============================================================================

# 지원하는 거래 유형
DEAL_TYPES = ["전세", "월세", "매매", "단기임대"]

# 지원하는 스타일 태그 (34개)
STYLE_TAGS = [
    "깔끔함", "세련됨", "아늑함", "모던함", "럭셔리함", "탁트인전망", "화이트톤인테리어",
    "실용적임", "풀옵션", "채광좋음", "조용함", "넓은공간", "수납공간많음", "복층구조", "테라스있음",
    "1인가구추천", "신혼부부추천", "직장인추천", "학생추천", "재택근무추천",
    "신축", "가성비좋음", "반려동물가능", "주차가능", "보안좋음", "엘리베이터있음", "분리형원룸",
    "에어컨있음", "세탁기있음", "냉장고있음", "인덕션있음", "고층", "저층", "남향"
]


def _merge_conditions(existing: Dict, hard_filters: Dict, soft_filters: List[str]) -> Dict:
    """
    기존 수집 조건과 새 분석 결과를 병합
    
    병합 규칙:
    - 새 값이 있으면 기존 값을 덮어씀 (위치 변경 등)
    - soft_filters는 리스트에 추가
    """
    merged = existing.copy() if existing else {}
    
    # 위치 조건 병합
    new_location = hard_filters.get("location", "")
    if new_location:
        merged["location"] = new_location
    
    # 거래 유형 병합
    new_deal_type = hard_filters.get("deal_type", "")
    if new_deal_type:
        merged["deal_type"] = new_deal_type
    
    # 스타일/소프트 필터 병합 (기존 + 새로운)
    existing_styles = merged.get("style", [])
    if isinstance(existing_styles, str):
        existing_styles = [existing_styles] if existing_styles else []
    new_styles = soft_filters or []
    combined_styles = list(set(existing_styles + new_styles))
    if combined_styles:
        merged["style"] = combined_styles
    
    # 가격 정보 병합
    price_info = merged.get("price_info", {})
    if hard_filters.get("max_deposit"):
        price_info["max_deposit"] = hard_filters["max_deposit"]
    if hard_filters.get("min_deposit"):
        price_info["min_deposit"] = hard_filters["min_deposit"]
    if hard_filters.get("max_rent"):
        price_info["max_rent"] = hard_filters["max_rent"]
    if price_info:
        merged["price_info"] = price_info
    
    # 건물 타입 병합
    if hard_filters.get("building_type"):
        merged["building_type"] = hard_filters["building_type"]
    
    # 시설 병합
    if hard_filters.get("facilities"):
        existing_facilities = merged.get("facilities", [])
        merged["facilities"] = list(set(existing_facilities + hard_filters["facilities"]))
    
    return merged


def _check_missing_conditions(conditions: Dict) -> List[str]:
    """
    필수 조건 누락 체크
    
    필수 조건 (모두 충족해야 검색 실행):
    1. location: 위치 조건 (구/동/역/시설 기반)
    2. deal_type: 거래 유형 (전세/월세/매매/단기임대)
    3. style: 스타일/옵션 조건
    
    Returns:
        누락된 조건 목록 (순서대로 질문)
    """
    missing = []
    
    # 1. 위치 조건 체크
    has_location = bool(conditions.get("location")) or bool(conditions.get("facilities"))
    if not has_location:
        missing.append("location")
    
    # 2. 거래 유형 체크
    if not conditions.get("deal_type"):
        missing.append("deal_type")
    
    # 3. 스타일/옵션 체크
    if not conditions.get("style"):
        missing.append("style")
    
    return missing


def _generate_followup_question(missing_type: str, current_conditions: Dict) -> str:
    """
    누락된 조건에 대한 자연스러운 후속 질문 생성
    
    Args:
        missing_type: "location" | "deal_type" | "style"
        current_conditions: 현재까지 수집된 조건 (컨텍스트용)
    
    Returns:
        사용자에게 보낼 질문 문자열
    """
    # 현재 수집된 조건 컨텍스트
    location = current_conditions.get("location", "")
    deal_type = current_conditions.get("deal_type", "")
    
    if missing_type == "location":
        return (
            "어떤 지역에서 집을 찾고 계신가요? 🏠\n\n"
            "**지하철역** 홍대역, 강남역, 신촌역\n"
            "**행정구역** 마포구, 강남구, 서초구\n"
            "**동 단위** 합정동, 역삼동\n"
            "**주변 시설** 편의점 많은 곳, 공원 가까운 곳\n\n"
            "💡 원하는 지역을 자유롭게 말씀해주세요!"
        )
    
    elif missing_type == "deal_type":
        location_str = f"**{location}**에서 " if location else ""
        return (
            f"{location_str}어떤 거래 유형을 원하시나요? 📝\n\n"
            "**전세** 목돈을 맡기고 월세 없이 거주\n"
            "**월세** 보증금 + 매달 월세 지불\n"
            "**매매** 집을 직접 구매\n"
            "**단기임대** 몇 개월 단위 임시 거주"
        )
    
    elif missing_type == "style":
        context_parts = []
        if location:
            context_parts.append(f"**{location}**")
        if deal_type:
            context_parts.append(f"**{deal_type}**")
        context_str = " ".join(context_parts) + " 조건으로 " if context_parts else ""
        
        return (
            f"{context_str}어떤 스타일의 집을 원하시나요? ✨\n\n"
            "🎨 **자유롭게 원하는 분위기나 조건을 말씀해주세요!**\n\n"
            "예시)\n"
            "• 햇살 잘 들어오는 집\n"
            "• 깔끔하고 모던한 인테리어\n"
            "• 에어컨, 세탁기 있는 풀옵션\n"
            "• 조용하고 보안 좋은 곳\n"
            "• 직장인한테 추천할만한 곳\n\n"
            "💡 위 예시 외에도 원하는 조건을 자유롭게 입력하세요!"
        )
    
    # 기본 폴백
    return "추가 조건을 알려주세요!"


def _sync_collected_to_filters(state: RAGState, collected: Dict) -> None:
    """
    ★★★ 핵심 함수 ★★★
    멀티턴에서 수집된 조건을 hard_filters/soft_filters에 동기화
    
    이 함수가 없으면 멀티턴에서 수집한 location, deal_type이 
    실제 검색에 반영되지 않음!
    """
    hard_filters = state.get("hard_filters", {}) or {}
    soft_filters = state.get("soft_filters", []) or []
    
    # 1. 위치 동기화 (가장 중요!)
    if collected.get("location") and not hard_filters.get("location"):
        hard_filters["location"] = collected["location"]
        print(f"[Sync] 📍 위치 동기화: {collected['location']}")
    
    # 2. 거래 유형 동기화
    if collected.get("deal_type") and not hard_filters.get("deal_type"):
        hard_filters["deal_type"] = collected["deal_type"]
        print(f"[Sync] 🏠 거래유형 동기화: {collected['deal_type']}")
    
    # 3. 건물 타입 동기화
    if collected.get("building_type") and not hard_filters.get("building_type"):
        hard_filters["building_type"] = collected["building_type"]
    
    # 4. 가격 정보 동기화
    if collected.get("price_info"):
        price_info = collected["price_info"]
        if price_info.get("max_deposit") and not hard_filters.get("max_deposit"):
            hard_filters["max_deposit"] = price_info["max_deposit"]
        if price_info.get("max_rent") and not hard_filters.get("max_rent"):
            hard_filters["max_rent"] = price_info["max_rent"]
    
    # 5. 시설 동기화
    if collected.get("facilities") and not hard_filters.get("facilities"):
        hard_filters["facilities"] = collected["facilities"]
    
    # 6. 스타일 동기화
    if collected.get("style"):
        collected_styles = collected["style"]
        if isinstance(collected_styles, str):
            collected_styles = [collected_styles]
        # 기존 soft_filters에 추가
        for s in collected_styles:
            if s and s not in soft_filters:
                soft_filters.append(s)
        print(f"[Sync] ✨ 스타일 동기화: {collected_styles}")
    
    # state 업데이트
    state["hard_filters"] = hard_filters
    state["soft_filters"] = soft_filters
    
    print(f"[Sync] ✅ 최종 hard_filters: {hard_filters}")
    print(f"[Sync] ✅ 최종 soft_filters: {soft_filters}")






