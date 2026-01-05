/**
 * LandDetail 컴포넌트
 *
 * 매물 상세정보를 표시하는 컴포넌트
 */

'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import Image from 'next/image';
import { Land } from '../types/land';
import { fetchLandById } from '../api/landApi';
import { recordListingView } from '../api/historyApi';
import { useRouter } from 'next/navigation';

interface LandDetailProps {
  landId: string;
}

type TempId = 'safety' | 'convenience' | 'pet' | 'traffic' | 'culture';

export default function LandDetail({ landId }: LandDetailProps) {
  const router = useRouter();
  const [land, setLand] = useState<Land | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [liked, setLiked] = useState(false);
  const [showPriceTooltip, setShowPriceTooltip] = useState(false);
  const [maxScrollDepth, setMaxScrollDepth] = useState(0);
  const maxScrollDepthRef = useRef(0);

  useEffect(() => {
    const loadLand = async () => {
      try {
        setLoading(true);
        const data = await fetchLandById(landId);
        setLand(data);
      } catch (err) {
        console.error('Failed to fetch land details:', err);
        setError('매물 정보를 불러오는데 실패했습니다.');
      } finally {
        setLoading(false);
      }
    };

    if (landId) loadLand();
  }, [landId]);

  // ✅ 온도 설명 토글 상태
  const [activeTempId, setActiveTempId] = useState<TempId | null>(null);

  // 스크롤 깊이 추적
  useEffect(() => {
    const handleScroll = () => {
      const windowHeight = window.innerHeight;
      const documentHeight = document.documentElement.scrollHeight;
      const scrollTop = window.scrollY;

      // 현재 스크롤 위치를 퍼센트로 계산
      const scrollPercentage = Math.round(((scrollTop + windowHeight) / documentHeight) * 100);

      // 최대 스크롤 깊이 업데이트 (state와 ref 모두)
      const newMaxDepth = Math.max(maxScrollDepthRef.current, Math.min(scrollPercentage, 100));
      maxScrollDepthRef.current = newMaxDepth;
      setMaxScrollDepth(newMaxDepth);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // 매물 조회 이력 추적
  useEffect(() => {
    const startTime = Date.now();

    // 컴포넌트 언마운트 시 총 조회 시간 및 스크롤 깊이 저장
    return () => {
      const totalViewDuration = Math.floor((Date.now() - startTime) / 1000);
      // 최소 1초 이상 조회한 경우만 기록
      if (totalViewDuration >= 1) {
        recordListingView(landId, totalViewDuration, maxScrollDepthRef.current);
      }
    };
  }, [landId]); // maxScrollDepth 제거!

  // 신뢰도 등급에 따른 아이콘 반환
  const getTrustBadgeImage = (score: string | null | undefined) => {
    switch (score) {
      case 'A':
        return '/assets/land_broker/gold.png';
      case 'B':
        return '/assets/land_broker/silver.png';
      case 'C':
        return '/assets/land_broker/bronze.png';
      default:
        return null;
    }
  };

  // 가격 분류 레이블 배지 색상
  const getPriceBadgeColor = (label: string | undefined) => {
    switch (label) {
      case '저렴':
        return 'text-green-600';
      case '적정':
        return 'text-blue-600';
      case '비쌈':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  // 관리비 파싱 함수 - "~만원" 형태로 추출
  const parseMaintenanceFee = (fee: string | undefined): string => {
    if (!fee || fee === '-') return '-';
    const match = fee.match(/(\d+)\s*만\s*원/);
    if (match) {
      return `${match[1]}만원`;
    }
    return fee;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="w-8 h-8 border-4 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (error || !land) {
    return (
      <div className="flex justify-center items-center min-h-[400px] text-red-500">
        {error || '매물을 찾을 수 없습니다.'}
      </div>
    );
  }

  // ✅ 온도 설명 내용
  const tempExplain: Record<TempId, { title: string; subtitle: string; body: string[] }> = {
    convenience: {
      title: '생활편의',
      subtitle: '일상 시설 접근성',
      body: [
        '편의점·세탁소·마트·공원까지의 거리를 기준으로, 일상생활이 얼마나 편리한지를 평가합니다.',
        '전체 매물의 거리 분포를 기준으로 “가깝다 / 보통 / 멀다” 구간을 나눕니다.',
        '가까울수록 점수가 높고, 기준 거리 이상부터는 점수가 크게 낮아집니다.',
        '공원은 단순 거리뿐 아니라 면적(규모)까지 함께 고려해 작은 공원이 과대평가되는 문제를 줄였습니다.',
      ],
    },
    traffic: {
      title: '교통',
      subtitle: '지하철 + 버스 접근성',
      body: [
        '지하철은 역까지의 거리, 버스는 정류장 개수를 기준으로 출퇴근과 이동의 편리함을 평가합니다.',
        '지하철은 초역세권 / 역세권 / 보통 / 비역세권 구조로 직관적으로 해석됩니다.',
        '버스는 거리보다 정류장 개수(밀도)가 체감에 더 큰 영향을 주기 때문에 개수 기반으로 점수화합니다.',
        '전체 매물 분포 대비 해당 매물이 어느 위치에 있는지를 보여줍니다.',
      ],
    },
    culture: {
      title: '문화',
      subtitle: '희소성 + 접근성',
      body: [
        '도서관·영화관·공연장·미술관 등 문화시설 접근성을 종합적으로 평가합니다.',
        '문화시설은 지역별 분포가 불균형하므로 희소한 시설일수록 가중치를 높게 반영합니다.',
        '가까울수록 점수가 높아지는 거리 감쇠 방식을 적용합니다.',
        '과대대표될 수 있는 시설(예: 도서관)은 가중치를 낮춰 변별력을 확보했습니다.',
      ],
    },
    safety: {
      title: '안전',
      subtitle: '범죄 위험 + 안전 인프라',
      body: [
        '범죄 위험과 안전 인프라를 함께 고려해 거주 시 체감되는 안심도를 평가합니다.',
        '범죄는 유형별 위험도를 다르게 반영해 중범죄 영향이 묻히지 않도록 설계했습니다.',
        'CCTV, 경찰관서, 비상벨 등 안전 인프라는 정규화 후 가중합으로 반영합니다.',
        '평균 기준선으로 36.5°C를 사용해 다른 매물과 직관적으로 비교할 수 있습니다.',
      ],
    },
    pet: {
      title: '반려',
      subtitle: '반려 생활환경',
      body: [
        '반려동물과 함께 살기 좋은 환경인지를 평가합니다.',
        '동물병원·반려놀이터·그루밍·반려용품점·공원 등 반려 관련 시설 접근성을 종합합니다.',
        '시설별 기준 거리 내에 있을수록 점수가 높아집니다.',
        '기준 거리 밖이면 해당 항목은 0점 처리되어 해석이 명확합니다.',
        '반려놀이터, 동물병원처럼 체감이 큰 시설에 더 높은 가중치를 적용했습니다.',
      ],
    },
  };

  const toggleTemp = (id: TempId) => {
    setActiveTempId((prev) => (prev === id ? null : id));
  };

  const tempItems = [
    { id: 'safety', label: '안전 온도', value: land.temperatures?.safety || 36.5, icon: '🛡️', desc: '치안 및 인프라' },
    { id: 'convenience', label: '편의 온도', value: land.temperatures?.convenience || 36.5, icon: '🛒', desc: '생활 밀접 시설' },
    { id: 'pet', label: '반려동물 온도', value: land.temperatures?.pet || 36.5, icon: '🐾', desc: '반려견 산책 및 병원' },
    { id: 'traffic', label: '교통 온도', value: land.temperatures?.traffic || 36.5, icon: '🚇', desc: '대중교통 접근성' },
    { id: 'culture', label: '문화 온도', value: land.temperatures?.culture || 36.5, icon: '🏛️', desc: '문화 및 예술 시설' },
  ];

  const activeTemp = activeTempId ? tempExplain[activeTempId] : null;
  const activeTempItem = activeTempId ? tempItems.find((item) => item.id === activeTempId) : null;
  const visibleTempItems = activeTempId ? tempItems.filter((item) => item.id !== activeTempId) : tempItems;

  // 이미지가 없으면 기본 placeholder 사용
  const defaultPlaceholder = '/images/gozip_loading.png';
  const images = land.images && land.images.length > 0 ? land.images : [land.image || defaultPlaceholder];

  const handlePrevImage = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentImageIndex((prev) => (prev === 0 ? images.length - 1 : prev - 1));
  };

  const handleNextImage = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentImageIndex((prev) => (prev === images.length - 1 ? 0 : prev + 1));
  };

  const handleLike = (e: React.MouseEvent) => {
    e.stopPropagation();
    setLiked(!liked);
  };

  // listing_info에서 카테고리별 데이터 추출 및 파싱
  const getCategorizedFacilities = () => {
    const listingInfo = land.listing_info || {};
    // 문자열을 배열로 변환하고 괄호, 따옴표 제거하는 헬퍼 함수
    const parseToArray = (value: any): string[] => {
      if (!value) return [];

      // 이미 배열이면 그대로 반환
      if (Array.isArray(value)) return value;

      // 문자열이면 쉼표로 분리하고 정리
      if (typeof value === 'string') {
        return value
          .split(',')
          .map(item => item
            .trim()
            .replace(/[\[\]()'"]/g, '') // 괄호, 따옴표 제거
            .trim()
          )
          .filter(item => item.length > 0); // 빈 문자열 제거
      }

      return [];
    };
    return {
      heating: parseToArray(listingInfo['난방방식']),
      cooling: parseToArray(listingInfo['냉방시설']),
      living: parseToArray(listingInfo['생활시설']),
      security: parseToArray(listingInfo['보안시설']),
      facilities: parseToArray(listingInfo['기타시설'])
    };
  };
  // additional_options 파싱 (배열 또는 문자열)
  const getAdditionalOptions = () => {
    if (!land.additional_options) return [];

    // 이미 배열이면 그대로 반환
    if (Array.isArray(land.additional_options)) {
      return land.additional_options;
    }

    // 문자열이면 쉼표로 분리
    if (typeof land.additional_options === 'string') {
      return land.additional_options
        .split(',')
        .map((opt: string) => opt
          .trim()
          .replace(/[\[\]()'"]/g, '') // 괄호, 따옴표 제거
          .trim()
        )
        .filter((opt: string) => opt.length > 0); // 빈 문자열 제거
    }

    return [];
  };

  const categorizedFacilities = getCategorizedFacilities();
  const additionalOptions = getAdditionalOptions();
  const availableOptions: any[] = []; // Placeholder

  // 주소에서 구 정보 추출
  const extractDistrict = (address: string | undefined) => {
    if (!address) return '서울특별시';
    const match = address.match(/서울[특별시]*\s*(\S+구)/);
    return match ? `서울특별시 ${match[1]}` : '서울특별시';
  };

  return (
    <div className="space-y-6">
      {/* 헤더 섹션: 매물번호, 주소, 가격 */}
      <div className="p-4">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
            <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="flex-1">
            <p className="text-sm text-gray-500 mb-1">매물번호 {land.land_num}</p>
            <h1 className="text-xl font-bold text-slate-800 mb-2">{land.address || '주소 정보 없음'}</h1>

            <div className="flex items-center gap-3 mb-3">
              <span className="text-2xl font-bold text-blue-600">{land.price || '-'}</span>

              {land.price_prediction?.predicted_label_kr && (
                <div className="relative inline-flex items-center gap-2">
                  <span
                    className={`px-3 py-1 rounded-lg text-sm font-bold ${land.price_prediction.predicted_label_kr === '저렴'
                      ? 'bg-green-500 text-white'
                      : land.price_prediction.predicted_label_kr === '적정'
                        ? 'bg-blue-500 text-white'
                        : 'bg-red-500 text-white'
                      }`}
                  >
                    {land.price_prediction.predicted_label_kr}
                  </span>
                  <button
                    className="w-5 h-5 rounded-full bg-gray-200 text-gray-600 text-xs font-bold hover:bg-gray-300 transition-colors"
                    onMouseEnter={() => setShowPriceTooltip(true)}
                    onMouseLeave={() => setShowPriceTooltip(false)}
                  >
                    ?
                  </button>

                  {showPriceTooltip && (
                    <div className="absolute top-full left-0 mt-2 w-72 bg-white rounded-lg shadow-xl border border-gray-200 p-4 z-50">
                      <p className="text-sm text-slate-700">
                        해당 매물은 서울특별시 법정동 건물용도별 평당가로 분석했을 때{' '}
                        <strong className={getPriceBadgeColor(land.price_prediction.predicted_label_kr)}>
                          '{land.price_prediction.predicted_label_kr}'
                        </strong>
                        에 해당합니다.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* 스타일 태그 */}
            {land.style_tags && land.style_tags.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {land.style_tags.map((tag, idx) => (
                  <span
                    key={idx}
                    className="px-3 py-1.5 bg-gradient-to-r from-indigo-50 to-purple-50 text-indigo-700 rounded-full text-sm font-medium border border-indigo-100 hover:from-indigo-100 hover:to-purple-100 transition-all cursor-default"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 이미지 + 부동산 온도 지수 (2컬럼) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        <div className="rounded-2xl border border-gray-200 bg-white shadow-sm h-fit overflow-visible">
          <div className="relative aspect-square bg-gray-100 group">
            <Image
              src={images[currentImageIndex]}
              alt={land.title}
              fill
              sizes="(max-width: 768px) 100vw, 50vw"
              className="object-cover"
            />

            <button onClick={handleLike} className="absolute top-4 right-4 hover:scale-110 transition-transform z-10">
              <Image src={liked ? '/icons/whish_on.png' : '/icons/whish_off.png'} alt="찜하기" width={40} height={40} />
            </button>

            {images.length > 1 && (
              <>
                <button
                  onClick={handlePrevImage}
                  className="absolute left-4 top-1/2 -translate-y-1/2 bg-white/80 hover:bg-white rounded-full w-10 h-10 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-10 text-xl"
                >
                  ‹
                </button>
                <button
                  onClick={handleNextImage}
                  className="absolute right-4 top-1/2 -translate-y-1/2 bg-white/80 hover:bg-white rounded-full w-10 h-10 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-10 text-xl"
                >
                  ›
                </button>
              </>
            )}

            <div className="absolute bottom-4 right-4 bg-black/60 text-white px-3 py-1 rounded-full text-sm">
              {currentImageIndex + 1} / {images.length}
            </div>
          </div>
        </div>

        {/* ✅ 부동산 온도 지수 + 아이콘 클릭 설명 토글 */}
        <div className="rounded-2xl border border-gray-200 bg-white shadow-sm flex flex-col aspect-square">
          <div className="bg-slate-700 text-white px-4 py-3 rounded-t-2xl">
            <h3 className="font-bold flex items-center gap-3">
              <span className="flex items-center gap-2">
                <span className="text-xl">🌡️</span>
                <span>부동산 온도</span>
              </span>
              <span className="text-[11px] text-gray-300 font-normal text-left flex-1">
                온도에 대해 궁금한점은 아이콘을 눌러보세요
              </span>
            </h3>
          </div>

          <div className="p-4 flex-1 overflow-hidden">
            <div className="flex h-full flex-col transition-all duration-300 ease-out">
              <div className={`flex-1 min-h-0 flex flex-col ${activeTemp ? 'gap-6' : ''}`}>
                <div
                  className={[
                    'overflow-hidden transition-all duration-500 ease-out',
                    activeTempItem && activeTemp ? 'max-h-[260px] opacity-100 translate-y-0' : 'max-h-0 opacity-0 -translate-y-2',
                  ].join(' ')}
                >
                  {activeTempItem && activeTemp && (
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                      <div className="grid grid-cols-[56px_1fr] items-center gap-4">
                        <button
                          type="button"
                          onClick={() => toggleTemp(activeTempItem.id as TempId)}
                          aria-pressed
                          aria-label={`${activeTempItem.label} 설명 닫기`}
                          className={[
                            'w-14 h-14 rounded-xl flex items-center justify-center text-[24px] shadow-sm border transition-all duration-200',
                            'bg-white border-gray-100 hover:scale-110 active:scale-105',
                            'ring-2 ring-slate-300',
                          ].join(' ')}
                          title={`${activeTempItem.label} 설명 닫기`}
                        >
                          {activeTempItem.icon}
                        </button>

                        <div>
                          <div className="flex items-center justify-between text-lg mb-2">
                            <span className="font-semibold text-slate-700">{activeTempItem.label}</span>
                            <span
                              className={`font-black ${activeTempItem.value >= 39
                                ? 'text-red-500'
                                : activeTempItem.value >= 35
                                  ? 'text-orange-500'
                                  : 'text-blue-500'
                                }`}
                            >
                              {activeTempItem.value.toFixed(1)}
                              <span className="text-base text-gray-400 ml-1">°C</span>
                            </span>
                          </div>
                          <div className="h-5 bg-gray-100 rounded-full p-[2px] shadow-inner overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-1000 ease-out relative bg-gradient-to-r from-blue-400 via-yellow-400 to-red-500"
                              style={{
                                width: `${Math.min(100, Math.max(0, ((activeTempItem.value - 13) / (60 - 13)) * 100))}%`,
                                backgroundSize: '500px 100%',
                              }}
                            >
                              <div className="absolute top-0 right-0 w-8 h-full bg-white/20 skew-x-[-20deg] animate-pulse"></div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div
                  className={[
                    'overflow-hidden transition-all duration-700 ease-out',
                    activeTemp ? 'max-h-[520px] opacity-100 translate-y-0' : 'max-h-0 opacity-0 translate-y-2',
                  ].join(' ')}
                >
                  {activeTempItem && activeTemp && (
                    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                      <div className="flex items-start justify-between gap-3 mb-4">
                        <div className="flex items-center gap-2">
                          <span className="text-xl">{activeTempItem.icon}</span>
                          <div>
                            <div className="text-lg font-extrabold text-slate-800">{activeTemp.title}</div>
                            <div className="text-sm text-slate-500">{activeTemp.subtitle}</div>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => setActiveTempId(null)}
                          className="text-xs text-slate-500 hover:text-slate-700"
                        >
                          닫기 X
                        </button>
                      </div>

                      <ul className="space-y-3 text-sm text-slate-700 leading-relaxed">
                        {activeTemp.body.map((line, idx) => (
                          <li key={idx} className="flex items-center gap-2">
                            <span className="mt-[6px] w-1.5 h-1.5 rounded-full bg-slate-300 shrink-0" />
                            <span>{line}</span>
                          </li>
                        ))}
                      </ul>

                      <div className="mt-4 text-xs text-slate-500">
                        * 온도는 전체 매물 분포 대비 상대적 위치를 보여주며, 36.5°C는 평균 기준선입니다.
                      </div>
                    </div>
                  )}
                </div>

                {!activeTemp && (
                  <div className="grid h-full grid-rows-5 gap-3 transition-all duration-300 ease-out">
                    {visibleTempItems.map((temp) => {
                      const isActive = activeTempId === (temp.id as TempId);

                      return (
                        <div key={temp.id} className="grid grid-cols-[56px_1fr] items-center gap-4 h-full">
                          <button
                            type="button"
                            onClick={() => toggleTemp(temp.id as TempId)}
                            aria-pressed={isActive}
                            aria-label={`${temp.label} 설명 ${isActive ? '닫기' : '보기'}`}
                            className={[
                              'w-14 h-14 rounded-xl flex items-center justify-center text-[24px] shadow-sm border transition-all duration-200',
                              'bg-gray-50 border-gray-100 hover:scale-110 active:scale-105',
                              isActive ? 'ring-2 ring-slate-300 bg-white' : '',
                            ].join(' ')}
                            title={`${temp.label} 설명 ${isActive ? '닫기' : '보기'}`}
                          >
                            {temp.icon}
                          </button>

                          <div>
                            <div className="flex items-center justify-between text-lg mb-2">
                              <span className="font-semibold text-slate-700">{temp.label}</span>
                              <span
                                className={`font-black ${temp.value >= 39 ? 'text-red-500' : temp.value >= 35 ? 'text-orange-500' : 'text-blue-500'
                                  }`}
                              >
                                {temp.value.toFixed(1)}
                                <span className="text-base text-gray-400 ml-1">°C</span>
                              </span>
                            </div>
                            <div className="h-5 bg-gray-100 rounded-full p-[2px] shadow-inner overflow-hidden">
                              <div
                                className="h-full rounded-full transition-all duration-1000 ease-out relative bg-gradient-to-r from-blue-400 via-yellow-400 to-red-500"
                                style={{
                                  width: `${Math.min(100, Math.max(0, ((temp.value - 13) / (60 - 13)) * 100))}%`,
                                  backgroundSize: '500px 100%',
                                }}
                              >
                                <div className="absolute top-0 right-0 w-8 h-full bg-white/20 skew-x-[-20deg] animate-pulse"></div>
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {activeTemp && (
                <div className="pt-4 mt-auto">
                  <div className="flex items-center justify-between">
                    {tempItems.map((temp) => {
                      const isActive = activeTempId === (temp.id as TempId);

                      return (
                        <button
                          key={temp.id}
                          type="button"
                          onClick={() => toggleTemp(temp.id as TempId)}
                          aria-label={`${temp.label} 설명 ${isActive ? '닫기' : '보기'}`}
                          className={[
                            'w-16 h-16 rounded-xl flex items-center justify-center text-[26px] shadow-sm border transition-all duration-200',
                            'bg-gray-50 border-gray-100 hover:scale-110 active:scale-105',
                            isActive ? 'ring-2 ring-slate-300 bg-white' : '',
                          ].join(' ')}
                          title={`${temp.label} 설명 ${isActive ? '닫기' : '보기'}`}
                        >
                          {temp.icon}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 2컬럼 레이아웃: 핵심정보 / 계약 및 매물정보 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 핵심정보 */}
        <div className="rounded-2xl border border-gray-200 bg-white shadow-sm flex flex-col">
          <div className="bg-slate-700 text-white px-4 py-2 rounded-t-2xl">
            <h3 className="font-bold text-sm">핵심정보</h3>
          </div>
          <div className="p-4 flex-1">
            <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <div className="flex justify-between border-b border-gray-100 pb-1">
                <span className="text-gray-500">거래유형</span>
                <span className="font-medium text-slate-800">{land.transaction_type || '-'}</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-1">
                <span className="text-gray-500">관리비</span>
                <span className="font-medium text-slate-800">{parseMaintenanceFee(land.maintenance_fee)}</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-1">
                <span className="text-gray-500">건물형태/용도</span>
                <span className="font-medium text-slate-800">{land.building_type || '-'}</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-1">
                <span className="text-gray-500">공급면적/전용</span>
                <span className="font-medium text-slate-800">
                  {(() => {
                    const supply = land.area_supply?.replace(/m2/gi, '㎡');
                    const exclusive = land.area_exclusive?.replace(/m2/gi, '㎡');
                    const hasSupply = supply && !supply.startsWith('-');
                    const hasExclusive = exclusive && !exclusive.startsWith('-');

                    if (hasSupply && hasExclusive) return `${supply} / ${exclusive}`;
                    if (hasSupply) return supply;
                    if (hasExclusive) return exclusive;
                    return '-';
                  })()}
                </span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-1">
                <span className="text-gray-500">방/욕실</span>
                <span className="font-medium text-slate-800">{land.room_count || '-'}</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-1">
                <span className="text-gray-500">해당층/전체층</span>
                <span className="font-medium text-slate-800">{land.floor || '-'}</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-1">
                <span className="text-gray-500">방향</span>
                <span className="font-medium text-slate-800">{land.direction || '-'}</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-1">
                <span className="text-gray-500">방거실형태</span>
                <span className="font-medium text-slate-800">{land.listing_info?.['방거실형태'] || '-'}</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-1">
                <span className="text-gray-500">주차</span>
                <span className="font-medium text-slate-800">{land.parking || '-'}</span>
              </div>
            </div>
          </div>
        </div>

        {/* 계약 및 매물정보 */}
        <div className="rounded-2xl border border-gray-200 bg-white shadow-sm flex flex-col">
          <div className="bg-slate-700 text-white px-4 py-2 rounded-t-2xl">
            <h3 className="font-bold text-sm">계약 및 매물정보</h3>
          </div>
          <div className="p-4 flex-1">
            <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
              <div className="flex justify-between border-b border-gray-100 pb-1">
                <span className="text-gray-500">입주가능일</span>
                <span className="font-medium text-slate-800">{land.move_in_date || '-'}</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-1">
                <span className="text-gray-500">사용승인일</span>
                <span className="font-medium text-slate-800">{land.approval_date || '-'}</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-1">
                <span className="text-gray-500">전세자금대출</span>
                <span className="font-medium text-slate-800">{land.jeonse_loan || '-'}</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-1">
                <span className="text-gray-500">전입신고</span>
                <span className="font-medium text-slate-800">{land.move_in_report || '-'}</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-1">
                <span className="text-gray-500">현입주고객</span>
                <span className="font-medium text-slate-800">가능</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-1">
                <span className="text-gray-500">융자금</span>
                <span className="font-medium text-slate-800">없음</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-1">
                <span className="text-gray-500">위반건축물</span>
                <span className="font-medium text-slate-800">아님</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 생활 및 옵션정보 */}
      {(categorizedFacilities.heating.length > 0 ||
        categorizedFacilities.cooling.length > 0 ||
        categorizedFacilities.living.length > 0 ||
        categorizedFacilities.security.length > 0 ||
        categorizedFacilities.facilities.length > 0 ||
        additionalOptions.length > 0) && (
          <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
            <div className="bg-slate-700 text-white px-4 py-2 rounded-t-2xl">
              <h3 className="font-bold text-sm">생활 및 옵션정보</h3>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Left Column: 난방방식, 냉방시설, 생활시설 */}
                <div className="space-y-6">
                  {/* 난방방식 */}
                  {categorizedFacilities.heating.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <Image src="/assets/land_details/heating.png" alt="난방방식" width={24} height={24} />
                        <h4 className="font-semibold text-slate-800">난방방식</h4>
                      </div>
                      <div className="flex flex-wrap gap-2 ml-8">
                        {categorizedFacilities.heating.map((item: string, idx: number) => (
                          <span key={idx} className="px-3 py-1 bg-orange-50 text-orange-700 rounded-full text-sm">
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 냉방시설 */}
                  {categorizedFacilities.cooling.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <Image src="/assets/land_details/cooling.png" alt="냉방시설" width={24} height={24} />
                        <h4 className="font-semibold text-slate-800">냉방시설</h4>
                      </div>
                      <div className="flex flex-wrap gap-2 ml-8">
                        {categorizedFacilities.cooling.map((item: string, idx: number) => (
                          <span key={idx} className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm">
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 생활시설 */}
                  {categorizedFacilities.living.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <Image src="/assets/land_details/life.png" alt="생활시설" width={24} height={24} />
                        <h4 className="font-semibold text-slate-800">생활시설</h4>
                      </div>
                      <div className="flex flex-wrap gap-2 ml-8">
                        {categorizedFacilities.living.map((item: string, idx: number) => (
                          <span key={idx} className="px-3 py-1 bg-teal-50 text-teal-700 rounded-full text-sm">
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Right Column: 보안시설, 기타시설, 추가옵션 */}
                <div className="space-y-6">
                  {/* 보안시설 */}
                  {categorizedFacilities.security.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <Image src="/assets/land_details/security.png" alt="보안시설" width={24} height={24} />
                        <h4 className="font-semibold text-slate-800">보안시설</h4>
                      </div>
                      <div className="flex flex-wrap gap-2 ml-8">
                        {categorizedFacilities.security.map((item: string, idx: number) => (
                          <span key={idx} className="px-3 py-1 bg-green-50 text-green-700 rounded-full text-sm">
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 기타시설 */}
                  {categorizedFacilities.facilities.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <Image src="/assets/land_details/facilities.png" alt="기타시설" width={24} height={24} />
                        <h4 className="font-semibold text-slate-800">기타시설</h4>
                      </div>
                      <div className="flex flex-wrap gap-2 ml-8">
                        {categorizedFacilities.facilities.map((item: string, idx: number) => (
                          <span key={idx} className="px-3 py-1 bg-purple-50 text-purple-700 rounded-full text-sm">
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 추가옵션 */}
                  {additionalOptions.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <Image src="/assets/land_details/options.png" alt="추가옵션" width={24} height={24} />
                        <h4 className="font-semibold text-slate-800">추가옵션</h4>
                      </div>
                      <div className="flex flex-wrap gap-2 ml-8">
                        {additionalOptions.map((option: string, idx: number) => (
                          <span key={idx} className="px-3 py-1 bg-gray-50 text-gray-700 rounded-full text-sm border border-gray-200">
                            {option}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

      {/* 상세 설명 섹션 */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
        <div className="bg-slate-700 text-white px-4 py-2 rounded-t-2xl">
          <h3 className="font-bold text-sm">상세 설명</h3>
        </div>
        <div className="p-4">
          <p className="text-slate-700 whitespace-pre-line leading-relaxed text-sm">
            {land.description || '상세 설명이 없습니다.'}
          </p>
        </div>
      </div>

      {/* 중개사 정보 */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
        <div className="bg-slate-700 text-white px-4 py-2 rounded-t-2xl">
          <h3 className="font-bold text-sm">중개사 정보</h3>
        </div>
        <div className="p-4">
          <div className="flex items-start gap-4">
            <div className="flex-1 space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-gray-500 w-24">중개사무소</span>
                <span className="font-semibold text-slate-800">{land.broker?.office_name || '-'}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-500 w-24">대표자</span>
                <span className="font-semibold text-slate-800">{land.broker?.representative || '-'}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-500 w-24">연락처</span>
                <span className="font-semibold text-slate-800">{land.broker?.phone || '-'}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-500 w-24">중개사무소 주소</span>
                <span className="font-semibold text-slate-800 text-xs">{land.broker?.address || '-'}</span>
              </div>

              {/* 신뢰도 등급 표시 + PNG 아이콘 */}
              {land.broker?.trust_score && (
                <div className="flex items-center gap-2 pt-2 border-t border-gray-200">
                  <span className="text-gray-500 w-24">신뢰도</span>
                  {getTrustBadgeImage(land.broker.trust_score) && (
                    <Image
                      src={getTrustBadgeImage(land.broker.trust_score)!}
                      alt={`${land.broker.trust_score}`}
                      width={36}
                      height={36}
                      className="object-contain"
                    />
                  )}
                  <span className={`px-3 py-1 rounded-full text-sm font-bold ${land.broker.trust_score === 'A' ? 'bg-yellow-500 text-white' :
                    land.broker.trust_score === 'B' ? 'bg-gray-400 text-white' :
                      'bg-amber-700 text-white'
                    }`}>
                    {land.broker.trust_score === 'A' ? '골드' : land.broker.trust_score === 'B' ? '실버' : '브론즈'}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
