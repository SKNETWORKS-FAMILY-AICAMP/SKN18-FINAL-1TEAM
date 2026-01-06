from pathlib import Path

from loaders.data_loader import DataLoader
from preprocessing.preprocessor import PriceDataPreprocessor
from training.trainer import ModelTrainer
import matplotlib.pyplot as plt
import matplotlib as mpl

# 1) 폰트 설정
plt.rcParams["font.family"] = "Malgun Gothic" 

# 2) 마이너스(-) 깨짐 방지
mpl.rcParams["axes.unicode_minus"] = False

# 경로 설정 (analysis 폴더 안에 있으므로 parent가 한 단계 더 필요)
ML_ROOT = Path(__file__).resolve().parent.parent.parent  # analysis -> src -> price_model
PLOTS_DIR = ML_ROOT / "shap_plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

# 저장된 모델 경로
MODEL_DIR = ML_ROOT / "model"
MODEL_PATH = MODEL_DIR / "price_model_lightgbm.pkl"


def example_shap_analysis():
    """저장된 모델을 이용해 Test 데이터 기준 SHAP 분석"""

    print("\n" + "=" * 70)
    print(">> 저장된 모델 기반 SHAP 분석 예시 실행")
    print("=" * 70)

    # 1. 데이터 로딩
    print("\n[Step 1] 데이터 로딩")
    # price_model -> reco -> apps -> SKN18-FINAL-1TEAM (3개 parent)
    REPO_ROOT = ML_ROOT.parents[2]  # SKN18-FINAL-1TEAM
    data_dir = REPO_ROOT / "data" / "actual_transaction_price"
    loader = DataLoader(str(data_dir))
    train_df, test_df = loader.load_train_test(
        train_filename="월세_train(24.08~25.08).csv",
        test_filename="월세_test(25.09~25.10).csv",
    )

    # 2. 타깃 생성 및 고급 피처 엔지니어링
    print("\n[Step 2] 타깃 생성 및 고급 피처 엔지니어링")
    preprocessor = PriceDataPreprocessor()

    # 타깃 생성 (Train: 전체 통계 사용, Test: Train 통계 사용)
    train_df = preprocessor.create_target(train_df)
    test_df = preprocessor.create_target(
        test_df,
        train_stats={"gu_quantiles": preprocessor.train_gu_quantiles},
    )

    train_df, test_df = preprocessor.advanced_feature_engineering(train_df, test_df)

    # 3. Train/Val 분할
    print("\n[Step 3] Train/Val 분할")
    X_train, y_train, X_val, y_val = preprocessor.prepare_train_test_split(
        train_df, split_date="2025-06"
    )

    # 4. Test 피처 준비
    print("\n[Step 4] Test 피처 준비")
    X_test = test_df[preprocessor.candidate_features]
    y_test = test_df[preprocessor.target_name]

    # 5. Tree 모델용 피처 변환 (Label Encoding, No Scaling)
    print("\n[Step 5] Tree 모델용 피처 변환")
    X_train_t, X_val_t, X_test_t = preprocessor.prepare_tree_features(
        X_train, X_val, X_test
    )

    # 6. 저장된 모델 로드
    print("\n[Step 6] 저장된 모델 로드")
    trainer = ModelTrainer()
    model_bundle = trainer.load_model(str(MODEL_PATH))

    # trainer에 SHAP용 상태 세팅
    trainer.best_model = model_bundle["model"]
    trainer.best_model_name = model_bundle["model_name"]

    trainer.X_train = (
        X_train_t.values if hasattr(X_train_t, "values") else X_train_t
    )
    trainer.X_val = X_val_t.values if hasattr(X_val_t, "values") else X_val_t
    trainer.X_test = X_test_t.values if hasattr(X_test_t, "values") else X_test_t
    trainer.feature_names = preprocessor.candidate_features

    # 7. SHAP 분석 수행 (Test 데이터만, 기본 플롯 저장은 끔)
    print("\n[Step 7] SHAP 값 계산 (Test 데이터)")
    explainer_test = trainer.analyze_shap(
        model_name=None,        # best_model 사용
        data_type="test",
        max_samples=1000,
        output_dir=str(PLOTS_DIR),
        save_plots=False,       # 기본 save_all_plots 비활성화
    )

    # 8. 필요한 SHAP 플롯만 생성 (Summary + Bar)
    print("\n[Step 8] SHAP 플롯 생성 (Summary + Bar)")

    # 플롯용 배열 (numpy)로 변환
    X_test_plot = X_test_t.values if hasattr(X_test_t, "values") else X_test_t

    # 8-1. Summary Plot (dot)
    print("\n>> Summary Plot 생성...")
    explainer_test.plot_summary(
        X=X_test_plot[:1000],
        plot_type="dot",
        max_display=20,
        save_path=str(PLOTS_DIR / "summary_test.png"),
        show=False,
    )

    # 8-2. Bar Plot (Feature Importance)
    print("\n>> Bar Plot 생성...")
    explainer_test.plot_bar(
        X=X_test_plot[:1000],
        max_display=20,
        save_path=str(PLOTS_DIR / "bar_test.png"),
        show=False,
    )

    # 9. 피처 중요도 추출
    print("\n[Step 9] 피처 중요도 계산 및 출력")
    importance_df = explainer_test.get_feature_importance(top_n=15)

    # 10. SHAP 양수/음수 기여도 분석
    print("\n[Step 10] SHAP 양수/음수 기여도 분석")
    
    import numpy as np
    import pandas as pd
    
    # SHAP 값 가져오기
    shap_values = explainer_test.shap_values
    feature_names = trainer.feature_names
    
    # 각 피처별 양수/음수 기여도 계산
    positive_contributions = []
    negative_contributions = []
    net_contributions = []
    
    for i, feature in enumerate(feature_names):
        if len(shap_values.shape) == 3:  # 다중 클래스
            # 모든 클래스의 SHAP 값 평균
            feature_shap = shap_values[:, i, :].mean(axis=1)
        else:
            feature_shap = shap_values[:, i]
        
        pos_contrib = feature_shap[feature_shap > 0].sum()
        neg_contrib = feature_shap[feature_shap < 0].sum()
        net_contrib = feature_shap.sum()
        
        positive_contributions.append(pos_contrib)
        negative_contributions.append(neg_contrib)
        net_contributions.append(net_contrib)
    
    # DataFrame 생성
    contrib_df = pd.DataFrame({
        'Feature': feature_names,
        'Positive_Contribution': positive_contributions,
        'Negative_Contribution': negative_contributions,
        'Net_Contribution': net_contributions,
        'Abs_Total': [abs(p) + abs(n) for p, n in zip(positive_contributions, negative_contributions)]
    })
    
    # 절대값 기준 정렬
    contrib_df = contrib_df.sort_values('Abs_Total', ascending=False)
    
    print("\n상위 15개 피처의 양수/음수 기여도:")
    print(contrib_df.head(15).to_string(index=False))
    
    # 11. 양수/음수 기여도 시각화
    print("\n[Step 11] 양수/음수 기여도 시각화")
    
    top_features = contrib_df.head(15)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    y_pos = np.arange(len(top_features))
    
    # 양수 기여도 (오른쪽)
    ax.barh(y_pos, top_features['Positive_Contribution'], 
            color='#2ecc71', alpha=0.7, label='양수 기여도 (+)')
    
    # 음수 기여도 (왼쪽)
    ax.barh(y_pos, top_features['Negative_Contribution'], 
            color='#e74c3c', alpha=0.7, label='음수 기여도 (-)')
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(top_features['Feature'])
    ax.set_xlabel('SHAP 기여도 합계', fontsize=12)
    ax.set_title('피처별 SHAP 양수/음수 기여도 (상위 15개)', fontsize=14, fontweight='bold')
    ax.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "shap_positive_negative_contributions.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    print("✅ 저장: shap_positive_negative_contributions.png")

    print("\n" + "=" * 70)
    print(">> 저장된 모델 기반 SHAP 분석 예시 종료!")
    print("=" * 70)
    print("\n생성된 플롯 경로:")
    print("   - ./shap_plots/summary_test.png")
    print("   - ./shap_plots/bar_test.png")
    print("   - ./shap_plots/shap_positive_negative_contributions.png")
    print("\n상위 중요 피처:")
    print(importance_df.head(10))

    return explainer_test, importance_df, contrib_df


if __name__ == "__main__":
    # 메뉴 없이 바로 예시 실행
    explainer, importance_df, contrib_df = example_shap_analysis()

    print("\n" + "=" * 70)
    print("SHAP 플롯 사용 가이드:")
    print("=" * 70)
    print(
        """
    1. Summary Plot (summary_test.png):
       - Test 데이터 전체에 대한 피처별 SHAP 분포

    2. Bar Plot (bar_test.png):
       - Test 기준 피처 중요도 순위 (평균 |SHAP| 기준)
    
    3. Positive/Negative Contributions (shap_positive_negative_contributions.png):
       - 각 피처의 양수(+) 기여도와 음수(-) 기여도를 분리하여 표시
       - 초록색: 예측값을 높이는 방향 (+)
       - 빨간색: 예측값을 낮추는 방향 (-)
    """
    )
