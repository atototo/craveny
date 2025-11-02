"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface NewsItem {
  id: number;
  title: string;
  stock_code: string;
  stock_name: string;
  notified_at: string;
  source: string;
}

interface HotStock {
  stock_code: string;
  stock_name: string;
  news_count: number;
  notification_count: number;
}

export default function Home() {
  const [latestAlerts, setLatestAlerts] = useState<NewsItem[]>([]);
  const [hotStocks, setHotStocks] = useState<HotStock[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 최신 투자 알림 조회
    fetch("/api/news?notified=true&sort_by=notified_at&sort_order=desc&limit=10")
      .then((res) => res.json())
      .then((data) => {
        setLatestAlerts(data.items || []);
      })
      .catch((err) => {
        console.error("Failed to fetch latest alerts:", err);
      });

    // 오늘의 HOT 종목 조회
    fetch("/api/stocks/summary")
      .then((res) => res.json())
      .then((data) => {
        // 뉴스가 많은 상위 5개 종목
        setHotStocks(data.slice(0, 5));
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch hot stocks:", err);
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

  const getDirectionEmoji = (direction: string) => {
    switch (direction) {
      case "상승":
        return "📈";
      case "하락":
        return "📉";
      default:
        return "➡️";
    }
  };

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}일 전`;
    if (hours > 0) return `${hours}시간 전`;
    if (minutes > 0) return `${minutes}분 전`;
    return "방금";
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Hero Section */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">📊 Craveny</h1>
          <p className="text-gray-600">AI 기반 주식 뉴스 분석 및 예측 시스템</p>
        </div>

        {/* 최신 투자 알림 */}
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">🔔 최신 투자 알림</h2>
              <Link
                href="/predictions"
                className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                전체 보기 →
              </Link>
            </div>
          </div>
          <div className="divide-y divide-gray-200">
            {latestAlerts.length === 0 ? (
              <div className="px-6 py-12 text-center text-gray-500">
                아직 투자 알림이 없습니다.
              </div>
            ) : (
              latestAlerts.map((alert) => (
                <div key={alert.id} className="px-6 py-4 hover:bg-gray-50 transition">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Link
                          href={`/stocks/${alert.stock_code}`}
                          className="inline-flex items-center px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium hover:bg-blue-200 transition"
                        >
                          {alert.stock_name} ({alert.stock_code})
                        </Link>
                        <span className="text-xs text-gray-500">
                          {formatDateTime(alert.notified_at)}
                        </span>
                      </div>
                      <h3 className="text-gray-900 font-medium mb-1 line-clamp-2">
                        {alert.title}
                      </h3>
                      <p className="text-xs text-gray-500">{alert.source}</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 오늘의 HOT 종목 */}
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">🔥 오늘의 HOT 종목</h2>
              <Link
                href="/stocks"
                className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                전체 보기 →
              </Link>
            </div>
            <p className="text-sm text-gray-500 mt-1">뉴스가 많은 주목받는 종목</p>
          </div>
          <div className="divide-y divide-gray-200">
            {hotStocks.length === 0 ? (
              <div className="px-6 py-12 text-center text-gray-500">
                종목 정보를 불러올 수 없습니다.
              </div>
            ) : (
              hotStocks.map((stock, index) => (
                <Link
                  key={stock.stock_code}
                  href={`/stocks/${stock.stock_code}`}
                  className="block px-6 py-4 hover:bg-gray-50 transition"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="flex items-center justify-center w-8 h-8 bg-gradient-to-br from-orange-400 to-pink-500 text-white rounded-full font-bold text-sm">
                        {index + 1}
                      </div>
                      <div>
                        <h3 className="font-medium text-gray-900">{stock.stock_name}</h3>
                        <p className="text-sm text-gray-500">{stock.stock_code}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium text-gray-900">
                        뉴스 {stock.news_count}건
                      </div>
                      <div className="text-xs text-gray-500">
                        알림 {stock.notification_count}건
                      </div>
                    </div>
                  </div>
                </Link>
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
