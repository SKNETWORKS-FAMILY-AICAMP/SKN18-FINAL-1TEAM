/**
 * WishListPage 컴포넌트
 *
 * 찜 리스트 페이지
 *
 * - LandImage.tsx (매물 이미지)
 * - Pagination.tsx (페이지네이션)
 * - Button.tsx (비교하기 버튼)
 * - Comparison.tsx (매물 비교)
 */

'use client'

import { useState, useEffect } from 'react'
import SideTab from '@/components/SideTab'
import LandImage from '@/components/LandImage'
import Comparison from '@/components/Comparison'
import Button from '@/components/Button'
import LoadingSpinner from '@/components/LoadingSpinner'
import { fetchWishlist } from '@/api/wishlistApi'
import { fetchLandById } from '@/api/landApi'
import { Land } from '@/types/land'

export default function WishListPage() {
  // sessionStorage에서 비교 상태 복원
  const [showComparison, setShowComparison] = useState(() => {
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem('wishlist_showComparison') === 'true'
    }
    return false
  })
  const [selectedLands, setSelectedLands] = useState<number[]>(() => {
    if (typeof window !== 'undefined') {
      const saved = sessionStorage.getItem('wishlist_selectedLands')
      return saved ? JSON.parse(saved) : []
    }
    return []
  })
  const [wishlistLands, setWishlistLands] = useState<Land[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 8
  const totalPages = Math.ceil(wishlistLands.length / pageSize)

  // 비교 상태 변경 시 sessionStorage에 저장
  useEffect(() => {
    sessionStorage.setItem('wishlist_showComparison', String(showComparison))
  }, [showComparison])

  // 선택된 매물 변경 시 sessionStorage에 저장
  useEffect(() => {
    sessionStorage.setItem('wishlist_selectedLands', JSON.stringify(selectedLands))
  }, [selectedLands])

  // 찜 매물 데이터 로드
  useEffect(() => {
    async function loadWishlist() {
      try {
        setLoading(true)
        setError(null)

        // 1. 찜 목록 가져오기
        const wishlist = await fetchWishlist()

        // 2. 각 찜 매물의 상세 정보 가져오기
        const landPromises = wishlist.map(item =>
          fetchLandById(item.listing_id)
        )
        const lands = await Promise.all(landPromises)

        setWishlistLands(lands)
      } catch (err) {
        setError('찜 매물을 불러오는데 실패했습니다.')
      } finally {
        setLoading(false)
      }
    }

    loadWishlist()
  }, [])

  // 매물 선택/해제 핸들러
  const handleSelectLand = (landId: number) => {
    setSelectedLands((prev) => {
      if (prev.includes(landId)) {
        // 이미 선택된 경우 제거
        return prev.filter((id) => id !== landId)
      }
      if (prev.length < 3) {
        // 최대 3개까지만 선택 가능
        return [...prev, landId]
      }
      alert('최대 3개까지만 선택할 수 있습니다.')
      return prev
    })
  }

  // 가격 포맷팅 함수
  const formatPrice = (land: Land) => {
    if (land.deal_type === '월세') {
      return `월세 ${land.deposit || 0} / ${land.monthly_rent || 0}`
    } else if (land.deal_type === '전세') {
      return `전세 ${land.deposit || 0}`
    }
    return land.price || '가격 정보 없음'
  }

  // 온도 계산 (가격 예측 정보 기반)
  const getTemperature = (land: Land): number => {
    if (land.price_prediction) {
      const label = land.price_prediction.predicted_label_kr;
      if (label === '저렴') return 0.3
      if (label === '적정') return 0.6
      if (label === '비쌈') return 0.9
    }
    return 0.5
  }


  // 선택된 매물 데이터 가져오기 (Comparison 컴포넌트용으로 변환)
  const getSelectedLandData = () => {
    return selectedLands
      .map((id) => {
        const land = wishlistLands.find((l) => l.id === id)
        if (!land) return null

        // Land 타입을 LandData 타입으로 변환
        return {
          id: land.id.toString(),
          images: land.images,
          price: formatPrice(land),
          deposit: land.deposit ? `${land.deposit.toLocaleString()}만원` : undefined,
          monthlyRent: land.monthly_rent ? `${land.monthly_rent.toLocaleString()}만원` : undefined,
          buildingType: land.building_type,
          area: land.area_exclusive || land.area_supply,
          floor: land.floor,
          rooms: land.room_count,
          bathrooms: undefined, // 중복 제거 - 이미지에서 방/욕실에서 표시됨
          // 추가 필드
          direction: land.direction?.includes('/') ? land.direction.split('/')[1] : land.direction,
          parking: land.parking,
          heating: land.heating_method,
          elevator: land.elevator, // 관리비 제거, 엘리베이터 추가
          moveInDate: land.move_in_date,
          address: land.address,
          // 중개사 온도 (temperature)
          temperature: land.temperature,
          // ML 가격 예측
          pricePredictionLabel: land.price_prediction?.predicted_label_kr,
          pricePredictionProb: land.price_prediction?.underpriced_prob ||
            land.price_prediction?.fair_prob ||
            land.price_prediction?.overpriced_prob,
          // 중개사 신뢰도
          brokerTrustScore: land.broker?.trust_score,
          brokerTrustGrade: land.broker?.trust_grade,
          // 온도 데이터
          temperatures: land.temperatures,
        }
      })
      .filter(Boolean) as any[]
  }

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <SideTab />
        <LoadingSpinner message="찜 매물을 불러오는 중..." />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <SideTab />
        <div>
          <div className="bg-red-50 border border-red-200 rounded-lg p-12 text-center">
            <p className="text-red-600">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* 가로 탭 */}
      <SideTab />

      {/* 컨텐츠 영역 */}
      <div>

        {!showComparison ? (
          <>
            {/* 선택 안내 */}
            <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-2xl p-4 mb-6 shadow-sm">
              <p className="text-sm text-blue-800 font-medium">
                💡 비교할 매물을 선택하세요 (최대 3개) - 현재 <span className="font-bold text-blue-600">{selectedLands.length}</span>개 선택됨
              </p>
            </div>

            {/* 찜한 매물 목록 - 2행 4열 고정 그리드 */}
            <div className="grid grid-cols-4 gap-4 mb-6">
              {/* 현재 페이지의 매물들 */}
              {wishlistLands
                .slice((currentPage - 1) * pageSize, currentPage * pageSize)
                .map((land) => (
                  <div key={land.id} className="bg-white rounded-xl shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden">
                    <div className="relative">
                      {/* 커스텀 체크박스 */}
                      <div className="absolute top-3 left-3 z-10">
                        <label className="relative flex items-center justify-center w-6 h-6 cursor-pointer group">
                          <input
                            type="checkbox"
                            checked={selectedLands.includes(land.id)}
                            onChange={() => handleSelectLand(land.id)}
                            className="sr-only"
                          />
                          <div className={`w-6 h-6 border-2 rounded-lg backdrop-blur-sm transition-all duration-200 group-hover:scale-110 shadow-lg ${selectedLands.includes(land.id)
                            ? 'bg-[#16375B] border-[#16375B]'
                            : 'bg-black/20 border-white'
                            }`}>
                            <svg
                              className={`w-full h-full text-white transition-opacity duration-200 ${selectedLands.includes(land.id) ? 'opacity-100' : 'opacity-0'
                                }`}
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={3}
                                d="M5 13l4 4L19 7"
                              />
                            </svg>
                          </div>
                        </label>
                      </div>
                      <LandImage
                        id={land.id.toString()}
                        images={land.images}
                        price={formatPrice(land)}
                        isLiked={true}
                        onLike={async () => {
                          // 찜 해제 시 목록에서 제거
                          try {
                            const { removeWishlist } = await import('@/api/wishlistApi');
                            await removeWishlist(land.id);
                            // 상태 업데이트하여 UI에서 제거
                            setWishlistLands(prev => prev.filter(l => l.id !== land.id));
                          } catch (error) {
                            console.error('Failed to remove from wishlist:', error);
                          }
                        }}
                      />
                    </div>
                    {/* 주소 정보 */}
                    <div className="px-3 pb-3">
                      <p className="text-sm text-gray-600 truncate flex items-center gap-1" title={land.address}>
                        <span className="text-blue-500">📍</span>
                        {land.address || '주소 정보 없음'}
                      </p>
                    </div>
                  </div>
                ))}

              {/* 빈 슬롯 (8개 채우기) */}
              {Array.from({
                length: Math.max(0, pageSize - wishlistLands.slice((currentPage - 1) * pageSize, currentPage * pageSize).length)
              }).map((_, index) => (
                <div key={`empty-${index}`} className="bg-slate-50/50 rounded-xl border-2 border-dashed border-slate-200 min-h-[280px]"></div>
              ))}
            </div>

            {/* 빈 상태 메시지 */}
            {wishlistLands.length === 0 && (
              <div className="bg-white/50 border-2 border-white/40 backdrop-blur-md rounded-2xl p-12 text-center shadow-lg mb-6">
                <p className="text-slate-500 text-lg font-medium">찜한 매물이 없습니다.</p>
                <p className="text-slate-400 text-sm mt-2">마음에 드는 매물을 찜해보세요! ❤️</p>
              </div>
            )}

            {/* 페이지네이션 */}
            {wishlistLands.length > 0 && (
              <div className="flex items-center justify-center mb-8">
                <div className="inline-flex items-center gap-1 p-2 rounded-2xl bg-white/60 backdrop-blur-md border border-white/40 shadow-lg">
                  {/* 이전 버튼 */}
                  <button
                    type="button"
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={currentPage === 1}
                    className="w-9 h-9 rounded-xl flex items-center justify-center text-slate-500 disabled:text-slate-300 disabled:cursor-not-allowed hover:bg-blue-50 hover:text-blue-600 transition-all duration-200"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                  </button>

                  {/* 페이지 번호 */}
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                    <button
                      key={page}
                      type="button"
                      onClick={() => setCurrentPage(page)}
                      className={`
                        w-9 h-9 rounded-xl text-sm font-semibold transition-all duration-200
                        ${page === currentPage
                          ? 'bg-[#16375B] text-white shadow-lg shadow-[#16375B]/30 scale-105'
                          : 'text-slate-600 hover:bg-slate-50 hover:text-[#16375B]'
                        }
                      `}
                    >
                      {page}
                    </button>
                  ))}

                  {/* 다음 버튼 */}
                  <button
                    type="button"
                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    disabled={currentPage === totalPages}
                    className="w-9 h-9 rounded-xl flex items-center justify-center text-slate-500 disabled:text-slate-300 disabled:cursor-not-allowed hover:bg-blue-50 hover:text-blue-600 transition-all duration-200"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                </div>
              </div>
            )}

            {/* 비교하기 버튼 */}
            <div className="flex justify-center mt-8">
              <Button
                variant="primary"
                onClick={() => setShowComparison(true)}
                disabled={selectedLands.length < 2}
              >
                매물 비교하기 ({selectedLands.length}/3)
              </Button>
            </div>
          </>
        ) : (
          <>
            {/* 매물 비교 */}
            <Comparison lands={getSelectedLandData()} />

            {/* 목록으로 돌아가기 버튼 */}
            <div className="flex justify-center mt-8">
              <Button
                variant="secondary"
                onClick={() => setShowComparison(false)}
              >
                목록으로 돌아가기
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
