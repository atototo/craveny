"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface Mover {
  stock_code: string;
  stock_name: string;
  change_rate: number;
  current_price: number;
  ai_signals: number;
  positive_signals: number;
  negative_signals: number;
  confidence: number | null;
}

interface InvestorBuying {
  stock_code: string;
  stock_name: string;
  amount: number;
}

interface SectorTrend {
  sector: string;
  positive_signals: number;
  negative_signals: number;
  total_signals: number;
  sentiment: string;
}

interface MarketMomentum {
  top_gainers: Mover[];
  top_losers: Mover[];
  foreign_buying: InvestorBuying[];
  institution_buying: InvestorBuying[];
  sector_trends: SectorTrend[];
}

export default function Home() {
  const [momentum, setMomentum] = useState<MarketMomentum | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 시장 모멘텀 조회
    fetch("/api/dashboard/market-momentum")
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        setMomentum(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch market momentum:", err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  const formatAmount = (amount: number) => {
    // amount는 원 단위 (KIS API 원본)
    const billion = amount / 100000000; // 원 → 억
    const million = amount / 10000; // 원 → 만원

    if (Math.abs(billion) >= 1) {
      // 1억 이상
      return billion >= 0 ? `+${billion.toFixed(0)}억` : `${billion.toFixed(0)}억`;
    } else if (Math.abs(million) >= 1) {
      // 1만 이상
      return million >= 0 ? `+${million.toFixed(0)}만` : `${million.toFixed(0)}만`;
    } else {
      // 1만 미만
      return amount >= 0 ? `+${amount}원` : `${amount}원`;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Hero Section */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">📊 Craveny</h1>
          <p className="text-gray-600">AI 기반 주식 뉴스 분석 및 예측 시스템</p>
        </div>

        {/* 급등/급락 종목 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* 급등 종목 */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-900">🚀 급등 종목 TOP 5</h2>
              <p className="text-sm text-gray-500 mt-1">실시간 전체 시장 기준</p>
            </div>
            <div className="divide-y divide-gray-200">
              {!momentum || momentum.top_gainers.length === 0 ? (
                <div className="px-6 py-8 text-center text-gray-500">
                  데이터 없음
                </div>
              ) : (
                momentum.top_gainers.map((stock, index) => (
                  <Link
                    key={stock.stock_code}
                    href={`/stocks/${stock.stock_code}`}
                    className="block px-6 py-3 hover:bg-gray-50 transition"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 flex-1">
                        <span className="text-sm font-bold text-gray-400">{index + 1}</span>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900">{stock.stock_name}</span>
                            <span className="text-sm text-red-600 font-bold">
                              +{stock.change_rate}%
                            </span>
                          </div>
                          <div className="text-xs text-gray-500 mt-0.5">
                            {stock.current_price.toLocaleString()}원
                          </div>
                        </div>
                      </div>
                    </div>
                  </Link>
                ))
              )}
            </div>
          </div>

          {/* 급락 종목 */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-900">📉 급락 종목 TOP 5</h2>
              <p className="text-sm text-gray-500 mt-1">실시간 전체 시장 기준</p>
            </div>
            <div className="divide-y divide-gray-200">
              {!momentum || momentum.top_losers.length === 0 ? (
                <div className="px-6 py-8 text-center text-gray-500">
                  데이터 없음
                </div>
              ) : (
                momentum.top_losers.map((stock, index) => (
                  <Link
                    key={stock.stock_code}
                    href={`/stocks/${stock.stock_code}`}
                    className="block px-6 py-3 hover:bg-gray-50 transition"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 flex-1">
                        <span className="text-sm font-bold text-gray-400">{index + 1}</span>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900">{stock.stock_name}</span>
                            <span className="text-sm text-blue-600 font-bold">
                              {stock.change_rate}%
                            </span>
                          </div>
                          <div className="text-xs text-gray-500 mt-0.5">
                            {stock.current_price.toLocaleString()}원
                          </div>
                        </div>
                      </div>
                    </div>
                  </Link>
                ))
              )}
            </div>
          </div>
        </div>

        {/* 투자자 동향 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* 외국인 순매수 */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-900">🌐 외국인 순매수 TOP</h2>
              <p className="text-sm text-gray-500 mt-1">오늘 외국인이 가장 많이 산 종목</p>
            </div>
            <div className="divide-y divide-gray-200">
              {!momentum || momentum.foreign_buying.length === 0 ? (
                <div className="px-6 py-8 text-center text-gray-500">
                  데이터 없음
                </div>
              ) : (
                momentum.foreign_buying.map((stock, index) => (
                  <Link
                    key={stock.stock_code}
                    href={`/stocks/${stock.stock_code}`}
                    className="block px-6 py-3 hover:bg-gray-50 transition"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-bold text-gray-400">{index + 1}</span>
                        <span className="font-medium text-gray-900">{stock.stock_name}</span>
                      </div>
                      <span className="text-sm font-bold text-green-600">
                        {formatAmount(stock.amount)}
                      </span>
                    </div>
                  </Link>
                ))
              )}
            </div>
          </div>

          {/* 기관 순매수 */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-900">🏢 기관 순매수 TOP</h2>
              <p className="text-sm text-gray-500 mt-1">오늘 기관이 가장 많이 산 종목</p>
            </div>
            <div className="divide-y divide-gray-200">
              {!momentum || momentum.institution_buying.length === 0 ? (
                <div className="px-6 py-8 text-center text-gray-500">
                  데이터 없음
                </div>
              ) : (
                momentum.institution_buying.map((stock, index) => (
                  <Link
                    key={stock.stock_code}
                    href={`/stocks/${stock.stock_code}`}
                    className="block px-6 py-3 hover:bg-gray-50 transition"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-bold text-gray-400">{index + 1}</span>
                        <span className="font-medium text-gray-900">{stock.stock_name}</span>
                      </div>
                      <span className="text-sm font-bold text-green-600">
                        {formatAmount(stock.amount)}
                      </span>
                    </div>
                  </Link>
                ))
              )}
            </div>
          </div>
        </div>

        {/* AI 주목 종목 */}
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-bold text-gray-900">🤖 AI 주목 종목 TOP</h2>
            <p className="text-sm text-gray-500 mt-1">최근 3일간 AI 시그널이 가장 많은 종목</p>
          </div>
          <div className="divide-y divide-gray-200">
            {!momentum || momentum.sector_trends.length === 0 ? (
              <div className="px-6 py-12 text-center text-gray-500">
                데이터 없음
              </div>
            ) : (
              momentum.sector_trends.map((sector, index) => (
                <div key={sector.sector} className="px-6 py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <span className="font-medium text-gray-900">{sector.sector}</span>
                        {sector.sentiment === 'positive' ? (
                          <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full font-medium">
                            📈 긍정
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded-full font-medium">
                            📉 부정
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-4 mt-2">
                        <span className="text-sm text-green-600">
                          긍정 {sector.positive_signals}건
                        </span>
                        <span className="text-sm text-red-600">
                          부정 {sector.negative_signals}건
                        </span>
                        <span className="text-sm text-gray-500">
                          총 {sector.total_signals}건
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 주요 기능 안내 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Link
            href="/predictions"
            className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition"
          >
            <div className="text-3xl mb-3">📋</div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">예측 이력</h3>
            <p className="text-sm text-gray-600">
              AI가 분석한 모든 종목 예측 기록을 확인하세요
            </p>
          </Link>

          <Link
            href="/stocks"
            className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition"
          >
            <div className="text-3xl mb-3">📊</div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">종목 분석</h3>
            <p className="text-sm text-gray-600">
              종목별 뉴스와 AI 투자 의견을 상세히 확인하세요
            </p>
          </Link>

          <Link
            href="/admin/dashboard"
            className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition border-2 border-blue-100"
          >
            <div className="text-3xl mb-3">⚙️</div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">관리자 대시보드</h3>
            <p className="text-sm text-gray-600">
              시스템 통계와 크롤러 상태를 모니터링하세요
            </p>
          </Link>
        </div>
      </main>
    </div>
  );
}
