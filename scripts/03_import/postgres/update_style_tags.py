"""
기존 매물 데이터에 style_tags와 search_text를 업데이트하는 스크립트
"""
import sys
import os
import json
import psycopg2
from pathlib import Path

# Add scripts/03_import to path
IMPORT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(IMPORT_DIR))

from config import Config


def update_style_tags():
    """JSON 파일에서 style_tags, search_text를 읽어 DB 업데이트"""
    print("\n" + "=" * 60)
    print("  Style Tags & Search Text 업데이트")
    print("=" * 60 + "\n")
    
    # DB 연결
    conn = psycopg2.connect(
        dbname=Config.POSTGRES_DB,
        user=Config.POSTGRES_USER,
        password=Config.POSTGRES_PASSWORD,
        host=Config.POSTGRES_HOST,
        port=Config.POSTGRES_PORT
    )
    cur = conn.cursor()
    
    # JSON 파일 경로
    if os.path.exists("/data/RDB/land"):
        data_dir = "/data/RDB/land"
    else:
        data_dir = os.path.join(Config.BASE_DIR, "data", "RDB", "land")
    
    json_files = [
        "00_통합_빌라주택.json",
        "00_통합_아파트.json",
        "00_통합_오피스텔.json",
        "00_통합_원투룸.json"
    ]
    
    total_updated = 0
    
    for json_file in json_files:
        file_path = os.path.join(data_dir, json_file)
        if not os.path.exists(file_path):
            print(f"  ⚠ 파일 없음: {json_file}")
            continue
        
        print(f"[처리 중] {json_file}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        updated = 0
        for item in data:
            land_num = item.get("매물번호")
            if not land_num:
                continue
            
            # style_tags 추출
            style_tags = item.get("style_tags") or item.get("스타일태그")
            if isinstance(style_tags, list):
                style_tags = ", ".join(style_tags)
            
            # search_text 추출
            search_text = item.get("search_text") or item.get("검색텍스트")
            
            if style_tags or search_text:
                cur.execute("""
                    UPDATE land 
                    SET style_tags = %s, search_text = %s
                    WHERE land_num = %s
                """, (style_tags, search_text, land_num))
                
                if cur.rowcount > 0:
                    updated += 1
        
        conn.commit()
        print(f"  ✓ {updated}건 업데이트 완료")
        total_updated += updated
    
    # 결과 확인
    cur.execute("SELECT COUNT(*) FROM land WHERE style_tags IS NOT NULL")
    with_tags = cur.fetchone()[0]
    
    print("\n" + "=" * 60)
    print(f"  총 업데이트: {total_updated}건")
    print(f"  style_tags가 있는 매물: {with_tags}건")
    print("=" * 60 + "\n")
    
    cur.close()
    conn.close()


if __name__ == "__main__":
    update_style_tags()
