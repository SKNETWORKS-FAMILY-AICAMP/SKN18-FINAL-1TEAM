import urllib.request
import urllib.parse
import json
import time
import csv
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


def fetch_broker_offices(key, domain, ld_code=None, status_code="1", format_type="json"):
    """
    부동산 중개사무소 정보를 전체 조회
    
    Args:
        key: VWorld API 인증키
        domain: 도메인
        ld_code: 시군구코드 (선택, 없으면 전국)
        status_code: 상태구분코드 (1:영업중, 2:휴업, 3:휴업연정, 4:실효, 5:폐업, 6:전출, 7:등록취소, 8:업무정지)
        format_type: 응답 형식 (json 또는 xml)
    
    Returns:
        list: 전체 중개사무소 정보 리스트
    """
    url = "http://api.vworld.kr/ned/data/getEBOfficeInfo"
    all_data = []
    page_no = 1
    num_of_rows = 1000  # 최대 1000건씩 조회
    
    while True:
        params = {
            "key": key,
            "domain": domain,
            "format": format_type,
            "numOfRows": str(num_of_rows),
            "pageNo": str(page_no)
        }
        
        # 선택적 파라미터 추가
        if ld_code:
            params["ldCode"] = ld_code
        if status_code:
            params["sttusSeCode"] = status_code
        
        query_string = "?" + urllib.parse.urlencode(params)
        
        try:
            request = urllib.request.Request(url + query_string)
            request.get_method = lambda: "GET"
            response_body = urllib.request.urlopen(request).read()
            
            if format_type == "json":
                data = json.loads(response_body.decode('utf-8'))
                
                # 응답 구조 확인 및 데이터 추출
                # 실제 API 응답 구조: {"EDOffices": {"field": [...]}}
                if 'EDOffices' in data and 'field' in data['EDOffices']:
                    items = data['EDOffices']['field']
                    total_count = len(items) if items else 0
                    
                    if not items:
                        print(f"페이지 {page_no}: 더 이상 데이터가 없습니다.")
                        break
                    
                    all_data.extend(items)
                    print(f"페이지 {page_no}: {len(items)}건 조회 완료 (총 {len(all_data)}건 / 전체 {total_count}건)")
                    
                    # 마지막 페이지 확인
                    if len(items) < num_of_rows:
                        break
                    
                    page_no += 1
                    time.sleep(0.1)  # API 호출 간격 조절
                else:
                    print("응답 데이터 구조 확인 필요:", data)
                    break
            else:
                # XML 형식인 경우
                print(response_body.decode('utf-8'))
                break
                
        except Exception as e:
            print(f"오류 발생 (페이지 {page_no}): {e}")
            break
    
    return all_data


def main():
    """메인 실행 함수"""
    # 환경 변수에서 API 키와 도메인 가져오기
    API_KEY = os.getenv("VWORLD_API_KEY")
    DOMAIN = os.getenv("VWORLD_DOMAIN")
    
    if not API_KEY or not DOMAIN:
        raise ValueError("환경 변수 VWORLD_API_KEY와 VWORLD_DOMAIN을 .env 파일에 설정해주세요.")
    
    print(f"API 키 로드 완료: {API_KEY[:10]}...")
    print(f"도메인: {DOMAIN}")

    
    # 서울특별시 데이터 조회
    # 서울특별시 시군구 코드 목록
    seoul_codes = [
        "11110",  # 종로구
        "11140",  # 중구
        "11170",  # 용산구
        "11200",  # 성동구
        "11215",  # 광진구
        "11230",  # 동대문구
        "11260",  # 중랑구
        "11290",  # 성북구
        "11305",  # 강북구
        "11320",  # 도봉구
        "11350",  # 노원구
        "11380",  # 은평구
        "11410",  # 서대문구
        "11440",  # 마포구
        "11470",  # 양천구
        "11500",  # 강서구
        "11530",  # 구로구
        "11545",  # 금천구
        "11560",  # 영등포구
        "11590",  # 동작구
        "11620",  # 관악구
        "11650",  # 서초구
        "11680",  # 강남구
        "11710",  # 송파구
        "11740",  # 강동구
    ]
    
    broker_offices = []
    
    # 각 구별로 데이터 조회
    for ld_code in seoul_codes:
        print(f"\n{'='*50}")
        print(f"시군구 코드 {ld_code} 조회 중...")
        print(f"{'='*50}")
        
        offices = fetch_broker_offices(
            key=API_KEY,
            domain=DOMAIN,
            ld_code=ld_code,  # 서울특별시 각 구 코드
            status_code="1"  # 영업중인 곳만
        )
        
        broker_offices.extend(offices)
        print(f"누적 조회: {len(broker_offices)}건")
        time.sleep(0.5)  # 구별 조회 간 대기
    
    print(f"\n{'='*50}")
    print(f"총 {len(broker_offices)}건의 서울특별시 중개사무소 정보 조회 완료")
    print(f"{'='*50}")
    
    # 결과를 CSV 파일로 저장
    if broker_offices:
        csv_filename = 'data/brokerInfo/broker_offices.csv'
        
        # CSV 헤더 추출 (첫 번째 항목의 키 사용)
        if len(broker_offices) > 0:
            fieldnames = list(broker_offices[0].keys())
            
            with open(csv_filename, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(broker_offices)
            
            print(f"{csv_filename} 파일로 저장 완료")


if __name__ == "__main__":
    main()
