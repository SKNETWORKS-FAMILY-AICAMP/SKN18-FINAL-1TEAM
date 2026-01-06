import os
import re
from typing import List, Dict
from langchain_community.graphs import Neo4jGraph
from common.state import RAGState

# =============================================================================
# Neo4j 연결 (Lazy Loading)
# =============================================================================
_graph = None

def get_graph():
    global _graph
    if _graph is None:
        _graph = Neo4jGraph(
            url=os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
            username=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password")
        )
    return _graph


# =============================================================================
# 규칙 기반 쿼리 빌더 (Rule-Based Query Builder)
# =============================================================================
# LLM 없이 사용자 질문을 분석하여 동적으로 Cypher 쿼리를 생성합니다.
# 성능: 17,000ms (LLM Agent) → 150ms (규칙 기반)

# -----------------------------------------------------------------------------
# 1. 상수 및 키워드 사전 (Constants & Keyword Dictionaries)
# -----------------------------------------------------------------------------

# 스코어링 상수
SCORE_MAX_DISTANCE = 5000       # 최대 거리 점수 기준 (m)
SCORE_SUBWAY_BONUS = 500        # 지하철역 우선 보너스
SCORE_SAFETY_MULTIPLIER = 100   # 안전시설 개당 점수

# 시설 타입별 키워드 매핑
FACILITY_KEYWORDS = {
    "safety": ["안전", "치안", "cctv", "경찰", "소방", "비상벨", "안심", "범죄", 
               "보안", "안전한", "치안 좋은", "안심귀가"],
    "convenience": ["편의점", "마트", "gs25", "cu", "세븐일레븐", "이마트24",
                    "편세권", "슬세권", "미니스톱", "씨유"],
    "hospital": ["병원", "의원", "의료", "클리닉", "진료소"],
    "general_hospital": ["종합병원", "대학병원", "대형병원", "상급병원"],
    "pharmacy": ["약국", "약방"],
    "park": ["공원", "산책", "녹지", "운동", "조깅", "숲"],
    "university": ["대학교", "대학", "캠퍼스", "학교", "학세권"],
    "subway": ["역", "지하철", "전철", "교통", "역세권", "메트로"]
}

# 시설 타입 → Neo4j 관계/라벨 매핑
FACILITY_CONFIG = {
    "subway": {
        "relationship": "NEAR_SUBWAY",
        "label": "SubwayStation",
        "result_key": "trans_details"
    },
    "hospital": {
        "relationship": "NEAR_HOSPITAL|NEAR_GENERAL_HOSPITAL",
        "label": "Hospital",
        "result_key": "med_details"
    },
    "general_hospital": {
        "relationship": "NEAR_GENERAL_HOSPITAL",
        "label": "GeneralHospital",
        "result_key": "gen_hosp_details"
    },
    "pharmacy": {
        "relationship": "NEAR_PHARMACY",
        "label": "Pharmacy",
        "result_key": "pharmacy_details"
    },
    "convenience": {
        "relationship": "NEAR_CONVENIENCE",
        "label": "Convenience",
        "result_key": "conv_details"
    },
    "park": {
        "relationship": "NEAR_PARK",
        "label": "Park",
        "result_key": "park_details"
    },
    "university": {
        "relationship": "NEAR_COLLEGE",
        "label": "College",
        "result_key": "edu_details"
    },
    "safety": {
        "relationship": "NEAR_CCTV|NEAR_BELL|NEAR_POLICE|NEAR_FIRE",
        "label": "Safety",
        "result_key": "safety_details"
    }
}

# 시설 타입 → 온도 Metric 매핑 (온도 기반 검색용)
FACILITY_TO_TEMPERATURE = {
    "safety": "Safety",              # 안전, 치안, CCTV
    "convenience": "LivingConvenience",  # 편의점, 마트, 세탁소
    "hospital": "LivingConvenience",     # 병원, 약국
    "pharmacy": "LivingConvenience",     # 약국
    "subway": "Traffic",             # 지하철, 교통
    "park": "Culture",               # 공원, 산책
    "university": "Culture",         # 대학교
}

# 주요 지하철역/지역명 패턴 (서울 전 노선 커버)
LOCATION_PATTERNS = [
    # 지하철역 (역 접미사 포함) - 서울 1~9호선 전체
    # 1호선 (서울역~청량리, 경인선 일부)
    r"(서울역|시청|종각|종로3가|종로5가|동대문|동묘앞|신설동|제기동|청량리|"
    # 2호선 (순환선 + 지선)
    r"을지로입구|을지로3가|을지로4가|동대문역사문화공원|신당|상왕십리|왕십리|한양대|뚝섬|성수|"
    r"건대입구|강변|잠실나루|잠실|잠실새내|종합운동장|삼성|선릉|역삼|강남|교대|서초|방배|사당|"
    r"낙성대|서울대입구|봉천|신림|신대방|구로디지털단지|대림|신도림|문래|영등포구청|당산|합정|"
    r"홍대입구|신촌|이대|아현|충정로|용답|신답|용두|도림천|양천구청|신정네거리|까치산|"
    # 3호선
    r"지축|구파발|연신내|불광|녹번|홍제|무악재|독립문|경복궁|안국|충무로|동대입구|"
    r"약수|금호|옥수|압구정|신사|잠원|고속터미널|남부터미널|양재|매봉|도곡|대치|학여울|대청|일원|수서|가락시장|경찰병원|오금|"
    # 4호선
    r"당고개|상계|노원|창동|쌍문|수유|미아|미아사거리|길음|성신여대입구|한성대입구|혜화|"
    r"명동|회현|숙대입구|삼각지|신용산|이촌|동작|이수|남태령|"
    # 5호선
    r"방화|개화산|김포공항|송정|마곡|발산|우장산|화곡|신정|목동|오목교|영등포시장|신길|여의도|"
    r"여의나루|마포|공덕|애오개|서대문|광화문|청구|신금호|행당|마장|답십리|장한평|군자|아차산|광나루|천호|강동|"
    r"둔촌동|올림픽공원|길동|굽은다리|명일|고덕|상일동|방이|개롱|거여|마천|"
    # 6호선
    r"응암|역촌|독바위|구산|새절|증산|디지털미디어시티|월드컵경기장|마포구청|망원|상수|광흥창|대흥|"
    r"효창공원앞|녹사평|이태원|한강진|버티고개|창신|보문|안암|고려대|종암|월곡|상월곡|돌곶이|석계|태릉입구|화랑대|봉화산|신내|"
    # 7호선
    r"장암|도봉산|수락산|마들|중계|하계|공릉|먹골|중화|상봉|면목|사가정|용마산|중곡|어린이대공원|뚝섬유원지|청담|강남구청|학동|논현|반포|"
    r"내방|남성|숭실대입구|상도|장승배기|신대방삼거리|보라매|신풍|남구로|가산디지털단지|철산|광명사거리|천왕|온수|까치울|"
    # 8호선
    r"암사|강동구청|몽촌토성|석촌|송파|문정|장지|복정|"
    # 9호선
    r"개화|공항시장|신방화|마곡나루|양천향교|가양|증미|등촌|염창|신목동|선유도|국회의사당|샛강|노량진|노들|흑석|"
    r"구반포|신반포|사평|신논현|언주|선정릉|삼성중앙|봉은사|삼전|석촌고분|송파나루|한성백제|둔촌오륜|중앙보훈병원|"
    # 기타 주요역/지역명 (신분당선, 경의중앙선 일부 등)
    r"양재시민의숲|청계산입구|판교|정자|"
    r"구로|영등포|용산|금천|독산|금천구청|가산|"
    r"대학로|압구정로데오|연남|돈암)(?:역)?",

    # 대학교
    r"(서울대|연세대|고려대|이화여대|홍익대|건국대|한양대|성균관대|중앙대|경희대|"
    r"서강대|숙명여대|동국대|국민대|세종대|한국외대|시립대|광운대|상명대|덕성여대|"
    r"숭실대|가톨릭대|서울여대|한성대|삼육대|명지대|"
    r"서울과기대|서울시립대|단국대|인하대|숭의여대|총신대|KC대|감리교신학대|"
    r"서울교대|한예종|서울예대|추계예대)(?:학교)?(?:교)?",
    # 일반 지역명
    r"(신촌|홍대|이태원|강남|잠실|여의도|명동|종로|동대문|성수|"
    r"마포|용산|영등포|구로|노원|송파|강동|관악|동작|서초|강서|양천|은평|"
    r"도봉|강북|중랑|성북|광진|금천|구로디지털단지|"
    r"목동|화곡|방화|개화|발산|등촌|마곡|상암|연희|연남동|"
    r"청량리|회기|중화|상봉|망우|태릉입구|공릉|하계|중계|"
    r"문정|가락|거여|마천|방이|오금|개롱|"
    r"회현|남대문|후암|청파|원효로|한남|보광동|이태원동|독산동|시흥동|가산동)"
]



# -----------------------------------------------------------------------------
# 2. 질문 분석 함수 (Question Analysis Functions)
# -----------------------------------------------------------------------------

# 대학교 이름 패턴 (별도 정의 - 우선 매칭용)
UNIVERSITY_PATTERN = (
    r"(서울대|연세대|고려대|이화여대|홍익대|건국대|한양대|성균관대|중앙대|경희대|"
    r"서강대|숙명여대|동국대|국민대|세종대|한국외대|시립대|광운대|상명대|덕성여대|"
    r"숭실대|가톨릭대|서울여대|한성대|삼육대|명지대|"
    r"서울과기대|서울시립대|단국대|인하대|숭의여대|총신대|KC대|감리교신학대|"
    r"서울교대|한예종|서울예대|추계예대)(?:학교)?(?:교)?(?:근처|주변|앞)?"
)

# 대학교 의도 키워드
UNIVERSITY_INTENT_KEYWORDS = ["대학", "학교", "캠퍼스", "학세권", "대학교"]


def extract_location(question: str) -> tuple:
    """
    질문에서 위치 정보 추출 (정규식 기반)
    
    Returns:
        (location: str, location_type: str)
        location_type: 'university', 'subway', 'region', ''
    """
    # 1. 대학교 의도가 있는지 먼저 확인
    has_university_intent = any(kw in question for kw in UNIVERSITY_INTENT_KEYWORDS)
    
    # 2. 대학교 의도가 있으면 대학교 패턴 먼저 검사
    if has_university_intent:
        match = re.search(UNIVERSITY_PATTERN, question)
        if match:
            location = match.group(1)
            print(f"[QueryBuilder] 📍 Location: {location} (university, intent detected)")
            return location, "university"
    
    # 3. 대학교 패턴에서 정확히 매칭되는지 확인 (대학, 학교 접미사 포함된 경우)
    uni_match = re.search(UNIVERSITY_PATTERN + r"(?=\s|$|근처|주변|앞|역)", question)
    if uni_match:
        location = uni_match.group(1)
        print(f"[QueryBuilder] 📍 Location: {location} (university, exact match)")
        return location, "university"
    
    # 4. 일반 패턴 순서대로 검사
    for i, pattern in enumerate(LOCATION_PATTERNS):
        match = re.search(pattern, question)
        if match:
            location = match.group(1)
            # 패턴 인덱스로 타입 결정: 0=지하철, 1=대학교, 2=지역
            if i == 0:
                loc_type = "subway"
            elif i == 1:
                loc_type = "university"
            else:
                loc_type = "region"
            print(f"[QueryBuilder] 📍 Location: {location} ({loc_type})")
            return location, loc_type
    
    print("[QueryBuilder] ⚠️ No location found")
    return "", ""


def detect_facilities(question: str) -> Dict[str, bool]:
    """질문에서 요청된 시설 타입들 감지 (키워드 매칭)"""
    q = question.lower()
    detected = {}
    
    for facility, keywords in FACILITY_KEYWORDS.items():
        detected[facility] = any(kw in q for kw in keywords)
    
    return detected


def analyze_question(question: str) -> Dict:
    """
    질문 분석 - 위치와 시설 타입을 추출
    
    Returns:
        {
            'location': str,           # 추출된 위치
            'location_type': str,      # 'university', 'subway', 'region', ''
            'facilities': List[str],   # 감지된 시설 타입들
            'search_type': str         # 'single', 'multi', 'default'
        }
    """
    location, location_type = extract_location(question)
    facilities_dict = detect_facilities(question)
    active_facilities = [f for f, active in facilities_dict.items() if active]
    
    # 대학교 위치인 경우 university 시설로 강제 추가 (학교 근처 검색 최적화)
    if location_type == "university" and "university" not in active_facilities:
        facilities_dict["university"] = True
        active_facilities.append("university")
        print(f"[QueryBuilder] 🎓 Added 'university' facility for location_type=university")
    
    # 검색 타입 결정
    if len(active_facilities) >= 2:
        search_type = "multi"
    elif len(active_facilities) == 1:
        search_type = "single"
    else:
        search_type = "default"  # 지하철역 기본 검색
    
    print(f"[QueryBuilder] 🏷️ Facilities: {active_facilities}, Type: {search_type}")
    
    return {
        'location': location,
        'location_type': location_type,
        'facilities': active_facilities,
        'facilities_dict': facilities_dict,
        'search_type': search_type
    }



# -----------------------------------------------------------------------------
# 3. 동적 Cypher 쿼리 빌더 (Dynamic Cypher Query Builder)
# -----------------------------------------------------------------------------

def build_single_facility_query(facility_type: str) -> str:
    """단일 시설 타입에 대한 Cypher 쿼리 생성 (온도 기반 우선)"""
    
    # 온도 기반 검색 우선 사용
    temp_metric = FACILITY_TO_TEMPERATURE.get(facility_type)
    if temp_metric:
        print(f"[QueryBuilder] 🌡️ Using temperature-based search: {temp_metric}")
        return build_temperature_query(temp_metric)
    
    # 온도 매핑이 없는 경우 기존 방식 사용 (fallback)
    config = FACILITY_CONFIG.get(facility_type)
    if not config:
        return build_subway_query()  # 기본값
    
    if facility_type == "subway":
        return build_subway_query()
    elif facility_type == "university":
        return build_university_query()
    else:
        return build_facility_query(
            relationship=config["relationship"],
            label=config["label"],
            result_key=config["result_key"]
        )


def build_temperature_query(temp_metric: str) -> str:
    """
    온도 기반 검색 Cypher 쿼리 (TEXT INDEX 최적화)
    
    사전 계산된 온도 점수로 매물을 정렬합니다.
    - Safety: 안전 온도 (CCTV, 범죄율, 경찰서 등 종합)
    - Traffic: 교통 온도 (지하철, 버스 접근성)
    - LivingConvenience: 생활편의 온도 (편의점, 마트, 세탁소)
    - Culture: 문화 온도 (공원, 영화관, 도서관)
    - Pet: 반려동물 온도 (동물병원, 펫샵, 놀이터)
    """
    return f"""
    // 1. 위치 앵커 찾기 (TEXT INDEX 최적화: UNION으로 라벨별 분리)
    CALL {{
        MATCH (a:SubwayStation) WHERE a.name STARTS WITH $keyword OR a.name CONTAINS $keyword
        RETURN a as anchor LIMIT 3
        UNION ALL
        MATCH (a:College) WHERE a.name STARTS WITH $keyword OR a.name CONTAINS $keyword
        RETURN a as anchor LIMIT 3
        UNION ALL
        MATCH (a:Park) WHERE a.name STARTS WITH $keyword OR a.name CONTAINS $keyword
        RETURN a as anchor LIMIT 3
    }}
    WITH anchor LIMIT 5
    
    // 2. 앵커 근처 매물 조회
    MATCH (p:Property)-[r_anchor]-(anchor)
    WHERE type(r_anchor) STARTS WITH 'NEAR_'
    WITH DISTINCT p, anchor, r_anchor
    
    // 3. 온도 점수 조회 (핵심!)
    MATCH (p)-[r_temp:HAS_TEMPERATURE]->(m:Metric {{name: '{temp_metric}'}})
    
    // 4. 온도로 정렬
    WITH p, anchor, r_anchor, r_temp.temperature as temperature
    ORDER BY temperature DESC
    LIMIT 50
    
    // 5. 가장 가까운 지하철역 정보
    OPTIONAL MATCH (p)-[r_sub:NEAR_SUBWAY]->(sub:SubwayStation)
    WITH p, temperature, anchor, r_anchor, sub, r_sub
    ORDER BY CASE WHEN r_sub IS NULL THEN 9999 ELSE r_sub.distance END
    WITH p, temperature, anchor, r_anchor, 
         head(collect(sub)) as closest_sub, 
         head(collect(r_sub)) as closest_r_sub
    
    RETURN p.id as id,
           temperature,
           temperature as total_score,
           [{{name: anchor.name, dist: toInteger(r_anchor.distance)}}] as poi_details,
           CASE WHEN closest_sub IS NOT NULL 
               THEN [{{name: closest_sub.name, dist: toInteger(closest_r_sub.distance), time: toInteger(closest_r_sub.walking_time)}}]
               ELSE [] 
           END as trans_details
    """


def build_subway_query() -> str:
    """지하철역 검색 Cypher 쿼리 (TEXT INDEX 활용)"""
    return f"""
    MATCH (s:SubwayStation)
    WHERE s.name STARTS WITH $keyword OR s.name CONTAINS $keyword
    WITH s LIMIT 5
    
    MATCH (p:Property)-[r:NEAR_SUBWAY]->(s)
    WITH p, s, r ORDER BY r.distance LIMIT 100
    
    WITH p, s, r, ({SCORE_MAX_DISTANCE} - coalesce(toInteger(r.distance), {SCORE_MAX_DISTANCE})) as total_score
    RETURN p.id as id, total_score,
           collect({{name: s.name, dist: coalesce(toInteger(r.distance), 9999), time: coalesce(toInteger(r.walking_time), 9999)}}) as poi_details
    ORDER BY total_score DESC LIMIT 50
    """


def build_university_query() -> str:
    """대학교 검색 Cypher 쿼리 (TEXT INDEX 활용)"""
    return f"""
    MATCH (anchor:College)
    WHERE anchor.name STARTS WITH $keyword OR anchor.name CONTAINS $keyword
    WITH anchor LIMIT 5
    
    MATCH (p:Property)-[r_anchor:NEAR_COLLEGE]->(anchor)
    WITH p, anchor, r_anchor ORDER BY r_anchor.distance LIMIT 100
    
    OPTIONAL MATCH (p)-[r_sub:NEAR_SUBWAY]->(sub:SubwayStation)
    WITH p, anchor, r_anchor, sub, r_sub
    ORDER BY CASE WHEN r_sub IS NULL THEN 9999 ELSE r_sub.distance END
    WITH p, anchor, r_anchor, head(collect(sub)) as closest_sub, head(collect(r_sub)) as closest_r_sub
    
    WITH p, anchor, r_anchor, closest_sub, closest_r_sub,
         ({SCORE_MAX_DISTANCE} - coalesce(toInteger(r_anchor.distance), {SCORE_MAX_DISTANCE})) as total_score
    
    RETURN p.id as id, total_score,
           CASE WHEN closest_sub IS NOT NULL 
                THEN [{{name: closest_sub.name, dist: coalesce(toInteger(closest_r_sub.distance), 9999), time: coalesce(toInteger(closest_r_sub.walking_time), 9999)}}]
                ELSE [] 
           END as poi_details,
           [{{name: anchor.name, dist: coalesce(toInteger(r_anchor.distance), 9999), time: coalesce(toInteger(r_anchor.walking_time), 9999)}}] as edu_details
    ORDER BY total_score DESC LIMIT 50
    """


def build_safety_query() -> str:
    """안전 시설 검색 Cypher 쿼리 (TEXT INDEX 활용)"""
    return f"""
    MATCH (anchor)
    WHERE (anchor:SubwayStation OR anchor:College OR anchor:Hospital OR anchor:GeneralHospital OR anchor:Park)
      AND (anchor.name STARTS WITH $keyword OR anchor.name CONTAINS $keyword)
    WITH anchor LIMIT 5
    
    MATCH (p:Property)-[r_anchor]-(anchor)
    WHERE type(r_anchor) STARTS WITH 'NEAR_'
    WITH DISTINCT p, anchor, r_anchor
    ORDER BY r_anchor.distance LIMIT 100
    
    CALL {{ WITH p RETURN count{{(p)-[:NEAR_CCTV]->()}} as cctv_count }}
    CALL {{ WITH p RETURN count{{(p)-[:NEAR_BELL]->()}} as bell_count }}
    CALL {{ 
        WITH p 
        OPTIONAL MATCH (p)-[r:NEAR_POLICE]->(police:PoliceStation)
        RETURN collect({{name: police.name, dist: toInteger(r.distance), time: toInteger(r.walking_time)}})[..1] as police_list
    }}
    CALL {{
        WITH p
        OPTIONAL MATCH (p)-[r:NEAR_FIRE]->(fire:FireStation)
        RETURN collect({{name: fire.name, dist: toInteger(r.distance), time: toInteger(r.walking_time)}})[..1] as fire_list
    }}
    
    WITH p, anchor, r_anchor, cctv_count, bell_count,
         [item in police_list WHERE item.name IS NOT NULL] as police_details,
         [item in fire_list WHERE item.name IS NOT NULL] as fire_details
    
    WITH p, anchor, r_anchor, cctv_count, bell_count, police_details, fire_details,
         (cctv_count * {SCORE_SAFETY_MULTIPLIER} + bell_count * {SCORE_SAFETY_MULTIPLIER}) as count_score,
         CASE WHEN size(police_details) > 0 THEN ({SCORE_MAX_DISTANCE} - coalesce(police_details[0].dist, {SCORE_MAX_DISTANCE})) ELSE 0 END as police_score,
         CASE WHEN size(fire_details) > 0 THEN ({SCORE_MAX_DISTANCE} - coalesce(fire_details[0].dist, {SCORE_MAX_DISTANCE})) ELSE 0 END as fire_score,
         ({SCORE_MAX_DISTANCE} - coalesce(toInteger(r_anchor.distance), {SCORE_MAX_DISTANCE})) as anchor_score,
         CASE WHEN 'SubwayStation' IN labels(anchor) THEN {SCORE_SUBWAY_BONUS} ELSE 0 END as priority_score
    
    WITH p, anchor, cctv_count, bell_count, police_details, fire_details,
         (count_score + police_score + fire_score + anchor_score + priority_score) as total_score,
         {{name: anchor.name, dist: coalesce(toInteger(r_anchor.distance), 9999), time: coalesce(toInteger(r_anchor.walking_time), 9999)}} as anchor_info
    
    RETURN p.id as id, total_score,
           [anchor_info] as poi_details,
           cctv_count, bell_count, police_details, fire_details
    ORDER BY total_score DESC LIMIT 50
    """


def build_facility_query(relationship: str, label: str, result_key: str) -> str:
    """일반 시설 검색 Cypher 쿼리 (TEXT INDEX 활용)"""
    return f"""
    MATCH (anchor)
    WHERE (anchor:SubwayStation OR anchor:College OR anchor:Hospital OR anchor:GeneralHospital OR anchor:Park)
      AND (anchor.name STARTS WITH $keyword OR anchor.name CONTAINS $keyword)
    WITH anchor LIMIT 5
    
    MATCH (p:Property)-[r_anchor]-(anchor)
    WHERE type(r_anchor) STARTS WITH 'NEAR_'
    
    MATCH (p)-[r_fac:{relationship}]->(target:{label})
    
    WITH p, anchor, r_anchor, target, r_fac ORDER BY coalesce(toInteger(r_fac.distance), 99999) ASC
    WITH p, anchor, r_anchor, count(DISTINCT target) as fac_count,
         collect({{name: target.name, dist: coalesce(toInteger(r_fac.distance), 9999), time: coalesce(toInteger(r_fac.walking_time), 9999)}}) as all_details
    WITH p, anchor, r_anchor, fac_count, all_details[..3] as fac_details,
         CASE WHEN size(all_details) > 0 THEN ({SCORE_MAX_DISTANCE} - all_details[0].dist) ELSE 0 END as fac_score
    
    WITH p, anchor, r_anchor, fac_count, fac_details, fac_score, 
         ({SCORE_MAX_DISTANCE} - coalesce(toInteger(r_anchor.distance), {SCORE_MAX_DISTANCE})) as anchor_score,
         CASE WHEN 'SubwayStation' IN labels(anchor) THEN {SCORE_SUBWAY_BONUS} ELSE 0 END as priority_score
         
    WITH p, anchor, fac_count, fac_details, (anchor_score + fac_score + priority_score) as total_score,
         {{name: anchor.name, dist: coalesce(toInteger(r_anchor.distance), 9999), time: coalesce(toInteger(r_anchor.walking_time), 9999)}} as anchor_info
    
    RETURN p.id as id, total_score, 
           [anchor_info] as poi_details,
           fac_details as {result_key}
    ORDER BY total_score DESC LIMIT 50
    """


def build_multi_criteria_query() -> str:
    """다중 조건 검색 Cypher 쿼리 (TEXT INDEX 활용)"""
    return f"""
    MATCH (anchor)
    WHERE (anchor:SubwayStation OR anchor:College OR anchor:Hospital OR anchor:GeneralHospital OR anchor:Park)
      AND (anchor.name STARTS WITH $keyword OR anchor.name CONTAINS $keyword)
    WITH anchor LIMIT 5
    
    MATCH (p:Property)-[r_anchor]-(anchor)
    WHERE type(r_anchor) STARTS WITH 'NEAR_'
    WITH DISTINCT p, anchor, r_anchor
    ORDER BY r_anchor.distance LIMIT 150
    
    CALL {{
        WITH p
        OPTIONAL MATCH (p)-[r:NEAR_CONVENIENCE]->(n:Convenience)
        WITH n, r ORDER BY r.distance LIMIT 3
        RETURN count(n) as conv_count,
               collect({{name: n.name, dist: toInteger(r.distance), time: toInteger(r.walking_time)}}) as conv_list
    }}
    
    CALL {{
        WITH p
        OPTIONAL MATCH (p)-[r:NEAR_HOSPITAL|NEAR_GENERAL_HOSPITAL]->(n)
        WITH n, r ORDER BY r.distance LIMIT 3
        RETURN count(n) as hosp_count,
               collect({{name: n.name, dist: toInteger(r.distance), time: toInteger(r.walking_time)}}) as hosp_list
    }}
    
    CALL {{
        WITH p
        OPTIONAL MATCH (p)-[r:NEAR_PHARMACY]->(n:Pharmacy)
        WITH n, r ORDER BY r.distance LIMIT 3
        RETURN count(n) as pharm_count,
               collect({{name: n.name, dist: toInteger(r.distance), time: toInteger(r.walking_time)}}) as pharm_list
    }}
    
    CALL {{
        WITH p
        RETURN count{{(p)-[:NEAR_CCTV]->()}} as cctv_count,
               count{{(p)-[:NEAR_BELL]->()}} as bell_count
    }}
    
    CALL {{
        WITH p
        OPTIONAL MATCH (p)-[r:NEAR_POLICE]->(n:PoliceStation)
        WITH n, r ORDER BY r.distance LIMIT 1
        RETURN collect({{name: n.name, dist: toInteger(r.distance), time: toInteger(r.walking_time)}}) as police_list
    }}
    
    CALL {{
        WITH p
        OPTIONAL MATCH (p)-[r:NEAR_FIRE]->(n:FireStation)
        WITH n, r ORDER BY r.distance LIMIT 1
        RETURN collect({{name: n.name, dist: toInteger(r.distance), time: toInteger(r.walking_time)}}) as fire_list
    }}
    
    CALL {{
        WITH p
        OPTIONAL MATCH (p)-[r:NEAR_PARK]->(n:Park)
        WITH n, r ORDER BY r.distance LIMIT 3
        RETURN count(n) as park_count,
               collect({{name: n.name, dist: toInteger(r.distance), time: toInteger(r.walking_time)}}) as park_list
    }}
    
    WITH p, anchor, r_anchor,
         conv_count, [item in conv_list WHERE item.name IS NOT NULL] as conv_details,
         hosp_count, [item in hosp_list WHERE item.name IS NOT NULL] as hosp_details,
         pharm_count, [item in pharm_list WHERE item.name IS NOT NULL] as pharm_details,
         cctv_count, bell_count,
         [item in police_list WHERE item.name IS NOT NULL] as police_details,
         [item in fire_list WHERE item.name IS NOT NULL] as fire_details,
         park_count, [item in park_list WHERE item.name IS NOT NULL] as park_details
    
    WHERE
        (NOT $need_conv OR conv_count > 0) AND
        (NOT $need_hosp OR hosp_count > 0) AND
        (NOT $need_pharm OR pharm_count > 0) AND
        (NOT $need_safety OR (cctv_count + bell_count) > 0 OR size(police_list) > 0 OR size(fire_list) > 0) AND
        (NOT $need_park OR park_count > 0)
    
    WITH p, anchor, r_anchor,
         conv_details, hosp_details, pharm_details,
         cctv_count, bell_count, police_details, fire_details, park_details,
         ({SCORE_MAX_DISTANCE} - coalesce(toInteger(r_anchor.distance), {SCORE_MAX_DISTANCE})) as anchor_score,
         CASE WHEN 'SubwayStation' IN labels(anchor) THEN {SCORE_SUBWAY_BONUS} ELSE 0 END as priority_score
    
    WITH p, (anchor_score + priority_score) as total_score,
         {{name: anchor.name, dist: toInteger(r_anchor.distance), time: toInteger(r_anchor.walking_time)}} as anchor_info,
         conv_details, hosp_details, pharm_details,
         cctv_count, bell_count, police_details, fire_details, park_details
    
    RETURN p.id as id, total_score,
           [anchor_info] as poi_details,
           conv_details, hosp_details as med_details, pharm_details as pharmacy_details,
           cctv_count, bell_count, police_details, fire_details, park_details
    ORDER BY total_score DESC LIMIT 50
    """


def build_university_multi_query() -> str:
    """대학교 전용 다중 조건 검색 Cypher 쿼리 (College만 앵커로 사용)"""
    return f"""
    MATCH (anchor:College)
    WHERE anchor.name STARTS WITH $keyword OR anchor.name CONTAINS $keyword
    WITH anchor LIMIT 5
    
    MATCH (p:Property)-[r_anchor:NEAR_COLLEGE]->(anchor)
    WITH DISTINCT p, anchor, r_anchor
    ORDER BY r_anchor.distance LIMIT 150
    
    CALL {{
        WITH p
        OPTIONAL MATCH (p)-[r:NEAR_CONVENIENCE]->(n:Convenience)
        WITH n, r ORDER BY r.distance LIMIT 3
        RETURN count(n) as conv_count,
               collect({{name: n.name, dist: toInteger(r.distance), time: toInteger(r.walking_time)}}) as conv_list
    }}
    
    CALL {{
        WITH p
        OPTIONAL MATCH (p)-[r:NEAR_HOSPITAL|NEAR_GENERAL_HOSPITAL]->(n)
        WITH n, r ORDER BY r.distance LIMIT 3
        RETURN count(n) as hosp_count,
               collect({{name: n.name, dist: toInteger(r.distance), time: toInteger(r.walking_time)}}) as hosp_list
    }}
    
    CALL {{
        WITH p
        OPTIONAL MATCH (p)-[r:NEAR_PHARMACY]->(n:Pharmacy)
        WITH n, r ORDER BY r.distance LIMIT 3
        RETURN count(n) as pharm_count,
               collect({{name: n.name, dist: toInteger(r.distance), time: toInteger(r.walking_time)}}) as pharm_list
    }}
    
    CALL {{
        WITH p
        RETURN count{{(p)-[:NEAR_CCTV]->()}} as cctv_count,
               count{{(p)-[:NEAR_BELL]->()}} as bell_count
    }}
    
    CALL {{
        WITH p
        OPTIONAL MATCH (p)-[r:NEAR_POLICE]->(n:PoliceStation)
        WITH n, r ORDER BY r.distance LIMIT 1
        RETURN collect({{name: n.name, dist: toInteger(r.distance), time: toInteger(r.walking_time)}}) as police_list
    }}
    
    CALL {{
        WITH p
        OPTIONAL MATCH (p)-[r:NEAR_FIRE]->(n:FireStation)
        WITH n, r ORDER BY r.distance LIMIT 1
        RETURN collect({{name: n.name, dist: toInteger(r.distance), time: toInteger(r.walking_time)}}) as fire_list
    }}
    
    CALL {{
        WITH p
        OPTIONAL MATCH (p)-[r:NEAR_PARK]->(n:Park)
        WITH n, r ORDER BY r.distance LIMIT 3
        RETURN count(n) as park_count,
               collect({{name: n.name, dist: toInteger(r.distance), time: toInteger(r.walking_time)}}) as park_list
    }}
    
    // 추가: 가장 가까운 지하철역 정보
    CALL {{
        WITH p
        OPTIONAL MATCH (p)-[r:NEAR_SUBWAY]->(s:SubwayStation)
        WITH s, r ORDER BY r.distance LIMIT 1
        RETURN collect({{name: s.name, dist: toInteger(r.distance), time: toInteger(r.walking_time)}}) as subway_list
    }}
    
    WITH p, anchor, r_anchor,
         conv_count, [item in conv_list WHERE item.name IS NOT NULL] as conv_details,
         hosp_count, [item in hosp_list WHERE item.name IS NOT NULL] as hosp_details,
         pharm_count, [item in pharm_list WHERE item.name IS NOT NULL] as pharm_details,
         cctv_count, bell_count,
         [item in police_list WHERE item.name IS NOT NULL] as police_details,
         [item in fire_list WHERE item.name IS NOT NULL] as fire_details,
         park_count, [item in park_list WHERE item.name IS NOT NULL] as park_details,
         [item in subway_list WHERE item.name IS NOT NULL] as trans_details
    
    WHERE
        (NOT $need_conv OR conv_count > 0) AND
        (NOT $need_hosp OR hosp_count > 0) AND
        (NOT $need_pharm OR pharm_count > 0) AND
        (NOT $need_safety OR (cctv_count + bell_count) > 0 OR size(police_list) > 0 OR size(fire_list) > 0) AND
        (NOT $need_park OR park_count > 0)
    
    WITH p, anchor, r_anchor,
         conv_details, hosp_details, pharm_details,
         cctv_count, bell_count, police_details, fire_details, park_details, trans_details,
         ({SCORE_MAX_DISTANCE} - coalesce(toInteger(r_anchor.distance), {SCORE_MAX_DISTANCE})) as anchor_score
    
    WITH p, anchor_score as total_score,
         {{name: anchor.name, dist: toInteger(r_anchor.distance), time: toInteger(r_anchor.walking_time)}} as edu_info,
         conv_details, hosp_details, pharm_details,
         cctv_count, bell_count, police_details, fire_details, park_details, trans_details
    
    RETURN p.id as id, total_score,
           [edu_info] as edu_details,
           trans_details as poi_details,
           conv_details, hosp_details as med_details, pharm_details as pharmacy_details,
           cctv_count, bell_count, police_details, fire_details, park_details
    ORDER BY total_score DESC LIMIT 50
    """


# -----------------------------------------------------------------------------
# 4. 쿼리 실행 함수 (Query Execution)
# -----------------------------------------------------------------------------

def execute_query(location: str, analysis: Dict) -> List[Dict]:
    """
    분석 결과를 기반으로 적절한 Cypher 쿼리 실행
    
    Args:
        location: 추출된 위치
        analysis: analyze_question() 결과
    
    Returns:
        Neo4j 쿼리 결과 리스트
    """
    search_type = analysis['search_type']
    facilities = analysis['facilities']
    facilities_dict = analysis['facilities_dict']
    location_type = analysis.get('location_type', '')
    
    try:
        # 다중 시설 검색
        if search_type == "multi":
            print(f"[QueryBuilder] 🔀 Multi-criteria search: {facilities}")
            
            # 대학교 위치인 경우 대학교 전용 멀티 쿼리 사용
            if location_type == "university":
                print(f"[QueryBuilder] 🎓 Using university-anchor multi-criteria query")
                query = build_university_multi_query()
                params = {
                    "keyword": location,
                    "need_conv": facilities_dict.get("convenience", False),
                    "need_hosp": facilities_dict.get("hospital", False) or facilities_dict.get("general_hospital", False),
                    "need_pharm": facilities_dict.get("pharmacy", False),
                    "need_safety": facilities_dict.get("safety", False),
                    "need_park": facilities_dict.get("park", False)
                }
            else:
                query = build_multi_criteria_query()
                params = {
                    "keyword": location,
                    "need_conv": facilities_dict.get("convenience", False),
                    "need_hosp": facilities_dict.get("hospital", False) or facilities_dict.get("general_hospital", False),
                    "need_pharm": facilities_dict.get("pharmacy", False),
                    "need_safety": facilities_dict.get("safety", False),
                    "need_park": facilities_dict.get("park", False)
                }
            return get_graph().query(query, params=params)
        
        # 단일 시설 검색
        elif search_type == "single":
            facility_type = facilities[0]
            
            # 대학교 위치인 경우 university 쿼리 강제 사용
            if location_type == "university":
                print(f"[QueryBuilder] 🎓 University location detected - using university query")
                query = build_university_query()
                return get_graph().query(query, params={"keyword": location})
            
            # 시설 타입별 우선순위 조정
            if facilities_dict.get("general_hospital"):
                facility_type = "general_hospital"
            
            print(f"[QueryBuilder] 🔍 Single facility search: {facility_type}")
            query = build_single_facility_query(facility_type)
            return get_graph().query(query, params={"keyword": location})
        
        # 기본 검색 - location_type에 따라 분기
        else:
            if location_type == "university":
                print(f"[QueryBuilder] 🎓 Default university search")
                query = build_university_query()
            else:
                print(f"[QueryBuilder] 🚇 Default subway search")
                query = build_subway_query()
            return get_graph().query(query, params={"keyword": location})
    
    except Exception as e:
        print(f"[QueryBuilder] ❌ Query execution error: {e}")
        return []



# -----------------------------------------------------------------------------
# 5. 메인 검색 함수 (Main Search Function)
# -----------------------------------------------------------------------------

def generate_search_steps(location: str, facilities: List[str]) -> List[str]:
    """검색 의도에 따른 사용자 친화적 진행 메시지 생성"""
    steps = []
    
    # 1. 위치 검색 메시지
    if location:
        steps.append(f"{location} 근처 매물 찾는 중...")
    
    # 2. 시설별 검색 메시지
    facility_msg_map = {
        "safety": "안전한 방(CCTV/치안) 찾는 중...",
        "convenience": "가까운 편의점 찾는 중...",
        "hospital": "가까운 병원 확인하는 중...",
        "general_hospital": "종합병원 접근성 확인 중...",
        "pharmacy": "근처 약국 찾는 중...",
        "park": "산책하기 좋은 공원 찾는 중...",
        "university": "대학교 통학 거리 계산 중...",
        "subway": "역세권 매물 스캔 중..."
    }
    
    for fac in facilities:
        if fac in facility_msg_map:
            steps.append(facility_msg_map[fac])
        elif fac == "subway" and not location: # location이 없는데 subway만 있으면
            steps.append("역세권 매물 스캔 중...")
            
    return steps


def rule_based_search(state: RAGState) -> Dict:
    """
    규칙 기반 검색 (LLM 0회 호출)
    
    1. hard_filters가 있으면 사용, 없으면 질문 분석
    2. 동적 Cypher 쿼리 생성
    3. Neo4j 쿼리 실행
    4. 결과 정제 및 반환
    """
    import time
    start_time = time.time()
    
    # 위치 캐싱 import
    from common.redis_cache import get_location_cache, save_location_cache
    
    question = state["question"]
    hard_filters = state.get("hard_filters", {})
    
    print(f"\n{'='*60}")
    print(f"[Neo4j] 🚀 검색 시작: {question}")
    print(f"[Neo4j] 📋 하드 필터: {hard_filters}")
    print(f"{'='*60}\n")
    
    # 1. hard_filters가 있으면 사용, 없으면 질문 분석
    if hard_filters and (hard_filters.get("location") or hard_filters.get("facilities")):
        # 하드 필터에서 위치와 시설 추출
        location = hard_filters.get("location", "")
        facilities = hard_filters.get("facilities", [])
        location_type = ""  # 하드 필터에서는 location_type 추정 필요
        
        # location_type 추정
        if location:
            if any(uni in location for uni in ["대학", "대"]):
                location_type = "university"
            elif "역" in location or location in ["홍대", "강남", "신촌", "역삼", "선릉"]:
                location_type = "subway"
            else:
                location_type = "region"
        
        analysis = {
            'location': location,
            'location_type': location_type,
            'facilities': facilities,
            'facilities_dict': {f: True for f in facilities},
            'search_type': 'multi' if len(facilities) >= 2 else ('single' if facilities else 'default')
        }
        print(f"[Neo4j] 📍 하드필터 기반: location={location}, facilities={facilities}")
    else:
        # 기존 질문 분석 사용
        analysis = analyze_question(question)
        location = analysis['location']
        facilities = analysis['facilities']
    
    # 검색 진행 상황 메시지 생성 (UI 표시용)
    search_steps = generate_search_steps(location, facilities)
    print(f"[Neo4j] 📋 Progress Steps: {search_steps}")
    
    # 2. 위치가 없으면 검색 불가
    if not location:
        return {
            "graph_results": [],
            "graph_summary": "어느 지역이나 지하철역 근처를 찾으시나요? (예: 홍대입구역, 강남역)",
            "search_steps": search_steps or ["검색 조건을 확인 중입니다..."]
        }
    
    # 3. 캐시 확인 (단일 시설만, location_type 반영)
    location_type = analysis.get('location_type', '')
    cache_key = facilities[0] if len(facilities) == 1 else ("subway" if not facilities and location_type != "university" else None)
    
    # 대학교 검색인 경우 캐시 키에 university 접두사 추가
    full_cache_key = f"{location_type}:{cache_key}" if location_type and cache_key else cache_key
    
    if full_cache_key:
        cached_results = get_location_cache(location, full_cache_key)
        if cached_results:
            elapsed = int((time.time() - start_time) * 1000)
            print(f"[Neo4j] ⚡ 캐시 히트! | 시간: {elapsed}ms")
            
            # 캐시된 경우에도 steps는 반환
            return {
                "graph_results": cached_results,
                "graph_summary": f"캐시된 검색 결과: {location} 근처 {cache_key}",
                "search_steps": search_steps,
                "requested_facilities": facilities
            }
    
    # 4. 쿼리 실행
    results = execute_query(location, analysis)
    
    # 5. 결과 중복 제거
    if isinstance(results, list):
        unique_props = {p.get('id'): p for p in results if isinstance(p, dict) and p.get('id')}
        results = list(unique_props.values())
    
    elapsed = int((time.time() - start_time) * 1000)
    print(f"[Neo4j] ✅ 완료: {len(results)}개 결과 | 시간: {elapsed}ms")
    
    # 6. 캐시 저장 (단일 시설만, location_type 반영)
    if full_cache_key and results:
        save_location_cache(location, full_cache_key, results)
    
    return {
        "graph_results": results if isinstance(results, list) else [],
        "graph_summary": f"규칙 기반 검색 완료: {location} 근처 {facilities or ['기본']} 검색",
        "search_steps": search_steps,
        "requested_facilities": facilities
    }




# =============================================================================
# 진입점 (Entry Point)
# =============================================================================

def search(state: RAGState) -> Dict:
    """
    Neo4j 그래프 검색 - 순수 규칙 기반 (LLM 0회 호출)
    
    동작: 질문에서 위치/시설 추출 → Cypher 쿼리 생성 → Neo4j 실행
    성능: 17,000ms (LLM) → 150ms (규칙 기반)
    """
    return rule_based_search(state)
