#!/usr/bin/env python
"""
통합 데이터 Import 스크립트

Neo4j, PostgreSQL, Elasticsearch에 데이터를 일괄 적재합니다.

Usage:
    // 전체 Import
    docker compose --profile scripts run --rm scripts python 03_import/import_all.py

    // 특정 DB만 Import
    docker compose --profile scripts run --rm scripts python 03_import/import_all.py --only neo4j
    docker compose --profile scripts run --rm scripts python 03_import/import_all.py --only postgres
    docker compose --profile scripts run --rm scripts python 03_import/import_all.py --only es
"""
import sys
import os
import time
import argparse
import subprocess
from pathlib import Path

# Add scripts/03_import to path
IMPORT_DIR = Path(__file__).parent
sys.path.insert(0, str(IMPORT_DIR))

from config import Config
from db_health_check import DatabaseHealthCheck


def import_neo4j():
    """Neo4j 데이터 Import (subprocess로 실행)"""
    print("\n" + "=" * 70)
    print(" " * 20 + "📦 Neo4j Import 시작")
    print("=" * 70)
    
    neo4j_script = IMPORT_DIR / "neo4j" / "import_neo4j_only.py"
    result = subprocess.run(
        [sys.executable, str(neo4j_script)],
        cwd=str(IMPORT_DIR / "neo4j")
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Neo4j Import 실패 (exit code: {result.returncode})")
    
    print("\n✅ Neo4j Import 완료!")


def import_postgres():
    """PostgreSQL 데이터 Import (subprocess로 실행)"""
    print("\n" + "=" * 70)
    print(" " * 20 + "🐘 PostgreSQL Import 시작")
    print("=" * 70)
    
    postgres_script = IMPORT_DIR / "postgres" / "import_postgres_only.py"
    result = subprocess.run(
        [sys.executable, str(postgres_script)],
        cwd=str(IMPORT_DIR / "postgres")
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"PostgreSQL Import 실패 (exit code: {result.returncode})")
    
    print("\n✅ PostgreSQL Import 완료!")


def import_elasticsearch():
    """Elasticsearch 데이터 Import (subprocess로 실행)"""
    print("\n" + "=" * 70)
    print(" " * 20 + "� Elasticsearch Import 시작")
    print("=" * 70)
    
    es_script = IMPORT_DIR / "elasticsearch" / "es817_property_importer.py"
    result = subprocess.run(
        [sys.executable, str(es_script)],
        cwd=str(IMPORT_DIR / "elasticsearch")
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Elasticsearch Import 실패 (exit code: {result.returncode})")
    
    print("\n✅ Elasticsearch Import 완료!")


def main():
    parser = argparse.ArgumentParser(description="통합 데이터 Import 스크립트")
    parser.add_argument(
        "--only",
        choices=["neo4j", "postgres", "es", "elasticsearch"],
        help="특정 DB만 Import (생략 시 전체)"
    )
    parser.add_argument(
        "--skip-health-check",
        action="store_true",
        help="DB 연결 확인 스킵"
    )
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print(" " * 15 + "🚀 통합 데이터 Import 파이프라인")
    print("=" * 70)
    
    start_time = time.time()
    
    try:
        # 1. 환경 변수 검증
        print("\n[사전 검증] 환경 변수 확인 중...")
        Config.validate_env_vars()
        Config.validate_kakao_api_key()
        print("✓ 환경 변수 확인 완료")
        
        # 2. DB 연결 확인
        if not args.skip_health_check:
            print("\n[사전 검증] DB 연결 확인 중...")
            
            if args.only is None or args.only == "neo4j":
                DatabaseHealthCheck.wait_for_neo4j(
                    Config.NEO4J_URI, Config.NEO4J_USER, Config.NEO4J_PASSWORD
                )
            
            if args.only is None or args.only == "postgres":
                DatabaseHealthCheck.wait_for_postgres(
                    Config.POSTGRES_HOST, Config.POSTGRES_PORT,
                    Config.POSTGRES_DB, Config.POSTGRES_USER, Config.POSTGRES_PASSWORD
                )
            
            if args.only is None or args.only in ["es", "elasticsearch"]:
                try:
                    DatabaseHealthCheck.wait_for_elasticsearch(
                        os.getenv("ELASTICSEARCH_HOST", "elasticsearch"),
                        int(os.getenv("ELASTICSEARCH_PORT", "9200"))
                    )
                except Exception as e:
                    print(f"⚠️ Elasticsearch 연결 실패: {e}")
                    print("  Elasticsearch Import를 건너뜁니다.")
            
            print("✓ DB 연결 확인 완료")
        
        # 3. Import 실행
        if args.only == "neo4j":
            import_neo4j()
        elif args.only == "postgres":
            import_postgres()
        elif args.only in ["es", "elasticsearch"]:
            import_elasticsearch()
        else:
            # 전체 Import (순서: Neo4j → PostgreSQL → Elasticsearch)
            # Neo4j는 선택적 (연결 실패 시 건너뜀)
            try:
                import_neo4j()
            except Exception as e:
                print(f"\n⚠️ Neo4j Import 실패: {e}")
                print("  Neo4j Import를 건너뛰고 PostgreSQL Import를 계속 진행합니다.")
            
            import_postgres()
            
            # Elasticsearch는 선택적 (실패 시 건너뜀)
            try:
                import_elasticsearch()
            except Exception as e:
                print(f"\n⚠️ Elasticsearch Import 실패: {e}")
                print("  Elasticsearch Import를 건너뛰고 계속 진행합니다.")
        
        elapsed = time.time() - start_time
        print("\n" + "=" * 70)
        print(f"✅ 전체 Import 완료! (소요 시간: {elapsed:.1f}초)")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
