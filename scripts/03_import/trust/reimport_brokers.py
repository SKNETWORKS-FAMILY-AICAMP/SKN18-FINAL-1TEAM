"""
JSON 원본 파일에서 중개사 정보를 직접 추출하여 landbroker 테이블에 저장

agent_info 컬럼 제거로 인해 원본 JSON 파일(data/RDB/land/*.json)에서 직접 읽어옵니다.
"""
import os
import sys
import json
import psycopg2

# Database connection
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'realestate'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'postgres')
    )


def import_brokers_from_json():
    """JSON 파일에서 중개사 정보 추출 및 저장"""
    print("=" * 70)
    print(" " * 15 + "중개사 정보 Import (JSON 기반)")
    print("=" * 70 + "\n")
    
    # 1. JSON 파일 경로
    if os.path.exists("/data/RDB/land"):
        data_dir = "/data/RDB/land"
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(base_dir, "data", "RDB", "land")
    
    json_files = [
        "00_통합_빌라주택.json",
        "00_통합_아파트.json",
        "00_통합_오피스텔.json",
        "00_통합_원투룸.json"
    ]
    
    print(f"1. JSON 파일 읽기 중... (경로: {data_dir})\n")
    
    # 2. 중개사 정보 수집 (등록번호 기준 중복 제거)
    brokers_dict = {}  # {registration_number: {info, land_nums}}
    
    for json_file in json_files:
        file_path = os.path.join(data_dir, json_file)
        if not os.path.exists(file_path):
            print(f"  ⚠ 파일 없음: {json_file}")
            continue
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"  ✓ {json_file}: {len(data)}개 매물")
        
        for item in data:
            agent_info = item.get('중개사_정보', {})
            if not agent_info:
                continue
            
            # 등록번호 추출
            reg_num = agent_info.get('registration_number') or agent_info.get('등록번호')
            land_num = item.get('매물번호')
            
            if not reg_num or not land_num:
                continue
            
            if reg_num not in brokers_dict:
                brokers_dict[reg_num] = {
                    'info': agent_info,
                    'land_nums': []
                }
            
            brokers_dict[reg_num]['land_nums'].append(land_num)
    
    print(f"\n  총 {len(brokers_dict)}개 고유 중개사 발견\n")
    
    # 3. DB에 저장
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("2. LandBroker 테이블에 저장 중...\n")
    
    inserted = 0
    updated = 0
    failed = 0
    
    for reg_num, data in brokers_dict.items():
        info = data['info']
        
        # UPSERT
        query = """
        INSERT INTO landbroker (
            office_name, representative, phone, address, registration_number
        ) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (registration_number) DO UPDATE SET
            office_name = COALESCE(EXCLUDED.office_name, landbroker.office_name),
            representative = COALESCE(EXCLUDED.representative, landbroker.representative),
            phone = COALESCE(EXCLUDED.phone, landbroker.phone),
            address = COALESCE(EXCLUDED.address, landbroker.address),
            updated_at = CURRENT_TIMESTAMP
        RETURNING landbroker_id, (xmax = 0) AS is_new;
        """
        
        values = (
            info.get('name') or info.get('중개사명'),
            info.get('representative') or info.get('대표자'),
            info.get('phone') or info.get('전화번호'),
            info.get('address') or info.get('주소'),
            reg_num
        )
        
        try:
            cur.execute(query, values)
            result = cur.fetchone()
            broker_id = result[0]
            is_new = result[1]
            
            # Land 테이블의 FK 업데이트
            update_query = """
            UPDATE land 
            SET landbroker_id = %s
            WHERE land_num = ANY(%s)
            """
            cur.execute(update_query, (broker_id, data['land_nums']))
            
            conn.commit()
            
            if is_new:
                inserted += 1
            else:
                updated += 1
            
            if (inserted + updated) % 50 == 0:
                print(f"  진행: {inserted + updated}/{len(brokers_dict)}")
        
        except Exception as e:
            conn.rollback()
            print(f"  ✗ 오류 ({reg_num}): {e}")
            failed += 1
    
    # 4. 결과 출력
    print("\n" + "=" * 70)
    print(" " * 20 + "Import 완료")
    print("=" * 70)
    print(f"\n  신규 삽입: {inserted}개")
    print(f"  업데이트: {updated}개")
    print(f"  실패: {failed}개")
    
    # 5. 통계
    cur.execute("SELECT COUNT(*) FROM landbroker")
    broker_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM land WHERE landbroker_id IS NOT NULL")
    linked_count = cur.fetchone()[0]
    
    print(f"\n  총 중개소: {broker_count}개")
    print(f"  연결된 매물: {linked_count}개")
    print("\n" + "=" * 70 + "\n")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    try:
        import_brokers_from_json()
    except Exception as e:
        print(f"\n✗ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

