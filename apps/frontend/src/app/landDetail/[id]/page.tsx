/**
 * LandDetailPage
 * 
 * 매물 상세 페이지
 * 
 * 주요 구성:
 * - LandDetail 컴포넌트 (매물 상세 정보)
 * - Map 컴포넌트 (위치 및 주변 시설)
 * - MarkerInfo 컴포넌트 (주변 시설 정보 - Neo4j 연동)
 * - 커뮤니티 게시글 미리보기 (단지별)
 * - 비슷한 추천 매물 리스트
 */

'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Image from 'next/image';
import LandDetail from '@/components/LandDetail';
import Map from '@/components/Map';
import MarkerInfo from '@/components/MarkerInfo';
import LandList from '@/components/LandList';
import { fetchCommunityPosts } from '@/api/communityApi';
import { fetchSimilarListings } from '@/api/landApi';
import { Land } from '@/types/land';

interface CommunityPost {
    id: string;
    title: string;
    content: string;
    author_name: string;
    created_at: string;
    likes_count: number;
    comments_count: number;
    region?: string;
    dong?: string;
    complex_name?: string;
}

export default function LandDetailPage() {
    const params = useParams();
    const router = useRouter();
    const id = params.id as string;
    const [communityPosts, setCommunityPosts] = useState<CommunityPost[]>([]);
    const [loadingPosts, setLoadingPosts] = useState(true);
    const [activeMapCategories, setActiveMapCategories] = useState<Set<string>>(new Set());
    const [currentPostIndex, setCurrentPostIndex] = useState(0);
    const [landDong, setLandDong] = useState<string>('');
    const [similarListings, setSimilarListings] = useState<Land[]>([]);
    const [similarLoading, setSimilarLoading] = useState(false);

    // 커뮤니티 게시글 로드 - 매물의 행정동 기준으로 필터링
    useEffect(() => {
        const loadCommunityPosts = async () => {
            try {
                setLoadingPosts(true);

                // 1. 먼저 매물 정보를 가져와서 행정동 추출
                const landResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/listings/lands/${id}/`);
                if (!landResponse.ok) {
                    throw new Error('Failed to fetch land data');
                }
                const landData = await landResponse.json();

                // 주소에서 행정동 추출 (예: "서울특별시 종로구 낙원동" -> "낙원동")
                const extractDong = (address: string): string => {
                    if (!address) return '';
                    // 정규식으로 "동" 또는 "가"로 끝나는 행정동 추출
                    const match = address.match(/([가-힣]+(?:동|가))/);
                    return match ? match[1] : '';
                };

                const dong = extractDong(landData.address || '');
                setLandDong(dong);

                // 2. 행정동으로 필터링된 커뮤니티 게시글 가져오기
                const postsParams: any = { board: 'region' };
                if (dong) {
                    postsParams.dong = dong;
                }

                const response = await fetchCommunityPosts(postsParams);
                const posts = response.results || response || [];
                setCommunityPosts(posts.slice(0, 3)); // 최대 3개만 표시
            } catch (error) {
                console.error('Failed to fetch community posts:', error);
                setCommunityPosts([]);
            } finally {
                setLoadingPosts(false);
            }
        };

        loadCommunityPosts();
    }, [id]);

    // 유사 매물 로드
    useEffect(() => {
        const loadSimilar = async () => {
            try {
                setSimilarLoading(true);
                const similar = await fetchSimilarListings(id);
                setSimilarListings(similar);
            } catch (err) {
                console.error('Failed to fetch similar listings:', err);
            } finally {
                setSimilarLoading(false);
            }
        };

        if (id) loadSimilar();
    }, [id]);

    // 시설 카테고리 클릭 핸들러
    const handleCategoryClick = (category: string, isActive: boolean) => {
        setActiveMapCategories(prev => {
            const newSet = new Set(prev);
            if (isActive) {
                newSet.add(category);
            } else {
                newSet.delete(category);
            }
            return newSet;
        });
        // TODO: 지도에 해당 카테고리 시설 마커 표시
        console.log(`카테고리 ${category} ${isActive ? '활성화' : '비활성화'}`);
    };

    // 날짜 포맷
    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now.getTime() - date.getTime();
        const diffDays = Math.floor(diff / (1000 * 60 * 60 * 24));

        if (diffDays === 0) return '오늘';
        if (diffDays === 1) return '어제';
        if (diffDays < 7) return `${diffDays}일 전`;
        return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
    };

    // 캐러셀 네비게이션
    const handlePrevPost = () => {
        setCurrentPostIndex((prev) => (prev === 0 ? communityPosts.length - 1 : prev - 1));
    };

    const handleNextPost = () => {
        setCurrentPostIndex((prev) => (prev === communityPosts.length - 1 ? 0 : prev + 1));
    };

    return (
        <div className="max-w-7xl mx-auto px-4 py-8">
            {/* 매물 상세 정보 */}
            <LandDetail landId={id} />

            {/* 위치 및 주변 시설 정보 */}
            <div className="mt-8">
                <h3 className="text-xl font-bold mb-4 text-slate-800">위치 및 주변 시설</h3>
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-2">
                        <Map landId={id} activeCategories={activeMapCategories} />
                    </div>
                    <div className="lg:col-span-1">
                        <MarkerInfo landId={id} onCategoryClick={handleCategoryClick} />
                    </div>
                </div>
            </div>

            {/* 커뮤니티 게시글 미리보기 - 캐러셀 형식 */}
            <div className="mt-8">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xl font-bold text-slate-800">
                        행정동 커뮤니티 게시글
                        {landDong && <span className="text-purple-600 ml-2">({landDong})</span>}
                    </h3>
                    <a
                        href={`/community?board=region${landDong ? `&dong=${landDong}` : ''}`}
                        className="text-sm text-purple-600 hover:text-purple-800 font-medium transition-colors"
                    >
                        더보기 →
                    </a>
                </div>

                {loadingPosts ? (
                    <div className="flex justify-center items-center h-32">
                        <div className="w-6 h-6 border-3 border-purple-400 border-t-transparent rounded-full animate-spin"></div>
                    </div>
                ) : communityPosts.length > 0 ? (
                    <div className="relative">
                        {/* 캐러셀 컨테이너 */}
                        <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
                            <div
                                className="flex transition-transform duration-300 ease-in-out"
                                style={{ transform: `translateX(-${currentPostIndex * 100}%)` }}
                            >
                                {communityPosts.map((post) => (
                                    <a
                                        key={post.id}
                                        href={`/community?post=${post.id}`}
                                        className="min-w-full block p-6 hover:bg-gray-50 transition-colors"
                                    >
                                        {/* 지역 태그 */}
                                        <div className="flex flex-wrap gap-1 mb-3">
                                            {post.region && (
                                                <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full">
                                                    {post.region}
                                                </span>
                                            )}
                                            {post.dong && (
                                                <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">
                                                    {post.dong}
                                                </span>
                                            )}
                                        </div>

                                        {/* 제목 */}
                                        <h4 className="font-semibold text-slate-800 mb-2 text-lg line-clamp-1">
                                            {post.title}
                                        </h4>

                                        {/* 내용 미리보기 */}
                                        <p className="text-sm text-slate-600 line-clamp-3 mb-4">
                                            {post.content}
                                        </p>

                                        {/* 하단 정보 */}
                                        <div className="flex items-center justify-between text-xs text-slate-500">
                                            <span>{post.author_name}</span>
                                            <div className="flex items-center gap-3">
                                                <span>{formatDate(post.created_at)}</span>
                                            </div>
                                        </div>
                                    </a>
                                ))}
                            </div>
                        </div>

                        {/* 네비게이션 버튼 (게시글이 2개 이상일 때만 표시) */}
                        {communityPosts.length > 1 && (
                            <>
                                <button
                                    onClick={handlePrevPost}
                                    className="absolute left-2 top-1/2 -translate-y-1/2 bg-white/90 hover:bg-white rounded-full w-10 h-10 flex items-center justify-center shadow-lg transition-all z-10"
                                >
                                    <svg className="w-6 h-6 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                                    </svg>
                                </button>
                                <button
                                    onClick={handleNextPost}
                                    className="absolute right-2 top-1/2 -translate-y-1/2 bg-white/90 hover:bg-white rounded-full w-10 h-10 flex items-center justify-center shadow-lg transition-all z-10"
                                >
                                    <svg className="w-6 h-6 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                    </svg>
                                </button>

                                {/* 인디케이터 */}
                                <div className="flex justify-center gap-2 mt-4">
                                    {communityPosts.map((_, index) => (
                                        <button
                                            key={index}
                                            onClick={() => setCurrentPostIndex(index)}
                                            className={`w-2 h-2 rounded-full transition-all ${index === currentPostIndex
                                                ? 'bg-purple-600 w-6'
                                                : 'bg-gray-300 hover:bg-gray-400'
                                                }`}
                                        />
                                    ))}
                                </div>
                            </>
                        )}
                    </div>
                ) : (
                    <div className="rounded-2xl border border-gray-200 bg-white shadow-sm p-8 text-center">
                        <p className="text-slate-500">
                            {landDong ? `${landDong} 지역에 ` : ''}아직 등록된 게시글이 없습니다.
                        </p>
                        <a
                            href={`/community?board=region${landDong ? `&dong=${landDong}` : ''}`}
                            className="inline-block mt-2 text-purple-600 hover:text-purple-800 font-medium"
                        >
                            커뮤니티 바로가기 →
                        </a>
                    </div>
                )}
            </div>

            {/* 현재 매물과 비슷한 추천 매물 top3 */}
            <div className="mt-8">
                <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
                    <div className="bg-slate-700 text-white px-4 py-2 rounded-t-2xl">
                        <h3 className="font-bold text-base" style={{ color: '#ffffff' }}>현재 매물과 비슷한 추천 매물</h3>
                        <p className="text-xs mt-1" style={{ color: '#ffffff' }}>
                            같은 행정동 · 골드 등급 중개사 · 같은 거래유형 · 유사한 가격대 (±30%)
                        </p>
                    </div>
                    <div className="p-4">
                        {similarLoading ? (
                            <div className="flex justify-center items-center py-12">
                                <div className="w-8 h-8 border-4 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                            </div>
                        ) : similarListings.length > 0 ? (
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {similarListings.map((similarLand) => (
                                    <div
                                        key={similarLand.id}
                                        onClick={() => router.push(`/landDetail/${similarLand.id}`)}
                                        className="border border-gray-200 rounded-xl overflow-hidden hover:shadow-lg transition-shadow cursor-pointer bg-white"
                                    >
                                        <div className="relative aspect-video bg-gray-100">
                                            <Image
                                                src={similarLand.images?.[0] || similarLand.image || '/images/gozip_loading.png'}
                                                alt={similarLand.title}
                                                fill
                                                sizes="(max-width: 768px) 100vw, 33vw"
                                                className="object-cover"
                                            />
                                        </div>
                                        <div className="p-3">
                                            <p className="text-xs text-gray-500 mb-1 truncate">
                                                {similarLand.address || '주소 정보 없음'}
                                            </p>
                                            <p className="text-lg font-bold text-blue-600 mb-1">
                                                {similarLand.price || '-'}
                                            </p>
                                            <div className="flex items-center gap-2 text-xs text-gray-600">
                                                <span>{similarLand.transaction_type || '-'}</span>
                                                {similarLand.building_type && (
                                                    <>
                                                        <span>·</span>
                                                        <span>{similarLand.building_type}</span>
                                                    </>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-center py-12 text-gray-500">
                                <p className="text-sm">조건에 맞는 유사 매물이 없습니다.</p>
                                <p className="text-xs mt-2 text-gray-400">
                                    같은 행정동의 골드 등급 중개사 매물 중 유사한 가격대의 매물을 찾지 못했습니다.
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
