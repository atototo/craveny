import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Next.js 미들웨어 - 인증 및 권한 체크
 *
 * 모든 요청을 가로채서 인증 상태를 확인하고,
 * 비인증 사용자를 로그인 페이지로 리다이렉트합니다.
 */
export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 로그인 페이지와 API 엔드포인트는 체크하지 않음
  if (pathname === "/login" || pathname.startsWith("/api/")) {
    return NextResponse.next();
  }

  // 세션 쿠키 확인
  const sessionCookie = request.cookies.get("craveny_session");

  // 세션이 없으면 로그인 페이지로 리다이렉트
  if (!sessionCookie) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // 세션이 유효한지 백엔드에 확인 (선택적)
  try {
    const checkResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/auth/me`, {
      headers: {
        Cookie: `craveny_session=${sessionCookie.value}`,
      },
    });

    // 세션이 유효하지 않으면 로그인 페이지로 리다이렉트
    if (!checkResponse.ok) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }

    // 관리자 전용 페이지 체크
    if (pathname.startsWith("/admin/")) {
      const userData = await checkResponse.json();

      // 관리자가 아니면 대시보드로 리다이렉트
      if (userData.role !== "admin") {
        return NextResponse.redirect(new URL("/", request.url));
      }
    }

    return NextResponse.next();
  } catch (error) {
    console.error("인증 확인 실패:", error);

    // 에러 발생 시 로그인 페이지로 리다이렉트
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }
}

/**
 * 미들웨어가 실행될 경로 설정
 */
export const config = {
  matcher: [
    /*
     * 다음 경로를 제외한 모든 요청에 미들웨어 적용:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
