
import pandas as pd
import numpy as np
from pathlib import Path

def analyze_impact():
    print("⚖️ 자격 점수(서열 점수) 적용 전후 등급 변화 분석\n")
    
    # 데이터 로드
    df = pd.read_csv("data/ML/preprocessed_office_data.csv", encoding="utf-8-sig")
    
    # ---------------------------------------
    # 1. 공통: 거래성사율 및 지역별 Z-score 계산
    # ---------------------------------------
    df["거래성사율"] = np.where(
        (df["거래완료_숫자"] + df["등록매물_숫자"]) > 0,
        df["거래완료_숫자"] / (df["거래완료_숫자"] + df["등록매물_숫자"]),
        0
    )
    df["지역평균"] = df.groupby("지역명")["거래성사율"].transform("mean")
    df["지역표준편차"] = df.groupby("지역명")["거래성사율"].transform("std")
    df["Performance_Zscore"] = (df["거래성사율"] - df["지역평균"]) / df["지역표준편차"]

    # ---------------------------------------
    # 2. Case 1: 적용 전 (순수 실적 100%)
    # ---------------------------------------
    # 가중치 없이 실적 Z-score 그대로 사용
    df["Zscore_Before"] = df["Performance_Zscore"]
    
    # 등급 산출 (30/40/30)
    q30_b = df["Zscore_Before"].quantile(0.30)
    q70_b = df["Zscore_Before"].quantile(0.70)
    
    def classify_before(z):
        if z <= q30_b: return "C"
        elif z <= q70_b: return "B"
        else: return "A"
        
    df["Grade_Before"] = df["Zscore_Before"].apply(classify_before)

    # ---------------------------------------
    # 3. Case 2: 적용 후 (사용자 설정 맵 적용)
    # ---------------------------------------
    # 사용자 정의 맵
    qualification_map = {
        "법인": 2,
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
    
    # 가중치 합산 (실적 80 + 자격 20)
    df["Zscore_After"] = (df["Performance_Zscore"] * 0.8) + (df["Qual_Zscore"] * 0.2)

    # 추가 가중치 (대표자 구분 2차 보정) - create_target.py의 로직 유지
    대표자구분_가중치 = {
        '공인중개사': 0.0, 
        '법인': 0.2, 
        '중개보조원': -0.1, 
        '중개인': -0.3
    }
    df["대표자구분_조정값"] = df["대표자구분명"].map(대표자구분_가중치).fillna(0.0)
    df["Zscore_After_Adj"] = df["Zscore_After"] + df["대표자구분_조정값"]
    
    # 등급 산출 (30/40/30)
    q30_a = df["Zscore_After_Adj"].quantile(0.30)
    q70_a = df["Zscore_After_Adj"].quantile(0.70)
    
    def classify_after(z):
        if z <= q30_a: return "C"
        elif z <= q70_a: return "B"
        else: return "A"

    df["Grade_After"] = df["Zscore_After_Adj"].apply(classify_after)

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
        print(changed_df[["중개사무소명", "대표자구분명", "Performance_Zscore", "Qual_Zscore", "Grade_Before", "Grade_After"]].head(5).to_string(index=False))
        
        # 상승/하락 요약
        up = changed_df[df["Grade_Before"] > df["Grade_After"]] # C > B > A (문자열로는 C가 A보다 큼.. 아님)
        # 등급 순서: A > B > C
        # 문자열: A < B < C
        # 상승: C -> B (문자열 감소), B -> A (문자열 감소)
        # 하락: A -> B (문자열 증가), B -> C (문자열 증가)
        
        up_count = len(changed_df[changed_df["Grade_After"] < changed_df["Grade_Before"]])
        down_count = len(changed_df[changed_df["Grade_After"] > changed_df["Grade_Before"]])
        
        print(f"\n📈 등급 상승(이득 본 케이스): {up_count}개")
        print(f"📉 등급 하락(손해 본 케이스): {down_count}개")

if __name__ == "__main__":
    analyze_impact()
