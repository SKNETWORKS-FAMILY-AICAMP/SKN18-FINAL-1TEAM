"""
학습된 모델로 Trust Score 예측 (psycopg2 버전)

Django ORM 대신 psycopg2 사용 → scripts 컨테이너에서 실행 가능
"""
import os
import sys
import pickle
import psycopg2
from datetime import datetime
import numpy as np
import pandas as pd


def get_db_connection():
    """PostgreSQL 연결"""
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'realestate'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'postgres')
    )


def load_model():
    """모델 로드"""
    # scripts 컨테이너에서는 /data/trust_model/ 경로 사용
    model_path = '/data/trust_model/final_trust_model.pkl'
    if not os.path.exists(model_path):
        model_path = 'apps/reco/trust_model/final_trust_model.pkl'
    
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    
    return model_data['model'], model_data['scaler'], model_data['feature_names']


def create_features(broker_row):
    """
    Feature 생성 (학습 시와 동일한 14개)
    broker_row: dict 형태의 DB row
    """
    # 기본 값 추출
    거래완료 = broker_row.get('completed_deals') or 0
    등록매물 = broker_row.get('registered_properties') or 0
    공인중개사수 = broker_row.get('brokers_count') or 0
    중개보조원수 = broker_row.get('assistants_count') or 0
    일반직원수 = broker_row.get('staff_count') or 0
    
    # 대표자 구분
    대표자구분명 = broker_row.get('representative_type') or "공인중개사"
    
    # 1-3. 거래 지표 (로그 변환)
    등록매물_log = np.log1p(등록매물)
    총거래활동량 = 거래완료 + 등록매물
    총거래활동량_log = np.log1p(총거래활동량)
    
    # 1인당 거래량
    총_직원수 = 공인중개사수 + 중개보조원수 + 일반직원수
    총_직원수_safe = max(총_직원수, 1)
    일인당_거래량 = 총거래활동량 / 총_직원수_safe
    일인당_거래량_log = np.log1p(일인당_거래량)
    
    # 4-6. 인력 지표
    중개보조원_비율 = 중개보조원수 / 총_직원수_safe
    자격증_보유_인원 = 공인중개사수 + 중개보조원수
    자격증_보유비율 = 자격증_보유_인원 / 총_직원수_safe
    
    # 7-9. 운영 경험
    운영기간_년 = 0
    등록일 = broker_row.get('registration_date')
    if 등록일:
        try:
            if isinstance(등록일, str):
                from dateutil import parser
                등록일 = parser.parse(등록일).date()
            today = datetime.now().date()
            영업일수 = (today - 등록일).days
            운영기간_년 = 영업일수 / 365.25
        except:
            pass
    
    공인중개사_비율 = 공인중개사수 / 총_직원수_safe
    숙련도_지수 = 운영기간_년 * 공인중개사_비율
    운영_안정성 = 1 if 운영기간_년 >= 3 else 0
    
    # 10. 조직 구조
    대형사무소 = 1 if 총_직원수 >= 2 else 0
    
    # 11-12. 대표자 자격
    대표_공인중개사 = 1 if 대표자구분명 == "공인중개사" else 0
    대표_법인 = 1 if 대표자구분명 == "법인" else 0
    
    # 13. 지역 경쟁 강도 (평균값)
    지역_경쟁강도 = 50
    
    # 14. 1층 여부
    주소 = broker_row.get('address') or ""
    일층_여부 = 1 if ("1층" in 주소 or "101호" in 주소 or "102호" in 주소) else 0
    
    # 14개 Feature
    features = [
        등록매물_log,
        총거래활동량_log,
        일인당_거래량_log,
        총_직원수,
        중개보조원_비율,
        자격증_보유비율,
        운영기간_년,
        숙련도_지수,
        운영_안정성,
        대형사무소,
        대표_공인중개사,
        대표_법인,
        지역_경쟁강도,
        일층_여부
    ]
    
    return features


def predict():
    """예측 실행"""
    print("\n" + "=" * 70)
    print(" " * 15 + "Trust Score 예측 시작")
    print("=" * 70 + "\n")
    
    # 1. 모델 로드
    print("1. 모델 로드 중...")
    model, scaler, feature_names = load_model()
    print(f"  ✓ Feature: {feature_names}")
    
    # 2. DB 연결 및 Broker 조회
    print("\n2. Broker 데이터 조회 중...")
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT landbroker_id, office_name, completed_deals, registered_properties,
               brokers_count, assistants_count, staff_count, 
               registration_date, address
        FROM landbroker
    """)
    
    columns = [desc[0] for desc in cur.description]
    brokers = [dict(zip(columns, row)) for row in cur.fetchall()]
    total = len(brokers)
    print(f"  ✓ {total}개 broker")
    
    # 3. 예측
    print("\n3. 예측 실행 중...")
    updated = 0
    grade_dist = {'A': 0, 'B': 0, 'C': 0}
    
    for i, broker in enumerate(brokers, 1):
        try:
            # Feature 생성
            features = create_features(broker)
            features_df = pd.DataFrame([features], columns=feature_names)
            
            # 스케일링 및 예측
            features_scaled = scaler.transform(features_df)
            pred = model.predict(features_scaled)[0]
            
            # 등급 매핑
            if isinstance(pred, str):
                trust_score = pred
            else:
                grade_map = {0: 'A', 1: 'B', 2: 'C'}
                trust_score = grade_map.get(pred, 'C')
            
            # DB 업데이트
            cur.execute("""
                UPDATE landbroker 
                SET trust_score = %s, trust_score_updated_at = CURRENT_TIMESTAMP
                WHERE landbroker_id = %s
            """, (trust_score, broker['landbroker_id']))
            
            updated += 1
            grade_dist[trust_score] += 1
            
            if i % max(total // 10, 1) == 0:
                print(f"  진행: {i}/{total} ({i/total*100:.1f}%)")
        
        except Exception as e:
            print(f"  ✗ 예측 실패 ({broker.get('office_name', 'Unknown')}): {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    
    # 4. 결과
    print("\n" + "=" * 70)
    print(" " * 20 + "예측 완료")
    print("=" * 70)
    print(f"\n  성공: {updated}개")
    print(f"\n  등급 분포:")
    print(f"    A등급: {grade_dist['A']}개 ({grade_dist['A']/max(total,1)*100:.1f}%)")
    print(f"    B등급: {grade_dist['B']}개 ({grade_dist['B']/max(total,1)*100:.1f}%)")
    print(f"    C등급: {grade_dist['C']}개 ({grade_dist['C']/max(total,1)*100:.1f}%)")
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    try:
        predict()
    except Exception as e:
        print(f"\n✗ 오류: {e}")
        import traceback
        traceback.print_exc()
