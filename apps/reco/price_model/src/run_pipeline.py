"""
ML 파이프라인 통합 실행 스크립트
prepare_wolse_dataset → main(모델 학습) → example_shap(SHAP 분석) 순차 실행
"""
import sys
from pathlib import Path

# 경로 설정
ML_SRC = Path(__file__).resolve().parent
ML_ROOT = ML_SRC.parent
PRICE_MODEL_ROOT = ML_ROOT.parent

# 필요한 경로를 sys.path에 추가 (src 폴더 자체를 추가)
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

# 프로젝트 루트 (데이터 경로용)
# src -> price_model -> reco -> apps -> SKN18-FINAL-1TEAM (3개 parent)
REPO_ROOT = ML_ROOT.parents[2]
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "actual_transaction_price"

# 모델 저장 경로: scripts/03_import/price_model
MODEL_OUTPUT_DIR = REPO_ROOT / "scripts" / "03_import" / "price_model"


def run_pipeline(
    skip_prepare: bool = False,
    skip_train: bool = False,
    skip_shap: bool = False,
    data_dir: str = None,
    run_shap_in_main: bool = False,
):
    """
    전체 ML 파이프라인 실행

    Args:
        skip_prepare: 데이터 준비 단계 스킵
        skip_train: 모델 학습 단계 스킵
        skip_shap: SHAP 분석 단계 스킵
        data_dir: 데이터 디렉토리 경로 (None이면 기본값)
        run_shap_in_main: main.py에서 SHAP 분석 함께 실행 여부
    """
    print("\n" + "=" * 70)
    print("🚀 ML 파이프라인 시작")
    print("=" * 70)
    
    if data_dir is None:
        data_dir = str(DEFAULT_DATA_DIR)
    
    # ========================================
    # Step 1: 데이터셋 준비
    # ========================================
    if not skip_prepare:
        print("\n" + "=" * 70)
        print("📊 [Step 1/3] 데이터셋 준비 (prepare_wolse_dataset)")
        print("=" * 70)
        
        try:
            from loaders.prepare_wolse_dataset import run as prepare_data
            result = prepare_data()
            print("✅ 데이터셋 준비 완료!")
        except Exception as e:
            print(f"❌ 데이터셋 준비 중 오류 발생: {e}")
            raise
    else:
        print("\n⏭️  [Step 1/3] 데이터셋 준비 스킵")
    
    # ========================================
    # Step 2: 모델 학습
    # ========================================
    if not skip_train:
        print("\n" + "=" * 70)
        print("🤖 [Step 2/3] 모델 학습 (main)")
        print("=" * 70)
        
        try:
            from main import main as train_model
            model_path = train_model(
                data_dir=data_dir,
                output_dir=str(MODEL_OUTPUT_DIR),  # scripts/03_import/price_model
                split_date="2025-06",
                run_shap=run_shap_in_main,
                shap_output_dir=str(ML_ROOT / "shap_plots")
            )
            print(f"✅ 모델 학습 완료! 저장 경로: {model_path}")
        except Exception as e:
            print(f"❌ 모델 학습 중 오류 발생: {e}")
            raise
    else:
        print("\n⏭️  [Step 2/3] 모델 학습 스킵")
    
    # ========================================
    # Step 3: SHAP 분석
    # ========================================
    if not skip_shap and not run_shap_in_main:
        print("\n" + "=" * 70)
        print("🔍 [Step 3/3] SHAP 분석 (example_shap)")
        print("=" * 70)
        
        try:
            from analysis.example_shap import example_shap_analysis
            explainer, importance_df, contrib_df = example_shap_analysis()
            print("✅ SHAP 분석 완료!")
            
            # SHAP 플롯 경로 확인
            shap_plots_dir = ML_ROOT / "shap_plots"
            if shap_plots_dir.exists():
                print(f"\n📁 SHAP 플롯 저장 위치: {shap_plots_dir}")
                for f in shap_plots_dir.glob("*.png"):
                    print(f"   - {f.name}")
        except Exception as e:
            print(f"❌ SHAP 분석 중 오류 발생: {e}")
            raise
    else:
        if run_shap_in_main:
            print("\n⏭️  [Step 3/3] SHAP 분석 - main.py에서 이미 실행됨")
        else:
            print("\n⏭️  [Step 3/3] SHAP 분석 스킵")
    
    # ========================================
    # 완료
    # ========================================
    print("\n" + "=" * 70)
    print("🎉 ML 파이프라인 완료!")
    print("=" * 70)
    
    # 생성된 파일 요약
    print("\n📁 생성된 파일:")
    
    # 모델 파일
    if MODEL_OUTPUT_DIR.exists():
        for f in MODEL_OUTPUT_DIR.glob("*.pkl"):
            print(f"   - 모델: {f}")
    
    # SHAP 플롯
    shap_dir = ML_ROOT / "shap_plots"
    if shap_dir.exists():
        for f in shap_dir.glob("*.png"):
            print(f"   - SHAP: {f}")
    
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="월세 가격 분류 모델 전체 파이프라인 실행"
    )
    parser.add_argument(
        "--skip-prepare",
        action="store_true",
        help="데이터 준비 단계 스킵 (이미 데이터가 준비된 경우)"
    )
    parser.add_argument(
        "--skip-train",
        action="store_true",
        help="모델 학습 단계 스킵 (이미 모델이 학습된 경우)"
    )
    parser.add_argument(
        "--skip-shap",
        action="store_true",
        help="SHAP 분석 단계 스킵"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="데이터 디렉토리 경로"
    )
    
    args = parser.parse_args()
    
    run_pipeline(
        skip_prepare=args.skip_prepare,
        skip_train=args.skip_train,
        skip_shap=args.skip_shap,
        data_dir=args.data_dir,
    )
