"""
중개사 신뢰도 모델 - 전체 파이프라인 자동 실행 스크립트
올바른 순서 (데이터 누수 방지):
0) 데이터 로드 및 기본 클렌징 (_00)
1) Train/Test Split (_01)
2) Train 기준 Z-score 계산 및 Feature 생성 (_02)
3) 모델 학습 (_03)
4) 모델 평가 (_04)
5) 모델 저장 (_05)
"""

from pathlib import Path
import sys
import os

# 프로젝트 루트로 작업 디렉토리 변경 (data/ 폴더 접근을 위해)
project_root = Path(__file__).parent.parent.parent.parent.parent
os.chdir(project_root)
print(f"📁 작업 디렉토리 변경: {project_root}")

# pipeline 폴더 경로 추가
pipeline_dir = Path(__file__).parent / "pipeline"
sys.path.insert(0, str(pipeline_dir))

# 개별 단계 import
from _00_load_data import main as step00_load_data
from _01_create_target import main as step01_create_target
from _02_create_features import main as step02_create_features
from _03_train import main as step03_train
from _04_eval import main as step04_eval
from _05_save_model import main as step05_save_model


def main():
    print("\n====================================")
    print("🚀 중개사 신뢰도 모델 전체 파이프라인 실행 시작")
    print("====================================")

    try:
        # ---------------------------------------------
        # 0) 데이터 로드 및 전처리
        # ---------------------------------------------
        print("\n\n=== [0단계] 데이터 로드 및 전처리 ===")
        step00_load_data()
        print("✅ 0단계 완료")

        # ---------------------------------------------
        # 1) Train/Test Split
        # ---------------------------------------------
        print("\n\n=== [1단계] Train/Test Split ===")
        step01_create_target()
        print("✅ 1단계 완료")

        # ---------------------------------------------
        # 2) Train 기준 Z-score 계산 및 Feature 생성
        # ---------------------------------------------
        print("\n\n=== [2단계] Train 기준 Target 생성 및 Feature 생성 ===")
        step02_create_features()
        print("✅ 2단계 완료")

        # ---------------------------------------------
        # 3) 모델 학습
        # ---------------------------------------------
        print("\n\n=== [3단계] 모델 학습 ===")
        step03_train()
        print("✅ 3단계 완료")

        # ---------------------------------------------
        # 4) 모델 평가
        # ---------------------------------------------
        print("\n\n=== [4단계] 모델 평가 ===")
        step04_eval()
        print("✅ 4단계 완료")

        # ---------------------------------------------
        # 5) 모델 저장
        # ---------------------------------------------
        print("\n\n=== [5단계] 모델 저장 ===")
        step05_save_model()
        print("✅ 5단계 완료")

        print("\n====================================")
        print("🎉 전체 파이프라인 실행 완료!")
        print("====================================\n")

    except Exception as e:
        print(f"\n❌ 파이프라인 실행 중 오류 발생: {e}")
        print("파이프라인이 중단되었습니다.")
        raise


if __name__ == "__main__":
    main()
