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

interface ForceUpdateResult {
  total_stocks: number;
  stale_stocks: number;
  updated: number;
  failed: number;
  message: string;
}

export default function AdminDashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [updateResult, setUpdateResult] = useState<ForceUpdateResult | null>(null);
  const [ttlHours, setTtlHours] = useState(6.0);

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

  const handleForceUpdate = async () => {
    setUpdating(true);
    setUpdateResult(null);

    try {
      const response = await fetch(`/api/reports/force-update?ttl_hours=${ttlHours}`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error("Failed to force update reports");
      }

      const result: ForceUpdateResult = await response.json();
      setUpdateResult(result);
    } catch (error) {
      console.error("Failed to force update reports:", error);
      alert("리포트 업데이트 실패");
    } finally {
      setUpdating(false);
    }
  };

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
        <div className="bg-white rounded-lg shadow p-6 mb-8">
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

        {/* Force Update Reports */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4">🔄 리포트 강제 업데이트</h2>
          <p className="text-sm text-gray-600 mb-4">
            오래된 종목 리포트를 강제로 업데이트합니다. 버튼 누른 시점 기준으로 설정된 TTL보다 오래된 리포트가 업데이트됩니다.
          </p>

          <div className="flex items-center gap-4 mb-4">
            <div className="flex items-center gap-2">
              <label htmlFor="ttl-hours" className="text-sm font-medium text-gray-700">
                TTL (시간):
              </label>
              <input
                id="ttl-hours"
                type="number"
                min="0.5"
                max="24"
                step="0.5"
                value={ttlHours}
                onChange={(e) => setTtlHours(parseFloat(e.target.value))}
                className="w-20 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <button
              onClick={handleForceUpdate}
              disabled={updating}
              className={`px-6 py-2 rounded-md font-medium transition-colors ${
                updating
                  ? "bg-gray-400 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700 text-white"
              }`}
            >
              {updating ? "업데이트 중..." : "리포트 강제 업데이트"}
            </button>
          </div>

          {updateResult && (
            <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
              <h3 className="font-bold text-blue-900 mb-2">업데이트 결과</h3>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-700">전체 종목:</span>
                  <span className="font-medium">{updateResult.total_stocks}개</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-700">업데이트 필요:</span>
                  <span className="font-medium text-orange-600">{updateResult.stale_stocks}개</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-700">성공:</span>
                  <span className="font-medium text-green-600">{updateResult.updated}개</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-700">실패:</span>
                  <span className="font-medium text-red-600">{updateResult.failed}개</span>
                </div>
                <div className="mt-2 pt-2 border-t border-blue-200">
                  <p className="text-blue-800">{updateResult.message}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
