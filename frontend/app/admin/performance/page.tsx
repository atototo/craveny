"use client";

import { useEffect, useState } from "react";

interface DashboardData {
  today_queue_count: number;
  today_evaluated_count: number;
  models: Array<{
    model_id: number;
    model_name: string;
    avg_score: number;
    avg_achieved_rate: number;
    total_predictions: number;
  }>;
  recent_trend: Array<{
    date: string;
    model_id: number;
    model_name: string;
    avg_score: number;
  }>;
}

export default function PerformanceDashboard() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const response = await fetch("/api/evaluations/dashboard");
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      // Ensure data has the correct structure
      setDashboard({
        today_queue_count: data.today_queue_count || 0,
        today_evaluated_count: data.today_evaluated_count || 0,
        models: Array.isArray(data.models) ? data.models : [],
        recent_trend: Array.isArray(data.recent_trend) ? data.recent_trend : [],
      });
    } catch (error) {
      console.error("Failed to load dashboard:", error);
      setDashboard(null);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl text-red-500">데이터를 불러올 수 없습니다</div>
      </div>
    );
  }

  // 트렌드 데이터를 날짜별로 그룹화
  const trendByDate = (dashboard.recent_trend || []).reduce((acc, item) => {
    if (!acc[item.date]) {
      acc[item.date] = [];
    }
    acc[item.date].push(item);
    return acc;
  }, {} as Record<string, Array<{date: string; model_id: number; model_name: string; avg_score: number}>>);

  const sortedDates = Object.keys(trendByDate).sort().reverse().slice(0, 10);

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">모델 성능 대시보드</h1>
          <p className="mt-2 text-sm text-gray-600">
            최근 30일 모델 평가 성능 분석
          </p>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">오늘의 평가 대기</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">
                  {dashboard.today_queue_count}
                </p>
              </div>
              <div className="p-3 bg-blue-100 rounded-full">
                <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">오늘 평가 완료</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">
                  {dashboard.today_evaluated_count}
                </p>
              </div>
              <div className="p-3 bg-green-100 rounded-full">
                <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* Model Leaderboard */}
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-bold text-gray-900">모델 리더보드 (최근 30일)</h2>
          </div>
          <div className="overflow-x-auto">
            {dashboard.models.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                평가 데이터가 없습니다
              </div>
            ) : (
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">순위</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">모델</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">평균 점수</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">목표가 달성률</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">총 예측 수</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {dashboard.models.map((model, index) => (
                    <tr key={model.model_id} className={index === 0 ? "bg-yellow-50" : ""}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {index === 0 && <span className="text-2xl">🥇</span>}
                        {index === 1 && <span className="text-2xl">🥈</span>}
                        {index === 2 && <span className="text-2xl">🥉</span>}
                        {index > 2 && <span className="text-sm text-gray-500">{index + 1}</span>}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {model.model_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <div className="flex items-center">
                          <span className="font-bold">{model.avg_score.toFixed(1)}</span>
                          <span className="text-gray-500 ml-1">/ 100</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <span className={`font-medium ${model.avg_achieved_rate >= 50 ? "text-green-600" : "text-red-600"}`}>
                          {model.avg_achieved_rate.toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {model.total_predictions.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Recent Trend */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-bold text-gray-900">최근 성능 트렌드 (최근 10일)</h2>
          </div>
          <div className="p-6">
            {sortedDates.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                트렌드 데이터가 없습니다
              </div>
            ) : (
              <div className="space-y-4">
                {sortedDates.map((date) => (
                  <div key={date} className="border-l-4 border-blue-500 pl-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium text-gray-900">{date}</h3>
                      <span className="text-xs text-gray-500">
                        {trendByDate[date].length} 모델
                      </span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {trendByDate[date].map((item) => (
                        <div key={item.model_id} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                          <span className="text-sm text-gray-700">{item.model_name}</span>
                          <span className="text-sm font-bold text-gray-900">
                            {item.avg_score.toFixed(1)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
