/**
 * LandList 컴포넌트 - PropTech Bank-Level Design
 * 
 * 매물 목록을 표시하는 컴포넌트
 * 
 * 주요 기능:
 * - 가로형 매물 카드 표시
 * - AI 추천 배지
 * - 찜 버튼
 * - 페이지네이션
 */

'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { Land, LandFilterParams } from '../types/land';
import { fetchLands } from '../api/landApi';
import { fetchWishlist, addWishlist, removeWishlist } from '../api/wishlistApi';
import { useSession } from 'next-auth/react';


interface LandListProps {
    filterParams?: LandFilterParams;
    recommendedLandIds?: number[];
}

const ITEMS_PER_PAGE = 5; // 페이지당 5개 표시 (화면에 맞춤)

// sessionStorage에서 페이지 상태 로드
const loadPageStateFromStorage = () => {
    if (typeof window === 'undefined') return { page: 1, group: 0 };
    try {
        const saved = sessionStorage.getItem('landListPageState');
        return saved ? JSON.parse(saved) : { page: 1, group: 0 };
    } catch {
        return { page: 1, group: 0 };
    }
};

export default function LandList({ filterParams, recommendedLandIds }: LandListProps) {
    const router = useRouter();
    const { data: session } = useSession();
    const [lands, setLands] = useState<Land[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    // 페이지 상태를 sessionStorage에서 로드
    const savedPageState = loadPageStateFromStorage();
    const [currentPage, setCurrentPage] = useState<number>(savedPageState.page);
    const [currentPageGroup, setCurrentPageGroup] = useState<number>(savedPageState.group);
    const [favorites, setFavorites] = useState<Set<number>>(new Set());

    // 페이지 상태 변경 시 sessionStorage에 저장
    useEffect(() => {
        if (typeof window === 'undefined') return;
        sessionStorage.setItem('landListPageState', JSON.stringify({
            page: currentPage,
            group: currentPageGroup
        }));
    }, [currentPage, currentPageGroup]);


    useEffect(() => {
        const loadLands = async () => {
            try {
                setLoading(true);
                const data = await fetchLands(filterParams);

                // AI 추천 매물 ID가 있으면 필터링
                if (recommendedLandIds && recommendedLandIds.length > 0) {
                    const filtered = data.filter(land => recommendedLandIds.includes(land.id));
                    setLands(filtered);
                } else {
                    setLands(data);
                }

                setError(null);
            } catch (err) {
                console.error('Failed to fetch lands:', err);
                setError('매물 정보를 불러오는데 실패했습니다.');
            } finally {
                setLoading(false);
            }
        };

        loadLands();
    }, [filterParams, recommendedLandIds]);

    // 필터가 변경되면 페이지를 1로 리셋 (첫 마운트 제외)
    useEffect(() => {
        // 저장된 필터와 현재 필터를 비교
        const savedFilter = sessionStorage.getItem('landListFilter');
        if (savedFilter) {
            const parsed = JSON.parse(savedFilter);
            const currentFilter = {
                selectedRegion: filterParams?.region || '',
                selectedDong: filterParams?.dong || '',
                selectedTransaction: filterParams?.transaction_type || '',
                selectedBuilding: filterParams?.building_type || '',
            };

            // 필터가 실제로 변경된 경우에만 페이지 리셋
            if (JSON.stringify(parsed) !== JSON.stringify(currentFilter)) {
                setCurrentPage(1);
                setCurrentPageGroup(0);
            }
        }
    }, [filterParams]);
    // 로그인된 사용자 기준으로 DB에 있는 찜 목록 불러오기
    useEffect(() => {
        const loadFavoritesFromServer = async () => {
            if (!session) {
                setFavorites(new Set());
                return;
            }
            try {
                const wishlist = await fetchWishlist();
                const ids = wishlist.map(item => Number(item.listing_id));
                setFavorites(new Set(ids));
            } catch (err) {
                console.error('Failed to fetch wishlist:', err);
            }
        };

        loadFavoritesFromServer();
    }, [session]);


    // 페이지네이션 계산
    const totalPages = Math.ceil(lands.length / ITEMS_PER_PAGE);
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    const endIndex = startIndex + ITEMS_PER_PAGE;
    const currentLands = lands.slice(startIndex, endIndex);

    // 페이지 그룹 계산 (10개씩)
    const PAGES_PER_GROUP = 10;
    const totalPageGroups = Math.ceil(totalPages / PAGES_PER_GROUP);
    const startPage = currentPageGroup * PAGES_PER_GROUP + 1;
    const endPage = Math.min(startPage + PAGES_PER_GROUP - 1, totalPages);
    const visiblePages = Array.from({ length: endPage - startPage + 1 }, (_, i) => startPage + i);

    const handlePageClick = (page: number) => {
        setCurrentPage(page);
    };

    const handlePrevGroup = () => {
        if (currentPageGroup > 0) {
            setCurrentPageGroup(currentPageGroup - 1);
            setCurrentPage((currentPageGroup - 1) * PAGES_PER_GROUP + 1);
        }
    };

    const handleNextGroup = () => {
        if (currentPageGroup < totalPageGroups - 1) {
            setCurrentPageGroup(currentPageGroup + 1);
            setCurrentPage((currentPageGroup + 1) * PAGES_PER_GROUP + 1);
        }
    };

    const toggleFavorite = async (landId: number, e: React.MouseEvent) => {
        e.stopPropagation();
        // 로그인 안 되어 있으면 로그인 페이지로
        if (!session) {
            router.push('/login');
            return;
        }
        const isFavorite = favorites.has(landId);   //현재 상태 확인

        // UI를 먼저 반영하는 낙관적 업데이트
        setFavorites(prev => {
            const next = new Set(prev);
            if (isFavorite) {
                next.delete(landId);
            } else {
                next.add(landId);
            }
            return next;
        });

        try {
            if (isFavorite) {
                await removeWishlist(landId);
            } else {
                await addWishlist(landId);
            }
        } catch (error) {
            console.error('Failed to toggle wishlist:', error);

            // 실패 시 상태 롤백
            setFavorites(prev => {
                const next = new Set(prev);
                if (isFavorite) {
                    next.add(landId);
                } else {
                    next.delete(landId);
                }
                return next;
            });
        }
    };

    const handleCardClick = (landId: number) => {
        router.push(`/landDetail/${landId}`);
    };

    if (loading) {
        return (
            <div className="bg-white border border-[var(--color-border-light)] rounded-xl p-8 shadow-[var(--shadow-md)] min-h-[400px] flex items-center justify-center">
                <div className="text-center">
                    <div className="w-12 h-12 border-4 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-[var(--color-text-secondary)]">매물 정보를 불러오는 중...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-white border border-[var(--color-border-light)] rounded-xl p-8 shadow-[var(--shadow-md)] min-h-[400px] flex items-center justify-center">
                <div className="text-center text-[var(--color-error)]">
                    <p>{error}</p>
                </div>
            </div>
        );
    }

    if (lands.length === 0) {
        return (
            <div className="bg-white border border-[var(--color-border-light)] rounded-xl p-8 shadow-[var(--shadow-md)] min-h-[400px] flex items-center justify-center">
                <div className="text-center max-w-md">
                    {/* 아이콘 */}
                    <div className="mb-6 flex justify-center">
                        <svg width="80" height="80" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <circle cx="40" cy="40" r="40" fill="#F5F7FA" />
                            <path d="M40 24L24 34V56H32V42H48V56H56V34L40 24Z" fill="#C5CDD8" />
                        </svg>
                    </div>

                    {/* 메시지 */}
                    <h3 className="text-lg font-semibold text-[var(--color-text-primary)] mb-2">
                        조건에 맞는 매물이 없습니다
                    </h3>
                    <p className="text-sm text-[var(--color-text-secondary)] mb-6">
                        다른 조건으로 검색하거나<br />
                        AI 챗봇에게 매물 추천을 받아보세요
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* 매물 리스트 헤더 */}
            <div className="bg-white border border-[var(--color-border-light)] rounded-xl p-6 shadow-[var(--shadow-md)]">
                <div className="flex items-center justify-between mb-6">
                    <h3 className="text-lg font-semibold text-[var(--color-primary)]">추천 매물</h3>
                    <span className="text-sm text-[var(--color-text-tertiary)]">
                        총 {lands.length}개
                    </span>
                </div>

                {/* 매물 카드 리스트 */}
                <div className="space-y-4">
                    {currentLands.map((land, index) => (
                        <div
                            key={land.id}
                            onClick={() => handleCardClick(land.id)}
                            className="flex gap-4 p-4 border border-[var(--color-border-light)] rounded-lg hover:border-[var(--color-primary)] hover:shadow-[var(--shadow-lg)] transition-all cursor-pointer property-card-animate bg-white"
                            style={{ animationDelay: `${index * 50}ms` }}
                        >
                            {/* 썸네일 이미지 */}
                            <div className="relative w-40 h-32 flex-shrink-0 bg-[var(--color-bg-secondary)] rounded-lg overflow-hidden">
                                {land.image ? (
                                    <Image
                                        src={land.image}
                                        alt={`매물 ${land.id}`}
                                        fill
                                        className="object-cover"
                                    />
                                ) : (
                                    <div className="w-full h-full flex items-center justify-center text-[var(--color-text-tertiary)]">
                                        <svg width="48" height="48" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                                            <circle cx="32" cy="32" r="32" fill="var(--color-bg-tertiary)" />
                                            <path d="M32 20L20 28V44H26V34H38V44H44V28L32 20Z" fill="var(--color-border-dark)" />
                                        </svg>
                                    </div>
                                )}
                            </div>

                            {/* 매물 정보 */}
                            <div className="flex-1 flex flex-col justify-between min-w-0">
                                <div>

                                    {/* 매물명 또는 주소 */}
                                    <h4 className="text-base font-semibold text-[var(--color-text-primary)] mb-2 truncate">
                                        {land.address || `매물 ${land.id}`}
                                    </h4>

                                    {/* 가격 */}
                                    <p className="text-xl font-bold mb-1" style={{ color: '#16375B' }}>
                                        {land.price}
                                    </p>

                                    {/* 단기임대 상세 가격 (보증금/월세) */}
                                    {(land.deal_type === '단기임대' || land.transaction_type === '단기임대') && (
                                        <p className="text-sm text-[var(--color-text-secondary)] mb-1">
                                            {land.deposit ? `보증금 ${land.deposit.toLocaleString()}만원` : ''}
                                            {land.deposit && land.monthly_rent ? ' / ' : ''}
                                            {land.monthly_rent ? `월세 ${land.monthly_rent.toLocaleString()}만원` : ''}
                                        </p>
                                    )}

                                    {/* 메타 정보 */}
                                    <div className="flex gap-3 mt-2 text-xs text-[var(--color-text-tertiary)]">
                                        <span>{land.transaction_type || '매매'}</span>
                                        <span>•</span>
                                        <span>{land.building_type || '아파트'}</span>
                                    </div>
                                </div>
                            </div>

                            {/* 찜 버튼 */}
                            <button
                                onClick={(e) => toggleFavorite(land.id, e)}
                                className="flex-shrink-0 w-10 h-10 rounded-full bg-white border border-[var(--color-border)] hover:border-[var(--color-primary)] hover:bg-[var(--color-bg-hover)] flex items-center justify-center transition-all self-start"
                            >
                                <svg
                                    width="20"
                                    height="20"
                                    viewBox="0 0 24 24"
                                    fill={favorites.has(land.id) ? '#E53935' : 'none'}
                                    stroke={favorites.has(land.id) ? '#E53935' : 'var(--color-text-tertiary)'}
                                    strokeWidth="2"
                                    xmlns="http://www.w3.org/2000/svg"
                                >
                                    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
                                </svg>
                            </button>
                        </div>
                    ))}
                </div>

                {/* 페이지네이션 */}
                {totalPages > 1 && (
                    <div className="flex justify-center items-center gap-2 mt-8 pt-6 border-t border-[var(--color-border-light)]">
                        {/* 이전 그룹 버튼 */}
                        <button
                            onClick={handlePrevGroup}
                            disabled={currentPageGroup === 0}
                            className="px-3 py-2 rounded-lg text-sm font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            ◀
                        </button>

                        {/* 이전 페이지 */}
                        <button
                            onClick={() => handlePageClick(Math.max(1, currentPage - 1))}
                            disabled={currentPage === 1}
                            className="px-3 py-2 rounded-lg text-sm font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            이전
                        </button>

                        {/* 페이지 번호 (10개씩) */}
                        <div className="flex gap-1">
                            {visiblePages.map((page) => (
                                <button
                                    key={page}
                                    onClick={() => handlePageClick(page)}
                                    className={`w-10 h-10 rounded-lg text-sm font-semibold transition-all ${currentPage === page
                                        ? 'bg-[var(--color-primary)] text-white shadow-[var(--shadow-md)]'
                                        : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]'
                                        }`}
                                >
                                    {page}
                                </button>
                            ))}
                        </div>

                        {/* 다음 페이지 */}
                        <button
                            onClick={() => handlePageClick(Math.min(totalPages, currentPage + 1))}
                            disabled={currentPage === totalPages}
                            className="px-3 py-2 rounded-lg text-sm font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            다음
                        </button>

                        {/* 다음 그룹 버튼 */}
                        <button
                            onClick={handleNextGroup}
                            disabled={currentPageGroup === totalPageGroups - 1}
                            className="px-3 py-2 rounded-lg text-sm font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            ▶
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
