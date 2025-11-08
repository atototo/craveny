-- Verification queries for prediction migration
-- Run these queries after migration to verify data integrity

-- 1. Check total record count
SELECT COUNT(*) as total_records FROM predictions;

-- 2. Check new fields coverage
SELECT
    COUNT(*) as total,
    COUNT(sentiment_direction) as has_sentiment_direction,
    COUNT(sentiment_score) as has_sentiment_score,
    COUNT(impact_level) as has_impact_level,
    COUNT(relevance_score) as has_relevance_score,
    COUNT(urgency_level) as has_urgency_level,
    COUNT(impact_analysis) as has_impact_analysis
FROM predictions;

-- 3. Verify direction → sentiment_direction mapping
SELECT
    direction,
    sentiment_direction,
    COUNT(*) as count
FROM predictions
GROUP BY direction, sentiment_direction
ORDER BY direction, sentiment_direction;

-- 4. Verify sentiment_score range (-1.0 to 1.0)
SELECT
    MIN(sentiment_score) as min_score,
    MAX(sentiment_score) as max_score,
    AVG(sentiment_score) as avg_score
FROM predictions
WHERE sentiment_score IS NOT NULL;

-- 5. Check for invalid sentiment_scores
SELECT
    id,
    stock_code,
    sentiment_direction,
    sentiment_score
FROM predictions
WHERE sentiment_score < -1.0 OR sentiment_score > 1.0;

-- 6. Verify impact_level values
SELECT
    impact_level,
    COUNT(*) as count
FROM predictions
GROUP BY impact_level
ORDER BY impact_level;

-- 7. Check for invalid impact_levels
SELECT
    id,
    stock_code,
    impact_level
FROM predictions
WHERE impact_level NOT IN ('low', 'medium', 'high', 'critical')
AND impact_level IS NOT NULL;

-- 8. Verify urgency_level values
SELECT
    urgency_level,
    COUNT(*) as count
FROM predictions
GROUP BY urgency_level
ORDER BY urgency_level;

-- 9. Check for invalid urgency_levels
SELECT
    id,
    stock_code,
    urgency_level
FROM predictions
WHERE urgency_level NOT IN ('routine', 'notable', 'urgent', 'breaking')
AND urgency_level IS NOT NULL;

-- 10. Verify relevance_score range (0.0 to 1.0)
SELECT
    MIN(relevance_score) as min_relevance,
    MAX(relevance_score) as max_relevance,
    AVG(relevance_score) as avg_relevance
FROM predictions
WHERE relevance_score IS NOT NULL;

-- 11. Check consistency between direction and sentiment
SELECT
    direction,
    sentiment_direction,
    CASE
        WHEN direction = 'up' AND sentiment_direction != 'positive' THEN 'INCONSISTENT'
        WHEN direction = 'down' AND sentiment_direction != 'negative' THEN 'INCONSISTENT'
        WHEN direction = 'hold' AND sentiment_direction != 'neutral' THEN 'INCONSISTENT'
        ELSE 'CONSISTENT'
    END as consistency_check,
    COUNT(*) as count
FROM predictions
GROUP BY direction, sentiment_direction, consistency_check
HAVING CASE
    WHEN direction = 'up' AND sentiment_direction != 'positive' THEN 'INCONSISTENT'
    WHEN direction = 'down' AND sentiment_direction != 'negative' THEN 'INCONSISTENT'
    WHEN direction = 'hold' AND sentiment_direction != 'neutral' THEN 'INCONSISTENT'
    ELSE 'CONSISTENT'
END = 'INCONSISTENT';

-- 12. Sample records to verify transformation
SELECT
    id,
    stock_code,
    direction,
    confidence,
    sentiment_direction,
    sentiment_score,
    impact_level,
    relevance_score,
    urgency_level
FROM predictions
ORDER BY id
LIMIT 20;

-- 13. Summary statistics
SELECT
    'Total Records' as metric,
    COUNT(*) as value
FROM predictions
UNION ALL
SELECT
    'Positive Sentiment' as metric,
    COUNT(*) as value
FROM predictions
WHERE sentiment_direction = 'positive'
UNION ALL
SELECT
    'Negative Sentiment' as metric,
    COUNT(*) as value
FROM predictions
WHERE sentiment_direction = 'negative'
UNION ALL
SELECT
    'Neutral Sentiment' as metric,
    COUNT(*) as value
FROM predictions
WHERE sentiment_direction = 'neutral'
UNION ALL
SELECT
    'High Impact' as metric,
    COUNT(*) as value
FROM predictions
WHERE impact_level = 'high'
UNION ALL
SELECT
    'Medium Impact' as metric,
    COUNT(*) as value
FROM predictions
WHERE impact_level = 'medium'
UNION ALL
SELECT
    'Low Impact' as metric,
    COUNT(*) as value
FROM predictions
WHERE impact_level = 'low';
