"""
land_brokers.csv를 기준으로 broker_offices.csv와 brokers.csv를 매칭하는 모듈
등록번호를 기준으로 세 파일을 병합합니다.
"""
import csv
import json
from pathlib import Path
from typing import List, Dict, Any
import re


class BrokerMerger:
    """중개사 정보 병합 클래스"""
    
    def __init__(self):
        self.land_brokers = []
        self.broker_offices = {}
        self.brokers = {}
        self.brokers_by_name_rep = {}  # 중개사무소명+대표자명으로 매칭하기 위한 딕셔너리
        self.brokers_by_reg_num = {}  # 등록번호별 직원 목록을 위한 딕셔너리
        self.additional_matched_records = []  # 추가 매칭된 레코드들을 추적
        self.merged_brokers = []
    
    def normalize_registration_number(self, reg_num: str) -> str:
        """
        등록번호 정규화 (숫자만 추출)
        
        Args:
            reg_num: 등록번호
            
        Returns:
            정규화된 등록번호 (숫자만)
        """
        if not reg_num:
            return None
        # 숫자만 추출
        numbers_only = re.sub(r'[^\d]', '', str(reg_num))
        return numbers_only if numbers_only else None
    
    def load_land_brokers(self, filepath: str) -> List[Dict[str, Any]]:
        """
        land_brokers.csv 데이터 로드
        
        Args:
            filepath: CSV 파일 경로
            
        Returns:
            중개사 정보 리스트
        """
        filepath = Path(filepath)
        
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            data = list(reader)
        
        self.land_brokers = data
        print(f"land_brokers.csv 로드: {len(data)}건")
        return data
    
    def load_broker_offices(self, filepath: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        broker_offices.csv 데이터 로드 (중개사무소명+대표자를 키로 하는 딕셔너리, 리스트로 저장)
        
        Args:
            filepath: CSV 파일 경로
            
        Returns:
            중개사무소명+대표자를 키로 하는 중개사 정보 딕셔너리 (값은 리스트)
        """
        filepath = Path(filepath)
        
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            data = list(reader)
        
        # 중개사무소명(bsnmCmpnm)+대표자(brkrNm)를 키로 하는 딕셔너리 생성 (리스트로 저장)
        for broker in data:
            office_name = broker.get('bsnmCmpnm', '').strip()  # 중개사무소명
            representative = broker.get('brkrNm', '').strip()  # 대표자명
            
            if office_name and representative:
                key = f"{office_name}_{representative}"
                if key not in self.broker_offices:
                    self.broker_offices[key] = []
                self.broker_offices[key].append(broker)
        
        print(f"broker_offices.csv 로드: {len(data)}건")
        print(f"  - 유효한 중개사무소명+대표자 조합: {len(self.broker_offices)}건")
        return self.broker_offices
    
    def load_brokers(self, filepath: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        brokers.csv 데이터 로드 (등록번호+중개사무소명을 키로 하는 딕셔너리, 리스트로 저장)
        
        Args:
            filepath: CSV 파일 경로
            
        Returns:
            등록번호+중개사무소명을 키로 하는 중개사 정보 딕셔너리 (값은 리스트)
        """
        filepath = Path(filepath)
        
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            data = list(reader)
        
        # 등록번호(jurirno)+중개사무소명(bsnmCmpnm)을 키로 하는 딕셔너리 생성 (리스트로 저장)
        for broker in data:
            reg_num = self.normalize_registration_number(broker.get('jurirno'))
            office_name = broker.get('bsnmCmpnm', '').strip()
            
            if reg_num and office_name:
                key = f"{reg_num}_{office_name}"
                if key not in self.brokers:
                    self.brokers[key] = []
                self.brokers[key].append(broker)
        
        # 추가 매칭을 위한 중개사무소명+대표자명 딕셔너리도 생성
        self.brokers_by_name_rep = {}
        # 등록번호별 직원 목록 딕셔너리 생성
        self.brokers_by_reg_num = {}
        
        for broker in data:
            office_name = broker.get('bsnmCmpnm', '').strip()
            representative = broker.get('brkrNm', '').strip()  # 대표자명
            reg_num = self.normalize_registration_number(broker.get('jurirno'))
            
            # 중개사무소명+대표자명 딕셔너리
            if office_name and representative:
                key = f"{office_name}_{representative}"
                if key not in self.brokers_by_name_rep:
                    self.brokers_by_name_rep[key] = []
                self.brokers_by_name_rep[key].append(broker)
            
            # 등록번호별 직원 목록 딕셔너리
            if reg_num:
                if reg_num not in self.brokers_by_reg_num:
                    self.brokers_by_reg_num[reg_num] = []
                self.brokers_by_reg_num[reg_num].append(broker)
        
        print(f"brokers.csv 로드: {len(data)}건")
        print(f"  - 유효한 등록번호+중개사무소명 조합: {len(self.brokers)}건")
        print(f"  - 유효한 중개사무소명+대표자명 조합: {len(self.brokers_by_name_rep)}건")
        print(f"  - 유효한 등록번호별 직원 그룹: {len(self.brokers_by_reg_num)}건")
        return self.brokers
    
    def merge_brokers(self) -> List[Dict[str, Any]]:
        """
        brokers.csv를 기준으로 broker_offices.csv와 brokers.csv 병합
        1단계: brokers + broker_offices (중개사무소명+대표자로 매칭)
        2단계: 1단계 결과 + brokers (등록번호로 매칭)
        
        Returns:
            병합된 중개사 정보 리스트
        """
        print("\n=== 중개사 정보 병합 시작 ===\n")
        
        matched_with_offices = 0
        matched_with_brokers = 0
        matched_with_both = 0
        total_office_records = 0
        total_brokers_records = 0
        
        # 1단계: land_brokers + broker_offices (중개사무소명+대표자로 매칭)
        land_office_merged = []
        
        for land_broker in self.land_brokers:
            # land_brokers의 중개소명과 대표자로 키 생성
            broker_name = land_broker.get('중개사무소명', '').strip()
            representative = land_broker.get('대표자', '').strip()
            
            if broker_name and representative:
                key = f"{broker_name}_{representative}"
                office_list = self.broker_offices.get(key, [])
            else:
                office_list = []
            
            if office_list:
                matched_with_offices += 1
                total_office_records += len(office_list)
                
                # office 데이터가 있으면 각각에 대해 병합
                for office_data in office_list:
                    merged = {
                        'land_broker': land_broker,
                        'office_data': office_data
                    }
                    land_office_merged.append(merged)
            else:
                # office 데이터가 없으면 land만 저장
                merged = {
                    'land_broker': land_broker,
                    'office_data': None
                }
                land_office_merged.append(merged)
        
        print(f"1단계 완료 (land + office): {len(land_office_merged)}건")
        print(f"  - broker_offices와 매칭: {matched_with_offices}건 (총 {total_office_records}개 레코드)")
        
        # 2단계: 1단계 결과 + brokers (등록번호+중개사무소명으로 매칭)
        matched_with_additional = 0  # 추가 매칭 카운터
        
        for merged_item in land_office_merged:
            land_broker = merged_item['land_broker']
            office_data = merged_item['office_data']
            
            # 등록번호 + 중개소명으로 brokers 데이터 찾기 (1차 매칭)
            land_reg = self.normalize_registration_number(land_broker.get('등록번호'))
            broker_name = land_broker.get('중개사무소명', '').strip()
            
            if land_reg and broker_name:
                key = f"{land_reg}_{broker_name}"
                brokers_list = self.brokers.get(key, [])
            else:
                brokers_list = []
            
            # 1차 매칭이 실패한 경우, 중개사무소명+대표자명으로 2차 매칭 시도
            is_additional_match = False
            if not brokers_list:
                representative = land_broker.get('대표자', '').strip()
                if broker_name and representative:
                    name_rep_key = f"{broker_name}_{representative}"
                    brokers_list = self.brokers_by_name_rep.get(name_rep_key, [])
                    if brokers_list:
                        matched_with_additional += 1
                        is_additional_match = True
                        print(f"  추가 매칭 성공: {broker_name} - {representative}")
            
            if brokers_list:
                matched_with_brokers += 1
                total_brokers_records += len(brokers_list)
                
                if office_data:
                    matched_with_both += 1
                
                # brokers 데이터가 있으면 각 직원(공인중개사/중개보조원)마다 행 복제
                for broker_data in brokers_list:
                    merged_broker = {}
                    
                    # land 데이터 추가
                    for key, value in land_broker.items():
                        merged_broker[f'land_{key}'] = value
                    
                    # office 데이터 추가 (있는 경우)
                    if office_data:
                        for key, value in office_data.items():
                            merged_broker[f'office_{key}'] = value
                    
                    # brokers 데이터 추가 (각 직원 정보)
                    for key, value in broker_data.items():
                        merged_broker[f'broker_{key}'] = value
                    
                    # 추가 매칭된 경우 표시
                    if is_additional_match:
                        merged_broker['is_additional_match'] = True
                        self.additional_matched_records.append(merged_broker)
                    
                    self.merged_brokers.append(merged_broker)
            else:
                # brokers 데이터가 없으면 land + office만 저장
                merged_broker = {}
                
                # land 데이터 추가
                for key, value in land_broker.items():
                    merged_broker[f'land_{key}'] = value
                
                # office 데이터 추가 (있는 경우)
                if office_data:
                    for key, value in office_data.items():
                        merged_broker[f'office_{key}'] = value
                
                self.merged_brokers.append(merged_broker)
        
        print(f"\n2단계 완료 (+ brokers): {len(self.merged_brokers)}건")
        print(f"  - brokers와 매칭: {matched_with_brokers}건 (총 {total_brokers_records}개 레코드)")
        print(f"    * 등록번호+중개사무소명 매칭: {matched_with_brokers - matched_with_additional}건")
        print(f"    * 중개사무소명+대표자명 추가 매칭: {matched_with_additional}건")
        print(f"  - office와 brokers 둘 다 매칭: {matched_with_both}건")
        
        return self.merged_brokers
    
    def add_staff_list_for_additional_matches(self) -> None:
        """
        추가 매칭된 중개사무소들에 대해서만 해당 등록번호의 모든 직원 목록을 JSON으로 추가
        """
        print("\n=== 추가 매칭 건들에 대한 직원 목록 JSON 생성 시작 ===")
        
        staff_added_count = 0
        processed_reg_nums = set()  # 중복 처리 방지
        
        for merged_broker in self.merged_brokers:
            # 추가 매칭된 레코드만 처리
            if merged_broker.get('is_additional_match', False):
                # 등록번호 추출
                broker_reg = merged_broker.get('broker_jurirno', '')
                reg_num = self.normalize_registration_number(broker_reg)
                
                # 이미 처리한 등록번호는 스킵 (같은 등록번호의 여러 직원이 있을 수 있음)
                if reg_num and reg_num not in processed_reg_nums:
                    processed_reg_nums.add(reg_num)
                    
                    if reg_num in self.brokers_by_reg_num:
                        # 해당 등록번호의 모든 직원 정보 수집
                        staff_list = []
                        for staff in self.brokers_by_reg_num[reg_num]:
                            staff_info = {
                                '직원명': staff.get('brkrNm', ''),
                                '직원구분': staff.get('brkrAsortCodeNm', ''),
                                '자격취득일': staff.get('crqfcAcqdt', ''),
                                '자격번호': staff.get('crqfcNo', ''),
                                '사무소구분': staff.get('ofcpsSeCodeNm', ''),
                                '최종수정일': staff.get('lastUpdtDt', '')
                            }
                            staff_list.append(staff_info)
                        
                        # 같은 등록번호를 가진 모든 레코드에 직원목록 JSON 추가
                        for record in self.merged_brokers:
                            if (record.get('is_additional_match', False) and 
                                self.normalize_registration_number(record.get('broker_jurirno', '')) == reg_num):
                                record['직원목록_JSON'] = json.dumps(staff_list, ensure_ascii=False, indent=2)
                        
                        staff_added_count += 1
                        print(f"  직원목록 추가: {merged_broker.get('land_중개사무소명', '')} (등록번호: {reg_num}, 직원 {len(staff_list)}명)")
        
        print(f"추가 매칭 건들에 대한 직원 목록 JSON 추가 완료: {staff_added_count}개 중개사무소")
    
    def save_results(self, output_filepath: str = None) -> None:
        """
        병합 결과 저장
        
        Args:
            output_filepath: 출력 파일 경로 (기본값: data/brokerInfo/merged_brokers.csv)
        """
        if output_filepath is None:
            output_filepath = Path("data/brokerInfo") / "merged_brokers.csv"
        else:
            output_filepath = Path(output_filepath)
        
        # 디렉토리 생성
        output_filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if self.merged_brokers:
            # 모든 키를 수집하여 헤더 생성
            all_keys = set()
            for broker in self.merged_brokers:
                all_keys.update(broker.keys())
            
            # 헤더 정렬 (land_ -> office_ -> broker_ -> 기타 순서)
            land_keys = sorted([k for k in all_keys if k.startswith('land_')])
            office_keys = sorted([k for k in all_keys if k.startswith('office_')])
            broker_keys = sorted([k for k in all_keys if k.startswith('broker_')])
            other_keys = sorted([k for k in all_keys if not k.startswith(('land_', 'office_', 'broker_'))])
            headers = land_keys + office_keys + broker_keys + other_keys
            
            with open(output_filepath, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(self.merged_brokers)
            
            print(f"\n병합된 데이터 저장:")
            print(f"  - 파일: {output_filepath}")
            print(f"  - 총 컬럼 수: {len(headers)}개")
            print(f"    * land_ 컬럼: {len(land_keys)}개")
            print(f"    * office_ 컬럼: {len(office_keys)}개")
            print(f"    * broker_ 컬럼: {len(broker_keys)}개")
            print(f"    * 기타 컬럼: {len(other_keys)}개")


def main():
    """메인 실행 함수"""
    try:
        merger = BrokerMerger()
        
        # 데이터 디렉토리
        data_dir = Path("data/brokerInfo")
        
        # 파일 경로 설정
        land_file = data_dir / "land_brokers.csv"
        office_file = data_dir / "broker_offices.csv"
        brokers_file = data_dir / "brokers.csv"
        
        # 파일 존재 확인
        if not land_file.exists():
            print(f"오류: {land_file} 파일을 찾을 수 없습니다.")
            return
        
        if not office_file.exists():
            print(f"오류: {office_file} 파일을 찾을 수 없습니다.")
            return
        
        if not brokers_file.exists():
            print(f"오류: {brokers_file} 파일을 찾을 수 없습니다.")
            return
        
        print("=== 중개사 데이터 병합 프로그램 ===\n")
        print(f"land_brokers: {land_file.name}")
        print(f"broker_offices: {office_file.name}")
        print(f"brokers: {brokers_file.name}\n")
        
        # 데이터 로드
        merger.load_land_brokers(str(land_file))
        merger.load_broker_offices(str(office_file))
        merger.load_brokers(str(brokers_file))
        
        # 병합 수행
        merged = merger.merge_brokers()
        
        # 추가 매칭된 건들에 대해서만 직원 목록 JSON 추가
        merger.add_staff_list_for_additional_matches()
        
        # 결과 저장
        merger.save_results()
        
        print("\n=== 병합 완료 ===")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
