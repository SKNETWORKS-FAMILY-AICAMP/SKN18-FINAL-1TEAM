"""
grouped_offices.csv의 추가 정보를 landbroker 테이블에 업데이트
"""
import os
import sys
import psycopg2
import pandas as pd
from datetime import datetime

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'realestate'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'postgres')
    )


def update_broker_stats():
    """grouped_offices.csv 데이터로 broker 정보 업데이트"""
    print("=" * 70)
    print(" " * 15 + "Broker 정보 업데이트 시작")
    print("=" * 70)
    
    # 1. CSV 로드
    csv_path = '/data/brokerInfo/grouped_offices.csv'
    if not os.path.exists(csv_path):
        csv_path = 'data/brokerInfo/grouped_offices.csv'
    
    print(f"\n1. CSV 로드 중: {csv_path}")
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    print(f"  ✓ {len(df)}개 중개소 정보 로드")
    
    # 2. DB 연결
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 3. 업데이트
    print("\n2. LandBroker 테이블 업데이트 중...")
    updated = 0
    not_found = 0
    
    for idx, row in df.iterrows():
        reg_num = row.get('등록번호')
        if not reg_num or pd.isna(reg_num):
            continue
        
        # 거래 건수 파싱 (NaN이면 None으로 처리)
        completed_deals_str = row.get('거래완료')
        registered_properties_str = row.get('등록매물')
        
        # NaN 체크 후 파싱 (NaN이면 None 유지)
        if pd.notna(completed_deals_str):
            completed_deals_str = str(completed_deals_str)
            completed_deals = int(completed_deals_str.replace('건', '').strip()) if completed_deals_str and completed_deals_str != 'nan' else None
        else:
            completed_deals = None
            
        if pd.notna(registered_properties_str):
            registered_properties_str = str(registered_properties_str)
            registered_properties = int(registered_properties_str.replace('건', '').strip()) if registered_properties_str and registered_properties_str != 'nan' else None
        else:
            registered_properties = None
        
        # 직원 정보 (NaN이면 None)
        brokers_count = int(row.get('공인중개사수')) if pd.notna(row.get('공인중개사수')) else None
        assistants_count = int(row.get('중개보조원수')) if pd.notna(row.get('중개보조원수')) else None
        staff_count = int(row.get('일반직원수')) if pd.notna(row.get('일반직원수')) else None
        
        # 지역 정보
        region = row.get('지역명') if pd.notna(row.get('지역명')) else None
        
        # 등록일
        registration_date = None
        if pd.notna(row.get('등록일')):
            try:
                registration_date = pd.to_datetime(row.get('등록일')).date()
            except:
                pass
        
        # UPDATE 쿼리 (COALESCE로 기존 값 유지)
        update_query = """
        UPDATE landbroker 
        SET 
            completed_deals = COALESCE(%s, completed_deals),
            registered_properties = COALESCE(%s, registered_properties),
            brokers_count = COALESCE(%s, brokers_count),
            assistants_count = COALESCE(%s, assistants_count),
            staff_count = COALESCE(%s, staff_count),
            region = COALESCE(%s, region),
            registration_date = COALESCE(%s, registration_date),
            updated_at = CURRENT_TIMESTAMP
        WHERE registration_number = %s
        """
        
        try:
            cur.execute(update_query, (
                completed_deals,
                registered_properties,
                brokers_count,
                assistants_count,
                staff_count,
                region,
                registration_date,
                reg_num
            ))
            
            if cur.rowcount > 0:
                updated += 1
                if updated % 100 == 0:
                    print(f"  진행: {updated}/{len(df)}")
            else:
                not_found += 1
                
        except Exception as e:
            print(f"  ✗ 오류 ({reg_num}): {e}")
    
    conn.commit()
    
    # 4. 결과
    print("\n" + "=" * 70)
    print(" " * 20 + "업데이트 완료")
    print("=" * 70)
    print(f"\n  업데이트: {updated}개")
    print(f"  미발견: {not_found}개")
    print("\n" + "=" * 70 + "\n")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    try:
        update_broker_stats()
    except Exception as e:
        print(f"\n✗ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
