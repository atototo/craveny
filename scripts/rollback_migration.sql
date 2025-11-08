-- Rollback script for prediction migration
-- WARNING: This will revert the migration and drop new columns
-- Make sure to backup your database before running this script

-- Step 1: Verify current state
SELECT
    COUNT(*) as total_records,
    COUNT(sentiment_direction) as has_new_fields
FROM predictions;

-- Step 2: Restore old fields from new fields (if needed)
UPDATE predictions
SET direction = CASE
    WHEN sentiment_direction = 'positive' THEN 'up'
    WHEN sentiment_direction = 'negative' THEN 'down'
    WHEN sentiment_direction = 'neutral' THEN 'hold'
    ELSE 'hold'
END
WHERE direction IS NULL;

UPDATE predictions
SET confidence = CASE
    WHEN sentiment_score IS NOT NULL THEN ABS(sentiment_score * 100.0)
    ELSE 50.0
END
WHERE confidence IS NULL;

-- Step 3: Restore NOT NULL constraints
ALTER TABLE predictions
ALTER COLUMN direction SET NOT NULL,
ALTER COLUMN confidence SET NOT NULL;

-- Step 4: Drop new columns
ALTER TABLE predictions
DROP COLUMN IF EXISTS sentiment_direction,
DROP COLUMN IF EXISTS sentiment_score,
DROP COLUMN IF EXISTS impact_level,
DROP COLUMN IF EXISTS relevance_score,
DROP COLUMN IF EXISTS urgency_level,
DROP COLUMN IF EXISTS impact_analysis;

-- Step 5: Verify rollback
SELECT
    COUNT(*) as total_records,
    COUNT(direction) as has_direction,
    COUNT(confidence) as has_confidence
FROM predictions;

-- Step 6: Show sample data
SELECT
    id,
    stock_code,
    direction,
    confidence,
    short_term,
    medium_term,
    long_term
FROM predictions
ORDER BY id DESC
LIMIT 10;
