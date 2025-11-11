"use client";

import { usePathname } from "next/navigation";
import { useAuth } from "@/app/contexts/AuthContext";
import Navigation from "./Navigation";
import PredictionStatusBanner from "./PredictionStatusBanner";

/**
 * 레이아웃 래퍼 컴포넌트
 *
 * 인증 상태와 현재 경로에 따라 네비게이션과 배너를 조건부로 렌더링합니다.
 */
export default function LayoutWrapper({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { loading, isAuthenticated } = useAuth();

  // 로그인 페이지에서는 네비게이션과 배너를 숨김
  const isLoginPage = pathname === "/login";
  const shouldShowNavigation = !isLoginPage && isAuthenticated;

  // 로딩 중에는 스피너 표시
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-white"></div>
          <p className="mt-4 text-gray-400">로딩 중...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      {shouldShowNavigation && (
        <>
          <Navigation />
          <PredictionStatusBanner />
        </>
      )}
      {children}
    </>
  );
}
