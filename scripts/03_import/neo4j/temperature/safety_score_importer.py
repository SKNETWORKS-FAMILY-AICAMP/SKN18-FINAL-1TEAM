import sys
import os
# Add scripts/data_import to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import pandas as pd
import numpy as np
import psycopg2
from config import Config
from database import Database

"""
Safety Score Importer (안전 온도 계산기)

이 스크립트는 매물의 '안전 온도(Safety Temperature)'를 계산하여 Neo4j에 저장합니다.
안전 온도는 0~100 사이의 값이며, 점수가 높을수록 안전한 지역임을 의미합니다.

[점수 산정 로직 상세]

1. 총점 공식 (Total Safety Temperature)
   Total = (District_Score * 0.3) + (Street_Score * 0.2) + (Infra_Score * 0.5)

2. 세부 항목 계산식

   A. 지역 치안 점수 (District Score, 30%)   # 50% -> 30%
      - 데이터: 자치구별 5대 범죄 발생 건수 (살인, 강간, 강도, 절도, 폭력)
      - 1단계 (위험도 계산):
        Risk = (살인*3.0) + (강간*2.0) + (강도*1.8) + (폭력*1.0) + (절도*0.7)
      - 2단계 (정규화 및 반전):
        Score = (1 - (Risk - Min_Risk) / (Max_Risk - Min_Risk)) * 100
      - 의미: 범죄 위험도가 가장 낮은 구가 100점, 가장 높은 구가 0점.

   B. 골목 안전 점수 (Street Score, 20%)   # 10% -> 20%
      - 데이터: 매물 반경 200m 이내의 CCTV 및 비상벨 개수
      - 공식: Min(100, (CCTV * 5) + (Bell * 2))
      - 의미: CCTV와 비상벨이 많을수록 점수 상승 (최대 100점 제한).

   C. 응급 인프라 점수 (Infra Score, 50%)   # 40% -> 50%
      - 데이터: 매물에서 가장 가까운 경찰서(Police)와 소방서(Fire)까지의 직선 거리
      - 경찰 점수: Max(0, (1000 - Distance_to_Police) / 10)  (1km 이내 평가)
      - 소방 점수: Max(0, (2500 - Distance_to_Fire) / 25)    (2.5km 이내 평가)
      - 공식: (경찰 점수 + 소방 점수) / 2
      - 의미: 응급 시설이 가까울수록 고득점. (0m = 100점, 지정 거리 이상 = 0점)
"""

class SafetyScoreImporter:
    def __init__(self):
        self.driver = Database.get_driver()
        # No Postgres needed for Gu anymore? 
        # Actually user said "Don't use address info, use coordinates".
        # So I will disable the address update part or make it optional.
        # But wait, original task was to map crime rate which is BY GU.
        # So I still need to know which Gu a property is in.
        # The user wants to determine the Gu BY COORDINATE, not by address string.
        # So I don't need Postgres connection to fetch address string.
        # I only need Property coordinates from Neo4j/JSON.
        # Property nodes already have lat/lon in Neo4j.
        
        self.crime_weights = {
            'murder': 3.0, 
            'rape': 2.0, 
            'robbery': 1.8, 
            'theft': 0.7, 
            'violence': 1.0
        }
        self.gu_crime_scores = {}
        self.max_crime_score = 1
        self.min_crime_score = 0
        
        # Hardcoded Seoul District Centroids (Approximate)
        self.seoul_districts = {
            '강남구': {'lat': 37.5172, 'lon': 127.0473},
            '강동구': {'lat': 37.5527, 'lon': 127.1455},
            '강북구': {'lat': 37.6396, 'lon': 127.0257},
            '강서구': {'lat': 37.5509, 'lon': 126.8497},
            '관악구': {'lat': 37.4784, 'lon': 126.9516},
            '광진구': {'lat': 37.5385, 'lon': 127.0822},
            '구로구': {'lat': 37.4954, 'lon': 126.8581},
            '금천구': {'lat': 37.4568, 'lon': 126.8954},
            '노원구': {'lat': 37.6542, 'lon': 127.0568},
            '도봉구': {'lat': 37.6688, 'lon': 127.0471},
            '동대문구': {'lat': 37.5744, 'lon': 127.0400},
            '동작구': {'lat': 37.5124, 'lon': 126.9393},
            '마포구': {'lat': 37.5663, 'lon': 126.9016},
            '서대문구': {'lat': 37.5791, 'lon': 126.9368},
            '서초구': {'lat': 37.4837, 'lon': 127.0324},
            '성동구': {'lat': 37.5633, 'lon': 127.0371},
            '성북구': {'lat': 37.5891, 'lon': 127.0182},
            '송파구': {'lat': 37.5145, 'lon': 127.1066},
            '양천구': {'lat': 37.5169, 'lon': 126.8660},
            '영등포구': {'lat': 37.5264, 'lon': 126.8962},
            '용산구': {'lat': 37.5326, 'lon': 126.9904},
            '은평구': {'lat': 37.6027, 'lon': 126.9291},
            '종로구': {'lat': 37.5730, 'lon': 126.9794},
            '중구': {'lat': 37.5641, 'lon': 126.9979},
            '중랑구': {'lat': 37.6063, 'lon': 127.0926}
        }

    def close(self):
        pass

    def load_crime_data(self):
        """범죄 데이터를 로드하고 구별 점수를 계산합니다."""
        print("Loading Crime Data...")
        csv_path = os.path.join(Config.DATA_DIR, "../5대+범죄+발생현황_20251224115325.csv") 
        
        if not os.path.exists(csv_path):
             csv_path = os.path.join(Config.BASE_DIR, "data", "5대+범죄+발생현황_20251224115325.csv")

        if not os.path.exists(csv_path):
            print(f"Crime data file not found at {csv_path}")
            return

        try:
            df = pd.read_csv(csv_path)
            sub_df = df.iloc[4:].copy()
            sub_df['Gu'] = sub_df.iloc[:, 1]
            
            # Weighted Score Calc
            c_murder = pd.to_numeric(sub_df.iloc[:, 4], errors='coerce').fillna(0)
            c_robbery = pd.to_numeric(sub_df.iloc[:, 6], errors='coerce').fillna(0)
            c_rape = pd.to_numeric(sub_df.iloc[:, 8], errors='coerce').fillna(0)
            c_theft = pd.to_numeric(sub_df.iloc[:, 10], errors='coerce').fillna(0)
            c_violence = pd.to_numeric(sub_df.iloc[:, 12], errors='coerce').fillna(0)
            
            # MinMax Scaling per crime type (0-1 range)
            def minmax_scale(series):
                return (series - series.min()) / (series.max() - series.min())

            scores = (
                (minmax_scale(c_murder) * self.crime_weights['murder']) +
                (minmax_scale(c_rape) * self.crime_weights['rape']) +
                (minmax_scale(c_robbery) * self.crime_weights['robbery']) +
                (minmax_scale(c_theft) * self.crime_weights['theft']) +
                (minmax_scale(c_violence) * self.crime_weights['violence'])
            )
            
            self.gu_crime_scores = dict(zip(sub_df['Gu'], scores))
            
            # Since scores are already based on normalized inputs, we don't strictly need 
            # to normalize the Final Score again for calculation, but we do need to 
            # map it to a 0-100 scale for the output.
            if self.gu_crime_scores:
                self.max_crime_score = max(self.gu_crime_scores.values())
                self.min_crime_score = min(self.gu_crime_scores.values())
                
            print(f"Loaded crime scores for {len(self.gu_crime_scores)} districts.")
            
        except Exception as e:
            print(f"Error processing crime data: {e}")

    def import_safety_score(self):
        """
        안전 온도(Safety Temperature) 계산 및 Neo4j 저장
        
        Logic Changes:
        1. Gu Detection: Coordinate-based nearest neighbor using self.seoul_districts.
        2. Schema: HAS_TEMPERATURE relationship, 'temperature' property.
        3. Coverage: All properties.
        """
        print("Calculating and Importing Safety Temperature (Coord-based)...")
        
        self.load_crime_data()
        
        # Prepare normalized Gu scores (Higher is better/safer)
        # Original score: High = Danger.
        # We need: High = Safe (Temperature).
        # Normalize 0-1 then Invert.
        
        norm_gu_scores = {}
        for gu, score in self.gu_crime_scores.items():
            if self.max_crime_score > self.min_crime_score:
                norm = (score - self.min_crime_score) / (self.max_crime_score - self.min_crime_score)
            else:
                norm = 1.0 
            # Invert: Higher Risk (1.0) -> Lower Safety (0)
            norm_gu_scores[gu] = (1.0 - norm) * 100
        
        # Prepare district data for Cypher
        # List of maps: [{gu: 'Kangnam', lat: ..., lon: ..., score: ...}, ...]
        district_data = []
        for gu, info in self.seoul_districts.items():
            score = norm_gu_scores.get(gu, 50.0) # Default 50 if missing
            district_data.append({
                'gu': gu,
                'lat': info['lat'],
                'lon': info['lon'],
                'score': score
            })
            
        print("Running Batch Safety Temperature update via Cypher...")
        
        with self.driver.session() as session:
            count_res = session.run("MATCH (p:Property) RETURN count(p) as cnt")
            total_props = count_res.single()['cnt']
            print(f"Total properties to process: {total_props}")
            
            id_res = session.run("MATCH (p:Property) RETURN p.id as id")
            all_ids = [record['id'] for record in id_res]
            
            batch_size = 1000
            for i in range(0, len(all_ids), batch_size):
                batch_ids = all_ids[i:i+batch_size]
                
                query_score = """
                UNWIND $ids as pid
                MATCH (p:Property {id: pid})
                
                // 0. Find Nearest District Score (On-the-fly)
                WITH p
                UNWIND $districts as d
                WITH p, d, 
                     point.distance(point({latitude: p.latitude, longitude: p.longitude}), 
                                    point({latitude: d.lat, longitude: d.lon})) as dist
                ORDER BY dist ASC
                WITH p, head(collect(d.score)) as district_score
                
                // 1. Street Elements
                OPTIONAL MATCH (p)-[:NEAR_CCTV]->(cctv)
                WITH p, district_score, count(cctv) as cctv_count
                
                OPTIONAL MATCH (p)-[:NEAR_BELL]->(bell)
                WITH p, district_score, cctv_count, count(bell) as bell_count
                
                WITH p, district_score, cctv_count, bell_count,
                 CASE 
                    WHEN (cctv_count * 5 + bell_count * 2) > 100 THEN 100.0
                    ELSE toFloat(cctv_count * 5 + bell_count * 2)
                 END as street_score
                 
                // 2. Infra Elements
                OPTIONAL MATCH (p)-[rp:NEAR_POLICE]->(police)
                WITH p, district_score, street_score, min(rp.distance) as police_dist
                
                OPTIONAL MATCH (p)-[rf:NEAR_FIRE]->(fire)
                WITH p, district_score, street_score, police_dist, min(rf.distance) as fire_dist
                
                WITH p, district_score, street_score,
                     CASE WHEN police_dist IS NULL THEN 0 ELSE (1000 - police_dist) / 10.0 END as police_score_raw,
                     CASE WHEN fire_dist IS NULL THEN 0 ELSE (2500 - fire_dist) / 25.0 END as fire_score_raw
                
                WITH p, district_score, street_score, 
                     CASE WHEN police_score_raw < 0 THEN 0 ELSE police_score_raw END as police_score,
                     CASE WHEN fire_score_raw < 0 THEN 0 ELSE fire_score_raw END as fire_score
                     
                WITH p, district_score, street_score, (police_score + fire_score) / 2.0 as infra_score
                
                // Total Temperature (Updated Weights: District 30, Street 20, Infra 50)
                WITH p, 
                     (district_score * 0.3 + street_score * 0.2 + infra_score * 0.5) as raw_score
                
                // Convert to 30-43°C Temperature Scale (기존 로직 삭제 및 raw_score 설정)
                WITH p, raw_score
                
                MERGE (m:Metric {name: 'Safety'})
                MERGE (p)-[r:HAS_TEMPERATURE]->(m)
                SET r.raw_score = round(raw_score, 1),
                    r.updated_at = datetime()
                """
                session.run(query_score, ids=batch_ids, districts=district_data)
                print(f"Processed batch {i} - {i+len(batch_ids)}")

            # Step 2: Calculate Global Average and Scale to 36.5 Template
            print("  Step 2: Scaling towards 36.5 Global Average...")
            avg_result = session.run("""
            MATCH ()-[r:HAS_TEMPERATURE]->(m:Metric {name: 'Safety'})
            RETURN avg(r.raw_score) as global_avg
            """)
            global_avg = avg_result.single()['global_avg'] or 1.0
            print(f"    Global Average Raw Score: {global_avg:.2f}")

            session.run("""
            MATCH ()-[r:HAS_TEMPERATURE]->(m:Metric {name: 'Safety'})
            WITH r, $avg as raw_avg
            SET r.temperature = round(
                CASE 
                    WHEN r.raw_score <= raw_avg THEN 13 + r.raw_score * (23.5 / raw_avg)
                    ELSE 36.5 + (r.raw_score - raw_avg) * (23.5 / (100.0 - raw_avg))
                END, 1)
            """, avg=global_avg)

        print("Safety Temperature Import (Coord-based) Completed.")

if __name__ == "__main__":
    importer = SafetyScoreImporter()
    # Note: update_property_gu is removed/replaced by internal logic
    try:
        importer.import_safety_score()
    finally:
        importer.close()
        Database.close()
