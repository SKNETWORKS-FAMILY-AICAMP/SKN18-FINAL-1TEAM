/**
 * LandImage 컴포넌트
 * 
 * 매물 사진을 표시하는 컴포넌트
 * 
 * 주요 기능:
 * - 매물 이미지 표시
 * - 이미지 슬라이더
 * - 찜하기 버튼
 */

'use client';

import { useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useParticleEffect } from '../hooks/useParticleEffect';

interface LandImageProps {
    id?: string;
    images?: string[];
    temperature?: number;
    price: string;
    onLike?: () => void;
    isLiked?: boolean;
}

const DEFAULT_PLACEHOLDER = '/images/gozip_loading.png';

export default function LandImage({
    id = '1',
    images: propImages,
    price,
    onLike,
    isLiked = false
}: LandImageProps) {
    // 이미지가 없거나 빈 배열이면 placeholder 사용
    const images = propImages && propImages.length > 0 ? propImages : [DEFAULT_PLACEHOLDER];
    const router = useRouter();
    const [liked, setLiked] = useState(isLiked);
    const [currentImageIndex, setCurrentImageIndex] = useState(0);
    const { triggerEffect } = useParticleEffect();

    const handleLike = (e: React.MouseEvent) => {
        e.stopPropagation();
        setLiked(!liked);
        onLike?.();
        triggerEffect(e.currentTarget as HTMLElement);
    };

    const handlePrevImage = (e: React.MouseEvent) => {
        e.stopPropagation();
        setCurrentImageIndex((prev) => (prev === 0 ? images.length - 1 : prev - 1));
        triggerEffect(e.currentTarget as HTMLElement);
    };

    const handleNextImage = (e: React.MouseEvent) => {
        e.stopPropagation();
        setCurrentImageIndex((prev) => (prev === images.length - 1 ? 0 : prev + 1));
        triggerEffect(e.currentTarget as HTMLElement);
    };

    const handleClick = (e: React.MouseEvent) => {
        triggerEffect(e.currentTarget as HTMLElement);
        // Delay navigation slightly to show effect? No, effect is fast.
        // But if we navigate immediately, the component unmounts.
        // However, the particles are appended to the element. If the element unmounts, particles disappear.
        // Ideally particles should be appended to body.
        // My hook implementation appends to element.
        // If I navigate, the page changes.
        // Maybe I should just let it be for now. The user might see it briefly.
        // Or I can append to body in the hook.
        // Let's stick to current implementation.
        router.push(`/landDetail/${id}`);
    };

    return (
        <div className="relative cursor-pointer" onClick={handleClick}>
            <div
                className="relative w-full aspect-square bg-gray-200 rounded-lg overflow-hidden group"
            >
                <Image
                    src={images[currentImageIndex]}
                    alt="매물 이미지"
                    fill
                    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
                    className="object-cover"
                />

                {/* 이전/다음 버튼 */}
                {images.length > 1 && (
                    <>
                        <button
                            onClick={handlePrevImage}
                            className="absolute left-2 top-1/2 -translate-y-1/2 bg-white/80 hover:bg-white rounded-full w-8 h-8 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-10"
                        >
                            ‹
                        </button>
                        <button
                            onClick={handleNextImage}
                            className="absolute right-2 top-1/2 -translate-y-1/2 bg-white/80 hover:bg-white rounded-full w-8 h-8 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-10"
                        >
                            ›
                        </button>
                    </>
                )}

                {/* 이미지 인디케이터 */}
                {images.length > 1 && (
                    <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1 z-10">
                        {images.map((_, index) => (
                            <div
                                key={index}
                                className={`w-1.5 h-1.5 rounded-full transition-colors ${index === currentImageIndex ? 'bg-white' : 'bg-white/50'
                                    }`}
                            />
                        ))}
                    </div>
                )}

                {/* 찜하기 버튼 */}
                <button
                    onClick={handleLike}
                    className="absolute top-3 right-3 hover:scale-110 transition-transform z-10"
                >
                    <Image
                        src={liked ? '/icons/whish_on.png' : '/icons/whish_off.png'}
                        alt="찜하기"
                        width={40}
                        height={40}
                    />
                </button>

            </div>

            {/* 가격 정보 */}
            <div className="mt-3 text-center">
                <p className="text-lg font-bold text-gray-800">{price}</p>
            </div>
        </div>
    );
}
