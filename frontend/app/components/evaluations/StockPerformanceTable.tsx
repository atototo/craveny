'use client';

import { useState, useEffect } from 'react';

interface StockPerformanceTableProps {
  modelId: string | string[];
  period: string;
}

export default function StockPerformanceTable({
  modelId,
  period
}: StockPerformanceTableProps) {
  const [stockData, setStockData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStockPerformance();
  }, [modelId, period]);

  const fetchStockPerformance = async () => {
    try {
      const res = await fetch(
        `http://localhost:8000/api/evaluations/model/${modelId}/stocks?days=${period}`
      );
      const data = await res.json();
      setStockData(data);
    } catch (error) {
      console.error('종목별 성능 로드 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>로딩 중...</div>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b">
            <th className="text-left p-3">종목</th>
            <th className="text-left p-3">예측 건수</th>
            <th className="text-left p-3">평균 점수</th>
            <th className="text-left p-3">목표가 달성률</th>
            <th className="text-left p-3">손절가 이탈률</th>
            <th className="text-left p-3">추세</th>
          </tr>
        </thead>
        <tbody>
          {stockData.map((stock) => (
            <tr key={stock.stock_code} className="border-b hover:bg-gray-50">
              <td className="p-3 font-medium">
                {stock.stock_code}
              </td>
              <td className="p-3">{stock.prediction_count}</td>
              <td className="p-3">
                <span className="font-semibold">
                  {stock.avg_score?.toFixed(1) || 0}
                </span>
              </td>
              <td className="p-3">
                <span
                  className={`inline-block px-2 py-1 rounded text-sm ${
                    stock.target_achieved_rate > 50
                      ? 'bg-blue-100 text-blue-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {stock.target_achieved_rate?.toFixed(1) || 0}%
                </span>
              </td>
              <td className="p-3">
                <span
                  className={`inline-block px-2 py-1 rounded text-sm ${
                    stock.support_breach_rate < 20
                      ? 'bg-blue-100 text-blue-800'
                      : 'bg-red-100 text-red-800'
                  }`}
                >
                  {stock.support_breach_rate?.toFixed(1) || 0}%
                </span>
              </td>
              <td className="p-3">
                {stock.trend === 'up' ? (
                  <span className="text-green-500 text-xl">↑</span>
                ) : (
                  <span className="text-red-500 text-xl">↓</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
