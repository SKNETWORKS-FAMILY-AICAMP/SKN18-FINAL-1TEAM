"""
PostgreSQL Land 테이블에만 데이터를 적재하는 스크립트
data/landData 폴더의 4개 JSON 파일을 Land 테이블에 적재
"""
import sys
import os
from pathlib import Path

# Add scripts/03_import to path for config/db_health_check
IMPORT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(IMPORT_DIR))

from config import Config
from db_health_check import DatabaseHealthCheck
from postgres_importer import PostgresImporter


def main():
    print("\n" + "=" * 50)
    print("  PostgreSQL Land 테이블 데이터 적재")
    print("=" * 50 + "\n")
    
    try:
        # 1. PostgreSQL 연결 확인
        print("[1/3] PostgreSQL 연결 확인 중...")
        DatabaseHealthCheck.wait_for_postgres(
            Config.POSTGRES_HOST,
            Config.POSTGRES_PORT,
            Config.POSTGRES_DB,
            Config.POSTGRES_USER,
            Config.POSTGRES_PASSWORD
        )
        print("✓ PostgreSQL 연결 완료\n")
        
        # 2. 데이터 적재
        print("[2/3] Land 테이블 데이터 적재 중...")
        pg_importer = PostgresImporter()
        try:
            pg_importer.import_properties()
            print("\n✓ PostgreSQL 데이터 적재 완료!")
        finally:
            pg_importer.close()
        
        # 3. Style Tags & Search Text 업데이트
        print("\n[3/3] Style Tags & Search Text 업데이트 중...")
        from update_style_tags import update_style_tags
        update_style_tags()
        print("✓ Style Tags 업데이트 완료!")
            
    except Exception as e:
        print(f"\n✗ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
