"use client";

import { useEffect, useMemo, useState, useRef } from "react";
import { useParticleEffect } from "@/hooks/useParticleEffect";
import type { PreferenceSurveyPayload } from "@/types/user";

const JOB_OPTIONS = [
  { value: "직장인", label: "직장인" },
  { value: "학생", label: "학생" },
  { value: "취준생", label: "취준생" },
  { value: "프리랜서", label: "프리랜서" },
  { value: "자영업", label: "자영업자" },
];
const FEATURES = ["안전", "편의시설", "교통", "문화", "반려동물"];
const RANKS = [1, 2, 3, 4, 5];

interface Props {
  onSubmit: (data: PreferenceSurveyPayload) => Promise<void>;
  initialJob?: string | null;
  initialPriorities?: Record<string, number>;
  submitLabel?: string;
  isSubmitting?: boolean;
  disabled?: boolean;
}

// 커스텀 드롭다운 컴포넌트
function CustomJobDropdown({
  value,
  options,
  onChange,
  disabled = false,
}: {
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // 외부 클릭 감지
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (optionValue: string) => {
    onChange(optionValue);
    setIsOpen(false);
  };

  const selectedLabel = options.find(opt => opt.value === value)?.label || value;

  return (
    <div ref={dropdownRef} className="relative">
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={`relative w-full max-w-xs px-4 py-3 pr-10 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#16375B]/20 bg-white text-left font-medium transition-all ${disabled
          ? 'border-slate-200 text-slate-400 cursor-not-allowed bg-slate-50'
          : 'border-slate-200 text-slate-800 hover:border-[#16375B]/50 hover:shadow-md focus:border-[#16375B]'
          }`}
      >
        <span className="text-slate-800">{selectedLabel}</span>
        <div className={`absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none transition-transform ${isOpen ? 'rotate-180' : ''}`}>
          <svg className={`w-5 h-5 ${disabled ? 'text-slate-400' : 'text-[#16375B]'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* 드롭다운 메뉴 */}
      {isOpen && !disabled && (
        <div className="absolute z-50 w-full max-w-xs mt-2 bg-white border-2 border-[#16375B]/20 rounded-xl shadow-2xl overflow-hidden">
          <div className="max-h-60 overflow-y-auto">
            {options.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => handleSelect(option.value)}
                className={`w-full px-4 py-2.5 text-left text-sm transition-colors ${value === option.value
                  ? 'bg-[#16375B] text-white font-semibold'
                  : 'text-slate-700 hover:bg-slate-50'
                  }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function PreferenceRanking({
  onSubmit,
  initialJob,
  initialPriorities,
  submitLabel = "선호도 저장",
  isSubmitting = false,
  disabled = false,
}: Props) {
  const [job, setJob] = useState(initialJob || JOB_OPTIONS[0].value);
  const [priorities, setPriorities] = useState<Record<string, number | undefined>>(initialPriorities || {});
  const { triggerEffect } = useParticleEffect();
  const controlDisabled = disabled || isSubmitting;

  useEffect(() => {
    if (initialJob) {
      setJob(initialJob);
    }
  }, [initialJob]);

  useEffect(() => {
    if (initialPriorities) {
      setPriorities(initialPriorities);
    } else {
      setPriorities({});
    }
  }, [initialPriorities]);

  const jobOptions = useMemo(() => {
    if (initialJob && !JOB_OPTIONS.some((option) => option.value === initialJob)) {
      return [{ value: initialJob, label: initialJob }, ...JOB_OPTIONS];
    }
    return JOB_OPTIONS;
  }, [initialJob]);

  const handleCheck = (feature: string, rank: number, event: React.ChangeEvent<HTMLInputElement>) => {
    if (controlDisabled) return;
    triggerEffect(event.target);
    setPriorities((prev: Record<string, number | undefined>) => {
      const newPriorities = { ...prev };

      if (newPriorities[feature] === rank) {
        delete newPriorities[feature];
        return newPriorities;
      }

      Object.keys(newPriorities).forEach((f) => {
        if (newPriorities[f] === rank) {
          delete newPriorities[f];
        }
      });

      newPriorities[feature] = rank;
      return newPriorities;
    });
  };

  const handleJobChange = (value: string) => {
    if (controlDisabled) return;
    setJob(value);
  };

  const handleSubmit = async (e: React.MouseEvent<HTMLButtonElement>) => {
    if (controlDisabled) return;
    triggerEffect(e.currentTarget);
    const cleanPriorities: Record<string, number> = {};
    Object.entries(priorities).forEach(([key, value]) => {
      if (value !== undefined) {
        cleanPriorities[key] = value;
      }
    });
    await onSubmit({ job, priorities: cleanPriorities });
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-8 rounded-2xl border border-slate-200 bg-white shadow-sm">
      <h2 className="text-2xl font-bold mb-8 text-slate-900">매물 선호도 조사</h2>

      {/* 직업 섹션 */}
      <div className="mb-8">
        <div className="flex items-center mb-4">
          <span className="text-3xl mr-3">💼</span>
          <h3 className="text-lg font-bold text-slate-800">직업</h3>
        </div>
        <div className="ml-13 p-6 border border-slate-200 rounded-xl bg-slate-50">
          <label className="block font-semibold mb-3 text-slate-700">직업</label>
          <CustomJobDropdown
            value={job}
            options={jobOptions}
            onChange={handleJobChange}
            disabled={controlDisabled}
          />
        </div>
      </div>

      {/* 우선순위 섹션 */}
      <div className="mb-8">
        <div className="flex items-center mb-4">
          <span className="text-3xl mr-3">⭐</span>
          <div>
            <h3 className="text-lg font-bold text-slate-800">매물 선택 우선 순위 (5위까지)</h3>
            <p className="text-sm text-slate-500">우선순위는 매물 추천에 반영됩니다</p>
          </div>
        </div>

        <div className="ml-13 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-center border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="p-4 text-left text-slate-700 font-semibold"></th>
                {RANKS.map((rank) => (
                  <th key={rank} className="p-4 font-semibold text-slate-700">
                    {rank}위
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {FEATURES.map((feature, index) => (
                <tr
                  key={feature}
                  className={`border-b border-slate-100 last:border-b-0 hover:bg-slate-50 transition-colors ${index % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'
                    }`}
                >
                  <td className="p-4 text-left font-medium text-slate-700">{feature}</td>
                  {RANKS.map((rank) => (
                    <td key={rank} className="p-4">
                      <label className="relative inline-flex items-center justify-center w-6 h-6 cursor-pointer group">
                        <input
                          type="checkbox"
                          className="sr-only"
                          checked={priorities[feature] === rank}
                          disabled={controlDisabled}
                          onChange={(e) => handleCheck(feature, rank, e)}
                        />
                        <div className={`w-6 h-6 border-2 rounded-lg transition-all duration-200 group-hover:scale-110 shadow-sm ${priorities[feature] === rank
                          ? 'bg-[#16375B] border-[#16375B]'
                          : 'bg-white border-slate-300 group-hover:border-[#16375B]/50'
                          } ${controlDisabled ? 'opacity-50 cursor-not-allowed' : ''}`}>
                          <svg
                            className={`w-full h-full text-white transition-opacity duration-200 ${priorities[feature] === rank ? 'opacity-100' : 'opacity-0'
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
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 저장 버튼 */}
      <div className="flex justify-end">
        <button
          onClick={handleSubmit}
          disabled={controlDisabled}
          className="px-8 py-3 bg-[#16375B] text-white rounded-xl hover:bg-[#1a4270] font-semibold shadow-lg shadow-[#16375B]/30 transition-all duration-200 hover:scale-105 active:scale-95 disabled:bg-gray-300 disabled:shadow-none disabled:hover:scale-100"
        >
          {isSubmitting ? "저장 중..." : submitLabel}
        </button>
      </div>
    </div>
  );
}
