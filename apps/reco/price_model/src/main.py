"""
월세 가격 분류 모델 학습 메인 스크립트 (저렴/적정/비쌈)
"""
import argparse
from pathlib import Path

from loaders.data_loader import DataLoader
from preprocessing.preprocessor import PriceDataPreprocessor
from training.model import get_models
from training.trainer import ModelTrainer

ML_ROOT = Path(__file__).resolve().parent.parent  # src -> price_model
# price_model -> reco -> apps -> SKN18-FINAL-1TEAM (3개 parent)
REPO_ROOT = ML_ROOT.parents[2]  # SKN18-FINAL-1TEAM
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "actual_transaction_price"


def main(
    data_dir: str,
    output_dir: str = "model",
    split_date: str = "2025-06",
    run_shap: bool = False,
    shap_output_dir: str = "./shap_plots"
):
    """
    전체 파이프라인 실행

    Args:
        data_dir: 데이터 디렉토리 경로
        output_dir: 모델 저장 디렉토리
        split_date: Train/Val 분할 기준 날짜
        run_shap: SHAP 분석 실행 여부
        shap_output_dir: SHAP 플롯 저장 디렉토리
    """
    print("\n" + "=" * 60)
    print("📊 월세 가격 분류 모델 학습 시작 (저렴/적정/비쌈)")
    print("=" * 60)

    # 1. 데이터 로딩
    print("\n[Step 1] 데이터 로딩")
    loader = DataLoader(data_dir)
    train_df, test_df = loader.load_train_test()

    # 2. 전처리 및 피처 엔지니어링
    print("\n[Step 2] 전처리 및 피처 엔지니어링")
    preprocessor = PriceDataPreprocessor()

    # 타깃 생성 (Train: 자체 통계 사용, Test: Train 통계 사용)
    train_df = preprocessor.create_target(train_df)
    test_df = preprocessor.create_target(
        test_df,
        train_stats={"gu_quantiles": preprocessor.train_gu_quantiles}
    )

    # 고급 피처 엔지니어링 (노트북 기반)
    train_df, test_df = preprocessor.advanced_feature_engineering(train_df, test_df)

    # 3. Train/Val 분할
    print(f"\n[Step 3] Train/Val 분할 (기준일: {split_date})")
    X_train, y_train, X_val, y_val = preprocessor.prepare_train_test_split(
        train_df, split_date=split_date
    )

    # 테스트 데이터 준비
    X_test = test_df[preprocessor.candidate_features]
    y_test = test_df[preprocessor.target_name]

    # 4. Tree 모델용 피처 변환 (Label Encoding, No Scaling)
    print("\n[Step 4] Tree 모델용 피처 변환")
    X_train_t, X_val_t, X_test_t = preprocessor.prepare_tree_features(
        X_train, X_val, X_test
    )

    # 전처리 파이프라인은 None으로 설정 (Tree 모델용)
    pipeline = None

    # 5. 모델 학습
    print("\n[Step 5] 모델 학습")
    models = get_models()
    print(f"✅ 모델 정의 완료:")
    for model_name in models.keys():
        print(f"   - {model_name}")

    # 실제 사용될 피처 이름 (변환 후)
    actual_feature_names = X_train_t.columns.tolist() if hasattr(X_train_t, 'columns') else preprocessor.candidate_features

    trainer = ModelTrainer()
    results_df = trainer.train_models(
        models=models,
        X_train=X_train_t.values if hasattr(X_train_t, "values") else X_train_t,
        y_train=y_train.values,
        X_val=X_val_t.values if hasattr(X_val_t, "values") else X_val_t,
        y_val=y_val.values,
        X_test=X_test_t.values if hasattr(X_test_t, "values") else X_test_t,
        y_test=y_test.values,
        feature_names=actual_feature_names,
    )


    # 6. 모델 저장
    print(f"\n[Step 6] 모델 저장")
    ml_root = Path(__file__).resolve().parent.parent
    if Path(output_dir).is_absolute():
        resolved_output_dir = output_dir
    else:
        resolved_output_dir = str(ml_root / output_dir)

    model_path = trainer.save_model(
        preprocessor=preprocessor,
        output_dir=resolved_output_dir
    )

    # 7. SHAP 분석 (옵션)
    if run_shap:
        print(f"\n[Step 7] SHAP 분석")
        explainer = trainer.analyze_shap(
            model_name=None,  # best_model 사용
            data_type="test",
            max_samples=1000,
            output_dir=shap_output_dir,
            save_plots=True
        )
        print(f"✅ SHAP 플롯 저장 완료: {shap_output_dir}")

    print("\n" + "=" * 60)
    print("✅ 모든 작업 완료!")
    print("=" * 60)
    print(f"저장된 모델: {model_path}")
    print(f"최고 성능 모델: {trainer.best_model_name}")
    print(f"Test F1-Macro: {results_df.iloc[0]['f1_macro_test']:.4f}")
    print(f"Test Accuracy: {results_df.iloc[0]['accuracy_test']:.4f}")
    if run_shap:
        print(f"SHAP 플롯: {shap_output_dir}")

    return model_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="월세 가격 분류 모델 학습 (저렴/적정/비쌈)"
    )
    parser.add_argument(
        "--data_dir",
        type=str,
        default=str(DEFAULT_DATA_DIR),
        help="데이터 디렉토리 경로"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="model",
        help="모델 저장 디렉토리 (ML 폴더 기준 하위 경로 또는 절대 경로)"
    )
    parser.add_argument(
        "--split_date",
        type=str,
        default="2025-06",
        help="Train/Val 분할 기준 날짜 (YYYY-MM)"
    )
    parser.add_argument(
        "--run_shap",
        action="store_true",
        help="SHAP 분석 실행 여부"
    )
    parser.add_argument(
        "--shap_output_dir",
        type=str,
        default="./shap_plots",
        help="SHAP 플롯 저장 디렉토리"
    )

    args = parser.parse_args()

    main(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        split_date=args.split_date,
        run_shap=args.run_shap,
        shap_output_dir=args.shap_output_dir
    )
