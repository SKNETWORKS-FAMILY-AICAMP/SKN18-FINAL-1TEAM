"""
SHAP Feature 중요도 분석 (Updated)
- 최신 파이프라인 기준 (14개 피처 제한, Best Model 사용)
- SHAP을 사용하여 모델의 feature 중요도를 분석
- 클래스별로 어떤 feature가 중요한지 시각화
"""
import pickle
import shap
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import sys
import os

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.append(str(PROJECT_ROOT))

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'  # Windows
plt.rcParams['axes.unicode_minus'] = False

# 경로 설정
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
SAVE_DIR = BASE_DIR / "save_models"
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# ✅ 결정된 최종 14개 피처 리스트 (Data Leakage 방지)
VALID_FEATURES = [
    '등록매물_log', '1인당_거래량_log', '총거래활동량_log',
    '운영기간_년', '숙련도_지수', '총_직원수',
    '자격증_보유비율', '중개보조원_비율', '지역_경쟁강도',
    '대표_공인중개사', '대표_법인',
    '1층_여부', '운영_안정성', '대형사무소'
]

def load_data_and_model():
    """최신 데이터와 모델 로드"""
    print("📂 데이터 및 모델 로드 중...")
    
    # 1. 데이터 로드 (X_test.csv, y_test.csv)
    try:
        X_test = pd.read_csv(DATA_DIR / "X_test.csv")
        y_test = pd.read_csv(DATA_DIR / "y_test.csv").values.ravel()
        print(f"   ✅ X_test 로드 완료: {X_test.shape}")
    except FileNotFoundError:
        print("   ❌ X_test.csv 또는 y_test.csv를 찾을 수 없습니다. _00_load_data.py를 먼저 실행하세요.")
        return None, None, None, None

    # 2. 14개 피처만 선택 (Safety Lock)
    missing_features = [f for f in VALID_FEATURES if f not in X_test.columns]
    if missing_features:
        print(f"   ⚠️ 경고: 다음 피처가 X_test에 없습니다: {missing_features}")
        # 없는 경우 일단 진행하거나 에러 처리 (여기선 교집합만 사용)
        valid_current = [f for f in VALID_FEATURES if f in X_test.columns]
        X_test = X_test[valid_current]
    else:
        X_test = X_test[VALID_FEATURES]
    
    print(f"   ✅ 14개 핵심 피처 선택 완료: {X_test.shape}")
    
    # 3. 모델 로드 (Best Model 우선)
    model_path = SAVE_DIR / "best_model.pkl"
    if not model_path.exists():
        # 없으면 temp 로드 시도
        model_path = SAVE_DIR / "temp_trained_models.pkl"
        if not model_path.exists():
            print("   ❌ 학습된 모델이 없습니다.")
            return None, None, None, None
        
        print("   ⚠️ Best Model이 없어 임시 모델(temp_trained_models.pkl)을 로드합니다.")
        with open(model_path, "rb") as f:
            data = pickle.load(f)
            # temp 파일 구조에 따라 모델 추출 (가장 성능 좋은 것)
            cv_results = data.get("cv_results", {})
            best_name = max(cv_results.keys(), key=lambda k: cv_results[k]['cv_mean'])
            model = data['models'][best_name]
            print(f"   ✅ 임시 파일에서 '{best_name}' 모델 선택됨")
    else:
        print(f"   ✅ Best Model 로드: {model_path}")
        with open(model_path, "rb") as f:
            model = pickle.load(f)
            
            # 파이프라인인 경우 스텝 확인
            if hasattr(model, 'steps'):
                print(f"   ℹ️ 파이프라인 모델 감지: {[step[0] for step in model.steps]}")
    
    return model, X_test, VALID_FEATURES, y_test

def get_shap_explainer(model, X_background):
    """모델 타입에 따라 SHAP Explainer 반환"""
    
    # 파이프라인 전처리 분리
    if hasattr(model, 'steps'):
        # 전처리 단계 실행 (마지막 단계 제외)
        preprocess_pipe = model[:-1]
        final_estimator = model[-1]
        
        # 배경 데이터 변환
        X_bg_transformed = preprocess_pipe.transform(X_background)
        # DataFrame으로 복구 (컬럼명 유지 위해)
        X_bg_transformed = pd.DataFrame(X_bg_transformed, columns=VALID_FEATURES)
        
        print(f"   ℹ️ 파이프라인 전처리 적용 완료. Estimator: {type(final_estimator).__name__}")
        model_to_explain = final_estimator
    else:
        X_bg_transformed = X_background
        model_to_explain = model

    model_type = type(model_to_explain).__name__
    print(f"   - 최종 모델 타입: {model_type}")
    
    # 1. Tree-based Models
    tree_models = ['RandomForestClassifier', 'GradientBoostingClassifier', 
                   'XGBClassifier', 'LGBMClassifier', 'CatBoostClassifier', 'ExtraTreesClassifier']
    
    # 2. Linear Models
    linear_models = ['LogisticRegression', 'LinearRegression', 'Ridge', 'Lasso', 'ElasticNet']

    try:
        if model_type in tree_models:
            print("   - TreeExplainer 사용")
            explainer = shap.TreeExplainer(model_to_explain)
            return explainer, X_bg_transformed
            
        elif model_type in linear_models:
            print("   - KernelExplainer 사용 (Probability 단위 변환)")
            # 속도 최적화를 위해 샘플링 (최대 50개)
            background_sample = shap.sample(X_bg_transformed, min(50, len(X_bg_transformed)))
            
            # predict_proba 함수 래핑
            if hasattr(model, 'steps'):
                # 전체 파이프라인의 predict_proba 사용 (입력은 원본 데이터여야 함... 복잡함)
                # KernelExplainer는 모델의 입력을 받으므로, 전처리된 입력을 받는 Estimator의 predict_proba를 써야 함.
                explainer = shap.KernelExplainer(model_to_explain.predict_proba, background_sample)
            else:
                explainer = shap.KernelExplainer(model.predict_proba, background_sample)
                
            return explainer, X_bg_transformed
            
        else:
            print("   - KernelExplainer 사용 (일반)")
            background_sample = shap.sample(X_bg_transformed, min(50, len(X_bg_transformed)))
            if hasattr(model_to_explain, 'predict_proba'):
                explainer = shap.KernelExplainer(model_to_explain.predict_proba, background_sample)
            else:
                explainer = shap.KernelExplainer(model_to_explain.predict, background_sample)
            return explainer, X_bg_transformed
            
    except Exception as e:
        print(f"   ⚠️ Explainer 생성 중 오류 ({e}), 기본 KernelExplainer 시도")
        background_sample = shap.sample(X_bg_transformed, min(20, len(X_bg_transformed)))
        explainer = shap.KernelExplainer(model_to_explain.predict_proba, background_sample)
        return explainer, X_bg_transformed

def analyze_shap(model, X_test, feature_names):
    """SHAP 값 계산"""
    print("\n🔍 SHAP 분석 수행...")
    
    # Explainer 및 전처리된 데이터 획득
    explainer, X_test_transformed = get_shap_explainer(model, X_test)
    
    # SHAP 값 계산
    print("   - SHAP 값 계산 중 (시간이 조금 걸릴 수 있습니다)...")
    
    # 데이터 크기가 너무 크면 샘플링 (속도 문제)
    if len(X_test_transformed) > 300:
        print(f"   ℹ️ 데이터가 많아 300개로 샘플링하여 분석합니다.")
        X_sample = shap.sample(X_test_transformed, 300)
    else:
        X_sample = X_test_transformed

    try:
        if isinstance(explainer, shap.TreeExplainer):
             # check_additivity=False : 전처리 오차 무시
            shap_values = explainer.shap_values(X_sample, check_additivity=False)
        else:
            shap_values = explainer.shap_values(X_sample)
            
    except Exception as e:
        print(f"   ⚠️ 일반 shap_values 실패, explainer() 호출 시도: {e}")
        shap_values = explainer(X_sample)
        if hasattr(shap_values, 'values'):
            shap_values = shap_values.values

    # SHAP 값 차원 정리 (3D -> List of 2D)
    if not isinstance(shap_values, list) and len(np.array(shap_values).shape) == 3:
        # (samples, features, classes)
        print("   - 3D SHAP 값을 클래스별 리스트로 변환")
        vals = np.array(shap_values)
        shap_values = [vals[:, :, i] for i in range(vals.shape[2])]

    print(f"   ✅ SHAP 계산 완료")
    return shap_values, X_sample

def plot_shap_importance(shap_values, X_sample, feature_names, model):
    """SHAP 중요도 시각화 (A, B, C 등급)"""
    print("\n📊 SHAP 중요도 시각화 중...")
    
    classes = getattr(model, 'classes_', [0, 1, 2])
    # 매핑: 0->C, 1->B, 2->A (기본 가정)
    class_map = {0: '0등급(C / 부정)', 1: '1등급(B / 보통)', 2: '2등급(A / 긍정)'}
    
    # 실제 모델 클래스 확인
    if hasattr(model, 'steps'):
        try:
            classes = model.steps[-1][1].classes_
        except:
            pass
            
    for i, class_label in enumerate(classes):
        class_name = class_map.get(class_label, f'Class {class_label}')
        print(f"   Processing: {class_name}")
        
        # 해당 클래스의 SHAP 값
        if isinstance(shap_values, list):
            # 클래스 개수와 shap_values 리스트 길이가 맞는지 확인
            if i < len(shap_values):
                s_vals = shap_values[i]
            else:
                # 이진 분류의 경우 하나만 나올 수 있음 (일반적으로 1번 클래스)
                s_vals = shap_values[-1]
        else:
            s_vals = shap_values

        # 평균 절대값
        mean_abs_shap = np.abs(s_vals).mean(axis=0)
        
        # DataFrame 생성
        df_imp = pd.DataFrame({
            'Feature': feature_names,
            'Importance': mean_abs_shap
        }).sort_values('Importance', ascending=True)
        
        # Plot
        plt.figure(figsize=(10, 8))
        bars = plt.barh(df_imp['Feature'], df_imp['Importance'], color='#4c72b0')
        plt.xlabel(f'mean(|SHAP value|) - {class_name} 영향도')
        plt.title(f'SHAP Feature Importance - {class_name}', fontsize=14, fontweight='bold')
        
        # 수치 텍스트
        for bar in bars:
            width = bar.get_width()
            plt.text(width*1.01, bar.get_y() + bar.get_height()/2, 
                     f'{width:.4f}', ha='left', va='center', fontsize=9)
            
        plt.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        
        safe_name = str(class_label).replace(' ', '_')
        out_path = RESULTS_DIR / f"shap_importance_{safe_name}.png"
        plt.savefig(out_path, dpi=300)
        print(f"   ✅ Saved: {out_path}")
        plt.close()

def main():
    model, X_test, feature_names, y_test = load_data_and_model()
    if model is None:
        return

    shap_values, X_sample = analyze_shap(model, X_test, feature_names)
    plot_shap_importance(shap_values, X_sample, feature_names, model)
    print("\n✅ 모든 분석이 완료되었습니다. (apps/reco/models/trust_model/results 폴더 확인)")

if __name__ == "__main__":
    main()

