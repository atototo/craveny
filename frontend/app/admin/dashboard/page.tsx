"use client";

import { useEffect, useState } from "react";

interface DashboardSummary {
  today_predictions: number;
  total_predictions: number;
  total_news: number;
  recent_news: number;
  average_confidence: number;
  direction_distribution: {
    up: number;
    down: number;
    hold: number;
  };
}

export default function AdminDashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/dashboard/summary")
      .then((res) => res.json())
      .then((data) => {
        setSummary(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch dashboard summary:", err);
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

  return (
    <div className="min-h-screen">
      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">⚙️ 관리자 대시보드</h1>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">오늘의 예측 수</h3>
            <p className="text-3xl font-bold text-blue-600 mt-2">
              {summary?.today_predictions || 0}
            </p>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">평균 신뢰도</h3>
            <p className="text-3xl font-bold text-green-600 mt-2">
              {summary?.average_confidence || 0}%
            </p>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">총 예측 건수</h3>
            <p className="text-3xl font-bold text-purple-600 mt-2">
              {summary?.total_predictions || 0}
            </p>
          </div>
        </div>

        {/* Prediction Distribution */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-xl font-bold mb-4">📊 예측 방향 분포</h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                📈 {summary?.direction_distribution?.up || 0}%
              </div>
              <div className="text-sm text-gray-500 mt-1">상승</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">
                📉 {summary?.direction_distribution?.down || 0}%
              </div>
              <div className="text-sm text-gray-500 mt-1">하락</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-600">
                ➡️ {summary?.direction_distribution?.hold || 0}%
              </div>
              <div className="text-sm text-gray-500 mt-1">유지</div>
            </div>
          </div>
        </div>

        {/* System Status */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4">📡 시스템 상태</h2>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-gray-700">크롤러</span>
              <span className="text-green-600 font-medium">✅ 정상</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-700">총 뉴스</span>
              <span className="text-blue-600 font-medium">{summary?.total_news || 0}건</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-700">최근 1시간 뉴스</span>
              <span className="text-blue-600 font-medium">{summary?.recent_news || 0}건</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
