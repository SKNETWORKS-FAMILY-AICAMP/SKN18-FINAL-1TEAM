/**
 * MarkerInfo 컴포넌트
 * 
 * 지도 마커 정보 컴포넌트 - Neo4j 연동
 * 
 * 주요 기능:
 * - 주변 시설 정보 표시 (의료, 편의, 대중교통, CCTV)
 * - 카테고리 클릭 시 지도에 해당 시설 표시
 */

'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import { fetchNearbyFacilities, NearbyFacilities } from '../api/landApi';

interface MarkerInfoProps {
    landId?: string;
    onCategoryClick?: (category: string, isActive: boolean) => void;
}

export default function MarkerInfo({ landId, onCategoryClick }: MarkerInfoProps) {
    const [facilities, setFacilities] = useState<NearbyFacilities | null>(null);
    const [loading, setLoading] = useState(true);
    const [activeCategories, setActiveCategories] = useState<Set<string>>(new Set());

    useEffect(() => {
        const loadFacilities = async () => {
            if (!landId) {
                setLoading(false);
                return;
            }

            try {
                setLoading(true);
                const data = await fetchNearbyFacilities(landId);
                setFacilities(data);
                console.log('주변 시설 데이터 로드:', data);
            } catch (error) {
                console.error('Failed to fetch nearby facilities:', error);
            } finally {
                setLoading(false);
            }
        };

        loadFacilities();
    }, [landId]);

    const handleClick = (e: React.MouseEvent, category: string) => {
        // 카테고리 활성화/비활성화 토글
        setActiveCategories(prev => {
            const newSet = new Set(prev);
            if (newSet.has(category)) {
                newSet.delete(category);
                onCategoryClick?.(category, false);
            } else {
                newSet.add(category);
                onCategoryClick?.(category, true);
            }
            return newSet;
        });
    };

    // 기본 데이터 (API 실패 시 또는 로딩 중)
    const defaultFacilities = [
        {
            id: 'transportation',
            name: '대중교통',
            icon: '/assets/map_pin/bus.png',
            count: facilities?.transportation?.count ?? 0
        },
        {
            id: 'convenience',
            name: '편의시설',
            icon: '/assets/map_pin/convenience.png',
            count: facilities?.convenience?.count ?? 0
        },
        {
            id: 'medical',
            name: '의료시설',
            icon: '/assets/map_pin/medical_facilities.png',
            count: facilities?.medical?.count ?? 0
        },
        {
            id: 'safety',
            name: '치안/안전',
            icon: '/assets/map_pin/cctv.png',
            count: facilities?.safety?.count ?? 0
        }
    ];

    return (
        <div className="rounded-2xl border border-gray-200 bg-white shadow-sm h-[450px]">
            <div className="bg-slate-700 text-white px-4 py-2 rounded-t-2xl">
                <h3 className="font-bold text-sm" style={{ color: '#ffffff' }}>주변 시설 정보</h3>
            </div>

            <div className="p-4">
                {loading ? (
                    <div className="flex justify-center items-center h-64">
                        <div className="w-6 h-6 border-3 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {defaultFacilities.map((marker) => {
                            const isActive = activeCategories.has(marker.id);
                            return (
                                <div
                                    key={marker.id}
                                    onClick={(e) => handleClick(e, marker.id)}
                                    className={`flex items-center gap-3 p-3 rounded-xl transition-all cursor-pointer border ${isActive
                                        ? 'bg-blue-50 border-blue-300 shadow-sm'
                                        : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
                                        }`}
                                >
                                    <div className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center ${isActive ? 'bg-blue-100' : 'bg-white border border-gray-200'
                                        }`}>
                                        <Image
                                            src={marker.icon}
                                            alt={marker.name}
                                            width={24}
                                            height={24}
                                            className="object-contain"
                                        />
                                    </div>

                                    <div className="flex-1">
                                        <div className="flex items-center justify-between">
                                            <h4 className="font-semibold text-slate-800 text-sm">{marker.name}</h4>
                                            <span className={`text-base font-bold ${isActive ? 'text-blue-600' : 'text-slate-600'}`}>
                                                {marker.count}개
                                            </span>
                                        </div>
                                    </div>

                                    {/* 활성화 인디케이터 */}
                                    <div className={`w-2.5 h-2.5 rounded-full transition-colors ${isActive ? 'bg-blue-500' : 'bg-gray-300'
                                        }`}></div>
                                </div>
                            );
                        })}
                    </div>
                )}

                <p className="text-xs text-gray-400 mt-4 text-center">
                    카테고리를 클릭하면 지도에 표시됩니다
                </p>
            </div>
        </div>
    );
}
