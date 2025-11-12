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

  // 세션 쿠키가 있으면 일단 통과
  // 실제 인증 확인은 각 페이지나 API에서 수행
  return NextResponse.next();
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
