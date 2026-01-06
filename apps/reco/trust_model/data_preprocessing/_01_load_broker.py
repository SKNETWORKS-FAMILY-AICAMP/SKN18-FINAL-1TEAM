"""
VWorld API를 사용하여 부동산 중개업소 정보를 조회하는 모듈
"""
import os
import json
import csv
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


class VWorldBrokerAPI:
    """VWorld 부동산 중개업소 정보 API 클라이언트"""
    
    BASE_URL = "http://api.vworld.kr/ned/data/getEBBrokerInfo"
    
    def __init__(self, api_key: Optional[str] = None, domain: Optional[str] = None):
        """
        Args:
            api_key: VWorld API 인증키 (환경변수 VWORLD_API_KEY 사용 가능)
            domain: 도메인 (환경변수 VWORLD_DOMAIN 사용 가능)
        """
        self.api_key = api_key or os.getenv("VWORLD_API_KEY")
        self.domain = domain or os.getenv("VWORLD_DOMAIN", "http://localhost")
        
        if not self.api_key:
            raise ValueError("API 키가 필요합니다. 환경변수 VWORLD_API_KEY를 설정하거나 생성자에 전달하세요.")
    
    def get_broker_info(
        self,
        ld_code: str,
        bsnm_cmpnm: Optional[str] = None,
        brkr_nm: Optional[str] = None,
        jurirno: Optional[str] = None,
        format: str = "json",
        num_of_rows: int = 10,
        page_no: int = 1
    ) -> Dict[str, Any]:
        """
        부동산 중개업소 정보 조회
        
        Args:
            ld_code: 시군구코드 (2~5자리, 예: "11110")
            bsnm_cmpnm: 사업자상호 (선택)
            brkr_nm: 중개업자명 (선택)
            jurirno: 법인등록번호 (선택)
            format: 응답 형식 ("xml" 또는 "json")
            num_of_rows: 검색건수 (최대 1000)
            page_no: 페이지번호
            
        Returns:
            API 응답 데이터 (dict)
        """
        params = {
            "key": self.api_key,
            "domain": self.domain,
            "ldCode": ld_code,
            "format": format,
            "numOfRows": num_of_rows,
            "pageNo": page_no
        }
        
        # 선택적 파라미터 추가
        if bsnm_cmpnm:
            params["bsnmCmpnm"] = bsnm_cmpnm
        if brkr_nm:
            params["brkrNm"] = brkr_nm
        if jurirno:
            params["jurirno"] = jurirno
        
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            if format == "json":
                return response.json()
            else:
                return {"xml": response.text}
                
        except requests.exceptions.RequestException as e:
            print(f"API 호출 중 오류 발생: {e}")
            raise
    
    def get_all_brokers_by_region(
        self,
        ld_code: str,
        max_results: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        특정 지역의 모든 중개업소 정보를 페이징하여 조회
        
        Args:
            ld_code: 시군구코드
            max_results: 최대 조회 건수
            
        Returns:
            중개업소 정보 리스트
        """
        all_brokers = []
        page_no = 1
        num_of_rows = min(1000, max_results)
        
        while len(all_brokers) < max_results:
            result = self.get_broker_info(
                ld_code=ld_code,
                num_of_rows=num_of_rows,
                page_no=page_no
            )
            
            # VWorld API 응답 구조에 따라 데이터 추출
            items = []
            if "EDBrokers" in result:
                # EDBrokers.field 배열에서 데이터 추출
                items = result.get("EDBrokers", {}).get("field", [])
                total_count = int(result.get("EDBrokers", {}).get("totalCount", 0))
                
                if not items:
                    break
                
                all_brokers.extend(items)
                
                # 전체 데이터를 다 가져왔거나, 더 이상 데이터가 없으면 종료
                if len(all_brokers) >= total_count or len(items) < num_of_rows:
                    break
                
                page_no += 1
            else:
                break
        
        return all_brokers[:max_results]
    
    def save_to_json(self, data: List[Dict[str, Any]], filepath: str) -> None:
        """
        조회한 데이터를 JSON 파일로 저장
        
        Args:
            data: 저장할 데이터
            filepath: 저장할 파일 경로
        """
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"데이터가 {filepath}에 저장되었습니다. (총 {len(data)}건)")
    
    def save_to_csv(self, data: List[Dict[str, Any]], filepath: str) -> None:
        """
        조회한 데이터를 CSV 파일로 저장
        
        Args:
            data: 저장할 데이터
            filepath: 저장할 파일 경로
        """
        if not data:
            print("저장할 데이터가 없습니다.")
            return
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        # CSV 헤더 추출 (모든 키를 수집)
        headers = set()
        for row in data:
            headers.update(row.keys())
        headers = sorted(headers)
        
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)
        
        print(f"데이터가 {filepath}에 저장되었습니다. (총 {len(data)}건)")


# 서울시 전체 구 코드
SEOUL_DISTRICT_CODES = {
    "11110": "종로구",
    "11140": "중구",
    "11170": "용산구",
    "11200": "성동구",
    "11215": "광진구",
    "11230": "동대문구",
    "11260": "중랑구",
    "11290": "성북구",
    "11305": "강북구",
    "11320": "도봉구",
    "11350": "노원구",
    "11380": "은평구",
    "11410": "서대문구",
    "11440": "마포구",
    "11470": "양천구",
    "11500": "강서구",
    "11530": "구로구",
    "11545": "금천구",
    "11560": "영등포구",
    "11590": "동작구",
    "11620": "관악구",
    "11650": "서초구",
    "11680": "강남구",
    "11710": "송파구",
    "11740": "강동구",
}


def collect_seoul_brokers():
    """서울시 전체 중개업소 정보 수집"""
    api = VWorldBrokerAPI()
    all_brokers = []
    
    print("=== 서울시 전체 중개업소 정보 수집 시작 ===\n")
    
    for ld_code, district_name in SEOUL_DISTRICT_CODES.items():
        print(f"[{district_name}] 조회 중...")
        try:
            brokers = api.get_all_brokers_by_region(
                ld_code=ld_code,
                max_results=10000
            )
            
            all_brokers.extend(brokers)
            print(f"[{district_name}] {len(brokers)}건 수집 완료")
            
        except Exception as e:
            print(f"[{district_name}] 오류 발생: {e}")
            continue
    
    print(f"\n=== 총 {len(all_brokers)}건의 중개업소 정보 수집 완료 ===\n")
    
    if all_brokers:
        # CSV 파일로 저장
        csv_filepath = "data/brokerInfo/brokers.csv"
        api.save_to_csv(all_brokers, csv_filepath)
        
        print(f"\n서울시 전체 중개업소 정보가 저장되었습니다.")
        print(f"- CSV: {csv_filepath}")
    
    return all_brokers


def main():
    """사용 예시"""
    try:
        # 서울시 전체 중개업소 정보 수집
        brokers = collect_seoul_brokers()
        
    except Exception as e:
        print(f"오류 발생: {e}")


if __name__ == "__main__":
    main()
