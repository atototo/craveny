"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/app/contexts/AuthContext";

/**
 * ProtectedRoute Props
 */
interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

/**
 * 보호된 라우트 컴포넌트
 *
 * 인증되지 않은 사용자를 로그인 페이지로 리다이렉트하고,
 * 관리자 권한이 필요한 페이지에서 일반 사용자를 차단합니다.
 *
 * @param children - 렌더링할 자식 컴포넌트
 * @param requireAdmin - 관리자 권한 필요 여부 (기본값: false)
 */
export default function ProtectedRoute({ children, requireAdmin = false }: ProtectedRouteProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isAdmin, loading } = useAuth();

  useEffect(() => {
    if (loading) return;

    // 인증되지 않은 사용자는 로그인 페이지로 리다이렉트
    if (!isAuthenticated) {
      router.push(`/login?redirect=${encodeURIComponent(pathname)}`);
      return;
    }

    // 관리자 권한이 필요한데 일반 사용자인 경우 대시보드로 리다이렉트
    if (requireAdmin && !isAdmin) {
      router.push("/");
      return;
    }
  }, [isAuthenticated, isAdmin, loading, requireAdmin, router, pathname]);

  // 로딩 중이거나 인증되지 않은 경우 로딩 표시
  if (loading || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-white"></div>
          <p className="mt-4 text-gray-400">로딩 중...</p>
        </div>
      </div>
    );
  }

  // 관리자 권한이 필요한데 일반 사용자인 경우 권한 없음 표시
  if (requireAdmin && !isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <div className="text-6xl mb-4">🔒</div>
          <h1 className="text-2xl font-bold text-white mb-2">접근 권한이 없습니다</h1>
          <p className="text-gray-400 mb-6">이 페이지는 관리자 전용입니다.</p>
          <button
            onClick={() => router.push("/")}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            대시보드로 돌아가기
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
