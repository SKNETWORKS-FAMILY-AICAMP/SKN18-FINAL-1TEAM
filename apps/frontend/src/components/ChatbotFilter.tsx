// apps/frontend/src/components/ChatbotFilter.tsx
'use client';

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

interface ChatbotFilterProps {
    filterInfo: FilterInfo | null;
    onToggle?: () => void;
}

export default function ChatbotFilter({ filterInfo, onToggle }: ChatbotFilterProps) {
    const handleReset = () => {
        // 챗봇 필터는 초기화 기능이 없으므로 토글만 수행
        onToggle?.();
    };

    return (
        <div className="bg-white border border-[var(--color-border-light)] rounded-xl p-6 shadow-[var(--shadow-md)]">
            {/* 헤더 */}
            <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-[var(--color-primary)]">
                    🤖 AI 챗봇 필터
                </h3>
                <div className="flex items-center gap-2">
                    {/* 챗봇 필터 토글 버튼 - 활성 상태 */}
                    <button
                        onClick={onToggle}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-purple-600 border border-purple-600 rounded-lg hover:bg-purple-700 transition-colors"
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

            {/* 챗봇 필터 정보 표시 */}
            {filterInfo ? (
                <div className="space-y-4">
                    <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg">
                        <h4 className="text-sm font-semibold text-purple-900 mb-2">📋 검색 조건 요약</h4>
                        <p className="text-sm text-purple-700">{filterInfo.summary}</p>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        {filterInfo.details.location && (
                            <div className="p-3 bg-gray-50 rounded-lg">
                                <p className="text-xs font-medium text-gray-500 mb-1">📍 위치</p>
                                <p className="text-sm font-semibold text-gray-900">{filterInfo.details.location}</p>
                            </div>
                        )}

                        {filterInfo.details.deal_type && (
                            <div className="p-3 bg-gray-50 rounded-lg">
                                <p className="text-xs font-medium text-gray-500 mb-1">🏠 거래 유형</p>
                                <p className="text-sm font-semibold text-gray-900">{filterInfo.details.deal_type}</p>
                            </div>
                        )}

                        {filterInfo.details.building_type && (
                            <div className="p-3 bg-gray-50 rounded-lg">
                                <p className="text-xs font-medium text-gray-500 mb-1">🏢 건물 유형</p>
                                <p className="text-sm font-semibold text-gray-900">{filterInfo.details.building_type}</p>
                            </div>
                        )}

                        {(filterInfo.details.max_deposit || filterInfo.details.max_rent) && (
                            <div className="p-3 bg-gray-50 rounded-lg">
                                <p className="text-xs font-medium text-gray-500 mb-1">💰 가격 조건</p>
                                <p className="text-sm font-semibold text-gray-900">
                                    {filterInfo.details.max_deposit && `보증금: ${filterInfo.details.max_deposit}`}
                                    {filterInfo.details.max_deposit && filterInfo.details.max_rent && ' / '}
                                    {filterInfo.details.max_rent && `월세: ${filterInfo.details.max_rent}`}
                                </p>
                            </div>
                        )}

                        {filterInfo.details.facilities && filterInfo.details.facilities?.length > 0 && (
                            <div className="p-3 bg-gray-50 rounded-lg col-span-2">
                                <p className="text-xs font-medium text-gray-500 mb-1">🎯 필요 시설</p>
                                <div className="flex flex-wrap gap-2 mt-2">
                                    {filterInfo.details.facilities.map((facility, idx) => (
                                        <span key={idx} className="px-2 py-1 text-xs bg-white border border-gray-200 rounded-full">
                                            {facility}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        {filterInfo.details.style && filterInfo.details.style.length > 0 && (
                            <div className="p-3 bg-gray-50 rounded-lg col-span-2">
                                <p className="text-xs font-medium text-gray-500 mb-1">✨ 스타일</p>
                                <div className="flex flex-wrap gap-2 mt-2">
                                    {filterInfo.details.style.map((s, idx) => (
                                        <span key={idx} className="px-2 py-1 text-xs bg-purple-100 text-purple-700 border border-purple-200 rounded-full">
                                            {s}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    {filterInfo.search_strategy && (
                        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                            <h4 className="text-sm font-semibold text-blue-900 mb-2">🔍 검색 전략</h4>
                            <p className="text-sm text-blue-700">{filterInfo.search_strategy}</p>
                        </div>
                    )}
                </div>
            ) : (
                <div className="p-8 text-center text-gray-500">
                    <p>챗봇과 대화하여 필터 정보를 생성하세요.</p>
                </div>
            )}
        </div>
    );
}
