/**
 * Footer 컴포넌트
 * 
 * 애플리케이션의 하단 푸터 영역을 담당하는 컴포넌트
 * 
 * 주요 기능:
 * - 프로젝트 정보 표시
 * - 저작권 정보 
 **/

import React from "react";
import Link from "next/link";

const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-slate-700/50 bg-gradient-to-r from-slate-800/95 via-slate-900/95 to-slate-800/95 backdrop-blur-md text-[11px] text-slate-400">
      {/* 상단 링크 영역 (로그인 / 전체서비스 / 약관 / 개인정보) */}
      <div className="border-b border-slate-700/50">
        <div className="mx-auto flex max-w-6xl flex-wrap gap-3 px-4 py-5 text-[11px] text-slate-400">
          <span className="text-slate-600">|</span>
          <Link href="/terms" className="hover:text-cyan-400 transition-colors">
            이용약관
          </Link>
          <span className="text-slate-600">|</span>
          <Link href="/privacy" className="hover:text-cyan-400 transition-colors">
            개인정보 처리방침
          </Link>
        </div>
      </div>

      {/* 안내/면책 문구 영역 */}
      <div className="mx-auto max-w-6xl px-4 py-6 leading-loose">
        <p className="mb-4 text-slate-400">
          GoZip에서 제공하는 부동산 정보는 공공데이터 포털, 서울특별시 열린
          데이터, 국토교통부 실거래가 공개 시스템 등 외부 제공처로부터 수집된
          자료를 기반으로 한 참고용 정보입니다.
          서비스는 이용자가 해당 정보를 바탕으로 진행한 매매,
          전·월세 계약 등 의사결정의 결과에 대해 어떠한 법적 책임도 부담하지
          않습니다.
        </p>
        <p className="text-slate-500">
          본 서비스는 학습 및 포트폴리오 용도로 제작된 프로젝트이며, 실제 금융·부동산 중개 행위를 수행하지 않습니다.
        </p>
      </div>

      {/* 사업자(프로젝트 팀) 정보 영역 */}
      <div className="border-t border-slate-700/50 bg-slate-900/50">
        <div className="mx-auto max-w-6xl px-4 py-6 text-center">
          <p className="mb-3 font-semibold text-slate-300">
            GoZip 프로젝트 팀 정보
          </p>
          <div className="flex flex-col gap-2 text-[11px] text-slate-400 md:flex-row md:flex-wrap md:gap-x-6 md:justify-center">
            <div className="flex gap-1 justify-center">
              <span className="font-medium text-slate-500">TEAM</span>
              <span className="text-cyan-400">GoZip</span>
            </div>
            <div className="flex gap-1 justify-center">
              <span className="font-medium text-slate-500">문의</span>
              <Link
                href="mailto:final7333@gmail.com"
                className="hover:text-cyan-400 transition-colors"
              >
                final7333@gmail.com
              </Link>
            </div>
          </div>

          {/* 하단 저작권 문구 */}
          <div className="mt-4 text-[11px] text-slate-500">
            © {currentYear}{" "}
            <span className="font-medium bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">GoZip Team</span>. All
            rights reserved.
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
