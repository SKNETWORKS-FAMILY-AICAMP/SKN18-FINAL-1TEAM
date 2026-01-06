// apps/frontend/src/components/LandListFilter.tsx
'use client';

import { useRef, useState, useEffect } from 'react';
import { LandFilterParams } from '@/api/landApi';
// import { SEOUL_DISTRICTS, DONG_MAP } from '@/common/data/Region'; // 모듈 없음으로 인해 로컬 정의로 대체

const SEOUL_DISTRICTS = [
    '강남구', '강동구', '강북구', '강서구', '관악구',
    '광진구', '구로구', '금천구', '노원구', '도봉구',
    '동대문구', '동작구', '마포구', '서대문구', '서초구',
    '성동구', '성북구', '송파구', '양천구', '영등포구',
    '용산구', '은평구', '종로구', '중구', '중랑구'
];

const DONG_MAP: { [key: string]: string[] } = {
    '강남구': ['역삼동', '개포동', '청담동', '삼성동', '대치동', '신사동', '논현동', '압구정동', '세곡동', '자곡동', '율현동', '일원동', '수서동', '도곡동'],
    '강동구': ['명일동', '고덕동', '상일동', '길동', '둔촌동', '암사동', '성내동', '천호동', '강일동'],
    '강북구': ['미아동', '번동', '수유동', '우이동'],
    '강서구': ['염창동', '등촌동', '화곡동', '가양동', '마곡동', '내발산동', '외발산동', '공항동', '방화동', '개화동', '과해동', '오곡동', '오쇠동'],
    '관악구': ['봉천동', '신림동', '남현동'],
    '광진구': ['중곡동', '능동', '구의동', '광장동', '자양동', '화양동', '군자동'],
    '구로구': ['신도림동', '구로동', '가리봉동', '고척동', '개봉동', '오류동', '궁동', '온수동', '천왕동', '항동'],
    '금천구': ['가산동', '독산동', '시흥동'],
    '노원구': ['월계동', '공릉동', '하계동', '상계동', '중계동'],
    '도봉구': ['쌍문동', '방학동', '창동', '도봉동'],
    '동대문구': ['신설동', '용두동', '제기동', '전농동', '답십리동', '장안동', '청량리동', '회기동', '휘경동', '이문동'],
    '동작구': ['노량진동', '상도동', '상도1동', '본동', '흑석동', '동작동', '사당동', '대방동', '신대방동'],
    '마포구': ['아현동', '공덕동', '신공덕동', '도화동', '용강동', '토정동', '마포동', '대흥동', '염리동', '노고산동', '신수동', '현석동', '구수동', '창전동', '상수동', '하중동', '신정동', '당인동', '서교동', '동교동', '합정동', '망원동', '연남동', '성산동', '중동', '상암동'],
    '서대문구': ['충정로', '합동', '미근동', '냉천동', '천연동', '옥천동', '영천동', '현저동', '북아현동', '홍제동', '대현동', '대신동', '신촌동', '봉원동', '창천동', '연희동', '홍은동', '북가좌동', '남가좌동', '충현동'],
    '서초구': ['방배동', '양재동', '우면동', '원지동', '잠원동', '반포동', '서초동', '내곡동', '염곡동', '신원동'],
    '성동구': ['상왕십리동', '하왕십리동', '홍익동', '도선동', '마장동', '사근동', '행당동', '응봉동', '금호동', '옥수동', '성수동', '송정동', '용답동'],
    '성북구': ['성북동', '돈암동', '동소문동', '삼선동', '동선동', '안암동', '보문동', '정릉동', '길음동', '종암동', '하월곡동', '상월곡동', '장위동', '석관동'],
    '송파구': ['잠실동', '신천동', '풍납동', '송파동', '석촌동', '삼전동', '가락동', '문정동', '장지동', '방이동', '오금동', '거여동', '마천동'],
    '양천구': ['목동', '신월동', '신정동'],
    '영등포구': ['영등포동', '여의도동', '당산동', '도림동', '문래동', '양평동', '양화동', '신길동', '대림동'],
    '용산구': ['후암동', '용산동', '갈월동', '남영동', '동자동', '서계동', '청파동', '원효로', '신창동', '산천동', '청암동', '효창동', '도원동', '용문동', '문배동', '신계동', '한강로', '이촌동', '이태원동', '한남동', '동빙고동', '서빙고동', '주성동', '보광동'],
    '은평구': ['수색동', '녹번동', '불광동', '갈현동', '구산동', '대조동', '응암동', '역촌동', '신사동', '증산동', '진관동'],
    '종로구': ['청운동', '신교동', '궁정동', '효자동', '창성동', '통의동', '적선동', '통인동', '누상동', '누하동', '옥인동', '체부동', '필운동', '내자동', '사직동', '도렴동', '당주동', '내수동', '세종로', '신문로', '청진동', '서린동', '수송동', '중학동', '종로', '공평동', '관훈동', '견지동', '와룡동', '권농동', '운니동', '익선동', '경운동', '관철동', '인사동', '낙원동', '팔판동', '삼청동', '안국동', '소격동', '화동', '사간동', '송현동', '가회동', '재동', '계동', '원서동', '훈정동', '묘동', '봉익동', '돈의동', '장사동', '관수동', '인의동', '예지동', '원남동', '연지동', '효제동', '이화동', '연건동', '충신동', '동숭동', '혜화동', '명륜', '창신동', '숭인동', '교남동', '평동', '송월동', '홍파동', '교북동', '행촌동', '구기동', '평창동', '부암동', '홍지동', '신영동', '무악동'],
    '중구': ['무교동', '다동', '태평로', '을지로', '남대문로', '삼각동', '수하동', '장교동', '수표동', '소공동', '남창동', '북창동', '봉래동', '회현동', '충무로', '명동', '남산동', '저동', '예관동', '묵정동', '필동', '남학동', '주자동', '예장동', '장충동', '광희동', '쌍림동', '의주로', '충정로', '중림동', '만리동', '흥인동', '무학동', '황학동', '신당동'],
    '중랑구': ['면목동', '상봉동', '중화동', '묵동', '망우동', '신내동']
};

const INITIAL_FILTER: LandFilterParams = {
    selectedRegion: '',
    selectedDong: '',
    selectedTransaction: '',
    selectedBuilding: ''
};

const TRANSACTION_OPTIONS = ['매매', '전세', '월세', '단기임대'];
const BUILDING_OPTIONS = ['아파트', '오피스텔', '빌라주택', '원투룸'];

interface FilterInfo {
    summary: string
    details: {
        location?: string
        facilities?: string[]
        deal_type?: string
        building_type?: string
        max_deposit?: string
        max_rent?: string
        style?: string[]
    }
    search_strategy?: string
}

interface LandListFilterProps {
    onFilterChange?: (params: LandFilterParams) => void;
    chatbotFilterInfo?: FilterInfo | null;
    onToggleChatbotFilter?: () => void;
}

// sessionStorage에서 필터 값 로드
const loadFilterFromStorage = () => {
    if (typeof window === 'undefined') return null;
    try {
        const saved = sessionStorage.getItem('landListFilter');
        return saved ? JSON.parse(saved) : null;
    } catch {
        return null;
    }
};

export default function LandListFilter({ onFilterChange, chatbotFilterInfo, onToggleChatbotFilter }: LandListFilterProps) {
    // SSR과 클라이언트 일치를 위해 초기값은 고정값 사용
    const [selectedRegion, setSelectedRegion] = useState<string>(INITIAL_FILTER.selectedRegion);
    const [selectedDong, setSelectedDong] = useState<string>(INITIAL_FILTER.selectedDong);
    const [selectedTransaction, setSelectedTransaction] = useState<string>(INITIAL_FILTER.selectedTransaction);
    const [selectedBuilding, setSelectedBuilding] = useState<string>(INITIAL_FILTER.selectedBuilding);
    const [isMounted, setIsMounted] = useState(false);

    // 이전 자치구 값을 추적
    const prevRegionRef = useRef<string>(selectedRegion);

    // 마운트 후 sessionStorage에서 값 복원
    useEffect(() => {
        const savedFilter = loadFilterFromStorage();
        if (savedFilter) {
            setSelectedRegion(savedFilter.selectedRegion || '');
            setSelectedDong(savedFilter.selectedDong || '');
            setSelectedTransaction(savedFilter.selectedTransaction || '');
            setSelectedBuilding(savedFilter.selectedBuilding || '');
            prevRegionRef.current = savedFilter.selectedRegion || '';
        }
        setIsMounted(true);
    }, []);

    // 자치구가 변경되면 행정동을 초기화
    useEffect(() => {
        if (prevRegionRef.current !== selectedRegion) {
            setSelectedDong('');
            prevRegionRef.current = selectedRegion;
        }
    }, [selectedRegion]);

    // 필터 변경 시 상위 컴포넌트로 전달
    useEffect(() => {
        if (!isMounted) return;

        const params: LandFilterParams = {
            selectedRegion,
            selectedDong,
            selectedTransaction,
            selectedBuilding
        };

        // sessionStorage에 저장
        if (typeof window !== 'undefined') {
            sessionStorage.setItem('landListFilter', JSON.stringify(params));
        }

        onFilterChange?.(params);
    }, [selectedRegion, selectedDong, selectedTransaction, selectedBuilding, onFilterChange, isMounted]);

    const handleReset = () => {
        setSelectedRegion('');
        setSelectedDong('');
        setSelectedTransaction('');
        setSelectedBuilding('');

        // sessionStorage에서도 삭제
        if (typeof window !== 'undefined') {
            sessionStorage.removeItem('landListFilter');
        }
    };

    const dongList = selectedRegion ? (DONG_MAP[selectedRegion] || []) : [];

    return (
        <div className="bg-white border border-[var(--color-border-light)] rounded-xl p-6 shadow-[var(--shadow-md)]">
            {/* 헤더 */}
            <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-[var(--color-primary)]">
                    매물 필터
                </h3>
                <div className="flex items-center gap-2">
                    {/* 챗봇 필터 토글 버튼 - 비활성/대기 상태 */}
                    <button
                        onClick={onToggleChatbotFilter}
                        disabled={!chatbotFilterInfo}
                        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${chatbotFilterInfo
                            ? 'text-purple-600 border border-purple-300 hover:bg-purple-50'
                            : 'text-gray-400 border border-gray-200 cursor-not-allowed opacity-50'
                            }`}
                    >
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M2 2h12M4 6h8M6 10h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                        </svg>
                        🤖 챗봇 필터
                    </button>

                    {/* 초기화 버튼 */}
                    <button
                        onClick={handleReset}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-600 border border-red-300 rounded-lg hover:bg-red-50 hover:border-red-400 transition-colors"
                    >
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M14 8C14 11.3137 11.3137 14 8 14C4.68629 14 2 11.3137 2 8C2 4.68629 4.68629 2 8 2C11.3137 2 14 4.68629 14 8Z" stroke="currentColor" strokeWidth="1.5" />
                            <path d="M10 6L6 10M6 6L10 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                        </svg>
                        초기화
                    </button>
                </div>
            </div>

            {/* 일반 필터 UI */}
            <div className="flex items-end gap-4">
                {/* 자치구 선택 */}
                <div className="flex-1 space-y-2">
                    <label className="block text-sm font-medium text-[var(--color-text-secondary)]">
                        자치구
                    </label>
                    <select
                        value={selectedRegion}
                        onChange={(e) => setSelectedRegion(e.target.value)}
                        className="w-full px-4 py-2.5 border border-[var(--color-border)] rounded-lg text-sm text-[var(--color-text-primary)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent transition-all"
                    >
                        <option value="">전체</option>
                        {SEOUL_DISTRICTS.map((district) => (
                            <option key={district} value={district}>
                                {district}
                            </option>
                        ))}
                    </select>
                </div>

                {/* 행정동 선택 */}
                <div className="flex-1 space-y-2">
                    <label className="block text-sm font-medium text-[var(--color-text-secondary)]">
                        행정동
                    </label>
                    <select
                        value={selectedDong}
                        onChange={(e) => setSelectedDong(e.target.value)}
                        disabled={!selectedRegion || dongList.length === 0}
                        className="w-full px-4 py-2.5 border border-[var(--color-border)] rounded-lg text-sm text-[var(--color-text-primary)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent disabled:bg-[var(--color-bg-secondary)] disabled:cursor-not-allowed transition-all"
                    >
                        <option value="">
                            {selectedRegion ? '전체' : '선택'}
                        </option>
                        {dongList.map((dong) => (
                            <option key={dong} value={dong}>
                                {dong}
                            </option>
                        ))}
                    </select>
                </div>

                {/* 거래유형 드롭다운 */}
                <div className="flex-1 space-y-2">
                    <label className="block text-sm font-medium text-[var(--color-text-secondary)]">
                        거래유형
                    </label>
                    <select
                        value={selectedTransaction}
                        onChange={(e) => setSelectedTransaction(e.target.value)}
                        className="w-full px-4 py-2.5 border border-[var(--color-border)] rounded-lg text-sm text-[var(--color-text-primary)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent transition-all"
                    >
                        <option value="">전체</option>
                        {TRANSACTION_OPTIONS.map((option) => (
                            <option key={option} value={option}>
                                {option}
                            </option>
                        ))}
                    </select>
                </div>

                {/* 건물용도 드롭다운 */}
                <div className="flex-1 space-y-2">
                    <label className="block text-sm font-medium text-[var(--color-text-secondary)]">
                        건물용도
                    </label>
                    <select
                        value={selectedBuilding}
                        onChange={(e) => setSelectedBuilding(e.target.value)}
                        className="w-full px-4 py-2.5 border border-[var(--color-border)] rounded-lg text-sm text-[var(--color-text-primary)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent transition-all"
                    >
                        <option value="">전체</option>
                        {BUILDING_OPTIONS.map((option) => (
                            <option key={option} value={option}>
                                {option}
                            </option>
                        ))}
                    </select>
                </div>
            </div>
        </div>
    );
}
