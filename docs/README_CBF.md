# Content-Based Filtering (CBF) - 유사 매물 추천 시스템

## 📋 개요

Content-Based Filtering을 활용하여 현재 매물과 유사한 매물 Top 3를 추천하는 시스템입니다. 부동산 온도 벡터 기반의 유사도 계산을 통해 사용자에게 관련성 높은 매물을 제공합니다.

## 🎯 주요 기능

### 1. 다단계 필터링
현재 매물과 유사한 매물을 찾기 위해 다음 조건을 순차적으로 적용합니다:

1. **같은 행정동** - 동일한 지역(동) 내의 매물만 추천
2. **A등급(골드) 중개사** - 신뢰도가 높은 중개사의 매물만 선별
3. **같은 거래유형** - 월세, 전세, 매매, 단기임대 등 동일한 거래 방식
4. **유사한 가격대** - ±30% 범위 내의 가격
5. **온도 벡터 유사도** - 5가지 부동산 온도 기반 유클리드 거리 계산

### 2. 가격 유사도 계산

거래유형별로 다른 가격 기준을 적용합니다:

| 거래유형 | 가격 계산 방식 |
|---------|--------------|
| **월세/단기임대** | `보증금 + (월세 × 100)` |
| **전세** | `전세가` |
| **매매** | `매매가` |

모든 거래유형에서 **±30% 범위** 내의 매물만 추천합니다.

### 3. 온도 벡터 기반 유사도

5가지 부동산 온도를 벡터로 표현하여 유클리드 거리를 계산합니다:

```python
temperature_vector = [
    safety,        # 안전 온도
    convenience,   # 편의 온도
    pet,          # 반려동물 온도
    traffic,      # 교통 온도
    culture       # 문화 온도
]
```

**유사도 계산:**
```python
distance = √Σ(current_temp[i] - candidate_temp[i])²
```

거리가 가까울수록 유사한 매물로 판단하여 Top 3를 선정합니다.

## 📊 성능 분석

전체 매물(약 9,000개)에 대한 추천 커버리지 분석 결과:

📌 추천 0개: 1,729개 매물 (17.44%)
📌 추천 1개: 941개 매물 (9.49%)
📌 추천 2개: 651개 매물 (6.57%)
📌 추천 3개: 6,593개 매물 (66.50%)

## 📁 관련 파일

### Backend
- `apps/backend/apps/listings/views.py` - API 엔드포인트
- `apps/backend/apps/listings/utils/temperature_utils.py` - 온도 계산 유틸

### Frontend
- `apps/frontend/src/app/landDetail/[id]/page.tsx` - 페이지 컴포넌트
- `apps/frontend/src/api/landApi.ts` - API 클라이언트
- `apps/frontend/src/types/land.ts` - 타입 정의

### Analysis
- `notebooks/test_similar_listings_coverage.ipynb` - 커버리지 분석

