"""
월세 매물 가격 분류 적용 스크립트 (Docker 환경용)
저장된 모델을 사용하여 매물 데이터에 가격 분류를 적용하고 DB에 저장

Usage:
    docker compose --profile scripts run --rm scripts
"""
import argparse
import pickle
import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ========================================
# 환경별 경로 설정
# ========================================

# Docker 환경 감지
IS_DOCKER = os.path.exists("/app") or os.path.exists("/data")

if IS_DOCKER:
    # Docker 환경 (scripts 컨테이너)
    # apps/reco가 /app/apps/reco에 마운트됨
    SCRIPT_DIR = Path("/app/03_import/price_model")
    MODEL_DIR = Path("/app/03_import/price_model")
    DATA_DIR = Path("/data")
    JSON_DATA_DIR = DATA_DIR / "RDB" / "land"
    INTEREST_RATE_PATH = DATA_DIR / "actual_transaction_price" / "(총합)시장금리_및_대출금리(24.8~25.10).csv"
else:
    # 로컬 환경
    SCRIPT_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = SCRIPT_DIR.parents[2]  # SKN18-FINAL-1TEAM
    MODEL_DIR = PROJECT_ROOT / "apps" / "reco" / "price_model" / "model"
    DATA_DIR = PROJECT_ROOT / "data"
    JSON_DATA_DIR = DATA_DIR / "RDB" / "land"
    INTEREST_RATE_PATH = DATA_DIR / "actual_transaction_price" / "(총합)시장금리_및_대출금리(24.8~25.10).csv"

    # ML 소스 경로 추가
    ML_SRC_PATH = PROJECT_ROOT / "apps" / "reco" / "price_model" / "src"
    if str(ML_SRC_PATH) not in sys.path:
        sys.path.insert(0, str(ML_SRC_PATH))

# ML 모듈 경로 추가
SCRIPT_DIR = Path(__file__).resolve().parent

if IS_DOCKER:
    # Docker 환경 - 여러 경로 시도
    possible_paths = [
        Path("/app/apps/reco/price_model/src"),
        Path("/app/apps/backend/apps/reco/price_model/src"),
        SCRIPT_DIR.parents[2] / "apps" / "reco" / "price_model" / "src"
    ]
    ML_SRC = None
    for path in possible_paths:
        if path.exists():
            ML_SRC = path
            break
    
    if ML_SRC is None:
        ML_SRC = possible_paths[0]  # fallback
else:
    # 로컬 환경
    PROJECT_ROOT = SCRIPT_DIR.parents[2]
    ML_SRC = PROJECT_ROOT / "apps" / "reco" / "price_model" / "src"

if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

# ML 모듈 import
PriceDataPreprocessor = None
DataLoader = None
ML_INTEREST_RATE_PATH = None

try:
    from preprocessing.preprocessor import PriceDataPreprocessor
    from loaders.data_loader import DataLoader
    try:
        from core.config import INTEREST_RATE_PATH as ML_INTEREST_RATE_PATH
    except:
        pass
    
    # INTEREST_RATE_PATH 우선순위: ML config > 로컬 설정
    if ML_INTEREST_RATE_PATH and Path(ML_INTEREST_RATE_PATH).exists():
        INTEREST_RATE_PATH = Path(ML_INTEREST_RATE_PATH)
    
    print(f"✅ ML 모듈 로드 성공: {ML_SRC}")
except ImportError as e:
    print(f"⚠ ML 모듈 임포트 실패: {e}")
    print(f"   시도한 경로: {ML_SRC}")
    print("   기본 전처리 로직을 사용합니다.")

DEFAULT_MODEL_PATH = MODEL_DIR / "price_model_lightgbm.pkl"

# 클래스 레이블
CLASS_LABELS = {
    0: {"label": "UNDERPRICED", "label_kr": "저렴"},
    1: {"label": "FAIR", "label_kr": "적정"},
    2: {"label": "OVERPRICED", "label_kr": "비쌈"}
}

# 데이터베이스 설정
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "database": os.getenv("POSTGRES_DB", "realestate"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
}

RESULTS_TABLE = "price_classification_results"


# ========================================
# 데이터 전처리 유틸리티
# ========================================
import re
import json

class DataPreprocessor:
    """데이터 전처리 유틸리티"""
    
    GU_LIST = [
        "강남구", "강동구", "강북구", "강서구", "관악구",
        "광진구", "구로구", "금천구", "노원구", "도봉구",
        "동대문구", "동작구", "마포구", "서대문구", "서초구",
        "성동구", "성북구", "송파구", "양천구", "영등포구",
        "용산구", "은평구", "종로구", "중구", "중랑구"
    ]
    
    @staticmethod
    def parse_address(address: str) -> dict:
        """주소에서 자치구명과 법정동명 추출"""
        if not address:
            return {"자치구명": "알수없음", "법정동명": "알수없음"}
        
        자치구명 = None
        법정동명 = None
        
        # 자치구 찾기
        for gu in DataPreprocessor.GU_LIST:
            if gu in address:
                자치구명 = gu
                break
        
        # 법정동 찾기
        if 자치구명:
            parts = address.split(자치구명)
            if len(parts) > 1:
                after_gu = parts[1].strip()
                match = re.search(r'([^\s]+(?:동|로|가))', after_gu)
                if match:
                    법정동명 = match.group(1)
        
        return {
            "자치구명": 자치구명 or "알수없음",
            "법정동명": 법정동명 or "알수없음"
        }
    
    @staticmethod
    def parse_floor(floor_str) -> int:
        """층수 파싱"""
        if floor_str is None or floor_str == "":
            return 5
        
        floor_str = str(floor_str)
        
        # 지하/반지하
        if "지하" in floor_str or "반지하" in floor_str or "B" in floor_str.upper():
            return -1
        
        # 문자형 층수
        floor_mapping = {"저층": 2, "중층": 5, "중고층": 8, "고층": 12}
        for key, value in floor_mapping.items():
            if key in floor_str:
                return value
        
        # 숫자 추출 (예: "5층/10층" -> 5)
        match = re.search(r'(\d+)', floor_str)
        if match:
            return int(match.group(1))
        
        return 5
    
    @staticmethod
    def parse_area(area_str) -> float:
        """면적 파싱 (m2 단위)"""
        if not area_str:
            return 0.0
        
        area_str = str(area_str)
        
        # 숫자 추출 (예: "59.4m2/84.9m2" -> 59.4)
        match = re.search(r'([\d.]+)', area_str)
        if match:
            return float(match.group(1))
        
        return 0.0
    
    @staticmethod
    def parse_year(year_str) -> int:
        """건축년도 파싱"""
        if not year_str:
            return 2010
        
        year_str = str(year_str)
        
        # 4자리 년도 추출
        match = re.search(r'(\d{4})', year_str)
        if match:
            year = int(match.group(1))
            if 1950 <= year <= 2030:
                return year
        
        return 2010
    
    @staticmethod
    def parse_building_type(building_type: str) -> str:
        """건물용도 정규화"""
        if not building_type:
            return "연립다세대"
        
        building_type_lower = building_type.lower()
        
        if "아파트" in building_type_lower:
            return "아파트"
        if "오피스텔" in building_type_lower:
            return "오피스텔"
        
        return "연립다세대"


# ========================================
# 데이터베이스 관리자
# ========================================
class DatabaseManager:
    """PostgreSQL 데이터베이스 관리"""
    
    def __init__(self, db_config: dict = None):
        self.db_config = db_config or DB_CONFIG
        self.conn = None
        self.cursor = None
    
    def connect(self):
        import psycopg2
        self.conn = psycopg2.connect(**self.db_config)
        self.cursor = self.conn.cursor()
        print(f"✅ DB 연결 성공: {self.db_config['database']}")
    
    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print(f"✅ DB 연결 종료: {self.db_config['database']}")
    
    def load_monthly_rent_from_land(self) -> pd.DataFrame:
        """land 테이블에서 월세 매물 로드 및 파싱"""
        print(f"\n📊 land 테이블에서 월세 매물 로드 중...")
        
        # 월세 매물만 조회
        query = """
        SELECT 
            land_id,
            land_num,
            url,
            address,
            building_type,
            deal_type,
            deposit,
            monthly_rent,
            listing_info,
            created_at
        FROM land
        WHERE deal_type LIKE '%월세%'
           OR (monthly_rent IS NOT NULL AND monthly_rent > 0)
        """
        
        try:
            df = pd.read_sql(query, self.conn)
            print(f"✅ {len(df)}개 월세 매물 로드 완료")
            
            if df.empty:
                return df
            
            # listing_info JSONB 파싱
            def parse_listing_info(row):
                info = row.get('listing_info')
                
                # JSONB를 dict로 변환
                if isinstance(info, str):
                    try:
                        info = json.loads(info)
                    except:
                        info = {}
                elif not isinstance(info, dict):
                    info = {}
                
                # 필요한 정보 추출
                result = {
                    '전용/공급면적': info.get('전용/공급면적', ''),
                    '해당층/전체층': info.get('해당층/전체층', ''),
                    '사용승인일': info.get('사용승인일', ''),
                }
                
                return pd.Series(result)
            
            # listing_info 파싱
            parsed_info = df.apply(parse_listing_info, axis=1)
            df = pd.concat([df, parsed_info], axis=1)
            
            # 주소 파싱
            address_info = df['address'].apply(DataPreprocessor.parse_address)
            df['자치구명'] = address_info.apply(lambda x: x['자치구명'])
            df['법정동명'] = address_info.apply(lambda x: x['법정동명'])
            
            # 면적 파싱
            df['임대면적'] = df['전용/공급면적'].apply(DataPreprocessor.parse_area)
            
            # 층수 파싱
            df['층'] = df['해당층/전체층'].apply(DataPreprocessor.parse_floor)
            
            # 건축년도 파싱
            df['건축년도'] = df['사용승인일'].apply(DataPreprocessor.parse_year)
            
            # 건물용도 정규화
            df['건물용도'] = df['building_type'].apply(DataPreprocessor.parse_building_type)
            
            # 가격 변환 (DB 값 확인)
            avg_deposit = df['deposit'].mean()
            if avg_deposit > 100000:  # 원 단위
                print("→ DB 값이 원 단위로 저장되어 있음, 만원으로 변환")
                df['보증금(만원)'] = pd.to_numeric(df['deposit'], errors='coerce').fillna(0) / 10000
                df['임대료(만원)'] = pd.to_numeric(df['monthly_rent'], errors='coerce').fillna(0) / 10000
            else:  # 만원 단위
                print("→ DB 값이 만원 단위로 저장되어 있음")
                df['보증금(만원)'] = pd.to_numeric(df['deposit'], errors='coerce').fillna(0)
                df['임대료(만원)'] = pd.to_numeric(df['monthly_rent'], errors='coerce').fillna(0)
            
            # 매물번호와 URL 매핑
            df['매물번호'] = df['land_num']
            df['매물_URL'] = df['url']
            df['전체주소'] = df['address']
            
            # 유효한 데이터만 필터링
            valid_mask = (
                (df['임대면적'] > 0) &
                (df['임대료(만원)'] > 0) &
                (df['자치구명'] != '알수없음')
            )
            df = df[valid_mask].copy()
            
            print(f"✅ 유효한 데이터: {len(df)}건")
            
            return df
            
        except Exception as e:
            print(f"❌ 데이터 로드 실패: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def create_table(self):
        """결과 저장 테이블 생성 (간소화 + 영어 컬럼명 + 외래키)"""
        # 기존 테이블 삭제
        drop_sql = f"DROP TABLE IF EXISTS {RESULTS_TABLE} CASCADE;"
        self.cursor.execute(drop_sql)
        
        create_sql = f"""
        CREATE TABLE {RESULTS_TABLE} (
            id SERIAL PRIMARY KEY,
            land_num VARCHAR(50) NOT NULL,
            predicted_class INTEGER NOT NULL,
            predicted_label VARCHAR(20) NOT NULL,
            predicted_label_kr VARCHAR(20) NOT NULL,
            underpriced_prob DECIMAL(5, 4) NOT NULL,
            fair_prob DECIMAL(5, 4) NOT NULL,
            overpriced_prob DECIMAL(5, 4) NOT NULL,
            predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- 외래키 제약조건: land 테이블과 연결
            CONSTRAINT fk_price_class_land 
                FOREIGN KEY (land_num) 
                REFERENCES land(land_num) 
                ON DELETE CASCADE,
            
            -- 유니크 제약조건
            UNIQUE(land_num)
        );
        
        -- 인덱스 생성
        CREATE INDEX idx_price_class_land_num ON {RESULTS_TABLE}(land_num);
        CREATE INDEX idx_price_class_label_kr ON {RESULTS_TABLE}(predicted_label_kr);
        CREATE INDEX idx_price_class_predicted_at ON {RESULTS_TABLE}(predicted_at);
        
        -- 코멘트 추가
        COMMENT ON TABLE {RESULTS_TABLE} IS '월세 매물 가격 분류 결과 (AI 모델 예측)';
        COMMENT ON COLUMN {RESULTS_TABLE}.land_num IS 'land 테이블의 land_num (외래키)';
        COMMENT ON COLUMN {RESULTS_TABLE}.predicted_class IS '0: 저렴, 1: 적정, 2: 비쌈';
        """
        self.cursor.execute(create_sql)
        self.conn.commit()
        print(f"✅ 테이블 생성 완료 (외래키 연결): {RESULTS_TABLE}")
    
    def save_results(self, df: pd.DataFrame):
        """분류 결과 저장 (UPSERT) - 간소화된 구조"""
        from psycopg2.extras import execute_batch
        
        if df.empty:
            print("⚠ 저장할 데이터가 없습니다.")
            return
        
        insert_sql = f"""
        INSERT INTO {RESULTS_TABLE} (
            land_num,
            predicted_class,
            predicted_label,
            predicted_label_kr,
            underpriced_prob,
            fair_prob,
            overpriced_prob
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (land_num) DO UPDATE SET
            predicted_class = EXCLUDED.predicted_class,
            predicted_label = EXCLUDED.predicted_label,
            predicted_label_kr = EXCLUDED.predicted_label_kr,
            underpriced_prob = EXCLUDED.underpriced_prob,
            fair_prob = EXCLUDED.fair_prob,
            overpriced_prob = EXCLUDED.overpriced_prob,
            predicted_at = CURRENT_TIMESTAMP;
        """
        
        records = []
        for _, row in df.iterrows():
            try:
                record = (
                    str(row.get("land_num", "")),
                    int(row["예측_클래스"]),
                    row["예측_레이블"],
                    row["예측_레이블_한글"],
                    float(row["저렴_확률"]),
                    float(row["적정_확률"]),
                    float(row["비쌈_확률"]),
                )
                records.append(record)
            except Exception as e:
                print(f"⚠ 레코드 변환 실패 (land_num={row.get('land_num')}): {e}")
                continue
        
        if records:
            execute_batch(self.cursor, insert_sql, records, page_size=100)
            self.conn.commit()
            print(f"✅ {len(records)}개 레코드 저장 완료")


# ========================================
# 가격 분류 파이프라인
# ========================================
class PriceClassifier:
    """가격 분류 파이프라인"""
    
    def __init__(self, model_path: str):
        self.model_path = Path(model_path)
        self.model = None
        self.preprocessor = None
    
    def load_model(self):
        """저장된 모델 로드 (원본 로직 그대로 유지)"""
        print(f"\n🚚 모델 로딩: {self.model_path}")
        
        with open(self.model_path, 'rb') as f:
            saved_data = pickle.load(f)
        
        if 'model' in saved_data:
            self.model = saved_data['model']
        elif 'best_model' in saved_data:
            self.model = saved_data['best_model']
        else:
            raise KeyError("저장된 파일에 'model' 키가 없습니다.")
            
        # 전처리기 생성
        if PriceDataPreprocessor is None:
            raise ImportError(
                "PriceDataPreprocessor를 import할 수 없습니다. "
                "apps/reco/price_model/src 경로를 확인하세요."
            )
        
        self.preprocessor = PriceDataPreprocessor()
        
        # LabelEncoder 및 통계 복원
        if 'label_encoders' in saved_data:
            self.preprocessor.label_encoders = saved_data['label_encoders']
        if 'train_gu_quantiles' in saved_data:
            self.preprocessor.train_gu_quantiles = saved_data['train_gu_quantiles']
        
        print(f"✅ 모델 로드 완료: {saved_data.get('model_name', 'Unknown')}")
    
    def load_interest_rate(self):
        """금리 데이터 로드"""
        if not INTEREST_RATE_PATH or not INTEREST_RATE_PATH.exists():
            print(f"⚠ 금리 데이터 파일을 찾을 수 없습니다: {INTEREST_RATE_PATH}")
            return {"기준금리": 2.5}, "2025-10"
            
        print(f"\n📊 금리 데이터 로딩: {INTEREST_RATE_PATH}")
        self.interest_rate_df = pd.read_csv(INTEREST_RATE_PATH, encoding='utf-8-sig')
        
        columns = [col for col in self.interest_rate_df.columns if col != '구분']
        latest_month = columns[-1]
        print(f"✅ 최신 금리 데이터: {latest_month}")
        
        rate_dict = {}
        for _, row in self.interest_rate_df.iterrows():
            rate_name = row['구분']
            rate_value = row[latest_month]
            if pd.notna(rate_value):
                rate_dict[rate_name] = float(rate_value)
        
        return rate_dict, latest_month
    
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """데이터 전처리 (원본 로직 그대로 유지)"""
        print("\n[Step] 데이터 전처리 시작")
        
        # 0. 학습 데이터 로드 (분위수 재설정용)
        if DataLoader and INTEREST_RATE_PATH:
            try:
                loader = DataLoader(base_dir=str(INTEREST_RATE_PATH.parent))
                train_df_raw, _ = loader.load_train_test()
                train_df_raw = self.preprocessor.create_target(train_df_raw)
            except Exception as e:
                print(f"⚠ 학습 데이터 로드 실패: {e}")
                train_df_raw = pd.DataFrame()
        else:
            train_df_raw = pd.DataFrame()
        
        # 1. 금리 데이터 로드 및 적용
        if INTEREST_RATE_PATH and INTEREST_RATE_PATH.exists():
            macro = pd.read_csv(INTEREST_RATE_PATH, encoding="utf-8-sig")
            
            # wide -> long -> pivot
            macro_long = macro.melt(id_vars="구분", var_name="연월", value_name="값")
            macro_pivot = macro_long.pivot(index="연월", columns="구분", values="값").reset_index()
            
            # 최신 월 가져오기
            latest_month = macro_pivot["연월"].max()
            df["연월"] = latest_month
            
            # 조인
            df = df.merge(macro_pivot, on="연월", how="left")
            
            # 기준금리 및 적용이자율 설정
            rate_dict, _ = self.load_interest_rate()
            base_rate = rate_dict.get("기준금리", 2.5)
            df["기준금리"] = base_rate
            df["적용이자율"] = (df["기준금리"] + 2.0) / 100.0
        else:
            print("⚠ 금리 데이터가 없어 기본값을 사용합니다.")
            df["기준금리"] = 2.5
            df["적용이자율"] = (df["기준금리"] + 2.0) / 100.0
        
        # 2. 타깃 및 가격 컬럼 생성
        df = self.preprocessor.create_target(
            df,
            train_stats={"gu_quantiles": self.preprocessor.train_gu_quantiles}
        )
        
        # 3. 고급 피처 엔지니어링
        if not train_df_raw.empty:
            _, df_fe = self.preprocessor.advanced_feature_engineering(train_df_raw, df)
        else:
            _, df_fe = self.preprocessor.advanced_feature_engineering(df.iloc[:0], df)
            
        print(f"✅ 전처리 완료: {len(df_fe)}건")
        
        return df_fe
    
    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """모델 예측 수행 (원본 로직 그대로 유지)"""
        print("\n🔮 예측 수행 중...")
        
        if df.empty:
            return df
        
        # 1) 피처 선택
        X = df[self.preprocessor.candidate_features].copy()
        
        # 2) Tree용 전처리 (Label Encoding)
        empty_df = pd.DataFrame(columns=X.columns)
        _, _, X_transformed = self.preprocessor.prepare_tree_features(
            empty_df, empty_df, X
        )
        
        # 3) 모델이 기대하는 피처 수에 맞춰 정렬
        X_arr = X_transformed.values
        n_model_features = getattr(self.model, "n_features_in_", X_arr.shape[1])
        
        if X_arr.shape[1] != n_model_features:
            diff = n_model_features - X_arr.shape[1]
            if diff > 0:
                pad = np.zeros((X_arr.shape[0], diff))
                X_arr = np.hstack([X_arr, pad])
            else:
                X_arr = X_arr[:, :n_model_features]
        
        # 4) 예측
        y_pred_proba = self.model.predict_proba(X_arr)
        y_pred = np.argmax(y_pred_proba, axis=1)
        
        # 애매한 확률은 적정(1)으로
        max_proba = np.max(y_pred_proba, axis=1)
        uncertain = max_proba < 0.6
        y_pred[uncertain] = 1
        
        # 5) 결과 컬럼 추가
        df['예측_클래스'] = y_pred
        df['예측_레이블'] = [CLASS_LABELS[c]['label'] for c in y_pred]
        df['예측_레이블_한글'] = [CLASS_LABELS[c]['label_kr'] for c in y_pred]
        df['저렴_확률'] = y_pred_proba[:, 0]
        df['적정_확률'] = y_pred_proba[:, 1]
        df['비쌈_확률'] = y_pred_proba[:, 2]
        
        print(f"✅ 예측 완료: {len(df)}개 매물")
        
        # 예측 결과 요약
        class_counts = df['예측_레이블_한글'].value_counts()
        print("\n📊 예측 결과 요약:")
        for label, count in class_counts.items():
            print(f"   - {label}: {count}개 ({count/len(df)*100:.1f}%)")
            
        return df
    
    def run(self, save_to_db: bool = True) -> pd.DataFrame:
        """전체 파이프라인 실행"""
        print("\n" + "=" * 60)
        print("🚀 월세 매물 가격 분류 시작")
        print("=" * 60)
        print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. 모델 로드
        self.load_model()
        
        # 2. DB에서 데이터 로드
        db = DatabaseManager()
        try:
            db.connect()
            df = db.load_monthly_rent_from_land()
            
            if df.empty:
                print("⚠ 처리할 월세 매물이 없습니다.")
                return df
            
            # 3. 데이터 전처리
            df_processed = self.prepare_data(df)
            
            # 4. 예측
            df_result = self.predict(df_processed)
            
            # 5. DB 저장
            if save_to_db and not df_result.empty:
                print("\n💾 데이터베이스 저장 중...")
                db.create_table()
                db.save_results(df_result)
                
        except Exception as e:
            print(f"❌ 파이프라인 실행 중 오류: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            db.close()
        
        print("\n" + "=" * 60)
        print("✅ 모든 작업 완료!")
        print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60 + "\n")
        
        return df_result


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="월세 매물 가격 분류 (PostgreSQL land 테이블 → 결과 테이블)"
    )
    parser.add_argument(
        "--model_path",
        type=str,
        default=str(DEFAULT_MODEL_PATH),
        help="저장된 모델 경로"
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="DB 저장 없이 예측만 수행"
    )
    
    args = parser.parse_args()
    
    # 경로 확인 및 출력
    print("\n" + "=" * 60)
    print("📁 설정")
    print("=" * 60)
    print(f"   - 환경: {'Docker' if IS_DOCKER else '로컬'}")
    print(f"   - 모델 경로: {args.model_path}")
    print(f"   - 소스: PostgreSQL land 테이블")
    print(f"   - 결과 테이블: {RESULTS_TABLE}")
    print(f"   - DB 저장: {'No (dry-run)' if args.dry_run else 'Yes'}")
    
    # 분류기 실행
    classifier = PriceClassifier(args.model_path)
    results_df = classifier.run(save_to_db=not args.dry_run)


if __name__ == "__main__":
    main()
