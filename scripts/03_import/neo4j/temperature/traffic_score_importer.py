import os
import sys
import pandas as pd
import numpy as np

# Add scripts/data_import to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from database import Database

class TrafficScoreImporter:
    def __init__(self):
        self.driver = Database.get_driver()
        # Use relative path for Docker/Cross-platform compatibility
        # Assuming script is run from project root or handling path relative to this file
        base_path = os.path.dirname(os.path.abspath(__file__))
        # Path from this file to data: ../../../../../data/...
        # scripts/data_import/importers/neo4j_importers/temperature/ -> data/GraphDB_data...
        self.csv_path = os.path.join(base_path, "../../../../../data/GraphDB_data/subway_station/서울시 지하철 호선별 역별 시간대별 승하차 인원 정보.csv")
        self.work_hubs = [
            "가산디지털단지", "서울역", "여의도", "선릉", "시청", 
            "강남", "역삼", "잠실(송파구청)", "삼성(무역센터)", "을지로입구"
        ]

    def _load_and_calculate_station_grades(self):
        print(f"Loading data from {self.csv_path}...")
        try:
            df = pd.read_csv(self.csv_path, encoding='cp949')
        except:
            df = pd.read_csv(self.csv_path, encoding='utf-8')
            
        # Optimize: Filter latest year
        max_month = df['사용월'].max()
        latest_year_prefix = str(max_month)[:4]
        df = df[df['사용월'].astype(str).str.startswith(latest_year_prefix)].copy()
        
        # Preprocess Columns
        time_cols = [c for c in df.columns if '시' in c]
        for c in time_cols:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
        morning_cols = [c for c in time_cols if '07시' in c or '08시' in c]
        evening_cols = [c for c in time_cols if '17시' in c or '18시' in c]
        
        # Group by Station
        station_lines = df.groupby('지하철역')['호선명'].nunique()
        station_vol = df.groupby('지하철역')[time_cols].sum()
        
        station_vol['Rush_Flow'] = station_vol[morning_cols].sum(axis=1) + station_vol[evening_cols].sum(axis=1)
        station_vol['Daily_Total'] = station_vol[time_cols].sum(axis=1)
        
        stats = pd.concat([station_lines, station_vol], axis=1).rename(columns={'호선명': 'Line_Count'})
        
        # Scoring Logic
        # 1. Hub Score (40)
        def calc_hub(lines):
            if lines >= 4: return 40
            if lines == 3: return 32
            if lines == 2: return 20
            return 10
        stats['Hub_Score'] = stats['Line_Count'].apply(calc_hub)
        
        # 2. Volume Score (40)
        min_flow = stats['Rush_Flow'].min()
        max_flow = stats['Rush_Flow'].max()
        # Avoid log(0)
        if min_flow <= 0: min_flow = 1
        stats['Vol_Score'] = (np.log(stats['Rush_Flow'].clip(lower=1)) - np.log(min_flow)) / (np.log(max_flow) - np.log(min_flow)) * 40
        
        # 3. Comfort Score (+/- 20)
        stats['Rush_Ratio'] = stats['Rush_Flow'] / stats['Daily_Total']
        high_threshold = stats['Rush_Ratio'].quantile(0.85)
        low_threshold = stats['Rush_Ratio'].quantile(0.40)
        
        conditions = [
            (stats['Rush_Ratio'] > high_threshold),
            (stats['Rush_Ratio'] < low_threshold)
        ]
        choices = [-20, 20]
        stats['Comfort_Score'] = np.select(conditions, choices, default=0)
        
        # Total
        stats['Total_Grade'] = stats['Hub_Score'] + stats['Vol_Score'] + stats['Comfort_Score']
        stats['Total_Grade'] = stats['Total_Grade'].clip(0, 100)
        
        # Create Result Map
        # station_name -> grade_score
        grade_map = stats['Total_Grade'].to_dict()
        print(f"Calculated grades for {len(grade_map)} stations.")
        return grade_map

    def update_station_grades_in_db(self, grade_map):
        print("Updating Station Grades in Neo4j...")
        with self.driver.session() as session:
            # Batch update might be better, but explicit loop is safer for now or constructing a huge parameter list
            # Actually, passing a list of maps is best.
            data = [{"name": name, "score": float(score)} for name, score in grade_map.items()]
            
            query = """
            UNWIND $data as item
            MATCH (s:SubwayStation {name: item.name})
            SET s.traffic_grade = item.score
            """
            session.run(query, data=data)
            
            # Label Update (Static Logic for now)
            # S: >= 90, A: >= 70, B: >= 60, C: >= 40, D: < 40
            session.run("""
            MATCH (s:SubwayStation)
            WHERE s.traffic_grade IS NOT NULL
            WITH s, s.traffic_grade as score
            SET s.grade_label = CASE 
                WHEN score >= 90 THEN 'S'
                WHEN score >= 70 THEN 'A'
                WHEN score >= 60 THEN 'B'
                WHEN score >= 40 THEN 'C'
                ELSE 'D'
            END
            """)
        print("Station Node update complete.")

    def import_traffic_score(self):
        # 1. Calculate & Update Station Grades
        grade_map = self._load_and_calculate_station_grades()
        self.update_station_grades_in_db(grade_map)
        
        print("Calculating Final Traffic Temperature for Properties...")
        
        with self.driver.session() as session:
            # Clear existing Metric
            session.run("""
            MATCH (p:Property)-[r:HAS_TEMPERATURE]->(m:Metric {name: 'Traffic'})
            DELETE r
            """)
            
            # Define Work Hubs for Query
            work_hubs = self.work_hubs
            
            # Execute Calculation
            # 1. Station Score (Micro) - Max 40
            # 2. Work Hub Score (Macro) - Max 30
            # 3. Bus Score (Feeder) - Max 30
            
            query = """
            MATCH (p:Property)
            
            // 1. Station Grade Score (Micro)
            CALL {
                WITH p
                OPTIONAL MATCH (p)-[r1:NEAR_SUBWAY]->(s:SubwayStation)
                WHERE s.traffic_grade IS NOT NULL
                WITH p, s, r1.distance as dist, s.traffic_grade as grade
                ORDER BY dist ASC LIMIT 1
                
                WITH p, dist, grade,
                    CASE 
                        WHEN dist IS NULL THEN 0
                        WHEN dist <= 300 THEN 1.0
                        WHEN dist >= 800 THEN 0.0
                        ELSE 1.0 - (toFloat(dist) - 300) / 500.0
                    END as weight
                    
                RETURN (coalesce(grade, 0) * weight * 0.4) as score_station
            }
            
            // 2. Work Hub Access Score (Macro)
            CALL {
                WITH p
                // Match Work Hub Stations
                MATCH (wh:SubwayStation)
                WHERE wh.name IN $work_hubs
                
                // Calculate Distance using Point
                WITH p, wh, point.distance(p.location, wh.location) as dist_wh
                ORDER BY dist_wh ASC LIMIT 1
                
                WITH dist_wh,
                    CASE
                        WHEN dist_wh < 2000 THEN 30 // < 2km
                        WHEN dist_wh < 5000 THEN 25 // < 5km
                        WHEN dist_wh < 10000 THEN 15 // < 10km
                        ELSE 15 - ((dist_wh - 10000) / 2000) // Decay after 10km
                    END as raw_work_score
                
                RETURN CASE WHEN raw_work_score < 0 THEN 0 ELSE raw_work_score END as score_work
            }
            
            // 3. Bus Score (Feeder) - Max 30
            CALL {
                WITH p
                OPTIONAL MATCH (p)-[r2:NEAR_BUS]->(b:BusStation)
                WHERE r2.distance <= 300
                WITH count(b) as bus_count
                RETURN CASE 
                    WHEN bus_count * 3 > 30 THEN 30.0
                    ELSE toFloat(bus_count * 3)
                END as score_bus
            }
            
            // Calculate Total Score
            WITH p, score_station, score_work, score_bus,
                 (score_station + score_work + score_bus) as raw_score
                 
            MERGE (m:Metric {name: 'Traffic'})
            MERGE (p)-[r:HAS_TEMPERATURE]->(m)
            SET r.raw_score = raw_score,
                r.score_station = score_station,
                r.score_work = score_work,
                r.score_bus = score_bus,
                r.updated_at = datetime()
            """
            session.run(query, work_hubs=work_hubs)

            # Step 2: Calculate Global Average and Scale to 36.5 Template
            print("  Step 2: Scaling towards 36.5 Global Average...")
            avg_result = session.run("""
            MATCH ()-[r:HAS_TEMPERATURE]->(m:Metric {name: 'Traffic'})
            RETURN avg(r.raw_score) as global_avg
            """)
            global_avg = avg_result.single()['global_avg'] or 1.0
            print(f"    Global Average Raw Score: {global_avg:.2f}")

            session.run("""
            MATCH ()-[r:HAS_TEMPERATURE]->(m:Metric {name: 'Traffic'})
            WITH r, $avg as raw_avg
            WITH r, raw_avg,
                CASE 
                    WHEN r.raw_score <= raw_avg THEN 13 + r.raw_score * (23.5 / raw_avg)
                    ELSE 36.5 + (r.raw_score - raw_avg) * (23.5 / (100.0 - raw_avg))
                END as calc_temp
            SET r.temperature = round(
                CASE 
                    WHEN calc_temp < 13 THEN 13.0
                    WHEN calc_temp > 60 THEN 60.0
                    ELSE calc_temp
                END, 1)
            """, avg=global_avg)
            
        print("Finished calculating Traffic Temperature.")

if __name__ == "__main__":
    importer = TrafficScoreImporter()
    importer.import_traffic_score()
