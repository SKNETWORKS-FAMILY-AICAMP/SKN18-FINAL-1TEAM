export interface Land {
    id: number;
    title: string;
    image?: string;
    images?: string[];
    temperature: number;
    deposit: number;
    monthly_rent: number;
    price: string; // Formatted price from backend
    deal_type?: string; // 거래 유형 (월세, 전세 등)
    region?: string;
    transaction_type?: string;
    building_type?: string;
    land_num?: string;
    address?: string;
    floor?: string;
    room_count?: string;
    area_supply?: string;
    area_exclusive?: string;
    direction?: string;
    parking?: string;
    move_in_date?: string;
    maintenance_fee?: string;
    heating_method?: string;
    elevator?: string;
    description?: string;
    additional_options?: string | string[];
    listing_info?: {
        난방방식?: string[];
        냉방시설?: string[];
        생활시설?: string[];
        보안시설?: string[];
        기타시설?: string[];
        방거실형태?: string;
    };
    jeonse_loan?: string;        // 전세자금대출
    move_in_report?: string;     // 전입신고 여부
    approval_date?: string;      // 사용승인일
    trade_info?: any;            // 거래 정보 JSON

    // 스타일 태그
    style_tags?: string[];

    // 가격 예측 정보
    price_prediction?: {
        predicted_class: number;
        predicted_label: string;
        predicted_label_kr: string;
        underpriced_prob: number;
        fair_prob: number;
        overpriced_prob: number;
    };

    // 부동산 온도 데이터
    temperatures?: {
        safety: number;
        convenience: number;
        pet?: number;
        traffic?: number;
        culture?: number;
        pet_details?: {
            playground: number;
            hospital: number;
            park: number;
            etc: number;
        };
    };

    // 중개업소 정보 (agent_info 대신 broker 사용)
    broker?: {
        id: number;
        office_name?: string;
        representative?: string;
        phone?: string;
        address?: string;
        registration_number?: string;
        trust_score?: 'A' | 'B' | 'C' | null;
        trust_grade?: string;
        trust_score_updated_at?: string | null;
    };
}

export interface LandFilterParams {
    region?: string;
    dong?: string;
    transaction_type?: string;
    building_type?: string;
    search?: string;
}
