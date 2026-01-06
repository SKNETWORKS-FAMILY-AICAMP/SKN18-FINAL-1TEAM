import pandas as pd
from pathlib import Path

# 이 파일 위치 기준으로 프로젝트 루트 찾기
# loaders/ -> src/ -> price_model/ -> reco/ -> apps/ -> SKN18-FINAL-1TEAM (6개 parent)
REPO_ROOT = Path(__file__).resolve().parents[5]
BASE_DIR = REPO_ROOT / "data" / "actual_transaction_price"


# -------------------------------
# 1) 금리 데이터 통합 함수
# -------------------------------
def merge_rate_files():
    """
    4개의 금리 관련 CSV 파일을 통합하여 하나의 파일로 생성
    """
    print("=" * 60)
    print("금리 데이터 통합 시작...")
    print("=" * 60)

    # 1. 소비자물가상승률 로드
    print("1. 소비자물가상승률 데이터 로드 중...")
    cpi = pd.read_csv(BASE_DIR / "소비자물가상승률_24.08_25.11.csv", encoding="utf-8-sig")
    cpi.columns = [c.strip() for c in cpi.columns]

    # 날짜 컬럼 YYYY-MM 형식으로 변환
    rename_map = {
        c: f"{c.split('.')[0]}-{c.split('.')[1].zfill(2)}"
        for c in cpi.columns if c != "구분"
    }
    cpi = cpi.rename(columns=rename_map)

    # wide → long
    cpi_long = cpi.melt(id_vars="구분", var_name="연월", value_name="값")
    # 소비자물가만 사용
    cpi_data = cpi_long[cpi_long["구분"] == "소비자물가"][["연월", "값"]]
    cpi_data = cpi_data.rename(columns={"값": "소비자물가"})
    cpi_data["소비자물가"] = pd.to_numeric(cpi_data["소비자물가"], errors="coerce")

    # 2. 시장금리 로드
    print("2. 시장금리 데이터 로드 중...")
    market = pd.read_csv(BASE_DIR / "시장금리(월,분기,년)_24.8~25.11.csv", encoding="utf-8-sig")
    market.columns = [c.strip() for c in market.columns]

    # 날짜 컬럼 변환 (2024/08 → 2024-08)
    rename_map = {
        c: f"{c.split('/')[0]}-{c.split('/')[1].zfill(2)}"
        for c in market.columns if "/" in c
    }
    market = market.rename(columns=rename_map)

    # 필요한 행만 추출
    market_filtered = market[market["계정항목"].isin([
        "무담보콜금리(1일)",
        "KORIBOR(3개월)",
        "CD(91일)"
    ])]

    # wide → long
    value_cols = [c for c in market_filtered.columns if c not in ["통계표", "계정항목", "단위", "변환"]]
    market_long = market_filtered.melt(
        id_vars="계정항목",
        value_vars=value_cols,
        var_name="연월",
        value_name="값"
    )

    # pivot
    market_pivot = market_long.pivot(index="연월", columns="계정항목", values="값").reset_index()
    market_pivot = market_pivot.rename(columns={
        "무담보콜금리(1일)": "무담보콜금리",
        "KORIBOR(3개월)": "KORIBOR",
        "CD(91일)": "CD"
    })

    for col in ["무담보콜금리", "KORIBOR", "CD"]:
        market_pivot[col] = pd.to_numeric(market_pivot[col], errors="coerce")

    # 3. 예금은행 대출금리 로드
    print("3. 예금은행 대출금리 데이터 로드 중...")
    loan = pd.read_csv(BASE_DIR / "예금은행_대출금리_신규취급액_기준__24.8~25.10.csv", encoding="utf-8-sig")
    loan.columns = [c.strip() for c in loan.columns]

    # 날짜 컬럼 변환
    rename_map = {
        c: f"{c.split('.')[0]}-{c.split('.')[1].zfill(2)}"
        for c in loan.columns if c != "계정항목별"
    }
    loan = loan.rename(columns=rename_map)

    # 필요한 행만 추출
    loan_filtered = loan[loan["계정항목별"].isin([
        "기업대출 (연리%)",
        "전세자금대출 (연리%)",
        "변동형 주택담보대출 3) (연리%)"
    ])]

    # wide → long
    value_cols = [c for c in loan_filtered.columns if c != "계정항목별"]
    loan_long = loan_filtered.melt(
        id_vars="계정항목별",
        value_vars=value_cols,
        var_name="연월",
        value_name="값"
    )

    # pivot
    loan_pivot = loan_long.pivot(index="연월", columns="계정항목별", values="값").reset_index()
    loan_pivot = loan_pivot.rename(columns={
        "기업대출 (연리%)": "기업대출",
        "전세자금대출 (연리%)": "전세자금대출",
        "변동형 주택담보대출 3) (연리%)": "변동형주택담보대출"
    })

    for col in ["기업대출", "전세자금대출", "변동형주택담보대출"]:
        loan_pivot[col] = pd.to_numeric(loan_pivot[col], errors="coerce")

    # 4. 한국은행 기준금리 로드
    print("4. 한국은행 기준금리 데이터 로드 중...")
    base = pd.read_csv(BASE_DIR / "한국은행_기준금리(24.08~25.10).csv", encoding="utf-8-sig")
    base.columns = [c.strip() for c in base.columns]

    # 날짜 컬럼 변환
    rename_map = {
        c: f"{c.split('.')[0]}-{c.split('.')[1].zfill(2)}"
        for c in base.columns if c != "계정항목"
    }
    base = base.rename(columns=rename_map)

    # wide → long
    value_cols = [c for c in base.columns if c != "계정항목"]
    base_long = base.melt(
        id_vars="계정항목",
        value_vars=value_cols,
        var_name="연월",
        value_name="값"
    )

    base_data = base_long[base_long["계정항목"] == "한국은행 기준금리"][["연월", "값"]]
    base_data = base_data.rename(columns={"값": "기준금리"})
    base_data["기준금리"] = pd.to_numeric(base_data["기준금리"], errors="coerce")

    # 5. 모든 데이터 merge
    print("5. 모든 금리 데이터 병합 중...")
    merged = cpi_data
    merged = merged.merge(market_pivot, on="연월", how="outer")
    merged = merged.merge(loan_pivot, on="연월", how="outer")
    merged = merged.merge(base_data, on="연월", how="outer")

    # 연월 기준으로 정렬
    merged = merged.sort_values("연월").reset_index(drop=True)

    # 6. long → wide 형태로 변환 (원본 CSV와 동일한 형태)
    merged_long = merged.melt(id_vars="연월", var_name="구분", value_name="값")
    merged_wide = merged_long.pivot(index="구분", columns="연월", values="값").reset_index()

    # 날짜 컬럼을 YYYY.MM 형식으로 변경 (원본 형식과 동일하게)
    rename_map = {
        c: c.replace("-", ".")
        for c in merged_wide.columns if c != "구분"
    }
    merged_wide = merged_wide.rename(columns=rename_map)

    # 저장
    output_path = BASE_DIR / "(총합)시장금리_및_대출금리(24.8~25.10).csv"
    merged_wide.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\n✓ 통합 파일 생성 완료: {output_path}")
    print(f"  - 포함 항목: 소비자물가, 무담보콜금리, KORIBOR, CD, 기업대출, 전세자금대출, 변동형주택담보대출, 기준금리")
    print("=" * 60)

    return merged  # long 형태로 반환 (연월 기준)


# -------------------------------
# 2) 월세 데이터 전처리 함수
# -------------------------------
def load_and_filter_monthly(path: Path) -> pd.DataFrame:
    """
    월세 데이터를 로드하고 필터링
    """
    df = pd.read_csv(path, encoding="cp949")

    # 전월세 구분/면적 컬럼 자동 감지
    col_rent = "전월세구분" if "전월세구분" in df.columns else "전월세 구분"
    col_area = "임대면적" if "임대면적" in df.columns else "임대면적(㎡)"

    # 월세만 사용
    df = df[df[col_rent].astype(str).str.contains("월세", na=False)]

    # 층 처리
    df["층"] = pd.to_numeric(df.get("층", 0), errors="coerce").fillna(0)
    # 층이 0인 행 제거
    df = df[df["층"] != 0].copy()


    # 건축년도 null 제거
    df = df.dropna(subset=["건축년도"])

    # 계약일 처리 + 기간 필터링
    df["계약일"] = pd.to_datetime(df["계약일"].astype(str), format="%Y%m%d", errors="coerce")
    df = df[(df["계약일"] >= "2024-08-01") & (df["계약일"] <= "2025-10-31")]

    # 필요한 컬럼만 선택 + 통일
    df = df[[
        "자치구명", "법정동명", "층", "계약일",
        col_rent, col_area,
        "보증금(만원)", "임대료(만원)",
        "건축년도", "건물용도"
    ]].rename(columns={col_rent: "전월세구분", col_area: "임대면적"})

    return df


# -------------------------------
# 3) 메인 실행 함수
# -------------------------------
def run():
    """
    월세 데이터셋 준비 전체 파이프라인 실행
    외부 모듈에서 호출 가능
    """
    print("\n" + "=" * 60)
    print("월세 데이터셋 준비 시작")
    print("=" * 60 + "\n")

    # Step 1: 금리 데이터 통합 (4개 파일을 하나로 합치기)
    rate_data = merge_rate_files()

    # Step 2: 월세 데이터 합치기
    print("\n" + "=" * 60)
    print("월세 데이터 로드 및 전처리 시작...")
    print("=" * 60)

    print("- 2024년 월세 데이터 로드 중...")
    df_2024 = load_and_filter_monthly(BASE_DIR / "서울특별시_전월세가_2024.csv")
    print(f"  2024년 데이터: {len(df_2024):,}건")

    print("- 2025년 월세 데이터 로드 중...")
    df_2025 = load_and_filter_monthly(BASE_DIR / "서울특별시_전월세가_2025.csv")
    print(f"  2025년 데이터: {len(df_2025):,}건")

    df = pd.concat([df_2024, df_2025], ignore_index=True)
    print(f"✓ 전체 월세 데이터: {len(df):,}건")

    # 연월만 사용
    df["연월"] = df["계약일"].dt.to_period("M").astype(str)
    df = df.drop(columns=["계약일"])

    # 숫자형 통일
    for col in ["층", "임대면적", "보증금(만원)", "임대료(만원)", "건축년도"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Step 3: 금리 데이터와 병합
    print("\n" + "=" * 60)
    print("금리 데이터와 월세 데이터 병합 중...")
    print("=" * 60)

    df = df.merge(rate_data, on="연월", how="left")
    print(f"✓ 병합 완료: {len(df):,}건")

    # Step 4: 모델링용 컬럼만 유지
    model_cols = [
        "자치구명", "법정동명", "층", "연월",
        "임대면적", "보증금(만원)", "임대료(만원)",
        "건축년도", "건물용도",
        "소비자물가", "무담보콜금리", "KORIBOR", "CD",
        "기업대출", "전세자금대출",
        "변동형주택담보대출", "기준금리"
    ]

    df_model = df[model_cols].copy()

    # Null 값 확인
    null_counts = df_model.isnull().sum()
    if null_counts.sum() > 0:
        print("\n⚠ Null 값 발견:")
        for col, count in null_counts[null_counts > 0].items():
            print(f"  - {col}: {count:,}건")

    # Step 5: 전체 모델링 데이터 저장
    print("\n" + "=" * 60)
    print("모델링 데이터 저장 중...")
    print("=" * 60)

    out = BASE_DIR / "월세_모델링용(24.08~25.10).csv"
    df_model.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"✓ 모델링 데이터 저장 완료: {out}")
    print(f"  - 총 {len(df_model):,}건")
    print(f"  - 컬럼 수: {len(df_model.columns)}개")

    # Step 6: Train/Test Split
    print("\n" + "=" * 60)
    print("Train/Test 데이터 분할 중...")
    print("=" * 60)

    # Train: 2024-08 ~ 2025-08
    train_months = [f"2024-{m:02d}" for m in range(8, 13)] + [f"2025-{m:02d}" for m in range(1, 9)]

    # Test: 2025-09 ~ 2025-10
    test_months = ["2025-09", "2025-10"]

    df_train = df_model[df_model["연월"].isin(train_months)].copy()
    df_test = df_model[df_model["연월"].isin(test_months)].copy()

    print(f"- Train 기간: 2024-08 ~ 2025-08 ({len(df_train):,}건)")
    print(f"- Test 기간: 2025-09 ~ 2025-10 ({len(df_test):,}건)")

    # 저장
    out_train = BASE_DIR / "월세_train(24.08~25.08).csv"
    out_test = BASE_DIR / "월세_test(25.09~25.10).csv"

    df_train.to_csv(out_train, index=False, encoding="utf-8-sig")
    df_test.to_csv(out_test, index=False, encoding="utf-8-sig")

    print(f"\n✓ Train 데이터 저장 완료: {out_train}")
    print(f"✓ Test 데이터 저장 완료: {out_test}")

    # 최종 요약
    print("\n" + "=" * 60)
    print("전체 작업 완료!")
    print("=" * 60)
    print("\n생성된 파일:")
    print(f"1. {BASE_DIR / '(총합)시장금리_및_대출금리(24.8~25.10).csv'}")
    print(f"2. {out}")
    print(f"3. {out_train}")
    print(f"4. {out_test}")
    print("\n" + "=" * 60 + "\n")
    
    return {
        "rate_data_path": BASE_DIR / "(총합)시장금리_및_대출금리(24.8~25.10).csv",
        "model_data_path": out,
        "train_path": out_train,
        "test_path": out_test,
    }


# -------------------------------
# 4) 단독 실행 시
# -------------------------------
if __name__ == "__main__":
    run()
