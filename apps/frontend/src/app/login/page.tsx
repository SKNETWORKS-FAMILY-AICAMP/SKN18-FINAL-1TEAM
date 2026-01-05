"use client";

import { useEffect, Suspense } from "react";
import { useRouter } from "next/navigation";
import { signIn, useSession } from "next-auth/react";
import AuthProvider from "@/components/AuthProvider";

/**
 * LoginPage
 *
 * 로그인 페이지
 */
function LoginContent() {
    const router = useRouter();
    const { data: session, status } = useSession();

    useEffect(() => {
        if (status === 'authenticated' && session?.user) {
            if (session.user.isNewUser && !session.user.surveyCompleted) {
                router.push('/preferenceSurvey');
            } else {
                router.push('/main');
            }
        }
    }, [status, session, router]);

    if (status === 'authenticated') {
        return (
            <div className="flex flex-col items-center justify-center min-h-[80vh]">
                <div className="w-8 h-8 border-4 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                <p className="mt-4 text-slate-600">로그인 처리 중...</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col items-center justify-center min-h-[80vh] px-4">
            {/* 로그인 카드 */}
            <div className="w-full max-w-md">
                {/* 로고 & 타이틀 */}
                <div className="text-center mb-8">
                    <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
                        GoZip
                    </h1>
                    <p className="text-slate-600">
                        나에게 딱 맞는 집을 찾아보세요
                    </p>
                </div>

                {/* 로그인 카드 */}
                <div className="bg-white/80 backdrop-blur-md rounded-2xl shadow-xl border border-white/40 p-8">
                    <h2 className="text-2xl font-bold text-slate-800 text-center mb-6">
                        로그인
                    </h2>

                    {/* Google 로그인 버튼 */}
                    <button
                        onClick={() => signIn("google")}
                        className="w-full flex items-center justify-center gap-3 px-6 py-3.5 bg-white border-2 border-slate-200 rounded-xl hover:bg-slate-50 hover:border-slate-300 transition-all shadow-sm hover:shadow-md group"
                    >
                        {/* Google 아이콘 */}
                        <svg className="w-5 h-5" viewBox="0 0 24 24">
                            <path
                                fill="#4285F4"
                                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                            />
                            <path
                                fill="#34A853"
                                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                            />
                            <path
                                fill="#FBBC05"
                                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                            />
                            <path
                                fill="#EA4335"
                                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                            />
                        </svg>
                        <span className="font-medium text-slate-700 group-hover:text-slate-900">
                            Google로 계속하기
                        </span>
                    </button>

                    {/* 안내 문구 */}
                    <div className="text-center mt-8">
                        <p className="text-sm text-slate-500 mb-4">
                            Google 계정으로 간편하게 로그인하세요
                        </p>
                        <div className="flex items-center justify-center gap-2 text-xs text-slate-400">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                            </svg>
                            <span>안전한 OAuth 2.0 인증</span>
                        </div>
                    </div>
                </div>


            </div>
        </div>
    );
}

export default function LoginPage() {
    return (
        <AuthProvider>
            <Suspense fallback={
                <div className="flex items-center justify-center min-h-[80vh]">
                    <div className="w-8 h-8 border-4 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                </div>
            }>
                <LoginContent />
            </Suspense>
        </AuthProvider>
    );
}
