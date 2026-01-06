/**
 * MainPage - PropTech Chatbot Interface
 * 
 * 메인 페이지 - 2컬럼 레이아웃
 * 
 * - 좌측: 필터 패널 + 매물 리스트
 * - 우측: 챗봇 영역 (sticky 고정)
 */

'use client';

import { useState, useCallback, useEffect } from 'react';
import dynamic from 'next/dynamic';
import LandListFilter from '@/components/LandListFilter';
import ChatbotFilter from '@/components/ChatbotFilter';
import LandList from '@/components/LandList';
import useBackendUserGuard from '@/hooks/useBackendUserGuard';
import { LandFilterParams } from '@/types/land';

// Chatbot을 동적 import (SSR 비활성화)
const Chatbot = dynamic(() => import('@/components/Chatbot'), {
    ssr: false,
});

// FilterInfo 타입 정의 (Chatbot과 동일)
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

interface ChatbotRecommendData {
    landIds: number[]
    filterInfo: FilterInfo | null
    properties: any[]
}

// sessionStorage에서 필터 값 로드
const loadFilterFromStorage = (): LandFilterParams => {
    if (typeof window === 'undefined') return {};
    try {
        const saved = sessionStorage.getItem('landListFilter');
        if (!saved) return {};
        const parsed = JSON.parse(saved);
        return {
            region: parsed.selectedRegion || undefined,
            dong: parsed.selectedDong || undefined,
            transaction_type: parsed.selectedTransaction || undefined,
            building_type: parsed.selectedBuilding || undefined,
        };
    } catch {
        return {};
    }
};

export default function MainPage() {
    useBackendUserGuard();
    const [filterParams, setFilterParams] = useState<LandFilterParams>({});
    const [recommendedLandIds, setRecommendedLandIds] = useState<number[]>([]);
    const [chatbotFilterInfo, setChatbotFilterInfo] = useState<FilterInfo | null>(null);
    const [chatbotProperties, setChatbotProperties] = useState<any[]>([]);
    const [showChatbotFilter, setShowChatbotFilter] = useState(false);

    // 컴포넌트 마운트 시 sessionStorage에서 필터 로드
    useEffect(() => {
        const savedFilter = loadFilterFromStorage();
        if (Object.keys(savedFilter).length > 0) {
            setFilterParams(savedFilter);
        }
    }, []);

    const handleFilterChange = useCallback((params: LandFilterParams) => {
        setFilterParams(params);
    }, []);

    const handleRecommendedLands = useCallback((landIds: number[]) => {
        setRecommendedLandIds(landIds);
    }, []);

    // 챗봇에서 필터 정보와 매물 데이터 받기
    const handleChatbotRecommend = useCallback((data: ChatbotRecommendData) => {
        setRecommendedLandIds(data.landIds);
        setChatbotFilterInfo(data.filterInfo);
        setChatbotProperties(data.properties);
    }, []);

    // 챗봇 필터 토글
    const handleToggleChatbotFilter = useCallback(() => {
        setShowChatbotFilter(prev => !prev);
    }, []);

    return (
        <div className="max-w-[1440px] mx-auto px-8 py-8">
            {/* 2컬럼 그리드 레이아웃 - 반반 */}
            <div className="grid grid-cols-2 gap-8 isolate">
                {/* 좌측: 필터 + 매물 리스트 */}
                <main className="space-y-6 z-0">
                    {/* 매물 필터 */}
                    {/* 매물 필터 영역 - 조건부 렌더링 */}
                    {showChatbotFilter ? (
                        <ChatbotFilter
                            filterInfo={chatbotFilterInfo}
                            onToggle={handleToggleChatbotFilter}
                        />
                    ) : (
                        <LandListFilter
                            onFilterChange={handleFilterChange}
                            chatbotFilterInfo={chatbotFilterInfo}
                            onToggleChatbotFilter={handleToggleChatbotFilter}
                        />
                    )}

                    {/* 매물 리스트 */}
                    <LandList
                        filterParams={filterParams}
                        recommendedLandIds={recommendedLandIds}
                        chatbotProperties={chatbotProperties}
                        showChatbotFilter={showChatbotFilter}
                    />
                </main>

                {/* 우측: 챗봇 영역 (sticky 고정) */}
                <aside className="sticky top-24 h-fit max-h-[calc(100vh-7rem)] z-10">
                    <Chatbot
                        onRecommendLands={handleRecommendedLands}
                        onChatbotRecommend={handleChatbotRecommend}
                    />
                </aside>
            </div>
        </div>
    );
}
