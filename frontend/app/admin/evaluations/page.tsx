"use client";

import { useEffect, useState } from "react";

interface Evaluation {
  id: number;
  prediction_id: number;
  model_id: number;
  stock_code: string;
  stock_name?: string | null;
  model_name?: string | null;
  predicted_at: string;
  predicted_target_price: number | null;
  predicted_support_price: number | null;
  predicted_base_price: number;
  predicted_confidence: number | null;
  ai_reasoning?: string | null;
  // AI 리포트 상세
  overall_summary?: string | null;
  recommendation?: string | null;
  short_term_scenario?: string | null;
  risk_factors?: string[] | null;
  opportunity_factors?: string[] | null;
  actual_high_1d: number | null;
  actual_low_1d: number | null;
  actual_close_1d: number | null;
  actual_high_5d: number | null;
  actual_low_5d: number | null;
  actual_close_5d: number | null;
  target_achieved: boolean | null;
  target_achieved_days: number | null;
  support_breached: boolean | null;
  target_accuracy_score: number | null;
  timing_score: number | null;
  risk_management_score: number | null;
  final_score: number | null;
  human_rating_quality: number | null;
  human_rating_usefulness: number | null;
  human_rating_overall: number | null;
  human_evaluated_by: string | null;
  human_evaluated_at: string | null;
}

interface HumanRating {
  quality: number;
  usefulness: number;
  overall: number;
  evaluator: string;
  reason?: string;
}

export default function EvaluationsPage() {
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedEval, setSelectedEval] = useState<Evaluation | null>(null);
  const [rating, setRating] = useState<HumanRating>({
    quality: 3,
    usefulness: 3,
    overall: 3,
    evaluator: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [pageSize] = useState(20);

  useEffect(() => {
    loadEvaluations();
  }, [page]);

  const loadEvaluations = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/evaluations/all?limit=${pageSize}&offset=${(page - 1) * pageSize}`);
      const data = await response.json();
      setEvaluations(Array.isArray(data) ? data : []);

      // 전체 개수 조회를 위한 별도 API 호출
      const countResponse = await fetch("/api/evaluations/all?limit=1000");
      const allData = await countResponse.json();
      const total = Array.isArray(allData) ? allData.length : 0;
      setTotalPages(Math.ceil(total / pageSize));
    } catch (error) {
      console.error("Failed to load evaluations:", error);
      setEvaluations([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitRating = async () => {
    if (!selectedEval) return;
    if (!rating.evaluator.trim()) {
      alert("평가자 이름을 입력해주세요");
      return;
    }

    setSubmitting(true);
    try {
      const response = await fetch(`/api/evaluations/${selectedEval.id}/rate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(rating),
      });

      if (!response.ok) throw new Error("Failed to submit rating");

      alert("평가가 저장되었습니다");
      setSelectedEval(null);
      loadEvaluations();
    } catch (error) {
      console.error("Failed to submit rating:", error);
      alert("평가 저장에 실패했습니다");
    } finally {
      setSubmitting(false);
    }
  };

  const StarRating = ({ value, onChange }: { value: number; onChange: (v: number) => void }) => {
    return (
      <div className="flex gap-2">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => onChange(star)}
            className={`text-2xl ${star <= value ? "text-yellow-500" : "text-gray-300"}`}
          >
            ★
          </button>
        ))}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">모델 평가</h1>
          <p className="mt-2 text-sm text-gray-600">
            Priority 1-2 종목에 대한 사람 평가를 진행합니다
          </p>
        </div>

        {evaluations.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <p className="text-gray-500">평가 대기 중인 항목이 없습니다</p>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">종목</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">모델</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">예측일시</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">목표가</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">달성여부</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">자동점수</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">액션</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {evaluations.map((evaluation) => (
                  <tr key={evaluation.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{evaluation.id}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {evaluation.stock_name || "알 수 없음"} ({evaluation.stock_code})
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <a
                        href={`/admin/evaluations/model/${evaluation.model_id}`}
                        className="text-blue-600 hover:text-blue-800 hover:underline"
                      >
                        {evaluation.model_name || `Model ${evaluation.model_id}`}
                      </a>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(evaluation.predicted_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {evaluation.predicted_target_price?.toLocaleString() ?? "N/A"}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {evaluation.target_achieved === true && (
                        <span className="text-green-600">✓ 달성</span>
                      )}
                      {evaluation.target_achieved === false && (
                        <span className="text-red-600">✗ 미달성</span>
                      )}
                      {evaluation.target_achieved === null && (
                        <span className="text-gray-400">미평가</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {evaluation.final_score?.toFixed(1) ?? "N/A"}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <button
                        onClick={() => setSelectedEval(evaluation)}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        평가하기
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Rating Modal */}
        {selectedEval && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <h2 className="text-2xl font-bold mb-4">사람 평가</h2>

                <div className="bg-gray-50 p-4 rounded-lg mb-6">
                  <div className="mb-4">
                    <div className="text-sm text-gray-600 mb-2">
                      종목: <span className="font-medium text-gray-900">{selectedEval.stock_name || "알 수 없음"} ({selectedEval.stock_code})</span>
                      {" | "}
                      모델: <span className="font-medium text-gray-900">{selectedEval.model_name || `Model ${selectedEval.model_id}`}</span>
                    </div>
                  </div>

                  <div className="space-y-3">
                    {/* 예측 vs 실제 비교 */}
                    <div className="bg-white p-3 rounded border border-gray-200">
                      <div className="text-xs text-gray-500 mb-2">AI 예측 ({new Date(selectedEval.predicted_at).toLocaleDateString()})</div>
                      <div className="space-y-1">
                        <div className="flex items-baseline gap-2">
                          <span className="text-xs text-gray-500 w-16">기준가:</span>
                          <span className="text-lg font-semibold text-gray-700">
                            {selectedEval.predicted_base_price.toLocaleString()}원
                          </span>
                        </div>
                        <div className="flex items-baseline gap-2">
                          <span className="text-xs text-gray-500 w-16">목표가:</span>
                          <span className="text-xl font-bold text-blue-600">
                            {selectedEval.predicted_target_price?.toLocaleString() ?? "N/A"}원
                          </span>
                        </div>
                        <div className="flex items-baseline gap-2">
                          <span className="text-xs text-gray-500 w-16">손절가:</span>
                          <span className="text-lg font-semibold text-orange-600">
                            {selectedEval.predicted_support_price?.toLocaleString() ?? "N/A"}원
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="bg-white p-3 rounded border border-gray-200">
                      <div className="text-xs text-gray-500 mb-2">
                        실제 주가 (1일 후 - {
                          new Date(new Date(selectedEval.predicted_at).getTime() + 24 * 60 * 60 * 1000).toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' })
                        })
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-baseline gap-3">
                          <span className="text-xs text-gray-500 w-12">고가:</span>
                          <span className="text-lg font-bold text-red-600">
                            {selectedEval.actual_high_1d?.toLocaleString() ?? "N/A"}원
                          </span>
                          {selectedEval.actual_high_1d && selectedEval.predicted_target_price &&
                           selectedEval.actual_high_1d >= selectedEval.predicted_target_price && (
                            <span className="text-xs text-green-600 font-medium">✓ 목표가 달성</span>
                          )}
                        </div>
                        <div className="flex items-baseline gap-3">
                          <span className="text-xs text-gray-500 w-12">저가:</span>
                          <span className="text-lg font-bold text-blue-600">
                            {selectedEval.actual_low_1d?.toLocaleString() ?? "N/A"}원
                          </span>
                          {selectedEval.actual_low_1d && selectedEval.predicted_support_price &&
                           selectedEval.actual_low_1d <= selectedEval.predicted_support_price && (
                            <span className="text-xs text-orange-600 font-medium">⚠️ 손절가 이탈</span>
                          )}
                        </div>
                        <div className="flex items-baseline gap-3">
                          <span className="text-xs text-gray-500 w-12">종가:</span>
                          <span className="text-lg font-semibold text-gray-900">
                            {selectedEval.actual_close_1d?.toLocaleString() ?? "N/A"}원
                          </span>
                        </div>
                        {selectedEval.target_achieved !== null && (
                          <div className="mt-2 pt-2 border-t border-gray-200">
                            <span className={`text-sm font-medium ${selectedEval.target_achieved ? 'text-green-600' : 'text-red-600'}`}>
                              {selectedEval.target_achieved
                                ? `✓ 목표가 달성 (${selectedEval.target_achieved_days}일 만에)`
                                : '✗ 목표가 미달성'}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    {(selectedEval.actual_high_5d || selectedEval.actual_low_5d || selectedEval.actual_close_5d) && (
                      <div className="bg-white p-3 rounded border border-gray-200">
                        <div className="text-xs text-gray-500 mb-2">
                          실제 주가 (5일 후 - {
                            new Date(new Date(selectedEval.predicted_at).getTime() + 5 * 24 * 60 * 60 * 1000).toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' })
                          })
                        </div>
                        <div className="space-y-1 text-sm">
                          {selectedEval.actual_high_5d && (
                            <div>고가: <span className="font-medium text-red-600">{selectedEval.actual_high_5d.toLocaleString()}원</span></div>
                          )}
                          {selectedEval.actual_low_5d && (
                            <div>저가: <span className="font-medium text-blue-600">{selectedEval.actual_low_5d.toLocaleString()}원</span></div>
                          )}
                          {selectedEval.actual_close_5d && (
                            <div>종가: <span className="font-medium text-gray-700">{selectedEval.actual_close_5d.toLocaleString()}원</span></div>
                          )}
                        </div>
                      </div>
                    )}

                    {selectedEval.final_score !== null && (
                      <div className="text-xs text-gray-500">
                        자동 평가 점수: <span className="font-medium text-gray-700">{selectedEval.final_score.toFixed(1)}점</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* AI 리포트 상세 내용 */}
                {(selectedEval.overall_summary || selectedEval.recommendation || selectedEval.short_term_scenario) && (
                  <div className="space-y-3">
                    {selectedEval.overall_summary && (
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-sm font-bold text-blue-900">📋 종합 의견</span>
                        </div>
                        <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                          {selectedEval.overall_summary}
                        </div>
                      </div>
                    )}

                    {selectedEval.recommendation && (
                      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-sm font-bold text-green-900">🎯 최종 추천</span>
                        </div>
                        <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                          {selectedEval.recommendation}
                        </div>
                      </div>
                    )}

                    {selectedEval.short_term_scenario && (
                      <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-sm font-bold text-purple-900">💎 단기 투자 전략</span>
                        </div>
                        <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                          {selectedEval.short_term_scenario}
                        </div>
                      </div>
                    )}

                    {(selectedEval.risk_factors && selectedEval.risk_factors.length > 0) && (
                      <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-sm font-bold text-orange-900">⚠️ 리스크 요인</span>
                        </div>
                        <ul className="text-sm text-gray-700 space-y-1">
                          {selectedEval.risk_factors.map((risk, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                              <span className="text-orange-600 mt-1">•</span>
                              <span>{risk}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {(selectedEval.opportunity_factors && selectedEval.opportunity_factors.length > 0) && (
                      <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-sm font-bold text-teal-900">💡 기회 요인</span>
                        </div>
                        <ul className="text-sm text-gray-700 space-y-1">
                          {selectedEval.opportunity_factors.map((opp, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                              <span className="text-teal-600 mt-1">•</span>
                              <span>{opp}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* AI 분석 코멘트 (legacy) */}
                {selectedEval.ai_reasoning && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm font-bold text-blue-900">🤖 AI 분석 코멘트</span>
                    </div>
                    <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                      {selectedEval.ai_reasoning}
                    </div>
                  </div>
                )}

                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      가격 정확도 (1-5)
                    </label>
                    <p className="text-xs text-gray-500 mb-2">
                      예측 주가가 실제 주가와 얼마나 가까운가요?
                    </p>
                    <StarRating
                      value={rating.quality}
                      onChange={(v) => setRating({...rating, quality: v})}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      추천 신뢰도 (1-5)
                    </label>
                    <p className="text-xs text-gray-500 mb-2">
                      이 AI 추천을 실제 투자 결정에 활용할 만한가요?
                    </p>
                    <StarRating
                      value={rating.usefulness}
                      onChange={(v) => setRating({...rating, usefulness: v})}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      종합 만족도 (1-5)
                    </label>
                    <p className="text-xs text-gray-500 mb-2">
                      전반적으로 이 예측에 만족하시나요?
                    </p>
                    <StarRating
                      value={rating.overall}
                      onChange={(v) => setRating({...rating, overall: v})}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      평가자 이름 *
                    </label>
                    <input
                      type="text"
                      value={rating.evaluator}
                      onChange={(e) => setRating({...rating, evaluator: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      placeholder="평가자 이름 입력"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      비고 (선택사항)
                    </label>
                    <textarea
                      value={rating.reason || ""}
                      onChange={(e) => setRating({...rating, reason: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      rows={3}
                      placeholder="추가 의견 입력"
                    />
                  </div>
                </div>

                <div className="mt-6 flex gap-3">
                  <button
                    onClick={handleSubmitRating}
                    disabled={submitting}
                    className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400"
                  >
                    {submitting ? "저장 중..." : "평가 저장"}
                  </button>
                  <button
                    onClick={() => setSelectedEval(null)}
                    disabled={submitting}
                    className="flex-1 bg-gray-200 text-gray-800 px-4 py-2 rounded-md hover:bg-gray-300"
                  >
                    취소
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 페이징 */}
        {!loading && evaluations.length > 0 && totalPages > 1 && (
          <div className="mt-6 flex justify-center items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              이전
            </button>

            <div className="flex gap-1">
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum;
                if (totalPages <= 5) {
                  pageNum = i + 1;
                } else if (page <= 3) {
                  pageNum = i + 1;
                } else if (page >= totalPages - 2) {
                  pageNum = totalPages - 4 + i;
                } else {
                  pageNum = page - 2 + i;
                }

                return (
                  <button
                    key={pageNum}
                    onClick={() => setPage(pageNum)}
                    className={`px-3 py-1 rounded-md ${
                      page === pageNum
                        ? "bg-blue-600 text-white"
                        : "border border-gray-300 hover:bg-gray-50"
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>

            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              다음
            </button>

            <span className="ml-4 text-sm text-gray-600">
              {page} / {totalPages} 페이지 (총 {evaluations.length}건 표시)
            </span>
          </div>
        )}
      </main>
    </div>
  );
}
