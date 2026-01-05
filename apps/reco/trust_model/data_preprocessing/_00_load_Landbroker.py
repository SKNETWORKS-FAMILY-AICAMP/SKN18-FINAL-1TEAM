"""
landData 폴더의 JSON 파일들에서 중개사 정보를 추출하여 통합하는 모듈
중복제거 기준: 등록번호
중개사_정보 필드만 추출 (매물 정보 제외)
"""
import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Set
from datetime import datetime


class LandBrokerExtractor:
    """크롤링된 매물 데이터에서 중개사 정보를 추출하는 클래스"""
    
    def __init__(self, data_dir: str = "data/RDB/land"):
        """
        Args:
            data_dir: JSON 파일들이 있는 디렉토리 경로
        """
        self.data_dir = Path(data_dir)
        self.brokers = []
        self.broker_ids = set()  # 중복 제거용
    
    def extract_brokers_from_file(self, filepath: Path) -> List[Dict[str, Any]]:
        """
        단일 JSON 파일에서 중개사 정보 추출
        
        Args:
            filepath: JSON 파일 경로
            
        Returns:
            중개사 정보 리스트
        """
        brokers = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                print(f"경고: {filepath.name}의 데이터 형식이 리스트가 아닙니다.")
                return brokers
            
            for item in data:
                broker_info = item.get("중개사_정보", {})
                
                # 중개사 정보가 비어있지 않은 경우만 추출
                if broker_info and isinstance(broker_info, dict):
                    # 담당자 필드 제외하고 중개사 정보만 저장
                    broker_data = {k: v for k, v in broker_info.items() if k != "담당자"}
                    brokers.append(broker_data)
            
            print(f"[{filepath.name}] {len(brokers)}개의 중개사 정보 추출")
            
        except json.JSONDecodeError as e:
            print(f"오류: {filepath.name} JSON 파싱 실패 - {e}")
        except Exception as e:
            print(f"오류: {filepath.name} 처리 중 오류 - {e}")
        
        return brokers
    
    def extract_all_brokers(self) -> List[Dict[str, Any]]:
        """
        landData 폴더의 모든 JSON 파일에서 중개사 정보 추출
        
        Returns:
            전체 중개사 정보 리스트
        """
        print("=== 중개사 정보 추출 시작 ===\n")
        
        # JSON 파일 목록 가져오기
        json_files = list(self.data_dir.glob("*.json"))
        
        if not json_files:
            print(f"경고: {self.data_dir}에 JSON 파일이 없습니다.")
            return []
        
        all_brokers = []
        
        for json_file in json_files:
            brokers = self.extract_brokers_from_file(json_file)
            all_brokers.extend(brokers)
        
        print(f"\n=== 총 {len(all_brokers)}개의 중개사 정보 추출 완료 ===")
        
        return all_brokers
    
    def remove_duplicates(self, brokers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        중복된 중개사 정보 제거 (등록번호 기준)
        
        Args:
            brokers: 중개사 정보 리스트
            
        Returns:
            중복이 제거된 중개사 정보 리스트
        """
        unique_brokers = []
        seen_registration_numbers = set()
        no_registration_brokers = []
        
        for broker in brokers:
            registration_number = broker.get("등록번호")
            
            if registration_number:
                # 등록번호로 중복 제거
                if registration_number not in seen_registration_numbers:
                    seen_registration_numbers.add(registration_number)
                    unique_brokers.append(broker)
            else:
                # 등록번호가 없는 경우 별도로 보관
                no_registration_brokers.append(broker)
        
        # 등록번호가 없는 중개사는 중개사명+전화번호로 중복 제거
        seen_keys = set()
        for broker in no_registration_brokers:
            key = f"{broker.get('중개사명', '')}|{broker.get('전화번호', '')}"
            if key not in seen_keys and key != "|":
                seen_keys.add(key)
                unique_brokers.append(broker)
        
        print(f"\n중복 제거 (등록번호 기준): {len(brokers)}건 → {len(unique_brokers)}건")
        print(f"  - 등록번호 있음: {len(seen_registration_numbers)}건")
        print(f"  - 등록번호 없음: {len(unique_brokers) - len(seen_registration_numbers)}건")
        
        return unique_brokers
    
    def save_to_csv(self, brokers: List[Dict[str, Any]], filepath: str) -> None:
        """
        중개사 정보를 CSV 파일로 저장
        컬럼명 변경: '중개사명' -> '중개사무소명'
        
        Args:
            brokers: 중개사 정보 리스트
            filepath: 저장할 파일 경로
        """
        if not brokers:
            print("저장할 중개사 정보가 없습니다.")
            return
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        # 컬럼명 매핑: 중개사명 -> 중개사무소명
        renamed_brokers = []
        for broker in brokers:
            renamed_broker = {}
            for key, value in broker.items():
                if key == '중개사명':
                    renamed_broker['중개사무소명'] = value
                else:
                    renamed_broker[key] = value
            renamed_brokers.append(renamed_broker)
        
        # 모든 키 수집
        headers = set()
        for broker in renamed_brokers:
            headers.update(broker.keys())
        headers = sorted(headers)
        
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(renamed_brokers)
        
        print(f"CSV 파일 저장: {filepath} (총 {len(renamed_brokers)}건)")
    
    def get_statistics(self, brokers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        중개사 정보 통계 생성
        
        Args:
            brokers: 중개사 정보 리스트
            
        Returns:
            통계 정보
        """
        stats = {
            "총_중개사_수": len(brokers),
            "필드_채워진_비율": {}
        }
        
        # 필드별 채워진 비율
        if brokers:
            all_fields = set()
            for broker in brokers:
                all_fields.update(broker.keys())
            
            for field in all_fields:
                filled_count = sum(1 for broker in brokers if broker.get(field))
                stats["필드_채워진_비율"][field] = f"{filled_count}/{len(brokers)} ({filled_count/len(brokers)*100:.1f}%)"
        
        return stats


def main():
    """메인 실행 함수"""
    try:
        # 중개사 정보 추출기 생성
        extractor = LandBrokerExtractor()
        
        # 모든 중개사 정보 추출
        all_brokers = extractor.extract_all_brokers()
        
        if not all_brokers:
            print("\n추출된 중개사 정보가 없습니다.")
            print("중개사_정보 필드가 비어있거나 데이터가 없는 것으로 보입니다.")
            return
        
        # 중복 제거
        unique_brokers = extractor.remove_duplicates(all_brokers)
        
        # 파일 저장
        csv_filepath = "data/brokerInfo/land_brokers.csv"
        extractor.save_to_csv(unique_brokers, csv_filepath)
        
        # 통계 출력
        stats = extractor.get_statistics(unique_brokers)
        print("\n=== 통계 정보 ===")
        print(f"총 중개사 수: {stats['총_중개사_수']}건")
        
        print("\n[필드 채워진 비율]")
        for field, ratio in sorted(stats["필드_채워진_비율"].items()):
            print(f"  {field}: {ratio}")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
