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


### **2. 🎯 신뢰도 등급(Target) 산출 로직**

#### **타겟**: 신뢰도 등급 (A/B/C)

### 2-1. **생성 프로세스 (4단계)**

**1️⃣ 거래성사율 계산**
```python
거래성사율 = 거래완료 / (거래완료 + 등록매물)
```
- **의미**: 전체 거래 활동 중 실제로 성사된 비율

**2️⃣ 지역별 표준화 (Z-score)**
- 지역별 평균(AVG)과 표준편차(STDEV) 계산
- 지역평균 = 각 지역의 거래성사율 평균
- 지역표준편차 = 각 지역의 거래성사율 표준편차

- **Z-score 계산** 
```python
Z_score = (개별_거래성사율 - 지역평균) / 지역표준편차
```

- **목적**: 지역별 시장 특성 차이를 보정
- **효과**: 같은 지역 내에서 상대적 성과 평가

- 이렇게 계산한 이유
![1765866346208](image/README/1765866346208.png)
1. 같은 지역 내에서 상대적 성과 평가
2. 지역별 시장 특성 차이를 보정

**3️⃣ 대표자 구분별 가중치 적용**
```python
대표자구분_가중치 = {
    '공인중개사': 0.0,     # 기준 (96.6% - 가장 일반적)
    '법인': +0.2,          # 가점 (2.4% - 조직 안정성 우수)
    '중개보조원': -0.1,    # 감점 (0.3% - 자격 수준 낮음)
    '중개인': -0.3         # 감점 (0.8% - 자격 수준 낮음)
}
```
![1765877802472](image/README/1765877802472.png)

**가중치 설정 근거:**
- **법인 (+0.2)**: 법인 형태로 조직 안정성 우수, 자본금 요구사항 충족, 지속 가능성 높음 (비율 2.4%)
- **공인중개사 (0.0)**: 국가 공인 자격증 보유, 가장 일반적이므로 기준점 설정 (비율 96.6%)
- **중개보조원 (-0.1)**: 보조 역할만 가능, 대표 등록이 이례적 (비율 0.3%)
- **중개인 (-0.3)**: 공인중개사보다 낮은 등급, 제한적 자격, 전문성 부족 우려 (비율 0.8%)

![1765866632105](image/README/1765866632105.png)

**최종 Target 계산 = Z_score + 대표자구분_가중치**


**4️⃣ 분위수 기반 등급 분류**
![1765867424752](image/README/1765867424752.png)

```python
q30 = 30% 분위수  # C등급 상한
q70 = 70% 분위수  # B등급 상한

# 등급 분류
if Z_score_조정 <= q30:
    등급 = "C"  # 하위 30%
elif Z_score_조정 <= q70:
    등급 = "B"  # 중위 40%
else:
    등급 = "A"  # 상위 30%
```

#### **최종 타겟 분포**
| 등급 | 비율 | 개수 | 의미 |
|------|------|------|------|
| **A등급** | 30.2% | 106개 | 우수 중개사 |
| **B등급** | 39.9% | 140개 | 보통 중개사 |
| **C등급** | 29.9% | 105개 | 개선 필요 중개사 |

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
공인중개사수
공인중개사_비율 = 공인중개사수 / 총_직원수
```

**🟡 운영 경험 (4개)**
```python
운영기간_년 = (현재날짜 - 등록일) / 365.25
운영경험_지수 = np.exp(운영기간_년 / 10)
숙련도_지수 = 운영기간_년 * 공인중개사_비율 # 오래운영하고 공인중개사가 많을수록 높은 숙련도
운영_안정성 = (운영기간_년 >= 3).astype(int)  # 3년 이상 = 안정
```
![1765873124662](image/README/1765873124662.png)
* 중앙값(3.8년) 기준으로 안정적 운영 경험 구분

**🔵 조직 구조 (2개)**
```python
대형사무소 = (총_직원수 >= 2).astype(int)
직책_다양성 = 직책_종류_수  # 공인중개사, 중개보조원, 대표, 일반직원
```
![1765872775403](image/README/1765872775403.png)
* 총_직원수 평균이 1.93명으로, 2명을 기준으로 평균 이상의 조직 규모 구분

**🟣 대표자 구분 (4개)**
```python
# 범주형 변수를 이진 변수로 변환
대표_공인중개사 = (대표자구분명 == "공인중개사").astype(int)
대표_법인 = (대표자구분명 == "법인").astype(int)
대표_중개인 = (대표자구분명 == "중개인").astype(int)
대표_중개보조원 = (대표자구분명 == "중개보조원").astype(int)
```

#### 피처 요약
| 피처 그룹 | 개수 | 설명 |
|----------|------|------|
| 거래 지표 | 2개 | 거래 실적 관련 피처 (로그 변환) |
| 인력 지표 | 3개 | 직원 구성 및 전문성 |
| 운영 경험 | 4개 | 사업 운영 기간 및 안정성 |
| 조직 구조 | 2개 | 조직 규모 및 다양성 |
| 대표자 구분 | 4개 | 대표자 자격 |

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
![alt text](image.png)
#### 🎯 최종 성능 지표

```
  Test Accuracy:   85.92%
  Train Accuracy:  82.50%
  과적합 정도:      -3.42% (과적합 완벽 해소)
  CV Mean:         79.64% (±6.25%)
  CV vs Test:      -6.27%
```

#### 📈 등급별 상세 성능

| 등급 | Precision | Recall | F1-Score | 해석 |
|------|-----------|--------|----------|------|
| **A등급** | 0.83 | 0.86 | 0.84 | 준수한 성능 유지 |
| **B등급** | 0.88 | 0.75 | 0.81 | 정밀도/재현율 균형 개선 |
| **C등급** | 0.88 | **1.00** | 0.93 | 완벽한 재현율 → 문제 사무소 100% 감지 (리스크 관리 탁월) |

- Precision (정밀도): "모델이 A등급이라고 예측한 것 중, 실제로 A등급인 비율"
- Recall (재현율): "실제 A등급인 것 중, 모델이 A등급이라고 예측한 비율"
- F1-Score: Precision과 Recall의 둘 다 고려한 균형 지표

#### 📊 혼동 행렬 (Confusion Matrix)
![혼동 행렬](results/validation/01_confusion_matrix.png)


---

### **6. SHAP 분석** 🔍

#### 📋 A등급 - 주요 피처 (중요도 순)

```
1. 총거래활동량_log      0.2871 (평균 기여도)
2. 등록매물_log          0.1958 
3. 운영_안정성           0.0315 
4. 공인중개사_비율       0.0269 
5. 대표_법인             0.0136 
```
![SHAP 분석](results/shap_importance_A.png)

#### 📋 B등급 - 주요 피처 (중요도 순)

```
1. 총거래활동량_log      0.1389 (활동량 중요)
2. 등록매물_log          0.0940 
3. 공인중개사_비율       0.0465 
4. 총_직원수             0.0211 
5. 운영_안정성           0.0175 
* B등급은 A와 C 사이의 중간적 성격으로, SHAP 절대값이 A/C 등급 대비 상대적으로 낮게 형성됨 (0.14 내외)
```
![SHAP 분석](results/shap_importance_B.png)

#### 📋 C등급 - 주요 피처 (중요도 순)

```
1. 총거래활동량_log      0.3010 (활동량 저조)
2. 등록매물_log          0.1792 
3. 운영_안정성           0.0265 
4. 총_직원수             0.0251 

```
![SHAP 분석](results/shap_importance_C.png)

![alt text](image-1.png)

**✅ 인사이트**: 
- **A등급**: '총거래활동량'과 '등록매물수'가 압도적으로 높으며, 이는 신뢰도를 형성하는 핵심 기반임
- **B등급**: 활동량이 A와 C의 중간 수준이며, 운영 안정성 등 보조 지표가 일부 기여함
- **C등급**: 거래 및 매물 활동이 현저히 낮아 '성실성 부족'이 주요 감점 요인으로 작용함 (재현율 100% 감지)


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
├── 📂 pipeline/                    # 모델 파이프라인
│   ├── _00_load_data.py           # 데이터 로드
│   ├── _01_create_target.py       # 타겟 생성 (A/B/C 등급)
│   ├── _02_create_features.py     # 피처 엔지니어링 (16개)
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