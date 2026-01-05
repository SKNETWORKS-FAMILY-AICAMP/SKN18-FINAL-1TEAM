"""
cleaned_brokers.csv를 사무소별로 집계하는 스크립트
등록번호를 기준으로 그룹화하여 사무소 정보와 소속 중개사/중개보조원 정보를 집계
"""
import pandas as pd
from pathlib import Path
import json


def group_by_office():
    """사무소별로 중개사 정보 집계"""
    
    # CSV 파일 읽기
    input_file = "data/brokerInfo/cleaned_brokers.csv"
    output_file = "data/brokerInfo/grouped_offices.csv"
    
    print(f"=== {input_file} 파일 로드 중 ===")
    df = pd.read_csv(input_file)
    print(f"원본 데이터: {len(df)}행, {len(df.columns)}컬럼")
    
    # 등록번호가 없는 행 제거
    df = df[df['land_등록번호'].notna()]
    print(f"등록번호 있는 데이터: {len(df)}행")
    
    # 사무소별로 그룹화
    grouped = df.groupby('land_등록번호')
    
    office_data = []
    
    print("\n=== 사무소별 집계 시작 ===")
    
    for reg_num, group in grouped:
        # 첫 번째 행에서 사무소 기본 정보 추출 (모든 행이 동일한 사무소 정보를 가짐)
        first_row = group.iloc[0]
        
        # 사무소 기본 정보
        office_info = {
            '등록번호': reg_num,
            '중개사무소명': first_row.get('land_중개사무소명'),
            '대표자': first_row.get('land_대표자'),
            '전화번호': first_row.get('land_전화번호'),
            '주소': first_row.get('land_주소'),
            '거래완료': first_row.get('land_거래완료'),
            '등록매물': first_row.get('land_등록매물'),
            
            # office 정보
            '보증보험시작일': first_row.get('office_estbsBeginDe'),
            '보증보험종료일': first_row.get('office_estbsEndDe'),
            '등록일': first_row.get('office_registDe'),
            '상태구분코드': first_row.get('office_sttusSeCode'),
            '상태구분명': first_row.get('office_sttusSeCodeNm'),
            '지역코드': first_row.get('office_ldCode'),
            '지역명': first_row.get('office_ldCodeNm'),
            '최종수정일': first_row.get('office_lastUpdtDt'),
        }
        
        # 소속 중개사/중개보조원 정보 집계
        staff_list = []
        for _, row in group.iterrows():
            staff_name = row.get('broker_brkrNm')
            if pd.notna(staff_name):
                staff_info = {
                    '이름': staff_name,
                    '구분코드': row.get('broker_brkrAsortCode'),
                    '구분명': row.get('broker_brkrAsortCodeNm'),
                    '자격취득일': row.get('broker_crqfcAcqdt'),
                    '자격번호': row.get('broker_crqfcNo'),
                    '직위구분코드': row.get('broker_ofcpsSeCode'),
                    '직위구분명': row.get('broker_ofcpsSeCodeNm'),
                }
                staff_list.append(staff_info)
        
        # 대표자 구분명 찾기
        representative_name = office_info.get('대표자')
        representative_classification = None
        if representative_name:
            for staff in staff_list:
                if staff.get('이름') == representative_name:
                    representative_classification = staff.get('구분명')
                    break
        office_info['대표자구분명'] = representative_classification
        
        # 직원 수 집계
        # 구분명 기준 집계 (자격 종류)
        공인중개사수 = sum(1 for s in staff_list if s.get('구분명') == '공인중개사')
        중개보조원수 = sum(1 for s in staff_list if s.get('구분명') == '중개보조원')
        중개인수 = sum(1 for s in staff_list if s.get('구분명') == '중개인')
        법인수 = sum(1 for s in staff_list if s.get('구분명') == '법인')
        
        office_info['공인중개사수'] = 공인중개사수
        office_info['중개보조원수'] = 중개보조원수
        office_info['중개인수'] = 중개인수
        office_info['법인수'] = 법인수
        
        # 총_직원수 = 4개 구분명의 합
        office_info['총_직원수'] = 공인중개사수 + 중개보조원수 + 중개인수 + 법인수
        
        # 직위구분명 기준 집계 (직책)
        office_info['대표수'] = sum(1 for s in staff_list if s.get('직위구분명') == '대표')
        office_info['일반직원수'] = sum(1 for s in staff_list if s.get('직위구분명') == '일반')
        
        # 직원 정보를 JSON 문자열로 저장
        office_info['직원목록_JSON'] = json.dumps(staff_list, ensure_ascii=False)
        
        # 직원 이름 리스트 (쉼표로 구분)
        office_info['직원명단'] = ', '.join([s['이름'] for s in staff_list if s.get('이름')])
        
        office_data.append(office_info)
    
    # DataFrame 생성
    result_df = pd.DataFrame(office_data)
    
    print(f"\n집계 완료: {len(result_df)}개 사무소")
    print(f"  - 평균 직원 수: {result_df['총_직원수'].mean():.2f}명")
    print(f"  - 평균 공인중개사 수: {result_df['공인중개사수'].mean():.2f}명")
    print(f"  - 평균 중개보조원 수: {result_df['중개보조원수'].mean():.2f}명")
    print(f"  - 평균 중개인 수: {result_df['중개인수'].mean():.2f}명")
    print(f"  - 평균 법인 수: {result_df['법인수'].mean():.2f}명")
    
    # CSV 파일로 저장
    result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n=== {output_file} 파일 저장 완료 ===")
    
    return result_df


def main():
    try:
        # 사무소별 집계
        result_df = group_by_office()
        
        print("\n=== 처리 완료 ===")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
