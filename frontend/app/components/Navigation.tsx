"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/app/contexts/AuthContext";

export default function Navigation() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isAdmin, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [logoutLoading, setLogoutLoading] = useState(false);

  // 전체 메뉴 목록
  const allLinks = [
    { href: "/", label: "대시보드", roles: ["user", "admin"] },
    { href: "/stocks", label: "종목 분석", roles: ["user", "admin"] },
    { href: "/predictions", label: "예측 이력", roles: ["admin"] },
    { href: "/models", label: "🤖 모델 관리", roles: ["admin"] },
    { href: "/ab-config", label: "🔬 A/B 설정", roles: ["admin"] },
    { href: "/admin/dashboard", label: "⚙️ 관리자", roles: ["admin"] },
    { href: "/admin/stocks", label: "⚙️ 종목 관리", roles: ["admin"] },
    { href: "/admin/evaluations", label: "📝 모델 평가", roles: ["admin"] },
    { href: "/admin/performance", label: "📊 성능 대시보드", roles: ["admin"] },
    { href: "/admin/users", label: "👥 사용자 관리", roles: ["admin"] },
  ];

  // 사용자 역할에 따라 메뉴 필터링
  const links = allLinks.filter((link) => link.roles.includes(user?.role || "user"));

  // 로그아웃 핸들러
  const handleLogout = async () => {
    setLogoutLoading(true);
    try {
      await logout();
      router.push("/login");
    } catch (error) {
      console.error("로그아웃 실패:", error);
    } finally {
      setLogoutLoading(false);
    }
  };

  return (
    <nav className="bg-white shadow">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <Link href="/">
                <h1 className="text-xl font-bold text-gray-900">📊 Craveny</h1>
              </Link>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              {links.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                    pathname === link.href
                      ? "border-blue-500 text-gray-900"
                      : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </div>
          </div>

          {/* User info and logout button */}
          <div className="hidden sm:ml-6 sm:flex sm:items-center sm:space-x-4">
            <div className="flex items-center space-x-2 text-sm text-gray-700">
              <span className="font-medium">{user?.nickname}</span>
              {isAdmin && (
                <span className="px-2 py-1 text-xs font-semibold text-blue-800 bg-blue-100 rounded-full">
                  관리자
                </span>
              )}
            </div>
            <button
              onClick={handleLogout}
              disabled={logoutLoading}
              className="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {logoutLoading ? "로그아웃 중..." : "로그아웃"}
            </button>
          </div>

          {/* Mobile menu button */}
          <div className="flex items-center sm:hidden">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
              aria-controls="mobile-menu"
              aria-expanded="false"
            >
              <span className="sr-only">메뉴 열기</span>
              {!mobileMenuOpen ? (
                <svg
                  className="block h-6 w-6"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                </svg>
              ) : (
                <svg
                  className="block h-6 w-6"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="sm:hidden" id="mobile-menu">
          <div className="pt-2 pb-3 space-y-1">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`block pl-3 pr-4 py-2 border-l-4 text-base font-medium ${
                  pathname === link.href
                    ? "bg-blue-50 border-blue-500 text-blue-700"
                    : "border-transparent text-gray-600 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-800"
                }`}
              >
                {link.label}
              </Link>
            ))}
          </div>
          {/* Mobile user info and logout */}
          <div className="pt-4 pb-3 border-t border-gray-200">
            <div className="flex items-center px-4">
              <div className="flex-1">
                <div className="text-base font-medium text-gray-800">{user?.nickname}</div>
                <div className="text-sm font-medium text-gray-500">{user?.email}</div>
                {isAdmin && (
                  <span className="inline-block mt-1 px-2 py-1 text-xs font-semibold text-blue-800 bg-blue-100 rounded-full">
                    관리자
                  </span>
                )}
              </div>
            </div>
            <div className="mt-3 px-2">
              <button
                onClick={handleLogout}
                disabled={logoutLoading}
                className="w-full text-left px-3 py-2 text-base font-medium text-gray-600 hover:text-gray-800 hover:bg-gray-50 rounded-md disabled:opacity-50"
              >
                {logoutLoading ? "로그아웃 중..." : "로그아웃"}
              </button>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
