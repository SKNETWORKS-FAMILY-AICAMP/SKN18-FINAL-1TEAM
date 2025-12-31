import sys
import os
import pandas as pd
import requests
import time
from pathlib import Path

# Add scripts/data_import to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from config import Config
from database import Database

class PetScoreImporter:
    def __init__(self):
        self.driver = Database.get_driver()
        self.base_dir = Path(Config.BASE_DIR)
        self.kakao_api_key = Config.KAKAO_API_KEY
        
    def get_coords(self, address):
        """카카오 API를 이용해 주소를 좌표로 변환"""
        if not address or not self.kakao_api_key:
            return None, None
            
        url = "https://dapi.kakao.com/v2/local/search/address.json"
        headers = {"Authorization": f"KakaoAK {self.kakao_api_key}"}
        params = {"query": address}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data['documents']:
                    return float(data['documents'][0]['y']), float(data['documents'][0]['x'])
        except Exception as e:
            print(f"  [Error] Geocoding failed for {address}: {e}")
        return None, None

    def import_nodes(self):
        """반려동물 전용 시설(놀이터 등) 노드 생성"""
        print("Importing PetPlayground nodes...")
        playground_csv = self.base_dir / "data" / "GraphDB_data" / "pet" / "반려동물 놀이터.csv"
        
        if not playground_csv.exists():
            print(f"File not found: {playground_csv}")
            return

        try:
            df = pd.read_csv(playground_csv, encoding='utf-8')
        except:
            df = pd.read_csv(playground_csv, encoding='cp949')

        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:PetPlayground) REQUIRE p.id IS UNIQUE")
            
            query = """
            UNWIND $batch AS row
            MERGE (p:PetPlayground {id: row.id})
            SET p.name = row.name,
                p.latitude = toFloat(row.lat),
                p.longitude = toFloat(row.lon),
                p.location = point({latitude: toFloat(row.lat), longitude: toFloat(row.lon)})
            """
            
            batch = []
            for i, row in df.iterrows():
                # 주소 컬럼(위치)에서 좌표 추출
                lat, lon = None, None
                if '위도' in row and pd.notna(row['위도']):
                    lat, lon = row['위도'], row['경도']
                # 좌표 데이터가 이미 있으므로 지오코딩 불필요
                # elif '위치' in row:
                #     lat, lon = self.get_coords(row['위치'])
                #     time.sleep(0.1) # Rate limit 방지
                
                if lat and lon:
                    batch.append({
                        "id": f"PG_{i}",
                        "name": row.get('공원명') or row.get('시설명'),
                        "lat": lat,
                        "lon": lon
                    })
                
                if len(batch) >= 100:
                    session.run(query, batch=batch)
                    batch = []
            if batch:
                session.run(query, batch=batch)
        print("Finished importing PetPlayground nodes.")

    def calculate_scores(self):
        """매물별 반려동물 온도 계산 및 저장 (NEAR_* 관계 기반 - 최적화)"""
        print("Calculating Pet Temperature for all properties...")
        
        with self.driver.session() as session:
            # 기존 점수 삭제
            session.run("MATCH (p:Property)-[r:HAS_TEMPERATURE]->(m:Metric {name: 'Pet'}) DELETE r")
            
            # IN TRANSACTIONS로 배치 처리 (관계 기반이라 훨씬 빠름)
            print("  Using NEAR_* relationships for fast calculation...")
            session.run("""
            MATCH (p:Property)
            CALL {
                WITH p
                
                // A. 반려동물 놀이터 (NEAR_PET_PLAYGROUND 관계 사용)
                OPTIONAL MATCH (p)-[r1:NEAR_PET_PLAYGROUND]->(pg:PetPlayground)
                WITH p,
                     count(r1) as pg_cnt,
                     sum(CASE WHEN r1.distance <= 500 THEN 2.0 ELSE 1.0 END) as pg_score_raw
                
                // B. 동물병원 (NEAR_ANIMAL_HOSPITAL 관계 사용)
                OPTIONAL MATCH (p)-[r2:NEAR_ANIMAL_HOSPITAL]->(ah:AnimalHospital)
                WITH p, pg_cnt, pg_score_raw,
                     count(r2) as h_cnt,
                     sum(CASE WHEN r2.distance <= 300 THEN 2.0 ELSE 1.0 END) as h_score_raw
                
                // C. 공원 (NEAR_PARK 관계 사용 - 문화 온도와 공유)
                OPTIONAL MATCH (p)-[r3:NEAR_PARK]->(pk:Park)
                WHERE pk.area >= 1500  // 1500m2 이상
                WITH p, pg_cnt, pg_score_raw, h_cnt, h_score_raw,
                     count(r3) as pk_cnt,
                     sum(CASE WHEN r3.distance <= 300 THEN 1.5 ELSE 1.0 END) as pk_score_raw
                
                // D. 펫샵 (NEAR_PET_SHOP 관계 사용)
                OPTIONAL MATCH (p)-[r4:NEAR_PET_SHOP]->(ps:PetShop)
                WITH p, pg_cnt, pg_score_raw, h_cnt, h_score_raw, pk_cnt, pk_score_raw,
                     count(r4) as s_cnt,
                     sum(CASE WHEN r4.distance <= 300 THEN 1.5 ELSE 1.0 END) as s_score_raw
                
                // 가중치 계산 (100점 만점)
                WITH p, pg_cnt, h_cnt, pk_cnt, s_cnt,
                     (CASE WHEN coalesce(pg_score_raw, 0) * 20 > 30 THEN 30.0 ELSE coalesce(pg_score_raw, 0) * 20 END +
                      CASE WHEN coalesce(h_score_raw, 0) * 10 > 25 THEN 25.0 ELSE coalesce(h_score_raw, 0) * 10 END +
                      CASE WHEN coalesce(pk_score_raw, 0) * 5 > 15 THEN 15.0 ELSE coalesce(pk_score_raw, 0) * 5 END +
                      CASE WHEN coalesce(s_score_raw, 0) * 5 > 30 THEN 30.0 ELSE coalesce(s_score_raw, 0) * 5 END) as raw_score
                
                // raw_score만 저장 (temperature는 나중에 글로벌 평균으로 계산)
                MERGE (m:Metric {name: 'Pet'})
                MERGE (p)-[r:HAS_TEMPERATURE]->(m)
                SET r.raw_score = raw_score,
                    r.playground_count = pg_cnt,
                    r.hospital_count = h_cnt,
                    r.park_count = pk_cnt,
                    r.shop_count = s_cnt,
                    r.updated_at = datetime()
            } IN TRANSACTIONS OF 1000 ROWS
            """)
            
            # Step 2: Calculate Global Average and Scale to 36.5
            print("  Step 2: Scaling towards 36.5 Global Average...")
            avg_result = session.run("""
            MATCH ()-[r:HAS_TEMPERATURE]->(m:Metric {name: 'Pet'})
            RETURN avg(r.raw_score) as global_avg
            """)
            global_avg = avg_result.single()['global_avg'] or 1.0
            print(f"    Global Average Raw Score: {global_avg:.2f}")

            session.run("""
            MATCH ()-[r:HAS_TEMPERATURE]->(m:Metric {name: 'Pet'})
            WITH r, $avg as raw_avg
            SET r.temperature = round(
                CASE 
                    WHEN r.raw_score <= raw_avg THEN 13 + r.raw_score * (23.5 / raw_avg)
                    ELSE 36.5 + (r.raw_score - raw_avg) * (23.5 / (100.0 - raw_avg))
                END, 1)
            """, avg=global_avg)
        
        print("Pet Temperature calculation completed.")

if __name__ == "__main__":
    importer = PetScoreImporter()
    importer.import_nodes()
    importer.calculate_scores()
    Database.close()
