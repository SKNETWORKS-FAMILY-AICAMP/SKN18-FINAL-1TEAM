from rest_framework import serializers
from .models import Land, LandBroker, PriceClassificationResult
from .utils.price_utils import (
    parse_korean_price,
    format_price_in_manwon,
    extract_deposit_from_deal_text,
    extract_monthly_rent_from_deal_text,
    get_price_display,
    extract_area_pyeong,
    extract_area_supply,
    extract_area_exclusive,
    extract_total_floors,
)
from .utils.temperature_utils import get_land_temperatures
import random


class BrokerSerializer(serializers.ModelSerializer):
    """중개업소 시리얼라이저"""
    id = serializers.IntegerField(source='landbroker_id')
    trust_grade = serializers.CharField(source='trust_grade_display', read_only=True)
    
    class Meta:
        model = LandBroker
        fields = [
            'id', 'office_name', 'representative', 'phone', 'address',
            'registration_number', 'trust_score', 'trust_grade',
            'trust_score_updated_at'
        ]


class PriceClassificationSerializer(serializers.ModelSerializer):
    """가격 분류 시리얼라이저 (영어 필드명)"""
    class Meta:
        model = PriceClassificationResult
        fields = [
            'predicted_class',
            'predicted_label',
            'predicted_label_kr',
            'underpriced_prob',
            'fair_prob',
            'overpriced_prob'
        ]


class LandSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='land_id')
    title = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    temperature = serializers.SerializerMethodField()
    deposit = serializers.SerializerMethodField()
    monthly_rent = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    region = serializers.CharField(source='address', allow_null=True, allow_blank=True)
    transaction_type = serializers.CharField(source='deal_type', allow_null=True, allow_blank=True)
    
    # Detail fields
    land_num = serializers.CharField()
    address = serializers.CharField(allow_null=True, allow_blank=True)
    building_type = serializers.CharField(allow_null=True, allow_blank=True)
    floor = serializers.SerializerMethodField()
    room_count = serializers.SerializerMethodField()
    area_supply = serializers.SerializerMethodField()
    area_exclusive = serializers.SerializerMethodField()
    direction = serializers.SerializerMethodField()
    parking = serializers.SerializerMethodField()
    move_in_date = serializers.SerializerMethodField()
    maintenance_fee = serializers.SerializerMethodField()
    heating_method = serializers.SerializerMethodField()
    elevator = serializers.SerializerMethodField()
    description = serializers.CharField(allow_null=True, allow_blank=True)
    approval_date = serializers.SerializerMethodField()  # 사용승인일
    additional_options = serializers.CharField(allow_null=True, allow_blank=True)
    jeonse_loan = serializers.SerializerMethodField()  # 전세자금대출
    move_in_report = serializers.SerializerMethodField()  # 전입신고
    
    # 중개업소 정보
    broker = BrokerSerializer(source='landbroker', read_only=True)
    
    # 가격 분류 정보
    price_prediction = serializers.SerializerMethodField()
    
    # 부동산 온도 데이터
    temperatures = serializers.SerializerMethodField()

    
    # listing_info (시설 정보)
    listing_info = serializers.JSONField(read_only=True)
    
    # 스타일 태그
    style_tags = serializers.SerializerMethodField()

    class Meta:
        model = Land
        fields = [
            'id', 
            'title', 
            'image', 
            'images',
            'temperature', 
            'deposit', 
            'monthly_rent', 
            'price',
            'region',
            'transaction_type',
            'building_type',
            'land_num',
            'address',
            'floor',
            'room_count',
            'area_supply',
            'area_exclusive',
            'direction',
            'parking',
            'move_in_date',
            'maintenance_fee',
            'heating_method',
            'elevator',
            'description',
            'approval_date',
            'additional_options',
            'jeonse_loan',
            'move_in_report',
            'broker',
            'price_prediction',
            'temperatures',
            'listing_info',
            'style_tags'
        ]

    def get_title(self, obj):
        """매물 제목 생성"""
        if obj.listing_info and isinstance(obj.listing_info, dict):
            building_form = obj.listing_info.get('건물형태', obj.building_type)
            area = obj.listing_info.get('전용/공급면적', '')
            if area:
                # 사전 컴파일된 정규식 사용
                pyeong = extract_area_pyeong(area)
                if pyeong:
                    area = pyeong
            return f"{building_form} {area}".strip() or obj.land_num
        return obj.land_num

    def get_image(self, obj):
        """첫 번째 이미지 반환"""
        if obj.images and isinstance(obj.images, list) and len(obj.images) > 0:
            return obj.images[0]
        return None

    def get_images(self, obj):
        """모든 이미지 반환"""
        if obj.images and isinstance(obj.images, list) and len(obj.images) > 0:
            return obj.images
        return []

    def get_temperature(self, obj):
        """부동산 온도 (임시로 랜덤 값, 추후 실제 계산 로직으로 대체)"""
        # TODO: 실제 온도 계산 로직 구현
        return round(random.uniform(30.0, 45.0), 1)

    def get_deposit(self, obj):
        """보증금 추출 - price_utils 사용"""
        deal_text = ''
        if obj.trade_info and isinstance(obj.trade_info, dict):
            deal_text = obj.trade_info.get('거래방식', '')
        
        return extract_deposit_from_deal_text(deal_text, obj.deal_type or '')

    def get_monthly_rent(self, obj):
        """월세 추출 - price_utils 사용"""
        deal_text = ''
        if obj.trade_info and isinstance(obj.trade_info, dict):
            deal_text = obj.trade_info.get('거래방식', '')
        
        return extract_monthly_rent_from_deal_text(deal_text, obj.deal_type or '')

    def get_price(self, obj):
        """가격 포맷팅 (만원 단위) - price_utils 사용"""
        return get_price_display(obj)

    def _get_listing_info_field(self, obj, field_name):
        """listing_info에서 필드 추출"""
        if obj.listing_info and isinstance(obj.listing_info, dict):
            return obj.listing_info.get(field_name, '-')
        return '-'

    def get_floor(self, obj):
        """층수 정보"""
        return self._get_listing_info_field(obj, '해당층/전체층')
    
    def get_room_count(self, obj):
        """방/욕실 개수"""
        return self._get_listing_info_field(obj, '방/욕실개수')
    
    def get_area_supply(self, obj):
        """공급면적 - price_utils 사용"""
        area = self._get_listing_info_field(obj, '전용/공급면적')
        return extract_area_supply(area)
    
    def get_area_exclusive(self, obj):
        """전용면적 - price_utils 사용"""
        area = self._get_listing_info_field(obj, '전용/공급면적')
        return extract_area_exclusive(area)
    
    def get_direction(self, obj):
        """방향"""
        return self._get_listing_info_field(obj, '주실기준/방향')
    
    def get_parking(self, obj):
        """주차 정보"""
        return self._get_listing_info_field(obj, '주차')
    
    def get_move_in_date(self, obj):
        """입주가능일"""
        if obj.trade_info and isinstance(obj.trade_info, dict):
            return obj.trade_info.get('입주가능일', '-')
        return '-'
    
    def get_maintenance_fee(self, obj):
        """관리비"""
        if obj.trade_info and isinstance(obj.trade_info, dict):
            return obj.trade_info.get('관리비', '-')
        return '-'
    
    def get_heating_method(self, obj):
        """난방방식"""
        return self._get_listing_info_field(obj, '난방방식')
    
    def get_elevator(self, obj):
        """엘리베이터 (층수 정보에서 유추) - price_utils 사용"""
        floor_info = self._get_listing_info_field(obj, '해당층/전체층')
        total_floors = extract_total_floors(floor_info)
        if total_floors is not None:
            return '있음' if total_floors >= 5 else '없음'
        return '-'
    
    def get_approval_date(self, obj):
        """사용승인일 (listing_info에서 추출)"""
        if obj.listing_info and isinstance(obj.listing_info, dict):
            return obj.listing_info.get('사용승인일', '-')
        return '-'
    
    def get_jeonse_loan(self, obj):
        """전세자금대출 (trade_info에서 추출)"""
        if obj.trade_info and isinstance(obj.trade_info, dict):
            return obj.trade_info.get('전세자금대출', '-')
        return '-'
    
    def get_move_in_report(self, obj):
        """전입신고 (listing_info에서 추출)"""
        if obj.listing_info and isinstance(obj.listing_info, dict):
            # listing_info에서 직접 확인 (최상위 레벨)
            value = obj.listing_info.get('전입신고 여부', '')
            if value and value != '-':
                return value
        return '-'
    
    def get_price_prediction(self, obj):
        """가격 분류 정보 조회 (외래키 기반)"""
        # context에 캐시된 price_predictions 사용 (N+1 쿼리 방지)
        price_cache = self.context.get('price_predictions')
        
        if price_cache is not None:
            # 캐시에서 조회
            price_class = price_cache.get(obj.land_num)
            if price_class:
                return {
                    'predicted_class': price_class.predicted_class,
                    'predicted_label': price_class.predicted_label,
                    'predicted_label_kr': price_class.predicted_label_kr,
                    'underpriced_prob': price_class.underpriced_prob,
                    'fair_prob': price_class.fair_prob,
                    'overpriced_prob': price_class.overpriced_prob
                }
            return None
        
        # 캐시가 없으면 외래키 역참조 사용 (폴백)
        try:
            # land.price_predictions는 related_name으로 역참조 가능
            price_class = obj.price_predictions.first()
            if price_class:
                return PriceClassificationSerializer(price_class).data
        except Exception as e:
            print(f"Error fetching price classification: {e}")
        return None
    
    
    def get_temperatures(self, obj):
        """Neo4j에서 부동산 온도 정보 조회"""
        return get_land_temperatures(obj.land_num)
    
    def get_style_tags(self, obj):
        """스타일 태그 반환 (쉼표 구분 문자열 → 리스트)"""
        if obj.style_tags:
            return [tag.strip() for tag in obj.style_tags.split(',') if tag.strip()]
        return []

