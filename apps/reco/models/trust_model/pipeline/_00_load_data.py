"""
데이터 로드 및 결측치 전처리 (거래완료, 등록매물 NaN만 제거)
+ 지역별 매물 수 필터링 (노이즈 제거)
"""
import pandas as pd
import numpy as np
from pathlib import Path

# ============================================
# 설정 (Configuration)
# ============================================
# 지역별 매물 수 필터링 설정
ENABLE_REGIONAL_FILTERING = False  # True: 필터링 적용, False: 필터링 비적용
MIN_REGIONAL_SAMPLES = 500        # 지역별 최소 총 매물 수 (500개 미만 지역 제거)


def load_processed_office_data(filepath: str = "data/brokerInfo/grouped_offices.csv") -> pd.DataFrame:
    """
    processed_office_data.csv 파일을 로드하여 DataFrame으로 반환.

    Args:
        filepath (str): 데이터 파일 경로

    Returns:
        pd.DataFrame: 로드된 데이터프레임
    """
    file = Path(filepath)

    if not file.exists():
        raise FileNotFoundError(f"[ERROR] 파일이 존재하지 않음: {filepath}")

    print(f"📊 [1단계] 데이터 로드")
    print(f"   파일: {filepath}")

    df = pd.read_csv(file, encoding="utf-8-sig")

    print(f"   행 수: {len(df):,}")
    print(f"   열 수: {len(df.columns)}")

    if "등록번호" not in df.columns:
        print("   ⚠️ 등록번호 컬럼이 존재하지 않습니다.")

    return df


def basic_preprocessing(df: pd.DataFrame) -> pd.DataFrame:
    """
    거래완료, 등록매물 컬럼 NaN 제거만 실행하는 최소 전처리

    Args:
        df (pd.DataFrame): 원본 데이터프레임

    Returns:
        pd.DataFrame: 전처리된 데이터프레임
    """

    print(f"\n🧹 [2단계] 기본 전처리 (거래완료 & 등록매물 NaN 제거)")

    # 문자열 "건" 제거 및 숫자형 변환
    df["거래완료"] = pd.to_numeric(df["거래완료"].str.replace("건", ""), errors="coerce")
    df["등록매물"] = pd.to_numeric(df["등록매물"].str.replace("건", ""), errors="coerce")

    before = len(df)
    df = df.dropna(subset=["거래완료", "등록매물"])
    after = len(df)

    print(f"   제거된 행 수: {before - after:,}개")
    print(f"   남은 행 수: {after:,}개")

    return df


def filter_by_regional_samples(df: pd.DataFrame) -> pd.DataFrame:
    """
    지역별 총 매물 수(거래완료 + 등록매물)가 적은 지역을 필터링하여 노이즈 제거
    
    Args:
        df (pd.DataFrame): 전처리된 데이터프레임
        
    Returns:
        pd.DataFrame: 지역 필터링된 데이터프레임
    """
    
    if not ENABLE_REGIONAL_FILTERING:
        print(f"\n⚠️ [2-1단계] 지역별 필터링 비활성화됨 (ENABLE_REGIONAL_FILTERING = False)")
        return df
    
    print(f"\n🗺️ [2-1단계] 지역별 총 매물 수 필터링 (최소 {MIN_REGIONAL_SAMPLES}개)")
    
    # 지역명 컬럼 확인
    region_col = None
    for col in ['지역명', '시도', '지역']:
        if col in df.columns:
            region_col = col
            break
    
    if region_col is None:
        print("   ⚠️ 지역 관련 컬럼을 찾을 수 없습니다. 필터링을 건너뜁니다.")
        return df
    
    print(f"   사용 컬럼: {region_col}")
    
    # 총 매물 수 계산 (거래완료 + 등록매물)
    df['총매물수'] = df['거래완료_숫자'] + df['등록매물_숫자']
    
    # 지역별 총 매물 수 합계 계산
    regional_total_properties = df.groupby(region_col)['총매물수'].sum().sort_values(ascending=False)
    regional_office_counts = df[region_col].value_counts().sort_values(ascending=False)
    
    print(f"   전체 지역 수: {len(regional_total_properties)}개")
    print(f"   지역별 총 매물 수 분포:")
    
    # 상위 10개 지역 출력
    print("   📊 상위 10개 지역 (총 매물 수):")
    for i, (region, total_properties) in enumerate(regional_total_properties.head(10).items()):
        office_count = regional_office_counts[region]
        avg_per_office = total_properties / office_count if office_count > 0 else 0
        print(f"      {i+1:2d}. {region}: {total_properties:,}개 매물 ({office_count}개 중개사, 평균 {avg_per_office:.1f}개/중개사)")
    
    # 필터링할 지역 식별
    regions_to_keep = regional_total_properties[regional_total_properties >= MIN_REGIONAL_SAMPLES].index
    regions_to_remove = regional_total_properties[regional_total_properties < MIN_REGIONAL_SAMPLES].index
    
    print(f"\n   🟢 유지할 지역: {len(regions_to_keep)}개 (≥{MIN_REGIONAL_SAMPLES}개 매물)")
    print(f"   🔴 제거할 지역: {len(regions_to_remove)}개 (<{MIN_REGIONAL_SAMPLES}개 매물)")
    
    if len(regions_to_remove) > 0:
        print(f"   제거될 지역 목록:")
        for region in regions_to_remove:
            total_properties = regional_total_properties[region]
            office_count = regional_office_counts[region]
            print(f"      - {region}: {total_properties:,}개 매물 ({office_count}개 중개사)")
    
    # 필터링 적용
    before_filter = len(df)
    before_total_properties = df['총매물수'].sum()
    
    df_filtered = df[df[region_col].isin(regions_to_keep)].copy()
    
    after_filter = len(df_filtered)
    after_total_properties = df_filtered['총매물수'].sum()
    
    removed_offices = before_filter - after_filter
    removed_properties = before_total_properties - after_total_properties
    
    print(f"\n   📉 필터링 결과:")
    print(f"      - 제거된 중개사: {removed_offices:,}개 ({removed_offices/before_filter*100:.1f}%)")
    print(f"      - 제거된 총 매물: {removed_properties:,}개 ({removed_properties/before_total_properties*100:.1f}%)")
    print(f"      - 남은 중개사: {after_filter:,}개 ({after_filter/before_filter*100:.1f}%)")
    print(f"      - 남은 총 매물: {after_total_properties:,}개 ({after_total_properties/before_total_properties*100:.1f}%)")
    
    # 필터링 후 지역별 분포 확인
    final_regional_properties = df_filtered.groupby(region_col)['총매물수'].sum().sort_values(ascending=False)
    final_regional_offices = df_filtered[region_col].value_counts().sort_values(ascending=False)
    
    print(f"      - 최종 지역 수: {len(final_regional_properties)}개")
    print(f"      - 지역별 최소 매물 수: {final_regional_properties.min():,}개")
    print(f"      - 지역별 최대 매물 수: {final_regional_properties.max():,}개")
    print(f"      - 전체 평균 매물/중개사: {after_total_properties/after_filter:.1f}개")
    
    # 임시 컬럼 제거
    df_filtered = df_filtered.drop('총매물수', axis=1)
    
    return df_filtered


def save_preprocessed(df: pd.DataFrame, filepath: str = "data/ML/preprocessed_office_data.csv"):
    """
    전처리된 df 저장

    Args:
        df (pd.DataFrame): 전처리 완료된 데이터프레임
        filepath (str): 저장할 파일 경로
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")

    print(f"\n💾 [3단계] 전처리된 데이터 저장 완료")
    print(f"   저장 파일: {filepath}")


def main():
    """메인 실행 함수"""
    print("📊 데이터 로드 및 전처리 중...")
    print(f"🔧 설정:")
    print(f"   - 지역별 필터링: {'활성화' if ENABLE_REGIONAL_FILTERING else '비활성화'}")
    if ENABLE_REGIONAL_FILTERING:
        print(f"   - 최소 매물 수: {MIN_REGIONAL_SAMPLES}개")

    # STEP 1: 데이터 로드
    df = load_processed_office_data()

    # STEP 2: 거래완료/등록매물 NaN 제거
    df = basic_preprocessing(df)

    # STEP 2-1: 지역별 매물 수 필터링 (선택적)
    df = filter_by_regional_samples(df)

    # STEP 3: 저장
    save_preprocessed(df)

    print("✅ 전처리 완료\n")

    return df


def set_regional_filtering(enable: bool = True, min_samples: int = 500):
    """
    지역별 필터링 설정을 변경하는 함수
    
    Args:
        enable (bool): 필터링 활성화 여부
        min_samples (int): 지역별 최소 매물 수
    """
    global ENABLE_REGIONAL_FILTERING, MIN_REGIONAL_SAMPLES
    ENABLE_REGIONAL_FILTERING = enable
    MIN_REGIONAL_SAMPLES = min_samples
    
    print(f"🔧 지역별 필터링 설정 변경:")
    print(f"   - 필터링: {'활성화' if enable else '비활성화'}")
    if enable:
        print(f"   - 최소 매물 수: {min_samples}개")


def get_current_settings():
    """현재 설정 확인"""
    print(f"🔧 현재 설정:")
    print(f"   - 지역별 필터링: {'활성화' if ENABLE_REGIONAL_FILTERING else '비활성화'}")
    if ENABLE_REGIONAL_FILTERING:
        print(f"   - 최소 매물 수: {MIN_REGIONAL_SAMPLES}개")
    
    return {
        'enable_filtering': ENABLE_REGIONAL_FILTERING,
        'min_samples': MIN_REGIONAL_SAMPLES
    }


if __name__ == "__main__":
    df = main()