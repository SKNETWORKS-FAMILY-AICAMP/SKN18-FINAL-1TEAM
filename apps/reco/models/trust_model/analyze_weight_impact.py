"""
analyze_weight_impact.py
자격 점수 가중치 적용 전후 등급 변화 분석
(현재 _01_create_target.py의 0.7/0.3 가중치 로직 반영)
"""

import pandas as pd
import numpy as np
from pathlib import Path

def analyze_impact():
    print("⚖️ 자격 점수 가중치 적용 전후 등급 변화 분석 (Original Code Logic)\n")
    
    # 데이터 로드
    df = pd.read_csv("data/ML/preprocessed_office_data.csv", encoding="utf-8-sig")
    
    # 숫자형 변환 (안전장치)
    df["거래완료_숫자"] = pd.to_numeric(df["거래완료"], errors='coerce').fillna(0)
    df["등록매물_숫자"] = pd.to_numeric(df["등록매물"], errors='coerce').fillna(0)
    
    # ---------------------------------------
    # 1. 공통: 거래성사율 및 지역별 Z-score 계산
    # ---------------------------------------
    # 거래성사율 = 거래완료 / (거래완료 + 등록매물)
    df["거래성사율"] = np.where(
        (df["거래완료_숫자"] + df["등록매물_숫자"]) > 0,
        df["거래완료_숫자"] / (df["거래완료_숫자"] + df["등록매물_숫자"]),
        0
    )
    
    # 지역별 통계 (Train 기준을 흉내내기 위해 전체 통계 사용)
    # 실제 파이프라인은 Train 통계를 사용하지만, 영향도 분석은 전체 데이터로 경향성만 확인
    df["지역평균"] = df.groupby("지역명")["거래성사율"].transform("mean")
    df["지역표준편차"] = df.groupby("지역명")["거래성사율"].transform("std").fillna(1.0)
    df.loc[df["지역표준편차"] == 0, "지역표준편차"] = 1.0
    
    df["Performance_Zscore"] = (df["거래성사율"] - df["지역평균"]) / df["지역표준편차"]
    df["Performance_Zscore"] = df["Performance_Zscore"].clip(-3, 3) # Clipping

    # ---------------------------------------
    # 2. Case 1: 적용 전 (순수 실적 100%)
    # ---------------------------------------
    # 가중치 없이 실적 Z-score 그대로 사용
    df["Score_Before"] = df["Performance_Zscore"]
    
    # 등급 산출 (30/40/30)
    q30_b = df["Score_Before"].quantile(0.30)
    q70_b = df["Score_Before"].quantile(0.70)
    
    def classify_before(z):
        if z <= q30_b: return "C"
        elif z <= q70_b: return "B"
        else: return "A"
        
    df["Grade_Before"] = df["Score_Before"].apply(classify_before)

    # ---------------------------------------
    # 3. Case 2: 적용 후 (현재 파이프라인 로직)
    # ---------------------------------------
    # 사용자 정의 맵 (원본 코드와 동일)
    qualification_map = {
        "법인": 2,          # 
        "공인중개사": 0,
        "중개보조원": -1,
        "중개인": -3,
    }
    
    df["대표자구분명"] = df["대표자구분명"].fillna("미등록")
    df["자격점수"] = df["대표자구분명"].map(qualification_map).fillna(-2)
    
    # 정규화
    qual_mean = df["자격점수"].mean()
    qual_std = df["자격점수"].std()
    if qual_std == 0: qual_std = 1
    
    df["Qual_Zscore"] = (df["자격점수"] - qual_mean) / qual_std
    df["Qual_Zscore"] = df["Qual_Zscore"].clip(-3, 3) # Clipping
    
    # 가중치 합산 (실적 0.7 + 자격 0.3)
    # 원본 코드: Score = (성사율_Z * 0.7) + (자격점수_Z * 0.3)
    df["Score_After"] = (df["Performance_Zscore"] * 0.7) + (df["Qual_Zscore"] * 0.3)
    
    # 등급 산출 (30/40/30)
    q30_a = df["Score_After"].quantile(0.30)
    q70_a = df["Score_After"].quantile(0.70)
    
    def classify_after(z):
        if z <= q30_a: return "C"
        elif z <= q70_a: return "B"
        else: return "A"

    df["Grade_After"] = df["Score_After"].apply(classify_after)

    # ---------------------------------------
    # 4. 비교 분석
    # ---------------------------------------
    # 등급이 변한 케이스 추출
    df["Change"] = df["Grade_Before"] + " -> " + df["Grade_After"]
    df["Is_Changed"] = df["Grade_Before"] != df["Grade_After"]
    
    changed_df = df[df["Is_Changed"]].copy()
    
    print(f"총 데이터 수: {len(df)}개")
    print(f"등급이 변동된 사무소 수: {len(changed_df)}개 ({len(changed_df)/len(df)*100:.1f}%)")
    
    if len(changed_df) > 0:
        print("\n[직책별 등급 변동 현황]")
        summary = changed_df.groupby(["대표자구분명", "Change"]).size().reset_index(name="Count")
        print(summary.to_string(index=False))
        
        print("\n[상세 변동 예시 (Top 5)]")
        # Grade 순서: A(상) > B(중) > C(하)
        # 문자열 정렬이 아님. 표기를 위해 로직 처리 필요하지만 여기선 날것 그대로 출력
        print(changed_df[["중개사무소명", "대표자구분명", "Performance_Zscore", "Qual_Zscore", "Grade_Before", "Grade_After"]].head(5).to_string(index=False))
        
        # 상승/하락 요약
        # A(2) > B(1) > C(0)
        grade_val = {"A": 2, "B": 1, "C": 0}
        changed_df["Val_Before"] = changed_df["Grade_Before"].map(grade_val)
        changed_df["Val_After"] = changed_df["Grade_After"].map(grade_val)
        
        up_count = len(changed_df[changed_df["Val_After"] > changed_df["Val_Before"]])
        down_count = len(changed_df[changed_df["Val_After"] < changed_df["Val_Before"]])
        
        print(f"\n📈 등급 상승(이득 본 케이스): {up_count}개")
        print(f"📉 등급 하락(손해 본 케이스): {down_count}개")

if __name__ == "__main__":
    analyze_impact()
