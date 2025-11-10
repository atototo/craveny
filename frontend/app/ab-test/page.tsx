'use client';

import { useState } from 'react';

export default function ABTestPage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const runABTest = async () => {
    setLoading(true);
    setError(null);

    try {
      // 테스트 데이터로 A/B 예측 수행
      const testNews = {
        title: "삼성전자, AI 반도체 수주 확대...글로벌 점유율 1위 전망",
        content: "삼성전자가 인공지능(AI) 반도체 분야에서 대규모 수주에 성공하며 글로벌 시장 점유율 1위를 달성할 것으로 전망된다.",
        stock_code: "005930"
      };

      const similarNews = [
        {
          news_title: "삼성전자, 신규 반도체 공장 착공",
          news_content: "삼성전자가 경기도 평택에 신규 반도체 공장 착공식을 가졌다.",
          similarity: 0.85,
          published_at: "2024-01-15",
          price_changes: {"1d": 2.5, "2d": 3.8, "3d": 5.2, "5d": 7.8, "10d": 12.5, "20d": 18.3}
        },
        {
          news_title: "삼성전자 HBM3 반도체, 엔비디아 공급 승인",
          news_content: "삼성전자의 고대역폭메모리(HBM3) 반도체가 엔비디아의 품질 검증을 통과했다.",
          similarity: 0.78,
          published_at: "2024-02-10",
          price_changes: {"1d": 3.2, "2d": 4.5, "3d": 6.1, "5d": 8.9, "10d": 11.2, "20d": 15.7}
        }
      ];

      // 백엔드 API 호출 (dual_predict) - 타임아웃 60초
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 60000);

      const response = await fetch('/api/ab-test/predict', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          current_news: testNews,
          similar_news: similarNews,
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || 'A/B 테스트 실패');
      }

      const data = await response.json();
      setResult(data);
    } catch (err: any) {
      if (err.name === 'AbortError') {
        setError('요청 시간 초과 (60초). API 응답이 너무 오래 걸립니다.');
      } else {
        setError(err.message || 'A/B 테스트 실패');
      }
      console.error('A/B 테스트 오류:', err);
    } finally {
      setLoading(false);
    }
  };

  const getDirectionEmoji = (prediction: string) => {
    if (prediction === '상승') return '📈';
    if (prediction === '하락') return '📉';
    return '➡️';
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">🤖 A/B 테스트 (GPT-4o vs DeepSeek)</h1>

        <button
          onClick={runABTest}
          disabled={loading}
          className="mb-8 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {loading && <span className="animate-spin">⏳</span>}
          {loading ? 'GPT-4o & DeepSeek 분석 중... (최대 60초 소요)' : 'A/B 테스트 실행'}
        </button>

        {error && (
          <div className="mb-8 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            ❌ 오류: {error}
          </div>
        )}

        {result && (
          <div className="space-y-6">
            {/* 비교 분석 요약 */}
            <div className="bg-white p-6 rounded-lg shadow">
              <h2 className="text-xl font-bold mb-4">🔍 비교 분석</h2>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center p-4 bg-gray-50 rounded">
                  <div className="text-sm text-gray-600 mb-2">예측 일치</div>
                  <div className="text-2xl font-bold">
                    {result.comparison.agreement ? '✅ 일치' : '⚠️ 불일치'}
                  </div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded">
                  <div className="text-sm text-gray-600 mb-2">신뢰도 차이</div>
                  <div className="text-2xl font-bold">{result.comparison.confidence_diff}%</div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded">
                  <div className="text-sm text-gray-600 mb-2">더 강한 모델</div>
                  <div className="text-2xl font-bold">
                    {result.comparison.stronger_model === 'model_a' ? 'GPT-4o' : result.comparison.stronger_model === 'model_b' ? 'DeepSeek' : '동등'}
                  </div>
                </div>
              </div>
            </div>

            {/* A/B 비교 - 풍부한 분석 */}
            <div className="grid grid-cols-2 gap-6">
              {/* Model A (GPT-4o) */}
              <div className="bg-blue-50 border-2 border-blue-200 p-6 rounded-lg">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-xl font-bold text-blue-900">📊 Model A</h3>
                  <span className="text-sm text-blue-700 bg-blue-100 px-3 py-1 rounded-full font-semibold">
                    {result.model_a.model}
                  </span>
                </div>

                <div className="space-y-4">
                  {/* 종합 의견 */}
                  <div className="bg-white p-4 rounded-lg border-l-4 border-blue-500">
                    <h4 className="font-semibold mb-2 text-blue-900 flex items-center gap-2">
                      🤖 AI 종합 투자 리포트
                    </h4>
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-4xl">{getDirectionEmoji(result.model_a.prediction)}</span>
                      <div className="text-right">
                        <div className="text-3xl font-bold text-blue-900">{result.model_a.prediction}</div>
                        <div className="text-sm text-gray-600">신뢰도: {result.model_a.confidence}%</div>
                      </div>
                    </div>
                    <p className="text-sm text-gray-700 leading-relaxed">{result.model_a.reasoning}</p>
                  </div>

                  {/* 신뢰도 분석 */}
                  {result.model_a.confidence_breakdown && (
                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-semibold mb-3 text-gray-700 flex items-center gap-2">
                        📋 종합 의견
                      </h4>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-600">유사 뉴스 품질</span>
                          <span className="font-semibold">{result.model_a.confidence_breakdown.similar_news_quality}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">패턴 일관성</span>
                          <span className="font-semibold">{result.model_a.confidence_breakdown.pattern_consistency}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">공시 영향도</span>
                          <span className="font-semibold">{result.model_a.confidence_breakdown.disclosure_impact}%</span>
                        </div>
                        <div className="mt-3 pt-3 border-t text-xs text-gray-600">
                          {result.model_a.confidence_breakdown.explanation}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 기간별 투자 전략 */}
                  <div className="bg-white p-4 rounded-lg">
                    <h4 className="font-semibold mb-3 text-gray-700 flex items-center gap-2">
                      📅 기간별 투자 전략
                    </h4>
                    <div className="space-y-3">
                      <div className="border-l-4 border-red-400 pl-3">
                        <div className="font-semibold text-sm text-red-700 mb-1">🔴 단기 (1일~1주)</div>
                        <p className="text-sm text-gray-600">{result.model_a.short_term}</p>
                      </div>
                      <div className="border-l-4 border-yellow-400 pl-3">
                        <div className="font-semibold text-sm text-yellow-700 mb-1">🟡 중기 (1주~1개월)</div>
                        <p className="text-sm text-gray-600">{result.model_a.medium_term}</p>
                      </div>
                      <div className="border-l-4 border-green-400 pl-3">
                        <div className="font-semibold text-sm text-green-700 mb-1">🟢 장기 (1개월 이상)</div>
                        <p className="text-sm text-gray-600">{result.model_a.long_term}</p>
                      </div>
                    </div>
                  </div>

                  {/* 패턴 분석 */}
                  {result.model_a.pattern_analysis && (
                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-semibold mb-3 text-gray-700">📊 과거 패턴 분석</h4>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div className="text-center p-2 bg-gray-50 rounded">
                          <div className="text-gray-600">평균 1일</div>
                          <div className="font-bold text-blue-600">{result.model_a.pattern_analysis.avg_1d}%</div>
                        </div>
                        <div className="text-center p-2 bg-gray-50 rounded">
                          <div className="text-gray-600">평균 3일</div>
                          <div className="font-bold text-blue-600">{result.model_a.pattern_analysis.avg_3d}%</div>
                        </div>
                        <div className="text-center p-2 bg-gray-50 rounded">
                          <div className="text-gray-600">평균 5일</div>
                          <div className="font-bold text-blue-600">{result.model_a.pattern_analysis.avg_5d || 'N/A'}</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Model B (DeepSeek) */}
              <div className="bg-green-50 border-2 border-green-200 p-6 rounded-lg">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-xl font-bold text-green-900">📊 Model B</h3>
                  <span className="text-sm text-green-700 bg-green-100 px-3 py-1 rounded-full font-semibold">
                    {result.model_b.model}
                  </span>
                </div>

                <div className="space-y-4">
                  {/* 종합 의견 */}
                  <div className="bg-white p-4 rounded-lg border-l-4 border-green-500">
                    <h4 className="font-semibold mb-2 text-green-900 flex items-center gap-2">
                      🤖 AI 종합 투자 리포트
                    </h4>
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-4xl">{getDirectionEmoji(result.model_b.prediction)}</span>
                      <div className="text-right">
                        <div className="text-3xl font-bold text-green-900">{result.model_b.prediction}</div>
                        <div className="text-sm text-gray-600">신뢰도: {result.model_b.confidence}%</div>
                      </div>
                    </div>
                    <p className="text-sm text-gray-700 leading-relaxed">{result.model_b.reasoning}</p>
                  </div>

                  {/* 신뢰도 분석 */}
                  {result.model_b.confidence_breakdown && (
                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-semibold mb-3 text-gray-700 flex items-center gap-2">
                        📋 종합 의견
                      </h4>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-600">유사 뉴스 품질</span>
                          <span className="font-semibold">{result.model_b.confidence_breakdown.similar_news_quality}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">패턴 일관성</span>
                          <span className="font-semibold">{result.model_b.confidence_breakdown.pattern_consistency}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">공시 영향도</span>
                          <span className="font-semibold">{result.model_b.confidence_breakdown.disclosure_impact}%</span>
                        </div>
                        <div className="mt-3 pt-3 border-t text-xs text-gray-600">
                          {result.model_b.confidence_breakdown.explanation}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 기간별 투자 전략 */}
                  <div className="bg-white p-4 rounded-lg">
                    <h4 className="font-semibold mb-3 text-gray-700 flex items-center gap-2">
                      📅 기간별 투자 전략
                    </h4>
                    <div className="space-y-3">
                      <div className="border-l-4 border-red-400 pl-3">
                        <div className="font-semibold text-sm text-red-700 mb-1">🔴 단기 (1일~1주)</div>
                        <p className="text-sm text-gray-600">{result.model_b.short_term}</p>
                      </div>
                      <div className="border-l-4 border-yellow-400 pl-3">
                        <div className="font-semibold text-sm text-yellow-700 mb-1">🟡 중기 (1주~1개월)</div>
                        <p className="text-sm text-gray-600">{result.model_b.medium_term}</p>
                      </div>
                      <div className="border-l-4 border-green-400 pl-3">
                        <div className="font-semibold text-sm text-green-700 mb-1">🟢 장기 (1개월 이상)</div>
                        <p className="text-sm text-gray-600">{result.model_b.long_term}</p>
                      </div>
                    </div>
                  </div>

                  {/* 패턴 분석 */}
                  {result.model_b.pattern_analysis && (
                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-semibold mb-3 text-gray-700">📊 과거 패턴 분석</h4>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div className="text-center p-2 bg-gray-50 rounded">
                          <div className="text-gray-600">평균 1일</div>
                          <div className="font-bold text-green-600">{result.model_b.pattern_analysis.avg_1d}%</div>
                        </div>
                        <div className="text-center p-2 bg-gray-50 rounded">
                          <div className="text-gray-600">평균 3일</div>
                          <div className="font-bold text-green-600">{result.model_b.pattern_analysis.avg_3d}%</div>
                        </div>
                        <div className="text-center p-2 bg-gray-50 rounded">
                          <div className="text-gray-600">평균 5일</div>
                          <div className="font-bold text-green-600">{result.model_b.pattern_analysis.avg_5d || 'N/A'}</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
