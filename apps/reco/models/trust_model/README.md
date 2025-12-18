# 🏢 중개사 신뢰도 평가 다중분류 모델 (Trust Model)

### 🎯 **목적**
부동산 중개사의 신뢰도를 **A/B/C 등급**으로 분류하는 ML

### 1. 📊 **데이터**
[서울특별시 중개사 정보]

- 크롤링 데이터의 중개소 정보
- V-WORLD API 중개업소 정보
- V-WORLD API 중개업자 정보 

### 1-1. 📊 **사용한 데이터 주요 정보**
**1️⃣ 크롤링한 매물 중개사 정보**
| 컬럼명 | 설명 | 출처 |
|--------|------|------|
| 중개사무소명 | 중개사무소 이름 | 크롤링 |
| 대표자 | 대표자 이름 | 크롤링 |
| 전화번호 | 연락처 | 크롤링 |
| 주소 | 사무소 주소 | 크롤링 |
| 등록번호 | 사업자등록번호 | 크롤링 |
| 거래완료 | 완료된 거래 건수 | 크롤링 |
| 등록매물 | 현재 등록된 매물 수 | 크롤링 |

**2️⃣ V-WORLD API 중개업소 정보**
| 컬럼명 | 설명 | 출처 |
|--------|------|------|
| jurirno | 등록번호 | API (office) |
| brkrNm | 대표자 이름 | API (office) |
| bsnmCmpnm | 중개사무소 이름 | API (office) |
| sttusSeCode | 상태구분 코드 (1:영업중,2:휴업,3:휴업연정,4:실효5:폐업,6:전출,7:등록취소,8:업무정지) | API (office) |
| registDe | 등록일자 | API (office) |
| ldCodeNm | 지역 | API (office) |
| estbsBeginDe | 보증보험 시작일 | API (office) |
| estbsEndDe | 보증보험 종료일 | API (office) |

**3️⃣ V-WORLD API 중개업자 정보**
| 컬럼명 | 설명 | 출처 |
|--------|------|------|
| jurirno | 법인등록번호 | API (brokers) |
| bsnmCmpnm | 사업자 상호 | API (brokers) |
| brkrNm | 중개업자 이름 | API (brokers) |
| brkrAsortCode | 중개보조원, 공인중개사, 법인, 중개인 | API (brokers) |
| crqfcAcqdt | 자격증 취득일자 | API (brokers) |
| crqfcNo | 자격증번호 | API (brokers) |
| ofcpsSeCodeNm | 대표, 일반 | API (brokers) |

### 1-2. 📊 **데이터 통합 과정**

**Step 1: 크롤링 데이터 + V-WORLD 중개업소 정보 매칭**
- **매칭 키**: `중개사무소명 + 대표자명`
- **목적**: 크롤링한 중개사 정보에 V-WORLD API의 중개업소 정보결합
- **결과**: 크롤링 데이터에 중개업소의 정보 추가

**Step 2: Step 1 결과 + V-WORLD 중개업자 정보 매칭 (1차)**
- **매칭 키**: `등록번호 + 중개사무소명`
- **목적**: 각 중개사무소에 소속된 공인중개사, 중개보조원 등 직원 정보 추가
- **결과**: 중개사무소별 인력 구성 정보 확보 (공인중개사 수, 중개보조원 수 등)

**Step 3: 2차 매칭 (보완)**
- **매칭 키**: `중개사무소명 + 대표자명` (1차 매칭 실패 시)
- **목적**: 등록번호가 불일치하거나 누락된 경우에도 중개업자 정보 최대한 확보
- **추가 처리**: 2차 매칭된 중개사무소의 모든 직원 정보 저장
- **최종 결과**: **351개 중개사무소**의 통합 데이터 생성


### **2. 🎯 신뢰도 등급(Target) 산출 로직 (데이터 누수 방지)**

#### **타겟**: 신뢰도 등급 (A/B/C)

### 2-1. **올바른 파이프라인 순서**

**🚨 중요: 데이터 누수(Data Leakage) 방지를 위한 올바른 순서**

```
1️⃣ Raw Data
2️⃣ 기본 클렌징 (NaN, 타입 변환)
3️⃣ Train / Test Split
4️⃣ [Train 기준]
   - 지역 평균 / 표준편차 계산
   - 자격점수 평균 / 표준편차 계산
   - Z-score → target 생성
5️⃣ [Test 기준]
   - Train에서 계산한 값으로만 Z-score 적용
6️⃣ Feature 생성
7️⃣ 모델 학습 / 평가
```

### 2-2. **Target 생성 프로세스**

**1️⃣ 거래성사율 계산**
```python
거래성사율 = 거래완료 / (거래완료 + 등록매물)
```
- **의미**: 전체 거래 활동 중 실제로 성사된 비율

**2️⃣ Train 기준 지역별 표준화 (Z-score)**
```python
# Train 데이터에서만 통계 계산
train_regional_stats = train_df.groupby("지역명")["거래성사율"].agg(['mean', 'std'])

# Train과 Test 모두에 Train 통계 적용
Z_score = (거래성사율 - train_지역평균) / train_지역표준편차
```

- **목적**: 지역별 시장 특성 차이를 보정
- **핵심**: Test 데이터 정보가 Train 과정에 누수되지 않도록 Train 통계만 사용

**3️⃣ Train 기준 자격점수 표준화**
```python
# Train 데이터에서만 자격점수 통계 계산
train_qual_mean = train_df["자격점수"].mean()
train_qual_std = train_df["자격점수"].std()

# Train과 Test 모두에 Train 통계 적용
Qual_Zscore = (자격점수 - train_qual_mean) / train_qual_std
```

**4️⃣ 복합 Z-score 및 가중치 적용**
```python
# 성사율 70% + 자격 30% 
Zscore = (Performance_Zscore * 0.7) + (Qual_Zscore * 0.3)

# (기존의 '대표자구분 가중치 2차 보정' 로직은 삭제. - 이중 보정 제거로 거품 제거)
Zscore_조정 = Zscore 
```

**5️⃣ Train 기준 분위수로 등급 분류**
```python
# Train 데이터에서만 분위수 계산
q30 = train_df["Zscore_조정"].quantile(0.30)
q70 = train_df["Zscore_조정"].quantile(0.70)

# Train과 Test 모두에 동일한 기준 적용
def classify_grade(z):
    if z <= q30: return "C"      # 하위 30%
    elif z <= q70: return "B"    # 중위 40%
    else: return "A"             # 상위 30%
```

#### **최종 타겟 분포** (전체 데이터 351개 기준)
| 등급 | 비율 | 개수 | 의미 |
|------|------|------|------|
| **A등급** | 29.6% | 104개 | 우수 중개사 |
| **B등급** | 42.2% | 148개 | 보통 중개사 |
| **C등급** | 28.2% | 99개 | 개선 필요 중개사 |

---

### **3. 피처 엔지니어링** 🏗️

**🔴 거래 지표 (2개)**
```python
# 로그 변환을 통한 스케일 조정
등록매물_log = np.log1p(등록매물)
총거래활동량_log = np.log1p(거래완료 + 등록매물)
```

**💡 로그 변환 이유:**
1. **왜도(Skewness) 해소**: 거래량 데이터는 극단적으로 치우친 분포 (소수가 매우 많고, 대다수가 적음)
2. **이상치 영향 감소**: 거래량 1000건과 10건의 차이를 완화 (log(1000)≈6.9, log(10)≈2.3)
3. **스케일 정규화**: 다른 피처들(0~1 범위)과 비슷한 스케일로 조정하여 모델 학습 안정화


**🟢 인력 지표 (3개)**
```python
총_직원수
중개보조원_비율
자격증_보유비율
```
- **공인중개사_비율**은 '중개보조원_비율'과 높은 상관관계(-0.97)로 인해 다중공선성 문제 방지 차원에서 제외

**🟡 운영 경험 (4개)**
```python
운영기간_년 = (현재날짜 - 등록일) / 365.25
숙련도_지수 = 운영기간_년 * 공인중개사_비율 
운영_안정성 = (운영기간_년 >= 3).astype(int)  # 3년 이상 안정
```
- **운영경험_지수**는 단순 지수형태라 '숙련도_지수'로 통합 대체
- **숙련도_지수**: 단순히 오래된 것보다, 전문 자격증(공인중개사) 비율이 높으면서 오래된 곳에 가점 부여
![1765873124662](image/README/1765873124662.png)
* 중앙값(3.8년) 기준으로 안정적 운영 경험 구분

**🔵 조직 구조 (2개)**
```python
```python
대형사무소 = (총_직원수 >= 2).astype(int)
# 직책_다양성은 실효성이 낮아 제외됨
```
![1765872775403](image/README/1765872775403.png)
* 총_직원수 평균이 1.93명으로, 2명을 기준으로 평균 이상의 조직 규모 구분

**🟣 대표자 구분 (4개)**
```python
# 범주형 변수를 이진 변수로 변환
```python
# 대표자 구분 중 '법인'과 '공인중개사'만 주요 피처로 사용
대표_공인중개사 = (대표자구분명 == "공인중개사").astype(int)
대표_법인 = (대표자구분명 == "법인").astype(int)
# 나머지(중개인, 중개보조원 등)는 비율이 극히 낮아 제외
```

#### 피처 요약
| 피처 그룹 | 개수 | 설명 |
|----------|------|------|
| 거래 지표 | 3개 | 등록매물_log, 총거래활동량_log, 1인당_거래량_log |
| 인력 지표 | 3개 | 총_직원수, 중개보조원_비율, 자격증_보유비율 |
| 운영 경험 | 3개 | 운영기간_년, 숙련도_지수, 운영_안정성 |
| 조직 구조 | 1개 | 대형사무소 |
| 대표자 구분 | 2개 | 대표_공인중개사, 대표_법인 |
| 지역/기타 | 2개 | 지역_경쟁강도, 1층_여부 |

![피처-신뢰도등급 상관계수](results/validation/02_feature_target_correlation_bar.png)

---

### **4. 모델학습** 🤖

#### 하이퍼파라미터 최적화

**GridSearchCV로 144개 조합 탐색:**
```python
# 탐색 범위
param_grid = {
    'C': [0.001, 0.01, 0.1, 1, 10, 100],
    'penalty': ['l1', 'l2'],
    'solver': ['liblinear', 'saga'],
    'class_weight': [None, 'balanced'],
    'max_iter': [1000, 2000]
}

# 결과: CV 정확도 68.93% → 83.21% (14.28%p 향상)
```

#### 최적 모델: Logistic Regression
```python
model = LogisticRegression(
    C=1,                      # 정규화 강도 (GridSearchCV 최적값)
    penalty='l1',             # L1 정규화 (피처 선택 효과)
    solver='saga',            # L1 지원 solver
    class_weight='balanced',  # 클래스 불균형 처리
    max_iter=1000,            # 충분한 반복
    random_state=42           # 재현성 확보
)
```

**최적 하이퍼파라미터 선택 이유**
- ✅ **C=1**: 정규화 완화로 모델 표현력 향상 (0.01 → 1)
- ✅ **penalty='l1'**: 불필요한 피처 자동 제거 (L2 → L1)
- ✅ **solver='saga'**: L1 정규화 지원 및 빠른 수렴
- ✅ **class_weight='balanced'**: A/B/C 등급 불균형 자동 조정

#### 데이터 분할

- **Train/Test 분할**: 8:2 비율로 분할 (stratify로 등급 비율 유지)
- **표준화**: StandardScaler를 사용하여 평균 0, 표준편차 1로 정규화

#### 교차 검증

- **방법**: 5-Fold Stratified Cross-Validation (등급 비율 유지)
- **결과**: CV Mean 66.79% (±5.00%)

---

### **5. 모델 성능 평가** 📊
![alt text](image-2.png)
#### 🎯 최종 성능 지표

```
  Test Accuracy:   74.65%
  Train Accuracy:  81.07%
  과적합 정도:      6.42% (정상 범위 안착)
  CV Mean:         73.93% (±4.60%)
  CV vs Test:      -0.72%
```

#### 📈 등급별 상세 성능

| 등급 | Precision | Recall | F1-Score | 해석 |
|------|-----------|--------|----------|------|
| **A등급** | 0.79 | 0.75 | 0.77 | 준수한 식별력 유지 |
| **B등급** | 0.80 | 0.67 | 0.73 | 정밀도 상승, 재현율 하락 |
| **C등급** | 0.64 | 0.93 | 0.76 | 높은 재현율(0.93)로 문제 중개사 대부분 감지 성공 |

- Precision (정밀도): "모델이 A등급이라고 예측한 것 중, 실제로 A등급인 비율"
- Recall (재현율): "실제 A등급인 것 중, 모델이 A등급이라고 예측한 비율"
- F1-Score: Precision과 Recall의 둘 다 고려한 균형 지표

#### 📊 혼동 행렬 (Confusion Matrix)
![alt text](results/validation/01_confusion_matrix.png)


---

### **6. SHAP 분석** 🔍

#### 📋 A등급 - 주요 피처 (중요도 순)

```
1. 1인당_거래량_log      0.2066
2. 등록매물_log          0.1924
3. 총거래활동량_log      0.0649 
4. 총_직원수             0.0611 
5. 운영기간_년           0.0407 
```
![SHAP 분석](results/shap_importance_2.png)

#### 📋 B등급 - 주요 피처 (중요도 순)

```
1. 1인당_거래량_log      0.1180
2. 등록매물_log          0.0974 
3. 운영기간_년           0.0523 
4. 숙련도_지수           0.0464 
5. 총거래활동량_log      0.0414 
* B등급은 A와 C 사이의 중간적 성격으로, SHAP 절대값이 A/C 등급 대비 상대적으로 낮게 형성됨 (0.14 내외)
```
![SHAP 분석](results/shap_importance_1.png)

#### 📋 C등급 - 주요 피처 (중요도 순)

```
1. 등록매물_log          0.2181
2. 1인당_거래량_log      0.2169 
3. 총거래활동량_log      0.0821
4. 총_직원수             0.0792
5. 중개보조원_비율       0.0168 

```
![SHAP 분석](results/shap_importance_0.png)

**✅ 인사이트**: 
- **A등급/C등급 결정타**: 단순한 총량이 아닌 **'1인당 거래 효율성(1인당_거래량_log)'**과 **'매물 확보 능력(등록매물_log)'**이 가장 결정적.  
즉, "직원이 많아서 거래가 많은 것"보다 "직원 1명당 얼마나 잘 파느냐"가 신뢰도의 핵심
- **B등급의 특징**: 효율성 지표 외에도 **'운영기간'**과 **'숙련도'**가 상위권에 등장.  
폭발적인 실적은 없더라도, 오랫동안 안정적으로 운영해온 사무소들이 B등급을 형성하고 있음.
- **결론**: 모델은 **"알짜배기 영업(효율성)"**과 **"꾸준함(경력)"**을 높게 평가하여 신뢰도를 산정하고 있습니다.


## 📁 프로젝트 구조

```
apps/reco/models/trust_model/
├── 📂 data_preprocessing/          # 데이터 전처리
│   ├── _00_load_Landbroker.py
│   ├── _01_load_broker.py
│   ├── _02_load_brokerOffice.py
│   ├── _03_merge_all_brokers.py
│   ├── _04_clean_broker.py
│   └── _05_group_by_office.py
│
├── 📂 pipeline/                    # 모델 파이프라인 (데이터 누수 방지)
│   ├── _00_load_data.py           # 데이터 로드 및 기본 클렌징
│   ├── _01_create_target.py       # Train/Test Split
│   ├── _02_create_features.py     # Train 기준 Z-score 계산 및 Feature 생성
│   ├── _03_train.py               # 모델 학습
│   ├── _04_eval.py                # 모델 평가
│   └── _05_save_model.py          # 모델 저장
│
├── 📂 results/                     # 분석 결과
│   ├── validation/                # 검증 차트 (17개)
│   └── shap_importance_*.png      # SHAP 분석 결과
│
├── 📂 save_models/                 # 학습된 모델
│   └── temp_trained_models.pkl
│
├── 📄 analyze_shap.py                # SHAP 분석 스크립트
├── 📄 run_all.py                     # 전체 파이프라인 실행
├── 📄 model_validation_analysis.py   # 모델 검증 분석, EDA(현재 주피터로 되었는 것들 추가 예정)
└── 📄 README.md                      # 이 문서
```

---

## 🚀 실행 방법

### 데이터 수집 및 전처리 실행
```bash
python apps/reco/models/trust_model/data_preprocessing/_00_load_Landbroker.py
python apps/reco/models/trust_model/data_preprocessing/_01_load_broker.py
python apps/reco/models/trust_model/data_preprocessing/_02_load_brokerOffice.py
python apps/reco/models/trust_model/data_preprocessing/_03_merge_all_brokers.py
python apps/reco/models/trust_model/data_preprocessing/_04_clean_broker.py
python apps/reco/models/trust_model/data_preprocessing/_05_group_by_office.py
```
→ 파일 순서대로 실행

### 1️⃣ 전체 파이프라인 실행 (학습)
```bash
python apps/reco/models/trust_model/run_all.py
```

### 3️⃣ 분석 실행
```bash
# SHAP 분석
python apps/reco/models/trust_model/analyze_shap.py
```

```bash
# 모델 검증 분석, EDA(현재 주피터로 되었는 것들 추가 예정)
python apps/reco/models/trust_model/model_validation_analysis.py
```