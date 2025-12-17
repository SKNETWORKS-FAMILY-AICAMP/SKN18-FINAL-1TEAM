"""
01_create_target.py
중개사 성사율 기반 Z-score 및 A/B/C 등급 생성
"""

import pandas as pd
import numpy as np
from pathlib import Path


def load_preprocessed_data(filepath: str = "data/ML/preprocessed_office_data.csv") -> pd.DataFrame:
    """
    전처리된 CSV 파일을 로드합니다.

    Args:
        filepath (str): 파일 경로

    Returns:
        pd.DataFrame: 로드된 DataFrame
    """
    file = Path(filepath)

    if not file.exists():
        raise FileNotFoundError(f"[ERROR] 파일이 존재하지 않습니다: {filepath}")

    print(f"📂 [1단계] 전처리된 데이터 로드")
    df = pd.read_csv(file, encoding="utf-8-sig")

    print(f"   - 행 수: {len(df):,}")
    print(f"   - 열 수: {len(df.columns)}")

    return df


def create_target(df: pd.DataFrame) -> pd.DataFrame:
    """
    Z-score 기반 타겟 생성 및 A/B/C 등급 매기기

    Args:
        df (pd.DataFrame): 전처리된 데이터프레임

    Returns:
        pd.DataFrame: 타겟 컬럼이 추가된 데이터프레임
    """

    # print(f"\n🎯 [2단계] 지역평균 / 표준편차 계산 및 Z-score 생성")

    # ---------------------------------------
    # 1) 거래성사율 계산
    # ---------------------------------------
    # _00_load_data.py에서 이미 변환된 거래완료_숫자, 등록매물_숫자 사용
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
        "법인": 2,
        "공인중개사": 0,
        "중개보조원": -1,
        "중개인": -3,
    }

    # 대표자구분명이 없는 경우(NaN) '미등록' 처리
    df["대표자구분명"] = df["대표자구분명"].fillna("미등록")
    df["자격점수"] = df["대표자구분명"].map(qualification_map).fillna(-2)  # 매핑 안되는 값은 최소점수(-2)

    # 자격점수 Z-score화 (정규화) - 전체 데이터 기준
    qual_mean = df["자격점수"].mean()
    qual_std = df["자격점수"].std()
    
    # 표준편차가 0인 경우 (자격이 모두 같은 경우) 처리
    if qual_std == 0:
        qual_std = 1
        
    df["Qual_Zscore"] = (df["자격점수"] - qual_mean) / qual_std

    # ---------------------------------------
    # 5) 최종 복합 Z-score 계산
    # ---------------------------------------
    # 성사율(실적) 80% + 자격(신뢰도) 20%
    weight_perf = 0.8
    weight_qual = 0.2
    
    df["Zscore"] = (df["Performance_Zscore"] * weight_perf) + (df["Qual_Zscore"] * weight_qual)

    print("\n⚖️ [2.5단계] 자격 가중치 적용 완료")
    print(f"   가중치 비율: 실적 {weight_perf*100}% + 자격 {weight_qual*100}%")
    print(f"   자격점수 분포: {df['자격점수'].value_counts().sort_index().to_dict()}")

    # print("   - Z-score 예시:")
    # print(df[["지역명", "거래성사율", "자격구분", "Performance_Zscore", "Qual_Zscore", "Zscore"]].head())

    # ---------------------------------------
    # 3-1) 대표자구분명 기반 가중치 적용
    # ---------------------------------------
    print("\n⚖️ [2-1단계] 대표자구분명 기반 가중치 적용")
    
    # 대표자 자격에 따른 신뢰도 조정값
    대표자구분_가중치 = {
        '공인중개사': 0.0,       # 기본 (가장 일반적, 조정 없음)
        '법인': 0.2,            # +0.2 가점 (조직 안정성)
        '중개보조원': -0.1,      # -0.1 감점 (자격 수준 낮음)
        '중개인': -0.3,          # -0.3 감점 (대표가 보조원은 이례적)
    }
    
    # 대표자구분명이 있으면 가중치 적용 (모든 데이터에 대표자구분명이 있다고 가정)
    df["대표자구분_조정값"] = df["대표자구분명"].map(대표자구분_가중치).fillna(0.0)
    df["Zscore_조정"] = df["Zscore"] + df["대표자구분_조정값"]
    
    # 대표자구분명 분포 출력
    if "대표자구분명" in df.columns:
        print("   - 대표자구분명 분포:")
        print(df["대표자구분명"].value_counts(dropna=False))
    
    print(f"   - 조정 전 Z-score 평균: {df['Zscore'].mean():.4f}")
    print(f"   - 조정 후 Z-score 평균: {df['Zscore_조정'].mean():.4f}")

    # ---------------------------------------
    # 4) 분위수 기반 A/B/C 등급 생성 (조정된 Z-score 사용)
    # ---------------------------------------
    print("\n🏷 [3단계] A/B/C 등급 생성 (분위수 기반 30/40/30)")

    # 조정된 Z-score를 기준으로 분위수 계산
    q30 = df["Zscore_조정"].quantile(0.30)
    q70 = df["Zscore_조정"].quantile(0.70)

    print(f"   - C 등급 상한(Z ≤): {q30:.4f}")
    print(f"   - B 등급 상한(Z ≤): {q70:.4f}")

    def classify(z):
        if z <= q30:
            return "C"
        elif z <= q70:
            return "B"
        else:
            return "A"

    # 조정된 Z-score를 기준으로 등급 분류
    df["신뢰도등급"] = df["Zscore_조정"].apply(classify)

    print("\n📌 등급 분포:")
    print(df["신뢰도등급"].value_counts(normalize=True).map(lambda x: round(x*100, 1)))

    df["신뢰도등급_숫자"] = df["신뢰도등급"].map({"A": 2, "B": 1, "C": 0})
    df["target"] = df["신뢰도등급_숫자"]

    return df


def save_target(df: pd.DataFrame, filepath: str = "data/ML/office_target.csv"):
    """
    타겟 생성 후 CSV 저장

    Args:
        df (pd.DataFrame): 타겟 포함 데이터프레임
        filepath (str): 저장 경로
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"\n💾 [4단계] 타겟 생성 파일 저장 완료: {filepath}")


def main():
    print("🎯 타겟 생성 중...")

    # 1) 전처리된 데이터 로드
    df = load_preprocessed_data("data/ML/preprocessed_office_data.csv")

    # 2) 타겟 생성
    df = create_target(df)

    # 3) 저장
    save_target(df)

    print("✅ 타겟 생성 완료\n")

    return df


if __name__ == "__main__":
    df = main()
