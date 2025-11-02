"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface StockSummary {
  stock_code: string;
  stock_name: string;
  news_count: number;
  notification_count: number;
  latest_news_date: string | null;
}

export default function StocksPage() {
  const [stocks, setStocks] = useState<StockSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetch("/api/stocks/summary")
      .then((res) => res.json())
      .then((data) => {
        setStocks(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch stocks:", err);
        setStocks([]);
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

  const filteredStocks = stocks.filter(
    (stock) =>
      stock.stock_name.toLowerCase().includes(search.toLowerCase()) ||
      stock.stock_code.includes(search)
  );

  return (
    <div className="min-h-screen">
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">종목 분석</h1>
          <p className="text-gray-600 mt-1">종목별 뉴스 및 예측 현황을 확인하세요</p>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">추적 중인 종목</h3>
            <p className="text-3xl font-bold text-blue-600 mt-2">{stocks.length}개</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">총 뉴스 수</h3>
            <p className="text-3xl font-bold text-green-600 mt-2">
              {stocks.reduce((sum, s) => sum + s.news_count, 0)}건
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">총 알림 수</h3>
            <p className="text-3xl font-bold text-purple-600 mt-2">
              {stocks.reduce((sum, s) => sum + s.notification_count, 0)}건
            </p>
          </div>
        </div>

        {/* Search */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <input
            type="text"
            placeholder="종목명 또는 코드로 검색..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Stocks Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredStocks.map((stock) => (
            <Link
              key={stock.stock_code}
              href={`/stocks/${stock.stock_code}`}
              className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition"
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-bold text-gray-900">{stock.stock_name}</h3>
                  <p className="text-sm text-gray-500">{stock.stock_code}</p>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">📰 뉴스</span>
                  <span className="font-medium text-blue-600">{stock.news_count}건</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">🔔 알림</span>
                  <span className="font-medium text-purple-600">{stock.notification_count}건</span>
                </div>
                {stock.latest_news_date && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">🕐 최근 뉴스</span>
                    <span className="text-gray-500">
                      {new Date(stock.latest_news_date).toLocaleDateString("ko-KR")}
                    </span>
                  </div>
                )}
              </div>
            </Link>
          ))}
        </div>

        {filteredStocks.length === 0 && (
          <div className="bg-white rounded-lg shadow p-12 text-center text-gray-500">
            <p className="text-lg">검색 결과가 없습니다</p>
          </div>
        )}
      </main>
    </div>
  );
}
