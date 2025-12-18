
import nbformat as nbf
import os

# Absolute path target
NOTEBOOK_PATH = "c:/dev/study/eunjeong/SKN18-FINAL-1TEAM/apps/reco/models/trust_model/pipeline/visualization_analysis.ipynb"

nb = nbf.v4.new_notebook()

# === Cell 1: Markdown Title ===
text_1 = """# 📊 중개사 신뢰도 모델 분석 리포트

이 노트북은 학습된 모델(로지스틱 회귀)의 성능과 특성을 시각적으로 분석하기 위해 작성되었습니다.

### 분석 항목
1. **📉 학습 곡선 (Learning Curve)**: 과적합 여부 확인
2. **🔲 혼동 행렬 (Confusion Matrix)**: 등급별 예측 정확도 및 오분류 패턴
3. **📊 피처 중요도 (Coefficients)**: 모델이 어떤 변수를 중요하게 봤는지
4. **📈 ROC-AUC 곡선**: 클래스별 분류 성능
5. **🐝 SHAP 분석**: 모델의 판단 근거 상세 분석"""

# === Cell 2: Imports & Setup ===
code_2 = """# 1. 환경 설정 및 데이터 로드
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
import os
import sys
from pathlib import Path

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 프로젝트 루트 맞추기
current_path = os.getcwd()
if 'trust_model' in current_path:
    if 'SKN18-FINAL-1TEAM' in current_path:
         while not current_path.endswith('SKN18-FINAL-1TEAM'):
            current_path = os.path.dirname(current_path)
            if len(current_path) < 5: break
         os.chdir(current_path)
    print(f"📂 작업 디렉토리 변경: {os.getcwd()}")
else:
    print(f"ℹ️ 현재 작업 디렉토리: {os.getcwd()}")

# 데이터 경로 설정
X_TRAIN_PATH = "data/ML/trust/X_train.csv"
X_TEST_PATH = "data/ML/trust/X_test.csv"
Y_TRAIN_PATH = "data/ML/trust/y_train.csv"
Y_TEST_PATH = "data/ML/trust/y_test.csv"
MODEL_PATH = "apps/reco/models/trust_model/save_models/temp_trained_models.pkl"

# 데이터 로드 함수
def load_data():
    X_train = pd.read_csv(X_TRAIN_PATH, encoding="utf-8-sig")
    X_test = pd.read_csv(X_TEST_PATH, encoding="utf-8-sig")
    y_train = pd.read_csv(Y_TRAIN_PATH, encoding="utf-8-sig").squeeze()
    y_test = pd.read_csv(Y_TEST_PATH, encoding="utf-8-sig").squeeze()
    
    # [중요] 학습에 사용된 14개 피처 명시 (Leakage 방지)
    valid_features = [
        "등록매물_log", "총거래활동량_log", "1인당_거래량_log", 
        "총_직원수", "중개보조원_비율", "자격증_보유비율", 
        "운영기간_년", "숙련도_지수", "운영_안정성", 
        "대형사무소", "대표_공인중개사", "대표_법인", 
        "지역_경쟁강도", "1층_여부"
    ]
    
    # 실제 파일에 존재하는 컬럼만 선택
    final_features = [col for col in valid_features if col in X_train.columns]
    
    X_train = X_train[final_features]
    X_test = X_test[final_features]
    
    return X_train, X_test, y_train, y_test, final_features

if not os.path.exists(X_TRAIN_PATH):
    print("⚠️ 데이터 파일을 찾을 수 없습니다. 경로를 확인해주세요.")
else:
    X_train, X_test, y_train, y_test, feature_names = load_data()
    
    # 전체 데이터 결합 (Learning Curve용)
    X = pd.concat([X_train, X_test], ignore_index=True)
    y = pd.concat([y_train, y_test], ignore_index=True)
    
    print("\\n✅ 데이터 로드 완료")
    print(f"  - X shape: {X.shape}")
    print(f"  - 사용된 피처 수: {len(feature_names)}")
    print(f"  - 피처 목록: {feature_names}")
    print(f"  - y class distribution: {y.value_counts().to_dict()}")
"""

# === Cell 3: Model Loading & Learning Curve ===
code_3 = """# 2. 📉 학습 곡선 (Learning Curve)
from sklearn.model_selection import learning_curve
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression

# 최신 모델 설정 (C=1, penalty='l1', solver='saga')
best_model = LogisticRegression(
    C=1, 
    penalty='l1', 
    solver='saga', 
    class_weight='balanced', 
    max_iter=1000, 
    random_state=42
)

# 파이프라인 구성
pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='mean')),
    ('scaler', StandardScaler()),
    ('clf', best_model)
])

print("📊 학습 곡선 생성 중...")
train_sizes, train_scores, test_scores = learning_curve(
    pipeline, X, y, cv=5, scoring='accuracy', n_jobs=-1, 
    train_sizes=np.linspace(0.1, 1.0, 10), shuffle=True, random_state=42
)

train_mean = np.mean(train_scores, axis=1)
train_std = np.std(train_scores, axis=1)
test_mean = np.mean(test_scores, axis=1)
test_std = np.std(test_scores, axis=1)

plt.figure(figsize=(10, 6))
plt.plot(train_sizes, train_mean, 'o-', color="r", label="Train score")
plt.plot(train_sizes, test_mean, 'o-', color="g", label="Cross-validation score")
plt.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, alpha=0.1, color="r")
plt.fill_between(train_sizes, test_mean - test_std, test_mean + test_std, alpha=0.1, color="g")

plt.title("학습 곡선 (Learning Curve)", fontsize=15, fontweight='bold')
plt.xlabel("학습 데이터 샘플 수", fontsize=12)
plt.ylabel("정확도 (Accuracy)", fontsize=12)
plt.legend(loc="best")
plt.grid(True, linestyle='--', alpha=0.6)
plt.show()

print("➕ 해석 Point: Train(Red)과 CV(Green) 곡선이 서로 비슷한 높이로 수렴해야 과적합이 없는 것입니다.")
"""

# === Cell 4: Confusion Matrix ===
code_4 = """# 3. 🔲 혼동 행렬 (Confusion Matrix)
from sklearn.metrics import confusion_matrix

# 모델 학습
print("📊 모델 학습 중...")
pipeline.fit(X_train, y_train)
y_pred = pipeline.predict(X_test)

# 혼동 행렬 계산
cm = confusion_matrix(y_test, y_pred)
labels = sorted(y.unique())

plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
            xticklabels=labels, yticklabels=labels,
            cbar_kws={'label': '건수'})

plt.title('혼동 행렬 (Confusion Matrix)', fontsize=15, fontweight='bold')
plt.xlabel('예측 등급', fontsize=12, fontweight='bold')
plt.ylabel('실제 등급', fontsize=12, fontweight='bold')

# 정확도 표시
accuracy = np.trace(cm) / np.sum(cm)
plt.text(0.5, -0.15, f'전체 정확도: {accuracy:.2%}', 
        ha='center', transform=plt.gca().transAxes, 
        fontsize=12, fontweight='bold')

plt.tight_layout()
plt.show()

print("➕ 해석 Point: 대각선(진한 색)에 숫자가 많을수록 좋습니다.")
"""

# === Cell 5: Feature Correlation ===
code_5 = """# 4. 📊 피처-타겟 상관관계 분석
target_map = {'A': 2, 'B': 1, 'C': 0}
if y.dtype == object:
    y_encoded = y.map(target_map)
else:
    y_encoded = y

df_corr = X.copy()
df_corr['Target'] = y_encoded

corr_matrix = df_corr.corr()
target_corr = corr_matrix['Target'].drop('Target').sort_values(ascending=False)

plt.figure(figsize=(12, 10))
# 색상: 양의 상관관계(초록), 음의 상관관계(빨강)
colors = ['green' if x > 0 else 'red' for x in target_corr.values]
plt.barh(range(len(target_corr)), target_corr.values, color=colors, alpha=0.7)
plt.yticks(range(len(target_corr)), target_corr.index)
plt.xlabel('상관계수 (Correlation)', fontsize=12, fontweight='bold')
plt.title('피처-신뢰도등급 상관관계', fontsize=15, fontweight='bold')
plt.axvline(x=0, color='black', linestyle='--', linewidth=1)
plt.grid(axis='x', alpha=0.3)

for i, v in enumerate(target_corr.values):
    plt.text(v, i, f' {v:.3f}', va='center', fontsize=9)

plt.tight_layout()
plt.show()
"""

# === Cell 6: Operational Period Distribution ===
code_6 = """# 5. 🏢 운영미간 분포 분석
TRAIN_TARGET_PATH = "data/ML/trust/train_target.csv"
TEST_TARGET_PATH = "data/ML/trust/test_target.csv"

df_train_orig = pd.read_csv(TRAIN_TARGET_PATH, encoding="utf-8-sig")
df_test_orig = pd.read_csv(TEST_TARGET_PATH, encoding="utf-8-sig")
df_target = pd.concat([df_train_orig, df_test_orig], ignore_index=True)

df_target['등록일'] = pd.to_datetime(df_target['등록일'], errors='coerce')
today = pd.Timestamp.now()
df_target['운영기간_일'] = (today - df_target['등록일']).dt.days.clip(lower=0)
df_target['운영기간_년'] = (df_target['운영기간_일'] / 365.25).fillna(0)

op_years = df_target['운영기간_년'].dropna()
median_years = op_years.median()
mean_years = op_years.mean()

plt.figure(figsize=(10, 6))
plt.hist(op_years, bins=30, color='steelblue', alpha=0.7, edgecolor='black')
plt.axvline(3, color='red', linestyle='--', linewidth=2, label='3년 기준 (안정성)')
plt.axvline(median_years, color='green', linestyle='--', linewidth=2, label=f'중앙값: {median_years:.1f}년')
plt.title('중개사무소 운영기간 분포', fontsize=15, fontweight='bold')
plt.xlabel('운영기간 (년)')
plt.ylabel('사무소 수')
plt.legend()
plt.grid(alpha=0.3)
plt.show()

print(f"📊 평균 운영기간: {mean_years:.2f}년, 중앙값: {median_years:.2f}년")
"""

nb.cells.append(nbf.v4.new_markdown_cell(text_1))
nb.cells.append(nbf.v4.new_code_cell(code_2))
nb.cells.append(nbf.v4.new_code_cell(code_3))
nb.cells.append(nbf.v4.new_code_cell(code_4))
nb.cells.append(nbf.v4.new_code_cell(code_5))
nb.cells.append(nbf.v4.new_code_cell(code_6))

with open(NOTEBOOK_PATH, 'w', encoding='utf-8') as f:
    nbf.write(nb, f)

print(f"✅ Notebook updated successfully at: {NOTEBOOK_PATH}")
