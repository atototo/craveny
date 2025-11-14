"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import NewsImpact from "../../components/NewsImpact";

interface StockPrice {
  close: number;
  open: number;
  high: number;
  low: number;
  volume: number;
  change_rate: number;
  date: string | null;
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

interface RecentNews {
  id: number;
  title: string;
  source: string;
  published_at: string | null;
  notified_at: string | null;
  prediction?: {
    // Epic 3: New impact analysis fields
    sentiment_direction?: string | null;
    sentiment_score?: number | null;
    impact_level?: string | null;
    relevance_score?: number | null;
    urgency_level?: string | null;
    impact_analysis?: string | null;
    reasoning?: string | null;
    // Deprecated fields (backward compatibility)
    direction?: string;
    confidence?: number;
    short_term?: string;
    medium_term?: string;
    long_term?: string;
    confidence_breakdown?: ConfidenceBreakdown;
    pattern_analysis?: PatternAnalysis;
  };
}

interface DirectionDistribution {
  up: number;
  down: number;
  hold: number;
}

interface SingleModelSummary {
  overall_summary: string;
  short_term_scenario?: string | null;
  medium_term_scenario?: string | null;
  long_term_scenario?: string | null;
  risk_factors: string[];
  opportunity_factors: string[];
  recommendation?: string | null;
}

interface ABTestSummary {
  ab_test_enabled: true;
  model_a: SingleModelSummary;
  model_b: SingleModelSummary;
  comparison?: {
    recommendation_match: boolean;
    risk_overlap: string[];
    opportunity_overlap: string[];
  };
}

interface AnalysisSummary {
  // Single model fields (backward compatibility)
  overall_summary?: string;
  short_term_scenario?: string | null;
  medium_term_scenario?: string | null;
  long_term_scenario?: string | null;
  risk_factors?: string[];
  opportunity_factors?: string[];
  recommendation?: string | null;
  statistics?: {
    total_predictions: number;
    up_count: number;
    down_count: number;
    hold_count: number;
    avg_confidence: number | null;
  };
  meta?: {
    last_updated: string | null;
    based_on_prediction_count: number;
  };
  // A/B test fields
  ab_test_enabled?: boolean;
  model_a?: SingleModelSummary;
  model_b?: SingleModelSummary;
  comparison?: {
    recommendation_match: boolean;
    risk_overlap: string[];
    opportunity_overlap: string[];
  };
}

interface StockDetail {
  stock_code: string;
  stock_name: string;
  statistics: {
    total_news: number;
    total_notifications: number;
    avg_confidence: number | null;
    direction_distribution: DirectionDistribution | null;
    investment_opinion: string | null;
    opinion_confidence: number | null;
    // Phase 2: 종합 통계
    confidence_breakdown_avg?: ConfidenceBreakdown;
    pattern_analysis_avg?: PatternAnalysis;
  };
  // Phase 2: LLM 기반 AI 투자 분석 요약
  analysis_summary?: AnalysisSummary;
  current_price: StockPrice | null;
  recent_news: RecentNews[];
}

export default function StockDetailPage() {
  const params = useParams();
  const stockCode = params.stockCode as string;

  const [stock, setStock] = useState<StockDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);
  const [abConfig, setAbConfig] = useState<{model_a: {name: string}, model_b: {name: string}} | null>(null);
  const [updating, setUpdating] = useState(false);
  const [updateMessage, setUpdateMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

  // 단일 모델 리포트 렌더링 함수
  const renderModelSummary = (
    model: SingleModelSummary,
    modelName: string,
    bgColor: string,
    borderColor: string
  ) => {
    return (
      <div className={`flex-1 ${bgColor} rounded-2xl shadow-xl p-6 border ${borderColor}`}>
        {/* 모델 헤더 */}
        <div className="mb-6 pb-4 border-b-2 border-gray-300">
          <h3 className="text-2xl font-bold text-gray-900 flex items-center">
            <span className="mr-2">🤖</span> {modelName}
          </h3>
        </div>

        {/* 종합 의견 */}
        <div className="mb-6">
          <h4 className="text-lg font-bold text-gray-900 mb-3 flex items-center">
            <span className="mr-2">📋</span> 종합 의견
          </h4>
          <div className="p-4 bg-white rounded-lg shadow border-l-4 border-indigo-400">
            <p className="text-gray-700 leading-relaxed text-sm">{model.overall_summary}</p>
          </div>
        </div>

        {/* 기간별 투자 전략 */}
        <div className="mb-6">
          <h4 className="text-lg font-bold text-gray-900 mb-3 flex items-center">
            <span className="mr-2">📅</span> 기간별 투자 전략
          </h4>
          <div className="space-y-3">
            {model.short_term_scenario && (
              <div className="bg-white rounded-lg p-4 shadow border-l-4 border-red-300">
                <div className="flex items-center mb-2">
                  <span className="text-lg mr-2">🔹</span>
                  <h5 className="text-sm font-bold text-red-700">단기 (1일~1주)</h5>
                </div>
                <p className="text-xs text-gray-700 leading-relaxed">{model.short_term_scenario}</p>
              </div>
            )}

            {model.medium_term_scenario && (
              <div className="bg-white rounded-lg p-4 shadow border-l-4 border-yellow-300">
                <div className="flex items-center mb-2">
                  <span className="text-lg mr-2">🔸</span>
                  <h5 className="text-sm font-bold text-yellow-700">중기 (1주~1개월)</h5>
                </div>
                <p className="text-xs text-gray-700 leading-relaxed">{model.medium_term_scenario}</p>
              </div>
            )}

            {model.long_term_scenario && (
              <div className="bg-white rounded-lg p-4 shadow border-l-4 border-green-300">
                <div className="flex items-center mb-2">
                  <span className="text-lg mr-2">🔶</span>
                  <h5 className="text-sm font-bold text-green-700">장기 (1개월 이상)</h5>
                </div>
                <p className="text-xs text-gray-700 leading-relaxed">{model.long_term_scenario}</p>
              </div>
            )}
          </div>
        </div>

        {/* 리스크 요인 */}
        {model.risk_factors && model.risk_factors.length > 0 && (
          <div className="mb-6">
            <h4 className="text-lg font-bold text-orange-700 mb-3 flex items-center">
              <span className="mr-2">⚠️</span> 리스크 요인
            </h4>
            <div className="bg-white rounded-lg p-4 shadow border-l-4 border-orange-300">
              <ul className="space-y-2">
                {model.risk_factors.map((risk, index) => (
                  <li key={index} className="text-xs text-gray-700 flex items-start">
                    <span className="mr-2 text-orange-500 flex-shrink-0">•</span>
                    <span>{risk}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* 기회 요인 */}
        {model.opportunity_factors && model.opportunity_factors.length > 0 && (
          <div className="mb-6">
            <h4 className="text-lg font-bold text-teal-700 mb-3 flex items-center">
              <span className="mr-2">💡</span> 기회 요인
            </h4>
            <div className="bg-white rounded-lg p-4 shadow border-l-4 border-teal-300">
              <ul className="space-y-2">
                {model.opportunity_factors.map((opportunity, index) => (
                  <li key={index} className="text-xs text-gray-700 flex items-start">
                    <span className="mr-2 text-teal-500 flex-shrink-0">•</span>
                    <span>{opportunity}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* 최종 추천 */}
        {model.recommendation && (
          <div>
            <h4 className="text-lg font-bold text-gray-900 mb-3 flex items-center">
              <span className="mr-2">🎯</span> 최종 추천
            </h4>
            <div className="bg-white rounded-lg p-4 shadow-lg border-2 border-indigo-200">
              <p className="text-gray-700 font-medium leading-relaxed text-sm">
                {model.recommendation}
              </p>
            </div>
          </div>
        )}
      </div>
    );
  };

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // A/B 설정 가져오기
  useEffect(() => {
    fetch("/api/ab-test/config")
      .then((res) => res.json())
      .then((data) => {
        if (data.model_a && data.model_b) {
          setAbConfig({
            model_a: { name: data.model_a.name },
            model_b: { name: data.model_b.name }
          });
        }
      })
      .catch((err) => {
        console.error("Failed to fetch A/B config:", err);
      });
  }, []);

  useEffect(() => {
    if (!stockCode) return;

    fetch(`/api/stocks/${stockCode}`)
      .then((res) => {
        if (!res.ok) {
          throw new Error("종목을 찾을 수 없습니다");
        }
        return res.json();
      })
      .then((data) => {
        setStock(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch stock detail:", err);
        setError(err.message);
        setLoading(false);
      });
  }, [stockCode]);

  // 리포트 강제 업데이트 핸들러
  const handleForceUpdate = async () => {
    if (!stockCode) return;

    setUpdating(true);
    setUpdateMessage(null);

    try {
      const response = await fetch(`/api/reports/force-update/${stockCode}`, {
        method: "POST",
        signal: AbortSignal.timeout(120000), // 2분 타임아웃
        // Next.js의 기본 캐시를 비활성화하여 항상 새 요청
        cache: 'no-store',
      });

      const result = await response.json();

      if (result.success) {
        // 백엔드에서 생성된 리포트 데이터를 직접 받아서 적용
        if (result.analysis_summary && stock) {
          setStock({
            ...stock,
            analysis_summary: result.analysis_summary
          });

          setUpdateMessage({
            type: 'success',
            text: '리포트가 성공적으로 업데이트되었습니다.'
          });
        } else {
          // analysis_summary가 없으면 페이지 전체 새로고침
          const stockResponse = await fetch(`/api/stocks/${stockCode}`);
          if (stockResponse.ok) {
            const stockData = await stockResponse.json();
            setStock(stockData);
            setUpdateMessage({
              type: 'success',
              text: '리포트가 성공적으로 업데이트되었습니다.'
            });
          }
        }
      } else {
        setUpdateMessage({
          type: 'error',
          text: result.message
        });
      }
    } catch (error) {
      console.error("Failed to update report:", error);
      setUpdateMessage({
        type: 'error',
        text: "리포트 업데이트 중 오류가 발생했습니다."
      });
    } finally {
      setUpdating(false);

      // 5초 후 메시지 자동 제거
      setTimeout(() => {
        setUpdateMessage(null);
      }, 5000);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  if (error || !stock) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-xl text-red-600 mb-4">{error || "종목을 찾을 수 없습니다"}</p>
          <Link href="/stocks" className="text-blue-600 hover:underline">
            ← 종목 목록으로 돌아가기
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-6">
          <Link href="/stocks" className="text-blue-600 hover:underline mb-2 inline-block">
            ← 종목 목록
          </Link>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">{stock.stock_name}</h1>
              <p className="text-gray-600 mt-1">{stock.stock_code}</p>
            </div>
          </div>
        </div>

        {/* Current Price Section */}
        {stock.current_price && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">현재 주가</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-gray-600">종가</p>
                <p className="text-2xl font-bold text-gray-900">
                  {stock.current_price.close.toLocaleString()}원
                </p>
                <p
                  className={`text-sm mt-1 ${
                    stock.current_price.change_rate >= 0
                      ? "text-red-600"
                      : "text-blue-600"
                  }`}
                >
                  {stock.current_price.change_rate >= 0 ? "▲" : "▼"}{" "}
                  {Math.abs(stock.current_price.change_rate)}%
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">시가</p>
                <p className="text-xl font-semibold text-gray-700">
                  {stock.current_price.open ? stock.current_price.open.toLocaleString() : '-'}원
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">고가</p>
                <p className="text-xl font-semibold text-red-600">
                  {stock.current_price.high ? stock.current_price.high.toLocaleString() : '-'}원
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">저가</p>
                <p className="text-xl font-semibold text-blue-600">
                  {stock.current_price.low ? stock.current_price.low.toLocaleString() : '-'}원
                </p>
              </div>
            </div>
            {isMounted && stock.current_price.date && (
              <p className="text-sm text-gray-500 mt-4">
                기준일: {new Date(stock.current_price.date).toLocaleDateString("ko-KR")}
              </p>
            )}
          </div>
        )}

        {/* LLM-Generated Investment Summary - A/B Test Support */}
        {stock.analysis_summary && (
          <div className="bg-gradient-to-br from-slate-50 to-blue-50 rounded-2xl shadow-2xl p-8 mb-6 border border-indigo-100">
            {/* 헤더 */}
            <div className="mb-8 pb-6 border-b-2 border-indigo-200">
              <div className="flex items-center justify-between">
                <h2 className="text-3xl font-bold bg-gradient-to-r from-indigo-600 to-blue-600 bg-clip-text text-transparent flex items-center">
                  <span className="mr-3 text-3xl">🤖</span> AI 종합 투자 리포트
                  {stock.analysis_summary.ab_test_enabled && (
                    <span className="ml-4 text-sm font-normal text-purple-600 bg-purple-100 px-3 py-1 rounded-full">
                      A/B Testing
                    </span>
                  )}
                </h2>
                <button
                  onClick={handleForceUpdate}
                  disabled={updating}
                  className={`px-4 py-2 rounded-md font-medium text-sm transition-colors ${
                    updating
                      ? "bg-gray-400 cursor-not-allowed text-white"
                      : "bg-indigo-600 hover:bg-indigo-700 text-white shadow-md"
                  }`}
                >
                  {updating ? "업데이트 중..." : "🔄 리포트 업데이트"}
                </button>
              </div>

              {/* 업데이트 메시지 */}
              {updateMessage && (
                <div className={`mt-4 p-3 rounded-md ${
                  updateMessage.type === 'success'
                    ? 'bg-green-50 border border-green-200 text-green-800'
                    : 'bg-red-50 border border-red-200 text-red-800'
                }`}>
                  <p className="text-sm font-medium">{updateMessage.text}</p>
                </div>
              )}
            </div>

            {/* A/B Test Mode: Side-by-side comparison */}
            {stock.analysis_summary.ab_test_enabled && stock.analysis_summary.model_a && stock.analysis_summary.model_b ? (
              <div className="flex flex-col md:flex-row gap-6">
                {/* Model A - Dynamic name from A/B config */}
                {renderModelSummary(
                  stock.analysis_summary.model_a,
                  abConfig ? `Model A (${abConfig.model_a.name})` : "Model A",
                  "bg-blue-50",
                  "border-blue-200"
                )}

                {/* Model B - Dynamic name from A/B config */}
                {renderModelSummary(
                  stock.analysis_summary.model_b,
                  abConfig ? `Model B (${abConfig.model_b.name})` : "Model B",
                  "bg-green-50",
                  "border-green-200"
                )}
              </div>
            ) : (
              // Single Model Mode (Backward Compatibility)
              <div>

            {/* Section 1: 종합 의견 */}
            <div className="mb-10">
              <div className="mb-4">
                <h3 className="text-xl font-bold text-gray-900 flex items-center">
                  <span className="mr-3 text-2xl">📋</span> 종합 의견
                </h3>
              </div>
              <div className="p-6 bg-white rounded-xl shadow-lg border-l-4 border-indigo-500">
                <p className="text-gray-700 leading-relaxed text-base">{stock.analysis_summary.overall_summary}</p>
              </div>
            </div>

            {/* Section 2: 기간별 투자 전략 */}
            <div className="mb-10">
              <div className="mb-4">
                <h3 className="text-xl font-bold text-gray-900 flex items-center">
                  <span className="mr-3 text-2xl">📅</span> 기간별 투자 전략
                </h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {/* Short-term */}
                {stock.analysis_summary.short_term_scenario && (
                  <div className="bg-white rounded-xl p-5 shadow-md hover:shadow-xl transition-shadow border-l-4 border-red-400">
                    <div className="flex items-center mb-3">
                      <span className="text-2xl mr-2">🔹</span>
                      <h4 className="text-base font-bold text-red-700">단기 (1일~1주)</h4>
                    </div>
                    <p className="text-sm text-gray-700 leading-relaxed">
                      {stock.analysis_summary.short_term_scenario}
                    </p>
                  </div>
                )}

                {/* Medium-term */}
                {stock.analysis_summary.medium_term_scenario && (
                  <div className="bg-white rounded-xl p-5 shadow-md hover:shadow-xl transition-shadow border-l-4 border-yellow-400">
                    <div className="flex items-center mb-3">
                      <span className="text-2xl mr-2">🔸</span>
                      <h4 className="text-base font-bold text-yellow-700">중기 (1주~1개월)</h4>
                    </div>
                    <p className="text-sm text-gray-700 leading-relaxed">
                      {stock.analysis_summary.medium_term_scenario}
                    </p>
                  </div>
                )}

                {/* Long-term */}
                {stock.analysis_summary.long_term_scenario && (
                  <div className="bg-white rounded-xl p-5 shadow-md hover:shadow-xl transition-shadow border-l-4 border-green-400">
                    <div className="flex items-center mb-3">
                      <span className="text-2xl mr-2">🔶</span>
                      <h4 className="text-base font-bold text-green-700">장기 (1개월 이상)</h4>
                    </div>
                    <p className="text-sm text-gray-700 leading-relaxed">
                      {stock.analysis_summary.long_term_scenario}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Section 3: 리스크 및 기회 요인 */}
            <div className="mb-10">
              <div className="mb-4">
                <h3 className="text-xl font-bold text-gray-900 flex items-center">
                  <span className="mr-3 text-2xl">⚖️</span> 리스크 및 기회 요인
                </h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {/* Risk Factors */}
                {stock.analysis_summary?.risk_factors && stock.analysis_summary.risk_factors.length > 0 && (
                  <div className="bg-white rounded-xl p-5 shadow-md border-l-4 border-orange-400">
                    <h4 className="text-lg font-bold text-orange-700 mb-4 flex items-center">
                      <span className="mr-2 text-xl">⚠️</span> 리스크 요인
                    </h4>
                    <ul className="space-y-3">
                      {stock.analysis_summary.risk_factors.map((risk, index) => (
                        <li key={index} className="text-sm text-gray-700 flex items-start">
                          <span className="mr-2 text-orange-500 flex-shrink-0 font-bold">•</span>
                          <span className="leading-relaxed">{risk}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Opportunity Factors */}
                {stock.analysis_summary?.opportunity_factors && stock.analysis_summary.opportunity_factors.length > 0 && (
                  <div className="bg-white rounded-xl p-5 shadow-md border-l-4 border-teal-400">
                    <h4 className="text-lg font-bold text-teal-700 mb-4 flex items-center">
                      <span className="mr-2 text-xl">💡</span> 기회 요인
                    </h4>
                    <ul className="space-y-3">
                      {stock.analysis_summary.opportunity_factors.map((opportunity, index) => (
                        <li key={index} className="text-sm text-gray-700 flex items-start">
                          <span className="mr-2 text-teal-500 flex-shrink-0 font-bold">•</span>
                          <span className="leading-relaxed">{opportunity}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>

            {/* Section 4: 최종 추천 */}
            {stock.analysis_summary.recommendation && (
              <div className="mb-6">
                <div className="mb-4">
                  <h3 className="text-xl font-bold text-gray-900 flex items-center">
                    <span className="mr-3 text-2xl">🎯</span> 최종 추천
                  </h3>
                </div>
                <div className="bg-white rounded-xl p-6 shadow-xl border-2 border-indigo-200">
                  <p className="text-gray-700 font-medium leading-relaxed text-base">
                    {stock.analysis_summary.recommendation}
                  </p>
                </div>
              </div>
            )}

            {/* Meta Info - 세련된 푸터 */}
            {stock.analysis_summary.meta && (
              <div className="mt-6 pt-5 border-t border-gray-300">
                <div className="flex items-center justify-center text-sm text-gray-500">
                  <span className="mr-2">📊</span>
                  <span className="font-medium">분석 기준: {stock.analysis_summary.meta.based_on_prediction_count}건의 예측</span>
                  {isMounted && stock.analysis_summary.meta.last_updated && (() => {
                    const lastUpdated = new Date(stock.analysis_summary.meta.last_updated);
                    const now = new Date();
                    const diffMs = now.getTime() - lastUpdated.getTime();
                    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
                    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

                    let timeAgo = '';
                    if (diffHours > 0) {
                      timeAgo = `${diffHours}시간 ${diffMinutes}분 전`;
                    } else {
                      timeAgo = `${diffMinutes}분 전`;
                    }

                    // 5시간 이상 지났으면 경고 스타일
                    const isStale = diffHours >= 5;

                    return (
                      <>
                        <span className="mx-2">|</span>
                        <span className={isStale ? "font-bold text-orange-600" : ""}>
                          🕐 리포트 생성: {lastUpdated.toLocaleString("ko-KR")} ({timeAgo})
                        </span>
                      </>
                    );
                  })()}
                </div>
              </div>
            )}
              </div>
            )}

            {/* Common Meta Info Footer */}
            {stock.analysis_summary.meta && (
              <div className="mt-6 pt-5 border-t border-gray-300">
                <div className="flex items-center justify-center text-sm text-gray-500">
                  <span className="mr-2">📊</span>
                  <span className="font-medium">분석 기준: {stock.analysis_summary.meta.based_on_prediction_count}건의 예측</span>
                  {isMounted && stock.analysis_summary.meta.last_updated && (() => {
                    const lastUpdated = new Date(stock.analysis_summary.meta.last_updated);
                    const now = new Date();
                    const diffMs = now.getTime() - lastUpdated.getTime();
                    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
                    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

                    let timeAgo = '';
                    if (diffHours > 0) {
                      timeAgo = `${diffHours}시간 ${diffMinutes}분 전`;
                    } else {
                      timeAgo = `${diffMinutes}분 전`;
                    }

                    // 5시간 이상 지났으면 경고 스타일
                    const isStale = diffHours >= 5;

                    return (
                      <>
                        <span className="mx-2">|</span>
                        <span className={isStale ? "font-bold text-orange-600" : ""}>
                          🕐 리포트 생성: {lastUpdated.toLocaleString("ko-KR")} ({timeAgo})
                        </span>
                      </>
                    );
                  })()}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Statistics Section - 뉴스 통계만 표시 */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">📊 뉴스 통계</h2>
          <div className="grid grid-cols-2 gap-6">
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-3xl font-bold text-green-600">
                {stock.statistics.total_news}
              </div>
              <div className="text-sm text-gray-600 mt-1">총 뉴스</div>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <div className="text-3xl font-bold text-purple-600">
                {stock.statistics.total_notifications}
              </div>
              <div className="text-sm text-gray-600 mt-1">알림 전송</div>
            </div>
          </div>
        </div>

        {/* Recent News Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">📰 최근 뉴스 & AI 분석</h2>
          {stock.recent_news.length > 0 ? (
            <div className="space-y-4">
              {stock.recent_news.map((news) => (
                <div
                  key={news.id}
                  className="border border-gray-200 rounded-lg overflow-hidden"
                >
                  <div className="p-4 bg-gray-50">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="font-medium text-gray-900 mb-2">{news.title}</h3>
                        <div className="flex items-center gap-3 text-sm text-gray-600">
                          <span>📰 {news.source}</span>
                          {isMounted && news.published_at && (
                            <span>
                              🕐 {new Date(news.published_at).toLocaleString("ko-KR")}
                            </span>
                          )}
                        </div>
                      </div>
                      {news.notified_at && (
                        <span className="ml-4 px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded-full">
                          알림 전송
                        </span>
                      )}
                    </div>

                    {/* Epic 5: News Impact Display */}
                    {news.prediction && (
                      <div className="mt-4">
                        <NewsImpact prediction={news.prediction} />
                      </div>
                    )}

                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <p>관련 뉴스가 없습니다</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
