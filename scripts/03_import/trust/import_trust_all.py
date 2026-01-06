"""
중개사 데이터 Import + 통계 업데이트 + Trust Score 예측 통합 스크립트

사용법:
    # 전체 실행 (Import → 통계 → 예측)
    docker compose --profile scripts run --rm scripts python 03_import/trust/import_trust_all.py

    # 개별 실행
    docker compose --profile scripts run --rm scripts python 03_import/trust/import_trust_all.py --import-only
    docker compose --profile scripts run --rm scripts python 03_import/trust/import_trust_all.py --stats-only
    docker compose --profile scripts run --rm scripts python 03_import/trust/import_trust_all.py --predict-only
"""
import sys
import os
import argparse

# 경로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# 같은 폴더의 모듈 import
from reimport_brokers import import_brokers_from_json
from update_broker_stats import update_broker_stats
from predict_trust_scores import predict


def main():
    parser = argparse.ArgumentParser(description='중개사 Import + 통계 + Trust Score 예측')
    parser.add_argument('--import-only', action='store_true', help='Import만 실행')
    parser.add_argument('--stats-only', action='store_true', help='통계 업데이트만 실행')
    parser.add_argument('--predict-only', action='store_true', help='예측만 실행')
    args = parser.parse_args()
    
    print("\n🏠 중개사 데이터 Import + 통계 업데이트 + Trust Score 예측\n")
    
    # 개별 실행 모드
    if args.import_only:
        import_brokers_from_json()
    elif args.stats_only:
        update_broker_stats()
    elif args.predict_only:
        predict()
    else:
        # 전체 실행 (순서: Import → 통계 → 예측)
        import_brokers_from_json()
        update_broker_stats()
        predict()
    
    print("✅ 완료\n")


if __name__ == "__main__":
    main()
