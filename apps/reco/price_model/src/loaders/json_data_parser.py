"""
JSON 데이터 파싱 모듈
JSON 파일을 로드하고 모델 입력 형식으로 변환
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
import numpy as np


class JSONDataParser:
    """JSON 데이터를 DataFrame으로 변환하는 파서"""
    
    def __init__(self):
        self.required_fields = [
            "매물번호", "매물_URL", "주소_정보", "거래_정보", "매물_정보"
        ]
        
        # 파일명 기반 건물용도 매핑
        self.filename_to_building_type = {
            # 아파트
            "아파트": "아파트",
            
            # 오피스텔
            "오피스텔": "오피스텔",
            
            # 연립다세대 (원룸, 투룸, 빌라, 연립, 다세대, 단독 등),
            "원룸": "연립다세대",
            "투룸": "연립다세대",
            "원투룸": "연립다세대",
            "빌라": "연립다세대",
            "연립": "연립다세대",
            "다세대": "연립다세대",
            "단독": "연립다세대",
        }
    
    def load_json_files(self, json_dir: str) -> List[Dict]:
        """
        JSON 파일들을 로드
        
        Args:
            json_dir: JSON 파일이 있는 디렉토리
            
        Returns:
            모든 JSON 데이터를 합친 리스트
        """
        json_path = Path(json_dir)
        all_data = []
        
        # 모든 JSON 파일 로드
        for json_file in json_path.glob("*.json"):
            print(f"📂 로딩: {json_file.name}")
            filename = json_file.stem  # 확장자 제외한 파일명
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    # 각 아이템에 파일명 정보 추가
                    for item in data:
                        item['_source_filename'] = filename
                    all_data.extend(data)
                else:
                    data['_source_filename'] = filename
                    all_data.append(data)
        
        print(f"✅ 총 {len(all_data)}개 매물 로드 완료")
        return all_data
    
    def filter_monthly_rent(self, data: List[Dict]) -> List[Dict]:
        """
        월세 매물만 필터링
        
        Args:
            data: 전체 매물 데이터
            
        Returns:
            월세 매물만 포함된 리스트
        """
        monthly_rent = []
        for item in data:
            거래_정보 = item.get("거래_정보", {})
            거래유형 = 거래_정보.get("거래유형", "")
            월세값 = 거래_정보.get("월세", "")
            
            if ("월세" in 거래유형) and (월세값 not in ["", "-", None]):
                monthly_rent.append(item)

        print(f">> 월세 매물: {len(monthly_rent)}개")
        return monthly_rent
    
    def parse_address(self, address: str) -> Dict[str, str]:
        """
        주소에서 자치구명과 법정동명 추출
        
        Args:
            address: 전체 주소
            
        Returns:
            {"자치구명": "강남구", "법정동명": "역삼동"}
        """
        # 서울시 자치구 리스트
        gu_list = [
            "강남구", "강동구", "강북구", "강서구", "관악구",
            "광진구", "구로구", "금천구", "노원구", "도봉구",
            "동대문구", "동작구", "마포구", "서대문구", "서초구",
            "성동구", "성북구", "송파구", "양천구", "영등포구",
            "용산구", "은평구", "종로구", "중구", "중랑구"
        ]
        
        자치구명 = None
        법정동명 = None
        
        # 자치구 찾기
        for gu in gu_list:
            if gu in address:
                자치구명 = gu
                break
        
        # 법정동 찾기 (자치구 뒤에 오는 동/로/가)
        if 자치구명:
            # 자치구 이후 부분 추출
            parts = address.split(자치구명)
            if len(parts) > 1:
                after_gu = parts[1].strip()
                # 동/로/가로 끝나는 첫 번째 단어 찾기
                match = re.search(r'([^\s]+(?:동|로|가))', after_gu)
                if match:
                    법정동명 = match.group(1)
        
        return {
            "자치구명": 자치구명 or "알수없음",
            "법정동명": 법정동명 or "알수없음"
        }
    
    def parse_area(self, area_str: str) -> Optional[float]:
        """
        면적 문자열에서 전용면적 추출 (m²)
        
        Args:
            area_str: "21.95m²(공급 31.95m²)" 형식
            
        Returns:
            전용면적 (float) 또는 None
        """
        if not area_str:
            return None
        
        # 전용면적 추출 (첫 번째 숫자)
        match = re.search(r'([\d.]+)\s*m', area_str)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None
    
    def parse_floor(self, floor_str: str) -> Optional[int]:
        """
        층수 문자열에서 해당층 추출
        
        Args:
            floor_str: "중층(총 9층)" 또는 "지하1층" 형식
            
        Returns:
            층수 (int) 또는 None
            - 지하/반지하: -1
            - 지상층: 양수
        """
        if not floor_str:
            return None
        
        # 지하/반지하 처리 (최우선)
        if "지하" in floor_str or "반지하" in floor_str or "B" in floor_str.upper():
            return -1
        
        # 문자형 층수 매핑 ("저층", "중층", "고층")
        floor_mapping = {
            "저층": 2,
            "중층": 5,
            "중고층": 8,
            "고층": 12
        }
        
        for key, value in floor_mapping.items():
            if key in floor_str:
                return value
        
        # 숫자가 있으면 추출 ("3층(총 9층)" 형식)
        match = re.search(r'(\d+)\s*층', floor_str)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        
        return 5  # 기본값: 중층
    
    def parse_year(self, year_str: str) -> Optional[int]:
        """
        건축년도 추출 -> 사용승인일
        
        Args:
            year_str: "2013" 또는 "2013년" 형식
            
        Returns:
            건축년도 (int) 또는 None
        """
        if not year_str:
            return None
        
        match = re.search(r'(\d{4})', str(year_str))
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None
    
    def parse_building_type(self, building_type: str, filename: str = None) -> str:
        """
        건물용도 정규화 (파일명 기반 우선, 건물용도 문자열 보조)
        
        CSV 학습 데이터는 3가지 카테고리만 존재:
        - 아파트: 공동주택 중 5개 층 이상
        - 연립다세대: 연립주택 + 다세대주택 + 다가구주택 + 단독주택
        - 오피스텔: 준주택 (업무시설)
        
        Args:
            building_type: 원본 건축물용도
            filename: JSON 파일명 (확장자 제외)
            
        Returns:
            정규화된 건물용도 ("아파트", "연립다세대", "오피스텔" 중 하나)
        """
        # 1. 파일명 기반 매핑 (최우선)
        if filename:
            filename_lower = filename.lower()
            
            # 파일명에서 키워드 찾기
            for keyword, mapped_type in self.filename_to_building_type.items():
                if keyword in filename_lower:
                    return mapped_type
        
        # 2. 건물용도 문자열 기반 매핑 (보조)
        if not building_type:
            return "연립다세대"  # 기본값
        
        # 대소문자 구분 없이 매칭하기 위해 소문자로 변환
        building_type_lower = building_type.lower()
        
        # 아파트 (공동주택 중 아파트)
        if "아파트" in building_type_lower:
            return "아파트"
        
        # 오피스텔 (준주택, 업무시설)
        if "오피스텔" in building_type_lower or "업무시설" in building_type_lower:
            return "오피스텔"
        
        # 연립다세대 (나머지 모든 주거용 건물)
        # - 공동주택 (아파트 제외): 연립주택, 다세대주택, 다가구주택
        # - 단독주택: 단독주택, 다중주택
        # - 원룸/투룸/빌라 등
        # - 근린생활시설, 숙박시설 등 (주거 목적으로 사용되는 경우)
        return "연립다세대"
    
    def parse_price(self, price_str: str) -> Optional[float]:
        """
        가격 문자열을 만원 단위로 변환
        
        Args:
            price_str: "2억 8,000만원" 또는 "50만원" 형식
            
        Returns:
            만원 단위 가격 (float) 또는 None
        """
        if not price_str or price_str == "-":
            return 0.0
        
        try:
            # 억, 만원 파싱
            억 = 0
            만 = 0
            
            # 억 추출
            억_match = re.search(r'([\d,]+)\s*억', price_str)
            if 억_match:
                억 = float(억_match.group(1).replace(',', ''))
            
            # 만원 추출
            만_match = re.search(r'([\d,]+)\s*만', price_str)
            if 만_match:
                만 = float(만_match.group(1).replace(',', ''))
            
            # 만원 단위로 변환
            total = 억 * 10000 + 만
            return total
        except Exception:
            return None
    
    def convert_to_dataframe(self, data: List[Dict]) -> pd.DataFrame:
        """
        JSON 데이터를 DataFrame으로 변환
        
        Args:
            data: 월세 매물 데이터
            
        Returns:
            DataFrame
        """
        records = []
        
        for item in data:
            try:
                # 기본 정보
                매물번호 = item.get("매물번호", "")
                매물_URL = item.get("매물_URL", "")
                
                # 주소 정보
                주소_정보 = item.get("주소_정보", {})
                전체주소 = 주소_정보.get("전체주소", "")
                주소_파싱 = self.parse_address(전체주소)
                
                # 거래 정보
                거래_정보 = item.get("거래_정보", {})
                보증금_str = 거래_정보.get("보증금", "0")
                월세_str = 거래_정보.get("월세", "0")
                
                보증금_만원 = self.parse_price(보증금_str)
                월세_만원 = self.parse_price(월세_str)
                
                # 매물 정보
                매물_정보 = item.get("매물_정보", {})
                면적_str = 매물_정보.get("전용/공급면적", "")
                층_str = 매물_정보.get("해당층/전체층", "")
                건축년도_str = 매물_정보.get("사용승인일", "")
                건물용도_str = 매물_정보.get("건축물용도", "")
                
                임대면적 = self.parse_area(면적_str)
                층 = self.parse_floor(층_str)
                건축년도 = self.parse_year(건축년도_str)
                
                # 파일명 정보 추출
                source_filename = item.get("_source_filename", None)
                
                # 파일명 기반 건물용도 매핑
                건물용도 = self.parse_building_type(건물용도_str, source_filename)
                
                # 필수 필드 검증
                if not all([임대면적, 보증금_만원 is not None, 월세_만원 is not None]):
                    continue

                if 임대면적 is None:
                    continue

                if 보증금_만원 is None:
                    continue

                if 월세_만원 is None:
                    월세_만원 = 0.0  # 파싱 실패하면 0으로 대체
                
                record = {
                    "매물번호": 매물번호,
                    "매물_URL": 매물_URL,
                    "전체주소": 전체주소,
                    "자치구명": 주소_파싱["자치구명"],
                    "법정동명": 주소_파싱["법정동명"],
                    "건물용도": 건물용도,
                    "보증금(만원)": 보증금_만원,
                    "임대료(만원)": 월세_만원,
                    "임대면적": 임대면적,
                    "층": 층 if 층 else 5,
                    "건축년도": 건축년도 if 건축년도 else 2010,
                }
                
                records.append(record)
                
            except Exception as e:
                print(f"⚠️  매물 {item.get('매물번호', 'unknown')} 파싱 실패: {e}")
                continue
        
        df = pd.DataFrame(records)
        print(f"✅ DataFrame 변환 완료: {len(df)}개 레코드")
        
        return df
    
    def load_and_parse(self, json_dir: str) -> pd.DataFrame:
        """
        JSON 파일을 로드하고 DataFrame으로 변환하는 전체 파이프라인
        
        Args:
            json_dir: JSON 파일 디렉토리
            
        Returns:
            변환된 DataFrame
        """
        print("\n" + "=" * 60)
        print("📊 JSON 데이터 로딩 및 파싱 시작")
        print("=" * 60)
        
        # 1. JSON 파일 로드
        all_data = self.load_json_files(json_dir)
        
        # 2. 월세 매물 필터링
        monthly_rent = self.filter_monthly_rent(all_data)
        
        # 3. DataFrame 변환
        df = self.convert_to_dataframe(monthly_rent)
        
        print("=" * 60)
        print(f"✅ 파싱 완료: {len(df)}개 월세 매물")
        print("=" * 60 + "\n")
        
        return df
