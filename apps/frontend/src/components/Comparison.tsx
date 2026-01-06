/**
 * Comparison 컴포넌트
 *
 * 매물 비교 컴포넌트
 *
 * 주요 기능:
 * - 두 개 이상의 매물을 나란히 비교 표시 (최대 3개)
 *
 * 사용 컴포넌트:
 * - LandImage: 매물 사진 표시
 */

'use client'

import { useState, useEffect, useMemo } from 'react'
import { useSession } from 'next-auth/react'
import axiosInstance from '@/lib/axios'
import LandImage from './LandImage'

interface LandData {
  id: string
  images?: string[]
  price: string
  deposit?: string
  monthlyRent?: string
  buildingType?: string
  area?: string
  floor?: string
  totalFloor?: string
  rooms?: number
  bathrooms?: number
  temperature?: number
  // 추가 필드
  direction?: string
  parking?: string
  heating?: string
  elevator?: string
  moveInDate?: string
  address?: string
  // ML 예측
  pricePredictionLabel?: string
  pricePredictionProb?: number
  // 중개사 신뢰도
  brokerTrustScore?: string
  brokerTrustGrade?: string
  // 온도 데이터
  temperatures?: {
    safety?: number
    traffic?: number
    convenience?: number
    culture?: number
    pet?: number
  }
}

interface ComparisonProps {
  lands?: LandData[]
  land1?: LandData
  land2?: LandData
}

export default function Comparison({ lands, land1, land2 }: ComparisonProps) {
  // lands prop이 있으면 사용, 없으면 land1, land2 사용 (하위 호환성)
  const compareData = lands && lands.length >= 2 ? lands : (land1 && land2 ? [land1, land2] : [])

  // 찜 목록에서 온 매물이므로 기본값은 모두 true (빨간 하트)
  const [likedStates, setLikedStates] = useState<Record<string, boolean>>(() => {
    const initialStates: Record<string, boolean> = {}
    compareData.forEach(land => {
      initialStates[land.id] = true
    })
    return initialStates
  })

  // 사용자 세션 및 우선순위
  const { data: session } = useSession()
  const [userPriorities, setUserPriorities] = useState<Record<string, number>>({})

  // 사용자 우선순위 가져오기
  useEffect(() => {
    if (!session) return
    axiosInstance.get('/api/users/preference-survey/')
      .then(res => {
        if (res.data?.priorities) {
          setUserPriorities(res.data.priorities)
        }
      })
      .catch(() => { })
  }, [session])

  // 우선순위 라벨 → ID 매핑
  const priorityLabelToId: Record<string, string> = {
    '안전': 'safety',
    '교통': 'traffic',
    '편의시설': 'convenience',
    '문화': 'culture',
    '반려동물': 'pet',
  }

  // 온도 카테고리 목록 (정렬 가능)
  const tempCategories = useMemo(() => {
    const items = [
      { id: 'safety', label: '안전', icon: '🛡️' },
      { id: 'traffic', label: '교통', icon: '🚇' },
      { id: 'convenience', label: '편의시설', icon: '🛒' },
      { id: 'culture', label: '문화', icon: '🏛️' },
      { id: 'pet', label: '반려동물', icon: '🐾' },
    ]

    if (Object.keys(userPriorities).length === 0) {
      return items
    }

    const idToPriority: Record<string, number> = {}
    for (const [label, rank] of Object.entries(userPriorities)) {
      const id = priorityLabelToId[label]
      if (id) idToPriority[id] = rank
    }

    return [...items].sort((a, b) => {
      const priorityA = idToPriority[a.id] ?? 99
      const priorityB = idToPriority[b.id] ?? 99
      return priorityA - priorityB
    })
  }, [userPriorities])

  // 매물이 2개 미만일 때
  if (compareData.length < 2) {
    return (
      <div className="max-w-7xl mx-auto p-6">
        <h2 className="text-3xl font-bold text-center mb-8">매물 비교</h2>
        <div className="bg-gray-50 rounded-lg p-12 text-center">
          <p className="text-gray-600 text-lg">
            비교할 매물을 선택해주세요. 최소 2개의 매물을 선택해야 비교할 수 있습니다.
          </p>
        </div>
      </div>
    )
  }

  const toggleLike = (landId: string) => {
    setLikedStates(prev => ({ ...prev, [landId]: !prev[landId] }))
  }

  // 탭 상태 (info: 매물정보, temp: 온도정보)
  const [activeTab, setActiveTab] = useState<'info' | 'temp'>('info')

  // 그리드 컬럼 개수 결정 (2개 또는 3개)
  const gridCols = compareData.length === 2 ? 'grid-cols-2' : 'grid-cols-3'

  // 온도 바 컬러 계산
  const getTempColor = (value: number) => {
    if (value >= 45) return 'bg-red-500'
    if (value >= 40) return 'bg-orange-500'
    if (value >= 35) return 'bg-yellow-500'
    return 'bg-blue-500'
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      <h2 className="text-3xl font-bold text-center mb-4" style={{ color: '#16375B' }}>매물 비교</h2>

      {/* 탭 버튼 */}
      <div className="flex justify-center gap-2 mb-8">
        <button
          onClick={() => setActiveTab('info')}
          className={`px-6 py-2 rounded-full font-semibold transition-all ${activeTab === 'info'
            ? 'bg-blue-600 text-white shadow-lg'
            : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
            }`}
        >
          📋 매물 정보
        </button>
        <button
          onClick={() => setActiveTab('temp')}
          className={`px-6 py-2 rounded-full font-semibold transition-all ${activeTab === 'temp'
            ? 'bg-blue-600 text-white shadow-lg'
            : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
            }`}
        >
          🌡️ 온도 비교
        </button>
      </div>

      {/* 매물 비교 */}
      <div className={`grid ${gridCols} gap-8 mb-8`}>
        {compareData.map((land, index) => (
          <div key={land.id} className="bg-white rounded-lg shadow-md p-6">
            {/* 매물 번호 라벨 */}
            <div className="mb-3">
              <span className="bg-blue-600 text-white px-3 py-1 rounded-full text-sm font-bold" style={{ color: '#ffffff' }}>
                매물{index + 1}
              </span>
            </div>

            {/* 매물 이미지 */}
            <LandImage
              id={land.id}
              images={land.images}
              price={land.price}
              temperature={land.temperature}
              onLike={() => toggleLike(land.id)}
              isLiked={likedStates[land.id] || false}
            />

            {/* 매물 정보 탭 */}
            {activeTab === 'info' && (
              <div className="mt-6 space-y-3">
                {/* 위치 */}
                {land.address && (
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-gray-600">위치</span>
                    <span className="font-semibold">{land.address}</span>
                  </div>
                )}
                {land.deposit && (
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-gray-600">보증금</span>
                    <span className="font-semibold">{land.deposit}</span>
                  </div>
                )}
                {land.monthlyRent && (
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-gray-600">월세</span>
                    <span className="font-semibold">{land.monthlyRent}</span>
                  </div>
                )}
                {land.buildingType && (
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-gray-600">건축물 용도</span>
                    <span className="font-semibold">{land.buildingType}</span>
                  </div>
                )}
                {land.area && (
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-gray-600">공급면적</span>
                    <span className="font-semibold">{land.area}</span>
                  </div>
                )}
                {land.floor && (
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-gray-600">층수</span>
                    <span className="font-semibold">{land.floor}</span>
                  </div>
                )}
                {land.rooms && (
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-gray-600">방</span>
                    <span className="font-semibold">{land.rooms}</span>
                  </div>
                )}
                {land.direction && (
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-gray-600">방향</span>
                    <span className="font-semibold">{land.direction}</span>
                  </div>
                )}
                {land.parking && (
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-gray-600">주차</span>
                    <span className="font-semibold">{land.parking}</span>
                  </div>
                )}
                {land.heating && (
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-gray-600">난방방식</span>
                    <span className="font-semibold">{land.heating}</span>
                  </div>
                )}
                {land.elevator && (
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-gray-600">엘리베이터</span>
                    <span className="font-semibold">{land.elevator}</span>
                  </div>
                )}
                {land.moveInDate && (
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-gray-600">입주가능일</span>
                    <span className="font-semibold">{land.moveInDate}</span>
                  </div>
                )}
                {/* 중개사 신뢰도 */}
                {land.brokerTrustScore && (
                  <div className="flex justify-between border-b pb-2 bg-purple-50 p-2 rounded">
                    <span className="text-purple-700 font-medium">🏢 중개사 신뢰도</span>
                    <span className={`font-bold ${land.brokerTrustScore === 'A' ? 'text-yellow-600' :
                      land.brokerTrustScore === 'B' ? 'text-gray-600' :
                        'text-amber-700'
                      }`}>
                      {land.brokerTrustScore === 'A' ? '골드' : land.brokerTrustScore === 'B' ? '실버' : '브론즈'}
                    </span>
                  </div>
                )}
                {/* 실거래가 판단 */}
                {land.pricePredictionLabel && (
                  <div
                    className="flex justify-between border-b pb-2 bg-blue-50 p-2 rounded cursor-help"
                    title="해당 행정동의 건물용도별 평당가 대비 ML 모델이 분석한 결과입니다."
                  >
                    <span className="text-blue-700 font-medium">📊 실거래가 판단</span>
                    <span className={`font-bold ${land.pricePredictionLabel === '저렴' ? 'text-green-600' :
                      land.pricePredictionLabel === '적정' ? 'text-blue-600' :
                        'text-red-600'
                      }`}>
                      {land.pricePredictionLabel}
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* 온도 정보 탭 */}
            {activeTab === 'temp' && (
              <div className="mt-6 space-y-5">
                {/* 우선순위 순서대로 온도 목록 렌더링 */}
                {tempCategories.map((cat) => {
                  const tempValue = (land.temperatures as any)?.[cat.id] || 36.5
                  // 온도 바 게이지 비율 계산 (13~60 범위 기준 - LandDetail과 동일)
                  const fillWidth = Math.min(100, Math.max(0, ((tempValue - 13) / (60 - 13)) * 100))
                  return (
                    <div key={cat.id} className="bg-white rounded-xl p-4 shadow-sm">
                      {/* 라벨 & 온도값 */}
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <span className="text-2xl">{cat.icon}</span>
                          <span className="text-gray-700 font-medium">{cat.label} 온도</span>
                        </div>
                        <span
                          className={`font-bold text-lg ${tempValue >= 39 ? 'text-red-500' : tempValue >= 35 ? 'text-orange-500' : 'text-blue-500'}`}
                          style={{
                            color: tempValue >= 39 ? '#ef4444' : tempValue >= 35 ? '#f97316' : '#3b82f6'
                          }}
                        >
                          {tempValue.toFixed(1)}°C
                        </span>
                      </div>
                      {/* 게이지 바 - LandDetail과 동일한 스타일 */}
                      <div className="h-5 bg-gray-100 rounded-full p-[2px] shadow-inner overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-1000 ease-out bg-gradient-to-r from-blue-400 via-yellow-400 to-red-500"
                          style={{
                            width: `${fillWidth}%`,
                            backgroundSize: '500px 100%'
                          }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
