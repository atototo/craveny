-- Migration: Remove UNIQUE constraint from stock_analysis_summaries.stock_code
-- Purpose: Allow multiple Investment Reports per stock code for different dates
-- Date: 2025-11-07

-- Step 1: Drop the UNIQUE constraint (if exists)
DROP INDEX IF EXISTS ix_stock_analysis_summaries_stock_code;

-- Step 2: Create a regular (non-unique) index on stock_code for query performance
CREATE INDEX IF NOT EXISTS idx_stock_analysis_stock_code
ON stock_analysis_summaries(stock_code);

-- Step 3: Create composite index for efficient date-based queries
CREATE INDEX IF NOT EXISTS idx_stock_analysis_stock_code_date
ON stock_analysis_summaries(stock_code, last_updated DESC);

-- Verification query
-- SELECT stock_code, last_updated, base_price, short_term_target_price
-- FROM stock_analysis_summaries
-- ORDER BY stock_code, last_updated DESC;
