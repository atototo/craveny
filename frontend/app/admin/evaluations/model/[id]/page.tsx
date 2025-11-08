'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import MetricBreakdownChart from '@/app/components/evaluations/MetricBreakdownChart';
import StockPerformanceTable from '@/app/components/evaluations/StockPerformanceTable';

export default function ModelDetailPage() {
  const params = useParams();
  const modelId = params.id;

  const [period, setPeriod] = useState('30');
  const [activeTab, setActiveTab] = useState('metrics');
  const [modelData, setModelData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchModelDetail();
  }, [modelId, period]);

  const fetchModelDetail = async () => {
    try {
      const res = await fetch(
        `http://localhost:8000/api/evaluations/model/${modelId}?days=${period}`
      );
      const data = await res.json();
      setModelData(data);
    } catch (error) {
      console.error('모델 상세 로드 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="p-6">로딩 중...</div>;
  if (!modelData) return <div className="p-6">데이터 없음</div>;

  return (
    <div className="p-6 space-y-6">
      {/* 헤더 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Model {modelId} 상세 분석</h1>
          <p className="text-gray-500">최근 {period}일 성능 분석</p>
        </div>

        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="px-4 py-2 border rounded-lg"
        >
          <option value="7">최근 7일</option>
          <option value="30">최근 30일</option>
          <option value="90">최근 90일</option>
        </select>
      </div>

      {/* 주요 지표 카드 */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-sm text-gray-500 mb-2">평균 최종 점수</div>
          <div className="text-3xl font-bold text-blue-600">
            {modelData.avg_final_score?.toFixed(1) || 0}
          </div>
          <div className="text-xs text-gray-500 mt-1">/100점</div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-sm text-gray-500 mb-2">목표가 달성률</div>
          <div className="text-3xl font-bold text-green-600">
            {modelData.target_achieved_rate?.toFixed(1) || 0}%
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {modelData.target_achieved_count || 0}건 달성
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-sm text-gray-500 mb-2">손절가 이탈률</div>
          <div className="text-3xl font-bold text-red-600">
            {modelData.support_breach_rate?.toFixed(1) || 0}%
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {modelData.support_breach_count || 0}건 이탈
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-sm text-gray-500 mb-2">총 예측 건수</div>
          <div className="text-3xl font-bold">
            {modelData.total_predictions || 0}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            사람 평가 {modelData.human_evaluated_count || 0}건
          </div>
        </div>
      </div>

      {/* 탭 */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b">
          <div className="flex space-x-4 p-4">
            <button
              onClick={() => setActiveTab('metrics')}
              className={`px-4 py-2 font-medium ${
                activeTab === 'metrics'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-600'
              }`}
            >
              메트릭 분석
            </button>
            <button
              onClick={() => setActiveTab('stocks')}
              className={`px-4 py-2 font-medium ${
                activeTab === 'stocks'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-600'
              }`}
            >
              종목별 성능
            </button>
            <button
              onClick={() => setActiveTab('insights')}
              className={`px-4 py-2 font-medium ${
                activeTab === 'insights'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-600'
              }`}
            >
              인사이트
            </button>
          </div>
        </div>

        <div className="p-6">
          {activeTab === 'metrics' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-bold mb-4">세부 메트릭 브레이크다운</h3>
                <MetricBreakdownChart
                  targetAccuracy={modelData.avg_target_accuracy || 0}
                  timing={modelData.avg_timing_score || 0}
                  riskManagement={modelData.avg_risk_management || 0}
                />
              </div>

              <div>
                <h3 className="text-lg font-bold mb-4">상세 통계</h3>
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2">메트릭</th>
                      <th className="text-right p-2">평균</th>
                      <th className="text-right p-2">중앙값</th>
                      <th className="text-right p-2">표준편차</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b">
                      <td className="p-2">목표가 정확도</td>
                      <td className="text-right">
                        {modelData.avg_target_accuracy?.toFixed(1) || 0}
                      </td>
                      <td className="text-right">
                        {modelData.median_target_accuracy?.toFixed(1) || 0}
                      </td>
                      <td className="text-right">
                        {modelData.std_target_accuracy?.toFixed(1) || 0}
                      </td>
                    </tr>
                    <tr className="border-b">
                      <td className="p-2">타이밍 점수</td>
                      <td className="text-right">
                        {modelData.avg_timing_score?.toFixed(1) || 0}
                      </td>
                      <td className="text-right">
                        {modelData.median_timing_score?.toFixed(1) || 0}
                      </td>
                      <td className="text-right">
                        {modelData.std_timing_score?.toFixed(1) || 0}
                      </td>
                    </tr>
                    <tr>
                      <td className="p-2">리스크 관리</td>
                      <td className="text-right">
                        {modelData.avg_risk_management?.toFixed(1) || 0}
                      </td>
                      <td className="text-right">
                        {modelData.median_risk_management?.toFixed(1) || 0}
                      </td>
                      <td className="text-right">
                        {modelData.std_risk_management?.toFixed(1) || 0}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'stocks' && (
            <div>
              <h3 className="text-lg font-bold mb-4">종목별 성능 분석</h3>
              <StockPerformanceTable modelId={modelId} period={period} />
            </div>
          )}

          {activeTab === 'insights' && (
            <div>
              <h3 className="text-lg font-bold mb-4">AI 인사이트 (향후 구현)</h3>
              <p className="text-gray-500">
                모델의 강점, 약점, 개선 기회를 AI가 분석하여 제공합니다.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
