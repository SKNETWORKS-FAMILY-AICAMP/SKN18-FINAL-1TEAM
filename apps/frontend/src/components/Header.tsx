/**
 * Header 컴포넌트 - PropTech Bank-Level Design
 *
 * 상단 헤더 영역
 *
 * 주요 기능:
 * - 로고 표시
 * - 네비게이션 메뉴
 * - 사용자 인증 상태 표시
 */

'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useSession } from 'next-auth/react'

export default function Header() {
  const pathname = usePathname()
  const { data: session, status } = useSession()

  const isLoginPage = pathname === '/login'

  return (
    <header className="bg-white border-b border-[var(--color-border-light)] shadow-[var(--shadow-sm)] sticky top-0 z-40">
      <div className="max-w-[1440px] mx-auto px-8 flex justify-between items-center" style={{ height: '72px' }}>
        {/* 로고 */}
        <Link
          href="/"
          className="flex items-center gap-3 text-2xl font-bold text-[var(--color-primary)] hover:text-[var(--color-primary-dark)] transition-colors"
        >
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="32" height="32" rx="6" fill="currentColor" />
            <path d="M16 8L8 14V24H12V18H20V24H24V14L16 8Z" fill="white" />
          </svg>
          <span>GoZip</span>
        </Link>

        {/* 네비게이션 */}
        <nav className="flex items-center gap-2">

          <Link
            href="/serviceIns"
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${pathname === '/serviceIns'
              ? 'bg-[var(--color-primary)] text-white'
              : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-primary)]'
              }`}
          >
            서비스 소개
          </Link>
          <Link
            href="/community"
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${pathname === '/community'
              ? 'bg-[var(--color-primary)] text-white'
              : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-primary)]'
              }`}
          >
            커뮤니티
          </Link>


          {/* 마이페이지 / 로그인 버튼 */}
          {session ? (
            <Link
              href="/my"
              className="ml-4 px-4 py-2 bg-[var(--color-primary)] text-white rounded-lg hover:bg-[var(--color-primary-dark)] transition-colors font-medium text-sm shadow-[var(--shadow-md)]"
            >
              마이페이지
            </Link>
          ) : (
            !isLoginPage && status !== 'loading' && (
              <Link
                href="/login"
                className="ml-4 px-4 py-2 bg-[var(--color-primary)] text-white rounded-lg hover:bg-[var(--color-primary-dark)] transition-colors font-medium text-sm shadow-[var(--shadow-md)]"
              >
                로그인
              </Link>
            )
          )}
        </nav>
      </div>
    </header>
  )
}
