import os
import json
import psycopg2
from psycopg2.extras import Json
from config import Config

class PostgresImporter:
    """
    PostgreSQL Land 테이블에 매물 데이터를 적재하는 Importer
    
    데이터 역할 분리:
    - PostgreSQL: 매물의 모든 상세 정보 저장 (주소, 가격, 옵션, 이미지, 설명 등)
    - Neo4j: 매물번호 + 좌표만 저장 (공간 기반 그래프 검색용)
    
    데이터 소스:
    - 경로: data/RDB/land/*.json
    - 파일: 00_통합_빌라주택.json, 00_통합_아파트.json, 00_통합_오피스텔.json, 00_통합_원투룸.json
    - 내용: 크롤링한 매물의 전체 정보
    """
    
    # 파일명과 building_type 매핑 (RDB/land의 JSON 파일 사용)
    FILE_TYPE_MAPPING = {
        "00_통합_빌라주택.json": "빌라주택",
        "00_통합_아파트.json": "아파트",
        "00_통합_오피스텔.json": "오피스텔",
        "00_통합_원투룸.json": "원투룸"
    }
    
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "postgres"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        self.cur = self.conn.cursor()
        
    def _create_land_table(self):
        """Land 테이블 확인 (init.sql에서 생성됨)"""
        check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'land'
        );
        """
        self.cur.execute(check_query)
        exists = self.cur.fetchone()[0]
        
        if not exists:
            create_table_query = """
            CREATE TABLE IF NOT EXISTS land (
                land_id SERIAL PRIMARY KEY,
                land_num VARCHAR(20) UNIQUE NOT NULL,
                landbroker_id INT,
                building_type VARCHAR(20) NOT NULL,
                address VARCHAR(200),
                deal_type VARCHAR(30),
                like_count INT DEFAULT 0,
                view_count INT DEFAULT 0,
                deposit INT DEFAULT 0,
                monthly_rent INT DEFAULT 0,
                jeonse_price INT DEFAULT 0,
                sale_price INT DEFAULT 0,
                url TEXT,
                images JSONB,
                trade_info JSONB,
                listing_info JSONB,
                additional_options TEXT[],
                description TEXT,
                agent_info JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            self.cur.execute(create_table_query)
            self.conn.commit()
            print("✓ Land 테이블 생성 완료")
        else:
            print("✓ Land 테이블 확인 완료")
    
    def _get_existing_count(self):
        """기존 매물 개수 확인"""
        self.cur.execute("SELECT COUNT(*) FROM land")
        return self.cur.fetchone()[0]

    def import_properties(self, skip_if_exists=True):
        """data/RDB/land 폴더의 JSON 파일들을 Land 테이블에 적재"""
        # 테이블 확인
        self._create_land_table()
        
        # 기존 데이터 확인
        existing_count = self._get_existing_count()
        if skip_if_exists and existing_count > 0:
            print(f"  ⏭ Land data already exists ({existing_count} records). Skipping import.")
            print("  (강제 업데이트를 원하면 skip_if_exists=False 사용)")
            return
        
        # Docker 환경에서는 /data/RDB/land, 로컬에서는 data/RDB/land
        if os.path.exists("/data/RDB/land"):
            data_dir = "/data/RDB/land"
            print("Docker 환경 감지: /data/RDB/land 사용")
        else:
            data_dir = os.path.join(Config.BASE_DIR, "data", "RDB", "land")
            print(f"로컬 환경 감지: {data_dir} 사용")
        
        if not os.path.exists(data_dir):
            print(f"✗ 데이터 디렉토리를 찾을 수 없습니다: {data_dir}")
            return

        # 처리할 JSON 파일 목록
        json_files = [f for f in os.listdir(data_dir) if f.endswith('.json') and f in self.FILE_TYPE_MAPPING]
        print(f"처리할 JSON 파일: {len(json_files)}개")
        
        total_inserted = 0
        total_updated = 0
        
        for file_idx, json_file in enumerate(json_files, 1):
            file_path = os.path.join(data_dir, json_file)
            building_type = self.FILE_TYPE_MAPPING.get(json_file, "기타")
            
            print(f"\n[{file_idx}/{len(json_files)}] [{building_type}] {json_file} 처리 중...")
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                inserted = 0
                updated = 0
                total_items = len(data)
                batch_size = 100  # For progress display
                
                for idx, item in enumerate(data):
                    result = self._insert_land(item, building_type)
                    if result == "inserted":
                        inserted += 1
                    elif result == "updated":
                        updated += 1
                    
                    # Progress display
                    if (idx + 1) % batch_size == 0:
                        self.conn.commit()
                        progress = idx + 1
                        print(f"  Progress: {progress}/{total_items} ({progress*100//total_items}%) - {inserted} inserted, {updated} updated")
                
                self.conn.commit()
                print(f"  ✓ {building_type}: {inserted}건 삽입, {updated}건 업데이트 (100%)")
                total_inserted += inserted
                total_updated += updated

            except Exception as e:
                self.conn.rollback()
                print(f"  ✗ 파일 처리 오류 ({json_file}): {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n총 결과: {total_inserted}건 삽입, {total_updated}건 업데이트")

    def _extract_deal_type(self, trade_info):
        """거래유형 추출"""
        deal_type = trade_info.get("거래유형")
        if deal_type and deal_type != "-":
            return deal_type
        
        deal_str = trade_info.get("거래방식", "")
        if "전세" in deal_str:
            return "전세"
        elif "월세" in deal_str:
            return "월세"
        elif "매매" in deal_str:
            return "매매"
        elif "단기임대" in deal_str:
            return "단기임대"
        return deal_str[:50] if deal_str else None

    def _parse_price_to_int(self, price_str):
        """한국어 가격 문자열을 만원 단위 정수로 변환"""
        if not price_str or price_str == '-' or price_str == '0원':
            return 0
        
        import re
        s = str(price_str).replace(',', '').replace(' ', '').replace('\xa0', '')
        
        eok = 0
        man = 0
        
        eok_match = re.search(r'(\d+)억', s)
        if eok_match:
            eok = int(eok_match.group(1))
        
        man_match = re.search(r'(\d+)만', s)
        if man_match:
            man = int(man_match.group(1))
        
        return eok * 10000 + man

    def _insert_land(self, item, building_type):
        """Land 테이블에 매물 데이터 삽입"""
        land_num = item.get("매물번호")
        if not land_num:
            return None

        address = item.get("주소_정보", {}).get("전체주소", "") if item.get("주소_정보") else None
        trade_info_raw = item.get("거래_정보", {})
        deal_type = self._extract_deal_type(trade_info_raw)
        
        deposit = self._parse_price_to_int(trade_info_raw.get("보증금"))
        monthly_rent = self._parse_price_to_int(trade_info_raw.get("월세"))
        jeonse_price = self._parse_price_to_int(trade_info_raw.get("보증금")) if deal_type == "전세" else 0
        sale_price = self._parse_price_to_int(trade_info_raw.get("매매가"))
        
        if deal_type == "전세":
            jeonse_price = deposit
            deposit = 0
        
        images_list = item.get("매물_이미지", [])
        url = item.get("매물_URL")
        trade_info = Json(trade_info_raw)
        listing_info = Json(item.get("매물_정보", {}))
        additional_options = item.get("추가_옵션", [])
        description = item.get("상세_설명")
        
        # 스타일태그 및 검색텍스트 추출 (OpenAI로 생성된 값만 사용)
        style_tags = item.get("style_tags") or item.get("스타일태그")
        if isinstance(style_tags, list):
            style_tags = ", ".join(style_tags)
        
        search_text = item.get("search_text") or item.get("검색텍스트")

        query = """
            INSERT INTO land (
                land_num, building_type, address, deal_type,
                deposit, monthly_rent, jeonse_price, sale_price,
                url, trade_info, listing_info,
                additional_options, description,
                style_tags, search_text
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s
            )
            ON CONFLICT (land_num) DO UPDATE SET
                building_type = EXCLUDED.building_type,
                address = EXCLUDED.address,
                deal_type = EXCLUDED.deal_type,
                deposit = EXCLUDED.deposit,
                monthly_rent = EXCLUDED.monthly_rent,
                jeonse_price = EXCLUDED.jeonse_price,
                sale_price = EXCLUDED.sale_price,
                url = EXCLUDED.url,
                trade_info = EXCLUDED.trade_info,
                listing_info = EXCLUDED.listing_info,
                additional_options = EXCLUDED.additional_options,
                description = EXCLUDED.description,
                style_tags = EXCLUDED.style_tags,
                search_text = EXCLUDED.search_text,
                updated_at = CURRENT_TIMESTAMP
            RETURNING land_id, (xmax = 0) AS inserted;
        """

        self.cur.execute(query, (
            land_num, building_type, address, deal_type,
            deposit, monthly_rent, jeonse_price, sale_price,
            url, trade_info, listing_info,
            additional_options, description,
            style_tags, search_text
        ))
        
        result = self.cur.fetchone()
        land_id = result[0] if result else None
        is_inserted = result[1] if result else False
        
        if land_id and images_list:
            self.cur.execute("DELETE FROM land_image WHERE land_id = %s", (land_id,))
            for img_url in images_list:
                if img_url:
                    self.cur.execute(
                        "INSERT INTO land_image (land_id, img_url) VALUES (%s, %s)",
                        (land_id, img_url)
                    )
        
        return "inserted" if is_inserted else "updated"

    def close(self):
        self.cur.close()
        self.conn.close()

if __name__ == "__main__":
    importer = PostgresImporter()
    try:
        importer.import_properties()
    finally:
        importer.close()
