# 네이버페이 부동산 AI 기술 세션 보고서

**일시**: 2025년 (DAN25 컨퍼런스)  
**발표자**: 황원상, 허문혁 (NAVER Pay Tech)  
**주제**: 부동산 매물 검색의 혁명 - 대화형 AI로 구현하는 검색-분석-투자 통합 생태계

---

## 📌 Executive Summary

네이버페이 부동산 팀이 **AI 집찾기**와 **AI 부동산 보고서** 서비스를 구축하면서 해결한 3가지 핵심 기술 과제와 솔루션을 공유했습니다. 특히 **4 Layer 아키텍처**를 통해 400만 개 매물 데이터를 처리하면서도 전문가 수준의 심층 분석을 제공하는 방법론이 인상적이었습니다.

**핵심 성과**:
- 검색 속도 **15초 → 4초** (73% 개선)
- 기존 필터 검색 대비 탐색 시간 **1분 7초 → 30초** (53% 단축)
- Prompt Cache 도입으로 비용 대폭 절감

---

## 🎯 Part 1: AI 집찾기 서비스

### 1.1 서비스 개요

**기존 부동산 검색의 한계**:
```
PC 네이버 부동산: 편의성 낮음, 탐색 속도 빠름
모바일 네이버 부동산: 편의성 높음, 탐색 속도 느림
```

**AI 집찾기의 혁신**:
- 자연어 대화로 매물 검색
- 기존 필터로 불가능했던 조건 지원
  - "도보 30분 이내"
  - "중층 이상"
  - "방 2개 이상"

**예시 시나리오**:
```
사용자: "네이버로 이직했어요. 도보 30분 이내, 아파트나 오피스텔, 
       전세 5억 미만, 방 2개 이상, 중층 이상 찾아주세요"

AI 집찾기: [정자역 근처 1km 이내 조건 자동 해석]
          → 맞춤 매물 추천 (30초 이내)
```

---

### 1.2 기술적 도전 과제

#### **Challenge 1: Hallucination (환각)**

**문제**: LLM이 없는 매물을 지어내거나 잘못된 정보 제공

**해결 방법**:

**① RAG (Retrieval Augmented Generation)**
```
[사용자 질의] → [매물 DB 검색] → [관련 데이터 추출] → [LLM에 Context 제공]
```

**② MCP (Model Context Protocol)**

네이버페이의 핵심 차별화 전략입니다.

```
[레거시 시스템들]     [MCP 서버]      [MCP Client]    [LLM]
  - 매물 DB    ←→   USB 같은    ←→   표준화된   ←→  Claude
  - 단지 정보         표준 프로토콜      인터페이스
  - 가격 정보
```

**MCP의 장점**:
- 레거시 시스템을 재구축하지 않고 AI와 연결
- 각 데이터 소스별 MCP 서버만 개발하면 됨
- LLM이 필요할 때만 실시간으로 데이터 조회

**실제 적용 예시** (강연 내용):
> "기존 부동산 시스템들이 20년 가까이 쌓여있는 상황에서, 
> 이걸 다 뜯어고칠 수는 없었습니다. 
> MCP를 통해 각 시스템을 AI에 연결하는 어댑터만 만들었고,
> 이를 통해 빠르게 서비스를 출시할 수 있었습니다."

---

#### **Challenge 2: Latency (지연 시간)**

**문제의 본질**:

LLM의 토큰 처리 시간은 **입력 토큰 수에 비례**합니다.

```
5,000 토큰:   ~770ms (TTFT) + ~950ms (Total) = 1.7초
10,000 토큰:  ~850ms (TTFT) + ~1,150ms (Total) = 2초
30,000 토큰:  ~1,400ms (TTFT) + ~1,600ms (Total) = 3초
```

**3가지 해결 전략**:

##### **① Micro Prompting + Prompt Cache**

**Micro Prompting**: 큰 프롬프트를 작은 단위로 분할

```
Before (Single Large Prompt):
┌─────────────────────────────────────┐
│ 시스템 프롬프트 (5,000 토큰)        │
│ + 매물 데이터 (20,000 토큰)         │ → 25,000 토큰 매번 처리
│ + 사용자 질문 (100 토큰)            │
└─────────────────────────────────────┘

After (Micro Prompting):
┌─────────────────────────────────────┐
│ 시스템 프롬프트 (5,000 토큰) [캐시] │ ← 한번만 처리
└─────────────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│ Task 1: 지역 필터링 (2,000 토큰)    │ ← 병렬 처리
│ Task 2: 가격 분석 (2,000 토큰)      │
│ Task 3: 조건 매칭 (2,000 토큰)      │
└─────────────────────────────────────┘
```

**Prompt Cache**:
```python
# Anthropic API 예시
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    system=[{
        "type": "text",
        "text": "당신은 부동산 전문가입니다...",  # 5,000 토큰
        "cache_control": {"type": "ephemeral"}  # ← 캐시 마킹
    }],
    messages=[{
        "role": "user",
        "content": "강남구 아파트 찾아줘"  # 100 토큰만 새로 처리
    }]
)
```

**실제 성과** (강연 자료):
- 기존: 15초
- 개선 후: 4초
- **73% 속도 향상** ✅

---

##### **② Coroutine (병렬 처리)**

**Kotlin Coroutine 활용** - 네이버페이는 백엔드를 Kotlin으로 구축

```kotlin
// 매물 조건이 많을 때 순차 처리하면 느림
// Before (순차):
val priceFilter = checkPrice()      // 2초
val locationFilter = checkLocation() // 2초
val roomFilter = checkRooms()       // 2초
// Total: 6초

// After (병렬):
coroutineScope {
    val price = async { checkPrice() }
    val location = async { checkLocation() }
    val rooms = async { checkRooms() }
    
    awaitAll(price, location, rooms)  // Total: 2초
}
```

**적용 영역**:
- 여러 매물 조건 동시 검증
- 다수 API 호출 병렬화
- LLM 호출 + DB 쿼리 동시 진행

---

##### **③ Opensearch (빠른 좌표 기반 검색)**

**구조**:
```
[매물 제공 업체 A]
[매물 제공 업체 B]  →  [매물 집중]  →  [Kafka]  →  [Consumer]
[매물 제공 업체 C]                                       ↓
                                                   [RDB 저장]
                                                        ↓
                                                   [Opensearch]
                                                        ↓
                                                   [AI 집찾기]
```

**Opensearch의 역할**:
1. **Geo-Spatial 검색**: "정자역 1km 이내" → 0.1초 이내 조회
2. **실시간 색인**: 새 매물 등록 즉시 반영
3. **복합 필터링**: 위치 + 가격 + 면적 등 복합 조건 고속 처리

**왜 Opensearch인가?**
- 일반 벡터 DB: 유사도 검색에 특화
- Opensearch: **지리 공간 검색 + 벡터 검색** 모두 지원
- 부동산 서비스의 핵심은 "위치 기반 검색"

---

#### **Challenge 3: 잦은 Prompt 변경**

**문제 상황**:
```
AI 서비스는 프롬프트를 자주 수정해야 함
→ 코드에 하드코딩 시 매번 재배포 필요 (30분~1시간 소요)
→ 빠른 실험과 개선이 불가능
```

**해결: Spring Cloud Config + Bus**

```
[Git Repository]
  └── application.yml
        ├── system_prompt: "당신은..."
        ├── search_prompt: "다음 조건으로..."
        └── filter_rules: [...]
              ↓ Git Push
      [Spring Cloud Config Server]
              ↓ 변경 감지
      [Spring Cloud Bus (Kafka)]
              ↓ 이벤트 전파
      [AI Service 1, 2, 3, ...]  ← 재시작 없이 적용!
```

**실제 프로세스**:
1. 개발자가 Git에서 프롬프트 수정
2. Config Server가 변경 감지
3. Bus가 모든 서비스에 알림
4. 각 서비스가 새 프롬프트 로드
5. **재배포 없이 3초 이내 적용** ✅

**장점**:
- A/B 테스트 즉시 가능
- 프롬프트 버전 관리 (Git 히스토리)
- 롤백도 Git Revert로 간단히

---

### 1.3 전체 아키텍처

```
┌──────────────────────────────────────────────────────────┐
│                      [사용자]                             │
│                        ↓ 질의                             │
│                [질문 파싱 및 요청]                         │
└──────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────┐
│                 [Micro Prompting]                         │
│   ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐              │
│   │Task1 │  │Task2 │  │Task3 │  │Task4 │  병렬 처리    │
│   └──────┘  └──────┘  └──────┘  └──────┘              │
└──────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────┐
│                   [Opensearch]                            │
│   - 지역 필터링 (Geo-Spatial)                            │
│   - 가격/면적 복합 필터링                                 │
│   - 실시간 매물 색인                                      │
└──────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────┐
│             [결과 통합 및 응답 생성]                      │
│   - Prompt Cache 활용                                     │
│   - 최종 매물 리스트 반환                                 │
└──────────────────────────────────────────────────────────┘
                        ↓
                    [사용자]
```

---

## 🎯 Part 2: AI 부동산 보고서

### 2.1 서비스 배경

**AI 집찾기의 한계**:
```
✅ 매물 찾기: 완료
❌ 투자 결정: 여전히 어려움
   - 이 가격이 적정한가?
   - 투자 가치가 있나?
   - 개발 잠재력은?
```

**목표**:
> "400만 개 매물 데이터 + 전문가 수준의 깊이 있는 분석"

---

### 2.2 토큰 제약 딜레마

**LLM의 근본적 한계**:

```
┌─────────────────────────────────────┐
│  Input Token (90%)                  │  많은 데이터 → 짧은 분석
│  Output Token (10%)                 │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Input Token (50%)                  │  깊은 분석 → 제한된 데이터
│  Output Token (50%)                 │
└─────────────────────────────────────┘
```

**기존 AI 분석 도구의 한계**:
1. 많은 데이터 입력 → 짧고 단편적인 분석만 가능
2. 깊이 있는 분석 → 제한된 데이터만 입력 가능

**네이버페이의 목표**:
```
데이터 많이 + 분석 깊게 = 토큰 한계 초과?
→ 4 Layer 아키텍처로 해결!
```

---

### 2.3 4 Layer 아키텍처 상세

#### **Layer 1: Section Agent (오케스트레이터)**

**역할**: 보고서 전체 구조 관리 및 섹션 간 맥락 전달

**핵심 전략: 맥락 누적 생성**

```
❌ 순차 생성의 문제:
Introduction → Background → Body → Conclusion
→ Body 작성 시 Introduction 내용을 몰라 모순 발생

❌ 병렬 생성의 문제:
4개 Section 동시 생성
→ "서론: 투자하세요" vs "배경: 시장 어려움" 불일치

✅ 네이버페이 해결책 (역순 생성):
Body → Background → Conclusion → Introduction
```

**실제 프로세스**:

```
Step 1: Body Section 생성
├─ 10개 Domain Agent 병렬 실행
├─ 시장동향 Agent: "강남구 실거래가 5% 상승"
├─ 단지분석 Agent: "대치동 은마아파트 재건축 호재"
├─ 수요분석 Agent: "학군 수요 지속 증가"
└─ ... (10개 결과)
→ Body 완성 (토큰: 15,000)

Step 2: Background Section 생성
├─ Body 참조하여 맞춤형 배경 설명
├─ "강남구 시장은 최근 정부 규제에도 불구하고..."
└─ Body 내용과 논리적 일관성 유지
→ Background 완성 (토큰: 5,000)

Step 3: Conclusion Section 생성
├─ Body + Background 종합
├─ "종합적으로 강남구는 중장기 투자가치 높음"
└─ 전체 내용의 결론 도출
→ Conclusion 완성 (토큰: 3,000)

Step 4: Introduction Section 생성
├─ 완성된 모든 Section 참조
├─ "본 보고서는 강남구 부동산 시장을 5가지 측면에서..."
└─ 전체 내용의 정확한 요약
→ Introduction 완성 (토큰: 2,000)
```

**장점**:
- 📝 문서 전체의 논리적 일관성 보장
- 🎯 Introduction이 전체 내용을 정확히 반영
- ⚡ Body는 병렬 처리로 속도 확보

---

#### **Layer 2: Plan Agent**

**역할**: 사용자 질의를 분석하고 실행 계획 수립

**3단계 프로세스**:

```
┌──────────────────────────────────────────────────────┐
│ Step 1: 질의 분석 및 목적 구조화                     │
│                                                      │
│ Input: "강남구 아파트 투자 분석해줘"                 │
│                                                      │
│ 분석 결과:                                           │
│  - 분석 범위: 강남구 전체                            │
│  - 투자 관점: 수익성 + 안정성                        │
│  - 분석 깊이: 심층 분석 (전문가 수준)                │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│ Step 2: Domain Agent 스캔                             │
│                                                      │
│ 10개 Agent의 메타데이터를 LLM이 검토:                │
│  ✅ 시장동향 Agent: 필요 (실거래가, 거래량 분석)      │
│  ✅ 단지인사이트 Agent: 필요 (단지별 비교)            │
│  ✅ 수요분석 Agent: 필요 (인구유입 추세)              │
│  ❌ 개발계획 Agent: 불필요 (질의와 무관)              │
│  ✅ 투자수익률 Agent: 필요 (수익성 분석)              │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│ Step 3: Main Plan 생성                                │
│                                                      │
│ {                                                    │
│   "주제": "강남구 시장 동향 분석",                   │
│   "목표": "투자 적합성 평가",                        │
│   "통찰": "중장기 관점의 수익성 분석",               │
│   "요구사항": [...],                                 │
│   "도구": ["실거래가 API", "인구이동 통계"],         │
│   "세부계획": {                                      │
│     "시장동향": "최근 3년 실거래가 변화율 분석",     │
│     "단지비교": "주요 단지 5개 비교",                │
│     "수요분석": "전입인구 추이"                      │
│   }                                                  │
│ }                                                    │
└──────────────────────────────────────────────────────┘
```

**실제 동작 예시** (강연 내용):

```
사용자: "강남구 아파트 투자 분석해줘"

Plan Agent의 내부 사고:
1. "강남구" → 지역 특정됨
2. "투자 분석" → 시장동향, 수익성, 리스크 필요
3. "아파트" → 단지 정보, 매물 정보 필요

→ 7개 Agent 선택 (10개 중)
→ 각 Agent에게 구체적 질문 할당
   - 시장동향 Agent: "강남구 실거래가 변화율은?"
   - 수요분석 Agent: "강남구 인구 유입 동향은?"
```

**장점**:
- 🎯 필요한 Agent만 선택적 활성화 (비용 절감)
- 📊 체계적인 분석 구조 사전 설계
- 🔧 Agent별로 구체적 질문 할당

---

#### **Layer 3: Domain Agent (10개 전문 Agent)**

**10개 Agent 구성** (추정):

| Agent | 역할 | 사용 Tool |
|-------|------|-----------|
| 시장동향 Agent | 실거래가, 거래량 분석 | 국토부 API, 내부 매물 DB |
| 단지인사이트 Agent | 단지별 특성 비교 | 단지정보 DB, 리뷰 데이터 |
| 수요분석 Agent | 인구 이동, 수요 추세 | 통계청 데이터 |
| 공급현황 Agent | 입주 예정, 분양 정보 | 청약홈 API |
| 개발계획 Agent | 재개발, 인프라 계획 | 지자체 공공데이터 |
| 교통인프라 Agent | 역세권, 교통 접근성 | 지도 API, 교통 데이터 |
| 학군분석 Agent | 학교 정보, 학군 평가 | 교육부 데이터 |
| 가격적정성 Agent | KB시세, 호가 비교 | KB부동산, 매물 DB |
| 투자수익률 Agent | 임대수익률, 매매차익 | 전월세 DB, 과거 시세 |
| 리스크평가 Agent | 규제, 시장 리스크 | 뉴스, 정책 데이터 |

**병렬 실행 구조**:

```python
# 10개 Agent 동시 실행
async def analyze_body_section(query, plan):
    tasks = []
    
    for agent_name in plan.selected_agents:
        agent = get_agent(agent_name)
        task = agent.analyze(plan.questions[agent_name])
        tasks.append(task)
    
    # 병렬 실행 (10개 LLM 호출 동시 진행)
    results = await asyncio.gather(*tasks)
    
    return results

# 예시 실행 시간:
# - 순차 실행: 10개 × 3초 = 30초
# - 병렬 실행: max(3초) = 3초
# → 10배 속도 향상!
```

**실제 Agent 동작 예시**:

```
수요분석 Agent:

질문: "강남구 인구 유입 동향은?"
    ↓
Tool 호출: get_population_movement("강남구", "2024")
    ↓
결과: {
    "전입인구": 2847명/월,
    "증가율": 8.1%,
    "주요연령": "30-40대",
    "전입지역": "서울 타구 60%, 경기 30%"
}
    ↓
LLM 분석:
"강남구는 월평균 2,847명이 전입하고 있으며,
전년 동기 대비 8.1% 증가했습니다.
특히 30-40대 가족 단위 전입이 많아
학군 수요가 지속적으로 증가하고 있습니다."
```

---

#### **Layer 4: Tool Sets (50+ Tools)**

**3 Layer 데이터 구조**:

```
┌─────────────────────────────────────────────────┐
│           내부 데이터 (네이버페이 보유)          │
├─────────────────────────────────────────────────┤
│ • 매물 정보: 400만개 (아파트, 오피스텔 등)      │
│ • 단지 정보: 평면도, 시설, 커뮤니티             │
│ • 거래 이력: 과거 매물 가격 변동                │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│          공공 데이터 (정부/공공기관)             │
├─────────────────────────────────────────────────┤
│ • 국토교통부: 실거래가, 전월세 신고              │
│ • 통계청: 인구 이동, 가구 수                     │
│ • 청약홈: 분양 정보, 입주 예정                   │
│ • 지자체: 도시계획, 재개발 정보                  │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│               외부 데이터 (크롤링)               │
├─────────────────────────────────────────────────┤
│ • 뉴스: 부동산 관련 기사 (네이버 뉴스)           │
│ • 교통: 지하철 노선, 버스 정보                   │
│ • 인프라: 학교, 병원, 쇼핑몰 위치                │
└─────────────────────────────────────────────────┘
```

**Tool 예시 (시장동향 Agent용)**:

```python
class MarketToolSet:
    """시장동향 Agent가 사용하는 Tool 모음"""
    
    def get_trade_price_trend(self, region: str, period: str):
        """실거래가 추이 조회"""
        # 국토부 API 호출
        return {
            "avg_price": 150000,  # 평당 만원
            "change_rate": 5.2,   # %
            "trade_count": 120
        }
    
    def get_trade_volume(self, region: str):
        """거래량 조회"""
        # 내부 DB 쿼리
        return {"monthly_trades": 45}
    
    def get_price_index(self, region: str):
        """KB 부동산 지수"""
        # KB API 호출
        return {"index": 105.2}
```

**실제 사용 흐름**:

```
수요분석 Agent가 질문 받음: "강남구 인구 유입 동향?"
    ↓
Agent가 Plan Agent로부터 받은 Tool 목록 확인
    ↓
필요한 Tool 선택 및 호출:
    - population_tool.get_migration_stats("강남구")
    - population_tool.get_age_distribution("강남구")
    ↓
Tool 결과를 LLM에 전달:
    "다음 데이터를 분석해줘: {tool_results}"
    ↓
Agent가 최종 분석 결과 반환
```

---

### 2.4 전체 Flow 예시

```
사용자: "서울 강남구 부동산 투자 분석 보고서 작성해줘"
                        ↓
┌─────────────────────────────────────────────────┐
│              Layer 2: Plan Agent                 │
│                                                  │
│ 1. 질의 분석                                     │
│    - 범위: 강남구                                │
│    - 관점: 투자 (수익성 + 안정성)                │
│    - 깊이: 전문가 수준                           │
│                                                  │
│ 2. Agent 선택                                    │
│    ✅ 시장동향, 단지분석, 수요분석...            │
│    (10개 중 7개 선택)                            │
│                                                  │
│ 3. Main Plan 생성                                │
│    {주제, 목표, 세부계획...}                     │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│          Layer 1: Section Agent (Body)           │
│                                                  │
│ Main Plan을 받아 Body Section 생성 시작           │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│     Layer 3: Domain Agents (병렬 실행)           │
│                                                  │
│  [시장동향]  [단지분석]  [수요분석]  ...         │
│      ↓          ↓          ↓                     │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│          Layer 4: Tool Sets (50+ Tools)          │
│                                                  │
│  [국토부API]  [매물DB]  [통계청API]  ...         │
└─────────────────────────────────────────────────┘
                        ↓
                7개 Agent 결과 취합
                        ↓
┌─────────────────────────────────────────────────┐
│      Layer 1: Section Agent (나머지 섹션)         │
│                                                  │
│ Body 완성 → Background 생성                      │
│           → Conclusion 생성                      │
│           → Introduction 생성                    │
└─────────────────────────────────────────────────┘
                        ↓
              최종 보고서 완성!
```

---

### 2.5 실제 결과물 (Preview)

강연 자료의 49-50페이지에 실제 생성된 보고서 이미지가 있습니다:

**보고서 구조**:
```
┌─────────────────────────────────────┐
│  2024-2025년 서울·경기·부산 부동산  │
│        시장 전망 보고서              │
└─────────────────────────────────────┘

I. 개요 요약
  - 2024-2025년 시장 전망 요약
  - 주요 트렌드 및 예측

II. 배경(Background)
  1. 거제 개발 이력
  2. 경기 · 부산 주요 개발사업
  3. 부동산 규제 현황
  ...

III. 본문(Body)
  1. 지역별 가격동향 및 특성
     - 서울: 5대 권역 분석
     - 경기: 도시별 분석
     - 부산: 해운대/동래 중심
  
  2. 전세가 관 전망 (연령별계층)
     [그래프: 22Q1~24Q2 추이]
  
  3. 규제 동향 및 중장기 정책 전망
  ...

IV. 결론
  - 종합 의견 및 투자 제언
```

**특징**:
- 📊 데이터 기반 그래프/표 포함
- 📝 전문가 수준의 문장 품질
- 🎯 논리적으로 연결된 섹션 구조
- 📄 20-30페이지 분량

---

## 🎯 Part 3: AI 집찾기 + 대출 연계

### 3.1 서비스 개요

**문제 인식**:
```
✅ 집 찾기: 완료
❌ 실제 구매: 여전히 복잡

1. 내가 이 집을 살 수 있나? (LTV/DSR 계산)
2. 대출은 어디서 얼마나 받아야 하나?
3. 최저 금리는 어디인가?
```

**해결 방안**: AI 집찾기 + 대출 통합

```
[사용자 입력]
  ↓
연봉: 6,000만원
자본금: 3억원
희망지역: 용산구
  ↓
[AI 자동 계산]
  ↓
LTV: 최대 3억 5천만원 대출 가능
DSR: 연 2,000만원 원리금 상환 가능
→ 구매 가능 금액: 6억 5천만원
  ↓
[AI 집찾기 필터링]
  ↓
용산구 6억 5천만원 이하 매물만 추천
  ↓
[대출 상품 비교]
  ↓
• 케이뱅크: 3.86% (주담대)
• 카카오뱅크: 3.99%
• 하나은행: 4.05%
  ↓
[원클릭 신청]
```

---

### 3.2 기술 구조

**LTV/DSR 자동 계산**:

```python
class LoanCalculator:
    def calculate_available_amount(self, income, capital, property_price):
        """구매 가능 금액 계산"""
        
        # LTV (Loan to Value): 주택가격 대비 대출 한도
        ltv_limit = property_price * 0.7  # 70% (규제지역 기준)
        
        # DSR (Debt Service Ratio): 소득 대비 원리금 상환 비율
        annual_payment_limit = income * 0.4  # 연소득의 40%
        
        # 월 상환액 = 대출액 × (이자율/12) / (1-(1+이자율/12)^-개월수)
        interest_rate = 0.04  # 4% 가정
        months = 360  # 30년
        
        max_loan_by_dsr = self.calculate_loan_by_monthly_payment(
            annual_payment_limit / 12, 
            interest_rate, 
            months
        )
        
        # 실제 대출 가능액 = min(LTV 한도, DSR 한도)
        max_loan = min(ltv_limit, max_loan_by_dsr)
        
        # 구매 가능 금액 = 자본금 + 대출 가능액
        return capital + max_loan
```

**대출 상품 비교**:

```python
class LoanProductComparator:
    async def compare_products(self, user_info, property_info):
        """여러 은행 대출 상품 비교"""
        
        banks = ["케이뱅크", "카카오뱅크", "하나은행", ...]
        
        tasks = [
            self.get_loan_rate(bank, user_info, property_info)
            for bank in banks
        ]
        
        # 병렬로 각 은행 API 호출
        rates = await asyncio.gather(*tasks)
        
        # 금리 순 정렬
        return sorted(rates, key=lambda x: x['rate'])
```

---

## 📊 종합 분석

### 1. 기술적 성과

| 지표 | 개선 전 | 개선 후 | 개선율 |
|------|---------|---------|--------|
| **검색 속도** | 15초 | 4초 | **73% ↓** |
| **탐색 시간** | 1분 7초 | 30초 | **53% ↓** |
| **편의성** | 필터 11번 클릭 | 자연어 1번 | **90% ↓** |

---

### 2. 핵심 기술 요약

#### **① 속도 개선 (Latency 해결)**

```
1. Prompt Cache
   - 시스템 프롬프트 캐싱
   - 비용 90% 절감

2. Micro Prompting
   - 큰 프롬프트를 작은 단위로 분할
   - 병렬 처리 가능

3. Coroutine
   - Kotlin 비동기 처리
   - 10배 속도 향상 가능

4. Opensearch
   - 지리공간 고속 검색
   - 0.1초 이내 조회
```

#### **② 품질 개선 (Hallucination 해결)**

```
1. MCP (Model Context Protocol)
   - 레거시 시스템 연결
   - 실시간 데이터 제공

2. RAG
   - 400만 매물 DB 활용
   - 정확한 정보 기반 답변

3. 4 Layer 아키텍처
   - 전문 Agent 10개
   - 50+ Tools 활용
```

#### **③ 운영 효율 (Prompt 관리)**

```
1. Spring Cloud Config
   - Git 기반 중앙 관리
   - 버전 관리 자동화

2. Spring Cloud Bus
   - 실시간 변경 전파
   - 재배포 없이 적용
```

---

### 3. 우리 프로젝트 적용 전략

#### **단계별 적용 로드맵**:

##### **Phase 1: MVP (1-2주)**
```python
# 기본 RAG + 프롬프트 캐시
class SimpleHousingAssistant:
    def __init__(self):
        self.system_prompt = load_cached_prompt()
        self.vector_db = ChromaDB()
    
    async def search(self, query):
        # 1. 벡터 검색
        docs = self.vector_db.search(query)
        
        # 2. LLM 호출 (캐시 활용)
        response = await claude.generate(
            system=self.system_prompt,  # 캐시됨
            context=docs,
            query=query
        )
        return response
```

**적용 기술**:
- ✅ Prompt Cache (Anthropic API 내장)
- ✅ 간단한 RAG (Chroma/FAISS)
- ✅ Async 처리 (asyncio)

**예상 효과**:
- 응답 속도: 5-10초
- 비용: 요청당 $0.01-0.02

---

##### **Phase 2: 고도화 (2-4주)**

```python
# Domain Agent 추가
class MarketAgent:
    async def analyze(self, location):
        # Tool 호출
        price_data = await get_trade_price(location)
        volume_data = await get_trade_volume(location)
        
        # LLM 분석
        analysis = await llm.analyze(price_data, volume_data)
        return analysis

class PropertyAgent:
    async def analyze(self, property_id):
        # 매물 상세 분석
        ...

# 병렬 실행
results = await asyncio.gather(
    MarketAgent().analyze(location),
    PropertyAgent().analyze(property_id)
)
```

**적용 기술**:
- ✅ 3-5개 Domain Agent
- ✅ Tool Sets 구축
- ✅ 병렬 처리 최적화

**예상 효과**:
- 응답 속도: 3-5초
- 분석 깊이: 2-3배 향상

---

##### **Phase 3: 프로덕션 (4-8주)**

```python
# 4 Layer 완성
class FullReportGenerator:
    async def generate(self, query):
        # Layer 2: Plan 수립
        plan = await PlanAgent().create_plan(query)
        
        # Layer 3: 선택된 Agent 실행
        agents = [get_agent(name) for name in plan.agents]
        results = await asyncio.gather(*[a.analyze() for a in agents])
        
        # Layer 1: 맥락 누적 생성
        body = integrate_results(results)
        background = generate_background(body)
        conclusion = generate_conclusion(body, background)
        intro = generate_intro(body, background, conclusion)
        
        return create_report(intro, background, body, conclusion)
```

**적용 기술**:
- ✅ 완전한 4 Layer 구조
- ✅ 10+ Domain Agents
- ✅ Opensearch/Pinecone
- ✅ Config 서버 (FastAPI + Redis)

**예상 효과**:
- 응답 속도: 2-3초
- 전문가급 보고서 생성

---

### 4. 투자 대비 효과 분석

| 단계 | 개발 기간 | 기술 난이도 | 비용 절감 | 품질 향상 | ROI |
|------|-----------|-------------|-----------|-----------|-----|
| Phase 1 | 1-2주 | ⭐⭐ | 50% | 2배 | ⭐⭐⭐⭐⭐ |
| Phase 2 | 2-4주 | ⭐⭐⭐ | 70% | 3배 | ⭐⭐⭐⭐ |
| Phase 3 | 4-8주 | ⭐⭐⭐⭐⭐ | 90% | 5배 | ⭐⭐⭐ |

**추천**: Phase 1부터 시작해서 단계적 확장

---

## 💡 결론 및 제언

### 1. 핵심 인사이트

**① "토큰 제약 극복 = 쪼개기 + 캐싱 + 병렬화"**
```
Micro Prompting + Prompt Cache + Coroutine
= 10배 속도 향상 + 90% 비용 절감
```

**② "품질 확보 = 실제 데이터 + 전문 Agent"**
```
MCP/RAG + Domain Agents + Tool Sets
= Hallucination 제거 + 전문가급 분석
```

**③ "맥락 누적 생성 = 일관성의 핵심"**
```
Body → Background → Conclusion → Introduction
= 논리적 일관성 + 정확한 요약
```

---

### 2. 우리 프로젝트 적용 시 우선순위

**즉시 적용 (높은 ROI)**:
1. ✅ **Prompt Cache**: Anthropic API 파라미터만 추가하면 됨
2. ✅ **asyncio 병렬화**: Python 기본 라이브러리
3. ✅ **간단한 RAG**: Chroma/FAISS로 1주일 이내 구축

**중기 적용 (2-4주)**:
4. ✅ **3-5개 Domain Agent**: 시장/매물/수요 분석
5. ✅ **Tool Sets 구축**: 5-10개 핵심 Tool
6. ✅ **맥락 누적 생성**: 간단한 Section 관리

**장기 적용 (1-2개월)**:
7. ⏳ **Opensearch**: 대용량 데이터 처리 필요 시
8. ⏳ **Plan Agent**: Agent 수가 10개 이상일 때
9. ⏳ **Config 서버**: 팀 규모 확대 시

---

### 3. 리스크 및 고려사항

#### **① 비용 관리**
```
네이버페이 규모 추정:
- 일 사용자: 10,000명
- 평균 토큰: 30,000 input + 2,000 output
- 월 비용: $50,000~100,000 (추정)

우리 프로젝트:
- Prompt Cache 필수 (90% 절감)
- Agent 수 최소화 (3-5개로 시작)
- Streaming으로 사용자 경험 개선
```

#### **② 품질 관리**
```
- Agent 결과 검증 로직 필요
- Tool 결과 신뢰성 확보
- 정기적인 프롬프트 A/B 테스트
```

#### **③ 인프라**
```
- Opensearch: 자체 호스팅 vs 관리형 (AWS OpenSearch)
- Config 서버: Redis vs Consul vs Etcd
- 모니터링: LangSmith, Weights & Biases
```

---

### 4. 다음 단계

**Week 1-2: POC 개발**
- [ ] Prompt Cache 적용된 기본 RAG 구현
- [ ] 3개 Tool 구축 (매물 검색, 시세 조회, 뉴스)
- [ ] 성능 측정 (속도, 비용, 품질)

**Week 3-4: Agent 추가**
- [ ] 3개 Domain Agent 개발
- [ ] asyncio 병렬화 구현
- [ ] Tool Sets 확장 (5-7개)

**Week 5-8: 고도화**
- [ ] Section Agent 구현 (맥락 누적 생성)
- [ ] Plan Agent 추가
- [ ] 벡터 DB 최적화

**이후: 프로덕션 준비**
- [ ] Opensearch 도입 검토
- [ ] Config 서버 구축
- [ ] 모니터링 체계 확립

---

이상으로 네이버페이 부동산 AI 기술 세션 내용을 정리했습니다. 

특히 **Prompt Cache + Micro Prompting + Coroutine** 조합으로 73% 속도 개선을 달성한 점과, **4 Layer 아키텍처**로 토큰 제약을 극복하면서도 전문가급 분석을 제공한 점이 핵심!