"""
01_create_target.py
중개사무소 신뢰도 등급(Target) 생성
- Train/Test Split 먼저 수행 (Data Leakage 방지)
- Train 데이터 기준으로 지역별 통계(평균, 표준편차) 산출
- Train 통계를 Test에도 적용하여 Z-Score 계산
- 자격점수 가중치 적용하여 최종 점수 산출
- 점수 분포 기반 3등급(A/B/C) 분류
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split

def load_data(filepath: str = "data/ML/preprocessed_office_data.csv") -> pd.DataFrame:
    """데이터 로드"""
    print(f"📂 [1단계] 데이터 로드: {filepath}")
    return pd.read_csv(filepath, encoding="utf-8-sig")

def split_data(df: pd.DataFrame, test_size=0.2, random_state=42):
    """Train/Test 분할"""
    print(f"\n✂️ [2단계] Train/Test 분할 (test_size={test_size})")
    train, test = train_test_split(df, test_size=test_size, random_state=random_state, shuffle=True)
    print(f"   - Train: {len(train):,}개")
    print(f"   - Test:  {len(test):,}개")
    return train.copy(), test.copy()

def preprocess_basic(df: pd.DataFrame) -> pd.DataFrame:
    """기본 전처리: 거래성사율 및 자격점수 계산"""
    
    # 1. 거래성사율
    # 안전한 숫자 변환 (원본 컬럼 '거래완료', '등록매물' 사용)
    df["거래완료_숫자"] = pd.to_numeric(df["거래완료"], errors='coerce').fillna(0)
    df["등록매물_숫자"] = pd.to_numeric(df["등록매물"], errors='coerce').fillna(0)
    
    df["거래성사율"] = np.where(
        (df["거래완료_숫자"] + df["등록매물_숫자"]) > 0,
        df["거래완료_숫자"] / (df["거래완료_숫자"] + df["등록매물_숫자"]),
        0
    )

    # ---------------------------------------
    # 2) 지역별 평균 & 표준편차 계산
    # ---------------------------------------
    df["지역평균"] = df.groupby("지역명")["거래성사율"].transform("mean")
    df["지역표준편차"] = df.groupby("지역명")["거래성사율"].transform("std")

    # # 표준편차가 0일 수 있으므로 안정적 계산
    # df["지역표준편차"] = df["지역표준편차"].replace(0, 1e-6)

    # ---------------------------------------
    # 3) 개인별 Z-score 계산 (거래성사율)
    # ---------------------------------------
    df["Performance_Zscore"] = (df["거래성사율"] - df["지역평균"]) / df["지역표준편차"]

    # ---------------------------------------
    # 4) 자격 가중치 적용 (법인 > 공인중개사 > 중개보조원 > 중개인)
    # ---------------------------------------
    # 데이터 서열 점수 매핑 (2점 만점)
    # 법인: 2, 공인중개사: 0, 중개보조원: -1, 중개인: -3
    qualification_map = {
        "법인": 2,          # 
        "공인중개사": 0,
        "중개보조원": -1,
        "중개인": -3,
    }

    # 대표자구분명이 없는 경우(NaN) '미등록' 처리
    df["대표자구분명"] = df["대표자구분명"].fillna("미등록")
    df["자격점수"] = df["대표자구분명"].map(qualification_map).fillna(-2)  # 매핑 안되는 값은 최소점수(-2)
    
    return df

def calculate_regional_stats(train_df: pd.DataFrame) -> pd.DataFrame:
    """
    Train 데이터로부터 지역별(시군구) 평균 및 표준편차 계산
    """
    print(f"\n📊 [3단계] 지역별 통계 추출 (Train 기준)")
    
    # 지역별 그룹화하여 평균과 표준편차 계산
    stats = train_df.groupby("지역명")["거래성사율"].agg(["mean", "std"]).reset_index()
    
    # 표준편차가 0이거나 NaN인 경우 1로 대체 (나눗셈 오류 방지)
    stats["std"] = stats["std"].fillna(1.0)
    stats.loc[stats["std"] == 0, "std"] = 1.0
    
    print(f"   - {len(stats)}개 지역 통계 산출 완료")
    
    return stats

def apply_z_score(df: pd.DataFrame, regional_stats: pd.DataFrame) -> pd.DataFrame:
    """
    지역별 통계를 이용하여 Z-Score 계산
    Z = (x - mean) / std
    """
    # 지역별 통계 병합
    df = df.merge(regional_stats, on="지역명", how="left")
    
    # 병합되지 않은 지역(Train에 없던 새로운 지역)은 평균 수준(0)으로 처리
    df["mean"] = df["mean"].fillna(df["거래성사율"])
    df["std"] = df["std"].fillna(1.0)
    
    # Z-Score 계산
    df["지역별_성사율_Z"] = (df["거래성사율"] - df["mean"]) / df["std"]
    
    # 임시 컬럼 제거
    df = df.drop(columns=["mean", "std"])
    
    return df

def calculate_final_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    최종 점수 계산
    - Z-Score와 자격점수를 모두 정규화하여 동일한 스케일에서 결합
    - Score = (성사율_Z * 0.7) + (자격점수_Z * 0.3)
    """
    # 1. 성사율 Z-Score 클리핑 (-3 ~ 3)
    df["지역별_성사율_Z"] = df["지역별_성사율_Z"].clip(-3, 3)
    
    # 2. 자격점수 정규화 (Z-Score 변환)
    qual_mean = df["자격점수"].mean()
    qual_std = df["자격점수"].std()
    
    # 표준편차가 0인 경우 방지 (모든 값이 같은 경우)
    if qual_std == 0:
        df["자격점수_Z"] = 0
    else:
        df["자격점수_Z"] = (df["자격점수"] - qual_mean) / qual_std
        df["자격점수_Z"] = df["자격점수_Z"].clip(-3, 3)
    
    # 3. 가중치 적용
    w_z = 0.7  # 성과(실력) 가중치
    w_q = 0.3  # 자격(신뢰) 가중치
    
    df["신뢰도점수"] = (df["지역별_성사율_Z"] * w_z) + (df["자격점수_Z"] * w_q)
    
    # 4. 임시 컬럼 제거
    df = df.drop(columns=["자격점수_Z"])
    
    return df

def assign_grade(train_df: pd.DataFrame, test_df: pd.DataFrame):
    """
    Train 데이터의 분포를 기준으로 등급(Target) 부여
    비율: A(30%), B(40%), C(30%)
    """
    print(f"\n🏆 [4단계] 등급 산정 (A:30%, B:40%, C:30%)")
    
    # Train 데이터 기준으로 분위수(Quantile) 계산
    # 상위 30% 지점 (70% 분위수)
    # 하위 30% 지점 (30% 분위수)
    threshold_high = train_df["신뢰도점수"].quantile(0.70)
    threshold_low = train_df["신뢰도점수"].quantile(0.30)
    
    print(f"   - A등급 기준: {threshold_high:.4f} 이상")
    print(f"   - C등급 기준: {threshold_low:.4f} 미만")
    
    def get_grade(score):
        if score >= threshold_high:
            return 2 # A
        elif score >= threshold_low:
            return 1 # B
        else:
            return 0 # C
            
    train_df["Target"] = train_df["신뢰도점수"].apply(get_grade)
    test_df["Target"] = test_df["신뢰도점수"].apply(get_grade)
    
    # 결과 확인
    grade_map = {2: "A", 1: "B", 0: "C"}
    
    print("\n   [Train 등급 분포]")
    dist = train_df["Target"].value_counts(normalize=True).sort_index()
    for g, p in dist.items():
        print(f"   - {grade_map[g]}: {p*100:.1f}%")
        
    print("\n   [Test 등급 분포]")
    dist_test = test_df["Target"].value_counts(normalize=True).sort_index()
    for g, p in dist_test.items():
        print(f"   - {grade_map[g]}: {p*100:.1f}%")
        
    return train_df, test_df

def save_data(train_df, test_df):
    """결과 저장"""
    Path("data/ML/trust").mkdir(parents=True, exist_ok=True)
    
    train_path = "data/ML/trust/train_target.csv"
    test_path = "data/ML/trust/test_target.csv"
    
    # 필요한 컬럼만 저장하거나 전체 저장
    # 여기서는 전체 저장
    train_df.to_csv(train_path, index=False, encoding="utf-8-sig")
    test_df.to_csv(test_path, index=False, encoding="utf-8-sig")
    
    print(f"\n💾 [5단계] 저장 완료")
    print(f"   - Train: {train_path}")
    print(f"   - Test:  {test_path}")

def main():
    # 1. 로드
    df = load_data()
    
    # 2. 전처리 (기본)
    df = preprocess_basic(df)
    
    # 3. Split
    train, test = split_data(df)
    
    # 4. 지역별 통계 계산 (Train 기준)
    regional_stats = calculate_regional_stats(train)
    
    # 5. Z-Score 적용 (Train 통계 사용)
    train = apply_z_score(train, regional_stats)
    test = apply_z_score(test, regional_stats)
    
    # 6. 최종 점수 계산
    train = calculate_final_score(train)
    test = calculate_final_score(test)
    
    # 7. 등급 부여
    train, test = assign_grade(train, test)
    
    # 8. 저장
    save_data(train, test)

if __name__ == "__main__":
    main()
