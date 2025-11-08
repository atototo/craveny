// Epic 5: Story 5.1 - News Impact Display Component
// Displays sentiment analysis, impact level, relevance/urgency indicators

interface NewsImpactProps {
  prediction?: {
    sentiment_direction?: string | null;
    sentiment_score?: number | null;
    impact_level?: string | null;
    relevance_score?: number | null;
    urgency_level?: string | null;
    // impact_analysis can be string (new format) or object (legacy format)
    impact_analysis?: string | { business_impact?: string; market_sentiment?: string } | null;
  } | null;
}

export default function NewsImpact({ prediction }: NewsImpactProps) {
  if (!prediction) return null;

  const {
    sentiment_direction,
    sentiment_score,
    impact_level,
    relevance_score,
    urgency_level,
    impact_analysis,
  } = prediction;

  // Sentiment Badge
  const getSentimentBadge = () => {
    if (!sentiment_direction) return null;

    const config = {
      positive: { bg: "bg-green-100", text: "text-green-800", emoji: "📈", label: "긍정" },
      negative: { bg: "bg-red-100", text: "text-red-800", emoji: "📉", label: "부정" },
      neutral: { bg: "bg-gray-100", text: "text-gray-800", emoji: "➡️", label: "중립" },
    };

    const style = config[sentiment_direction as keyof typeof config];
    if (!style) return null;

    return (
      <div className="flex items-center gap-2">
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${style.bg} ${style.text}`}>
          {style.emoji} {style.label}
        </span>
        {sentiment_score !== null && sentiment_score !== undefined && (
          <span className="text-sm text-gray-600">
            신뢰도: {(sentiment_score * 100).toFixed(0)}%
          </span>
        )}
      </div>
    );
  };

  // Impact Level Badge
  const getImpactBadge = () => {
    if (!impact_level) return null;

    const config = {
      high: { bg: "bg-red-500", label: "높음" },
      medium: { bg: "bg-yellow-500", label: "중간" },
      low: { bg: "bg-green-500", label: "낮음" },
    };

    const style = config[impact_level as keyof typeof config];
    if (!style) return null;

    return (
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-700 font-medium">영향도</span>
        <span className={`px-3 py-1 rounded-full text-sm font-medium text-white ${style.bg}`}>
          {style.label}
        </span>
      </div>
    );
  };

  // Urgency Level Badge
  const getUrgencyBadge = () => {
    if (!urgency_level) return null;

    const config = {
      urgent: { icon: "🔴", label: "긴급", color: "text-red-600" },
      high: { icon: "🟠", label: "높음", color: "text-orange-600" },
      medium: { icon: "🟡", label: "보통", color: "text-yellow-600" },
      low: { icon: "🟢", label: "낮음", color: "text-green-600" },
    };

    const style = config[urgency_level as keyof typeof config];
    if (!style) return null;

    return (
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-700 font-medium">긴급도</span>
        <span className={`flex items-center gap-1 text-sm font-medium ${style.color}`}>
          {style.icon} {style.label}
        </span>
      </div>
    );
  };

  // Relevance Score Bar
  const getRelevanceBar = () => {
    if (relevance_score === null || relevance_score === undefined) return null;

    const percentage = relevance_score * 100;
    const getColor = () => {
      if (percentage >= 80) return "bg-green-500";
      if (percentage >= 60) return "bg-yellow-500";
      return "bg-gray-400";
    };

    return (
      <div className="flex items-center gap-3">
        <span className="text-sm text-gray-700 font-medium w-16">관련성</span>
        <div className="flex-1 bg-gray-200 rounded-full h-2.5">
          <div
            className={`h-2.5 rounded-full ${getColor()}`}
            style={{ width: `${percentage}%` }}
          ></div>
        </div>
        <span className="text-sm text-gray-600 font-medium w-12 text-right">
          {percentage.toFixed(0)}%
        </span>
      </div>
    );
  };

  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4 space-y-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg font-bold text-gray-900">📊 뉴스 영향도 분석</span>
      </div>

      {/* Sentiment */}
      {getSentimentBadge()}

      {/* Impact & Urgency */}
      <div className="grid grid-cols-2 gap-4">
        {getImpactBadge()}
        {getUrgencyBadge()}
      </div>

      {/* Relevance Score */}
      {getRelevanceBar()}

      {/* Impact Analysis */}
      {impact_analysis && (
        <div className="mt-4 pt-4 border-t border-blue-200">
          <p className="text-sm font-medium text-gray-700 mb-2">📝 상세 분석</p>
          {typeof impact_analysis === 'string' ? (
            <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap">
              {impact_analysis}
            </p>
          ) : (
            // Legacy format: object with business_impact and market_sentiment
            <div className="space-y-2">
              {impact_analysis.business_impact && (
                <div>
                  <span className="text-sm font-medium text-gray-700">사업 영향: </span>
                  <span className="text-sm text-gray-600">{impact_analysis.business_impact}</span>
                </div>
              )}
              {impact_analysis.market_sentiment && (
                <div>
                  <span className="text-sm font-medium text-gray-700">시장 분위기: </span>
                  <span className="text-sm text-gray-600">{impact_analysis.market_sentiment}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
