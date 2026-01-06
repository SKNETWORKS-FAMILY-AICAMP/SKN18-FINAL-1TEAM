/**
 * PreferenceFilter 컴포넌트
 * 
 * 사용자 선호도 기반 매물 필터링 컴포넌트
 * 
 * 주요 기능:
 * - 버튼 형태의 필터 옵션 선택 (치안/안전, 교통, 편의시설, 문화, 반려동물, 초기화)
 * - 선택된 필터 조건 표시
 */

'use client';

import {
    motion,
    MotionValue,
    useMotionValue,
    useSpring,
    useTransform,
    type SpringOptions,
    AnimatePresence
} from 'framer-motion';
import React, { Children, cloneElement, useEffect, useMemo, useRef, useState } from 'react';
import { useParticleEffect } from '../hooks/useParticleEffect';

// --- Dock Components ---

type DockItemProps = {
    className?: string;
    children: React.ReactNode;
    onClick?: (event: React.MouseEvent<HTMLDivElement>) => void;
    mouseX: MotionValue<number>;
    spring: SpringOptions;
    distance: number;
    baseItemSize: number;
    magnification: number;
    isSelected?: boolean;
};

function DockItem({
    children,
    className = '',
    onClick,
    mouseX,
    spring,
    distance,
    magnification,
    baseItemSize,
    isSelected
}: DockItemProps) {
    const ref = useRef<HTMLDivElement>(null);
    const isHovered = useMotionValue(0);

    const mouseDistance = useTransform(mouseX, (val: number) => {
        const rect = ref.current?.getBoundingClientRect() ?? {
            x: 0,
            width: baseItemSize
        };
        return val - rect.x - baseItemSize / 2;
    });

    const targetSize = useTransform(mouseDistance, [-distance, 0, distance], [baseItemSize, magnification, baseItemSize]);
    const size = useSpring(targetSize, spring);

    return (
        <motion.div
            ref={ref}
            style={{
                width: size,
                height: size
            }}
            onHoverStart={() => isHovered.set(1)}
            onHoverEnd={() => isHovered.set(0)}
            onFocus={() => isHovered.set(1)}
            onBlur={() => isHovered.set(0)}
            onClick={onClick}
            className={`
                relative inline-flex items-center justify-center rounded-full border-2 shadow-md cursor-pointer
                transition-colors duration-200
                ${isSelected
                    ? 'bg-gradient-to-r from-purple-600 via-blue-600 to-cyan-500 border-purple-500 text-white shadow-lg shadow-purple-500/30'
                    : 'bg-white/80 border-slate-200 text-slate-600 hover:bg-white hover:border-purple-300'
                }
                ${className}
            `}
            tabIndex={0}
            role="button"
            aria-pressed={isSelected}
        >
            {Children.map(children, child =>
                React.isValidElement(child)
                    ? cloneElement(child as React.ReactElement<{ isHovered?: MotionValue<number> }>, { isHovered })
                    : child
            )}
        </motion.div>
    );
}

type DockLabelProps = {
    className?: string;
    children: React.ReactNode;
    isHovered?: MotionValue<number>;
};

function DockLabel({ children, className = '', isHovered }: DockLabelProps) {
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        if (!isHovered) return;
        const unsubscribe = isHovered.on('change', (latest: number) => {
            setIsVisible(latest === 1);
        });
        return () => unsubscribe();
    }, [isHovered]);

    return (
        <AnimatePresence>
            {isVisible && (
                <motion.div
                    initial={{ opacity: 0, y: 0 }}
                    animate={{ opacity: 1, y: -10 }}
                    exit={{ opacity: 0, y: 0 }}
                    transition={{ duration: 0.2 }}
                    className={`${className} absolute -top-8 left-1/2 w-fit whitespace-pre rounded-md border border-slate-600 bg-slate-800 px-2 py-1 text-xs text-white z-50`}
                    role="tooltip"
                    style={{ x: '-50%' }}
                >
                    {children}
                </motion.div>
            )}
        </AnimatePresence>
    );
}

type DockIconProps = {
    className?: string;
    children: React.ReactNode;
};

function DockIcon({ children, className = '' }: DockIconProps) {
    return <div className={`flex items-center justify-center text-xl ${className}`}>{children}</div>;
}

// --- PreferenceFilter Component ---

interface FilterOption {
    id: string;
    label: string;
    icon: string;
}

interface PreferenceFilterProps {
    onFilterChange?: (filters: string[]) => void;
    initialFilters?: string[];
}

const FILTER_OPTIONS: FilterOption[] = [
    { id: 'safety', label: '안전', icon: '🛡️' },
    { id: 'traffic', label: '교통', icon: '🚇' },
    { id: 'convenience', label: '편의시설', icon: '🏪' },
    { id: 'culture', label: '문화', icon: '🎭' },
    { id: 'pet', label: '반려동물', icon: '🐶' },
];

export default function PreferenceFilter({
    onFilterChange,
    initialFilters = []
}: PreferenceFilterProps) {
    const [selectedFilters, setSelectedFilters] = useState<Set<string>>(
        new Set(initialFilters)
    );

    const mouseX = useMotionValue(Infinity);
    const isHovered = useMotionValue(0);
    const { triggerEffect } = useParticleEffect();

    // Dock configuration
    const spring = { mass: 0.1, stiffness: 150, damping: 12 };
    const magnification = 45; // 호버 시 크기 변화 없음 (baseItemSize와 동일)
    const distance = 140;
    const baseItemSize = 45;
    const panelHeight = 68;

    const handleFilterClick = (filterId: string, event: React.MouseEvent<HTMLDivElement>) => {
        const newFilters = new Set(selectedFilters);

        if (newFilters.has(filterId)) {
            newFilters.delete(filterId);
        } else {
            newFilters.add(filterId);
            // Trigger particle effect only on selection
            triggerEffect(event.currentTarget as HTMLElement);
        }

        setSelectedFilters(newFilters);
        onFilterChange?.(Array.from(newFilters));
    };

    const handleReset = (event: React.MouseEvent<HTMLDivElement>) => {
        setSelectedFilters(new Set());
        onFilterChange?.([]);
        // Optional: Trigger effect on reset too
        triggerEffect(event.currentTarget as HTMLElement);
    };

    return (
        <div
            className="flex justify-center w-[600px] pb-4"
            style={{ height: panelHeight + 32 }}
        >
            <div className="flex items-end h-full w-full">
                <div
                    onMouseMove={({ pageX }: { pageX: number }) => {
                        isHovered.set(1);
                        mouseX.set(pageX);
                    }}
                    onMouseLeave={() => {
                        isHovered.set(0);
                        mouseX.set(Infinity);
                    }}
                    className="relative flex items-end justify-center w-full gap-3 rounded-2xl border border-purple-200/60 bg-gradient-to-r from-purple-50/90 via-blue-50/90 to-cyan-50/90 backdrop-blur-md pb-2 px-4 shadow-lg z-40"
                    style={{ height: panelHeight }}
                    role="toolbar"
                    aria-label="Filter dock"
                >
                    {FILTER_OPTIONS.map((option) => (
                        <DockItem
                            key={option.id}
                            onClick={(e: React.MouseEvent<HTMLDivElement>) => handleFilterClick(option.id, e)}
                            mouseX={mouseX}
                            spring={spring}
                            distance={distance}
                            magnification={magnification}
                            baseItemSize={baseItemSize}
                            isSelected={selectedFilters.has(option.id)}
                            className={`
                                ${selectedFilters.has(option.id)
                                    ? 'bg-gradient-to-r from-purple-600 via-blue-600 to-cyan-500 border-purple-500 text-white shadow-lg shadow-purple-500/30'
                                    : 'bg-white/80 border-slate-200 text-slate-600 hover:bg-white hover:border-purple-300'
                                }
                            `}
                        >
                            <DockIcon>{option.icon}</DockIcon>
                            <DockLabel>{option.label}</DockLabel>
                        </DockItem>
                    ))}

                    {/* Separator */}
                    <div className="w-[1px] h-8 bg-slate-400/30 mx-1 mb-3" />

                    {/* Reset Button */}
                    <DockItem
                        onClick={(e: React.MouseEvent<HTMLDivElement>) => handleReset(e)}
                        mouseX={mouseX}
                        spring={spring}
                        distance={distance}
                        magnification={magnification}
                        baseItemSize={baseItemSize}
                        className={selectedFilters.size === 0 ? 'opacity-50 cursor-not-allowed bg-white/50' : 'text-red-500 border-red-200 bg-white/80 hover:bg-red-50'}
                    >
                        <DockIcon>🔄</DockIcon>
                        <DockLabel>초기화</DockLabel>
                    </DockItem>

                </div>
            </div>
        </div>
    );
}
