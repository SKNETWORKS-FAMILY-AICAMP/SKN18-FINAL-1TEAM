"""
merged_brokers.csv에서 land_ 컬럼만 있고 나머지가 비어있는 행을 제거하는 스크립트
"""
import pandas as pd
from pathlib import Path


def clean_merged_brokers():
    """land_ 컬럼만 있고 나머지가 비어있는 행을 제거하고 불필요한 컬럼 삭제"""
    
    # CSV 파일 읽기
    input_file = "data/brokerInfo/merged_brokers.csv"
    output_file = "data/brokerInfo/cleaned_brokers.csv"
    
    print(f"=== {input_file} 파일 로드 중 ===")
    df = pd.read_csv(input_file)
    print(f"원본 데이터: {len(df)}행, {len(df.columns)}컬럼")
    
    # land_ 로 시작하는 컬럼들
    land_cols = [col for col in df.columns if col.startswith('land_')]
    
    # land_ 가 아닌 컬럼들
    non_land_cols = [col for col in df.columns if not col.startswith('land_')]
    
    print(f"\nland_ 컬럼 수: {len(land_cols)}")
    print(f"기타 컬럼 수: {len(non_land_cols)}")
    
    # land_ 컬럼만 있고 나머지가 모두 비어있는 행 찾기
    land_only_rows = df[
        df[land_cols].notna().any(axis=1) &  # land_ 컬럼 중 하나라도 값이 있음
        df[non_land_cols].isna().all(axis=1)  # 나머지 컬럼은 모두 비어있음
    ]
    
    print(f"\n삭제할 행 수 (land_ 컬럼만 있는 행): {len(land_only_rows)}")
    
    if len(land_only_rows) > 0:
        print("\n=== land_ 컬럼만 있고 나머지가 비어있는 행들 ===")
        print("=" * 100)
        for idx, row in land_only_rows.iterrows():
            print(f"\n[행 번호: {idx}]")
            # land_ 컬럼 중 값이 있는 것만 출력
            for col in land_cols:
                if pd.notna(row[col]):
                    print(f"  {col}: {row[col]}")
            print("-" * 100)
    
    # 해당 행들 제거
    cleaned_df = df[~df.index.isin(land_only_rows.index)]
    
    print(f"정제된 데이터: {len(cleaned_df)}행")
    
    # 삭제할 컬럼 목록
    columns_to_drop = [
        'office_brkrNm',
        'office_bsnmCmpnm',
        'office_jurirno',
        'office_rdnmadr',
        'office_rdnmadrcode',
        'broker_bsnmCmpnm',
        'broker_lastUpdtDt',
        'broker_ldCode',
        'broker_ldCodeNm'
    ]
    
    # 실제 존재하는 컬럼만 삭제
    existing_columns_to_drop = [col for col in columns_to_drop if col in cleaned_df.columns]
    
    if existing_columns_to_drop:
        print(f"\n삭제할 컬럼 수: {len(existing_columns_to_drop)}개")
        for col in existing_columns_to_drop:
            print(f"  - {col}")
        
        cleaned_df = cleaned_df.drop(columns=existing_columns_to_drop)
        print(f"\n컬럼 삭제 후: {len(cleaned_df.columns)}컬럼")
    else:
        print("\n삭제할 컬럼이 없습니다.")
    
    # CSV 파일로 저장
    cleaned_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n=== {output_file} 파일 저장 완료 ===")
    
    return cleaned_df


def main():
    try:
        cleaned_df = clean_merged_brokers()
        
        # 통계 출력
        print("\n=== 정제 완료 통계 ===")
        print(f"총 행 수: {len(cleaned_df)}")
        print(f"총 컬럼 수: {len(cleaned_df.columns)}")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        raise


if __name__ == "__main__":
    main()
