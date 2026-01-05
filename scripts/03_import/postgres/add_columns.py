#!/usr/bin/env python
"""
PostgreSQL land 테이블에 style_tags, search_text 컬럼 추가
"""
import sys
import os
import psycopg2
from pathlib import Path

# Add scripts/03_import to path
IMPORT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(IMPORT_DIR))

from config import Config


def add_columns():
    """land 테이블에 style_tags, search_text 컬럼 추가"""
    print("\n" + "=" * 70)
    print(" " * 15 + "PostgreSQL 테이블 컬럼 추가")
    print("=" * 70)
    
    try:
        # DB 연결
        print(f"\n연결 중: {Config.POSTGRES_HOST}:{Config.POSTGRES_PORT}/{Config.POSTGRES_DB}")
        conn = psycopg2.connect(
            dbname=Config.POSTGRES_DB,
            user=Config.POSTGRES_USER,
            password=Config.POSTGRES_PASSWORD,
            host=Config.POSTGRES_HOST,
            port=Config.POSTGRES_PORT
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        print("✓ 연결 성공\n")
        
        # 기존 컬럼 확인
        print("기존 컬럼 확인 중...")
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'land' 
            AND column_name IN ('style_tags', 'search_text')
        """)
        existing_columns = [row[0] for row in cur.fetchall()]
        
        if existing_columns:
            print(f"  이미 존재하는 컬럼: {', '.join(existing_columns)}")
        
        # style_tags 컬럼 추가
        if 'style_tags' not in existing_columns:
            print("\nstyle_tags 컬럼 추가 중...")
            cur.execute("""
                ALTER TABLE land 
                ADD COLUMN style_tags TEXT
            """)
            print("  ✓ style_tags 컬럼 추가 완료")
        else:
            print("\n  ⏭ style_tags 컬럼 이미 존재")
        
        # search_text 컬럼 추가
        if 'search_text' not in existing_columns:
            print("\nsearch_text 컬럼 추가 중...")
            cur.execute("""
                ALTER TABLE land 
                ADD COLUMN search_text TEXT
            """)
            print("  ✓ search_text 컬럼 추가 완료")
        else:
            print("\n  ⏭ search_text 컬럼 이미 존재")
        
        # 결과 확인
        print("\n최종 확인 중...")
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'land' 
            AND column_name IN ('style_tags', 'search_text')
            ORDER BY column_name
        """)
        
        print("\n현재 컬럼 상태:")
        for row in cur.fetchall():
            print(f"  - {row[0]}: {row[1]} (nullable: {row[2]})")
        
        print("\n" + "=" * 70)
        print("✅ 컬럼 추가 완료!")
        print("=" * 70 + "\n")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    add_columns()
