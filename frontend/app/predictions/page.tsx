"use client";

import { useEffect, useState } from "react";
import { format } from "date-fns";
import NewsImpact from "../components/NewsImpact";

interface PriceChange {
  day1?: number | null;
  day2?: number | null;
  day3?: number | null;
  day5?: number | null;
  day10?: number | null;
  day20?: number | null;
}

interface ConfidenceBreakdown {
  similar_news_quality?: number | null;
  pattern_consistency?: number | null;
  disclosure_impact?: number | null;
  explanation?: string | null;
}

interface PatternAnalysis {
  avg_1d?: number | null;
  avg_2d?: number | null;
  avg_3d?: number | null;
  avg_5d?: number | null;
  avg_10d?: number | null;
  avg_20d?: number | null;
  max_1d?: number | null;
  min_1d?: number | null;
  count?: number | null;
}

interface PredictionDetail {
  // Epic 3: New impact analysis fields
  sentiment_direction?: string | null;
  sentiment_score?: number | null;
  impact_level?: string | null;
  relevance_score?: number | null;
  urgency_level?: string | null;
  impact_analysis?: string | null;
  reasoning?: string | null;
  // Deprecated fields (backward compatibility)
  prediction?: string;
  confidence?: number;
  short_term?: string;
  medium_term?: string;
  long_term?: string;
  confidence_breakdown?: ConfidenceBreakdown | null;
  pattern_analysis?: PatternAnalysis | null;
  model?: string;
  timestamp?: string;
}

interface News {
  id: number;
  title: string;
  url: string;
  source: string;
  created_at: string;
  notified: boolean;
  stock_code: string | null;
  stock_name: string | null;
  prediction_direction: string | null;
  prediction_confidence: number | null;
  prediction_detail?: PredictionDetail | null;
  prediction?: PredictionDetail | null; // Epic 3: Full prediction data
}

interface NewsResponse {
  items: News[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export default function PredictionsPage() {
  const [data, setData] = useState<NewsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [stockFilter, setStockFilter] = useState("");
  const [notifiedFilter, setNotifiedFilter] = useState<string>("all");

  useEffect(() => {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: "20",
      sort_by: "created_at",
      sort_order: "desc",
    });

    if (search) params.append("search", search);
    if (stockFilter) params.append("stock_code", stockFilter);
    if (notifiedFilter !== "all") {
      params.append("notified", notifiedFilter === "yes" ? "true" : "false");
    }

    fetch(`/api/news?${params}`)
      .then((res) => res.json())
      .then((data) => {
        setData(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch news:", err);
        setLoading(false);
      });
  }, [page, search, stockFilter, notifiedFilter]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  const getDirectionBadge = (direction: string | null) => {
    if (!direction) return null;
    const colors = {
      up: "bg-green-100 text-green-800",
      down: "bg-red-100 text-red-800",
      hold: "bg-gray-100 text-gray-800",
    };
    const labels = {
      up: "📈 상승",
      down: "📉 하락",
      hold: "➡️ 유지",
    };
    return (
      <span className={`px-2 py-1 rounded text-xs font-medium ${colors[direction as keyof typeof colors]}`}>
        {labels[direction as keyof typeof labels]}
      </span>
    );
  };

  return (
    <div className="min-h-screen">
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">예측 이력</h1>
          <p className="text-gray-600 mt-1">뉴스 기반 주가 예측 결과를 확인하세요</p>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                검색
              </label>
              <input
                type="text"
                placeholder="제목으로 검색..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                종목 코드
              </label>
              <input
                type="text"
                placeholder="예: 005930"
                value={stockFilter}
                onChange={(e) => {
                  setStockFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                알림 여부
              </label>
              <select
                value={notifiedFilter}
                onChange={(e) => {
                  setNotifiedFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">전체</option>
                <option value="yes">알림 발송됨</option>
                <option value="no">알림 미발송</option>
              </select>
            </div>
          </div>
        </div>

        {/* News List */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="divide-y divide-gray-200">
            {data?.items.map((news) => (
              <div key={news.id} className="transition">
                <div className="p-6 hover:bg-gray-50">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        {news.notified && (
                          <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-medium">
                            ✅ 알림 발송
                          </span>
                        )}
                        {news.stock_code && (
                          <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded text-xs font-medium">
                            {news.stock_name || news.stock_code}
                          </span>
                        )}
                        {getDirectionBadge(news.prediction_direction)}
                      </div>
                      <h3 className="text-lg font-medium text-gray-900 mb-2">
                        {news.stock_code ? (
                          <a
                            href={`/stocks/${news.stock_code}`}
                            className="hover:text-blue-600 transition"
                          >
                            {news.title}
                          </a>
                        ) : (
                          <span>{news.title}</span>
                        )}
                      </h3>
                      <div className="flex items-center gap-4 text-sm text-gray-500 mb-3">
                        <span>📰 {news.source}</span>
                        <span>🕐 {format(new Date(news.created_at), "yyyy-MM-dd HH:mm")}</span>
                      </div>

                      {/* Epic 5: News Impact Display */}
                      {(news.prediction || news.prediction_detail) && (
                        <div className="mt-4">
                          <NewsImpact prediction={news.prediction || news.prediction_detail} />
                        </div>
                      )}
                    </div>
                    {news.stock_code && (
                      <a
                        href={`/stocks/${news.stock_code}`}
                        className="ml-4 px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-100 transition"
                      >
                        종목 상세
                      </a>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {data?.items.length === 0 && (
            <div className="p-12 text-center text-gray-500">
              <p className="text-lg">조건에 맞는 뉴스가 없습니다</p>
            </div>
          )}
        </div>

        {/* Pagination */}
        {data && data.pages > 1 && (
          <div className="mt-6 flex items-center justify-between">
            <div className="text-sm text-gray-700">
              전체 {data.total}개 중 {(page - 1) * data.limit + 1}-
              {Math.min(page * data.limit, data.total)}개 표시
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                이전
              </button>
              <span className="px-4 py-2 text-sm text-gray-700">
                {page} / {data.pages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
                disabled={page === data.pages}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                다음
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
