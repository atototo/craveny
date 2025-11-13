import { NextRequest, NextResponse } from 'next/server';

export async function POST(
  request: NextRequest,
  { params }: { params: { stockCode: string } }
) {
  const stockCode = params.stockCode;

  try {
    // 백엔드 URL (서버 사이드에서는 localhost:8000 사용 가능)
    const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

    // 백엔드로 요청 전달 (타임아웃 2분)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);

    const response = await fetch(`${backendUrl}/api/reports/force-update/${stockCode}`, {
      method: 'POST',
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error: any) {
    console.error('Force update error:', error);

    if (error.name === 'AbortError') {
      return NextResponse.json(
        { success: false, message: '요청 시간이 초과되었습니다.' },
        { status: 504 }
      );
    }

    return NextResponse.json(
      { success: false, message: error.message || '리포트 업데이트 실패' },
      { status: 500 }
    );
  }
}
