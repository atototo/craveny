"""
Migration: Add impact analysis fields to predictions table.

Changes:
- Add new fields: sentiment_direction, sentiment_score, impact_level, relevance_score, urgency_level, impact_analysis
- Make existing fields nullable: direction, confidence
- Transform existing data to new format

Run: python backend/db/migrations/add_impact_analysis_fields.py
Rollback: python backend/db/migrations/add_impact_analysis_fields.py downgrade
"""
import logging
from sqlalchemy import text
from backend.db.session import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def upgrade():
    """Add impact analysis fields and migrate existing data."""
    logger.info("🚀 Starting migration: add_impact_analysis_fields")

    with engine.connect() as conn:
        try:
            # Step 1: Add new columns
            logger.info("📊 Adding new impact analysis columns...")

            conn.execute(text("""
                ALTER TABLE predictions
                ADD COLUMN IF NOT EXISTS sentiment_direction VARCHAR(10),
                ADD COLUMN IF NOT EXISTS sentiment_score FLOAT,
                ADD COLUMN IF NOT EXISTS impact_level VARCHAR(20),
                ADD COLUMN IF NOT EXISTS relevance_score FLOAT,
                ADD COLUMN IF NOT EXISTS urgency_level VARCHAR(20),
                ADD COLUMN IF NOT EXISTS impact_analysis JSON
            """))

            # Step 2: Make existing columns nullable
            logger.info("🔧 Making deprecated columns nullable...")

            conn.execute(text("""
                ALTER TABLE predictions
                ALTER COLUMN direction DROP NOT NULL,
                ALTER COLUMN confidence DROP NOT NULL
            """))

            # Step 3: Migrate existing data
            logger.info("🔄 Migrating existing data...")

            # Count existing records
            result = conn.execute(text("SELECT COUNT(*) FROM predictions"))
            total_count = result.scalar()
            logger.info(f"📈 Found {total_count} records to migrate")

            # Transform direction → sentiment_direction
            logger.info("  → Transforming direction to sentiment_direction...")
            conn.execute(text("""
                UPDATE predictions
                SET sentiment_direction = CASE
                    WHEN direction = 'up' THEN 'positive'
                    WHEN direction = 'down' THEN 'negative'
                    WHEN direction = 'hold' THEN 'neutral'
                    ELSE 'neutral'
                END
                WHERE sentiment_direction IS NULL
            """))

            # Transform confidence → sentiment_score
            logger.info("  → Transforming confidence to sentiment_score...")
            conn.execute(text("""
                UPDATE predictions
                SET sentiment_score = CASE
                    WHEN direction = 'up' THEN (confidence / 100.0)
                    WHEN direction = 'down' THEN -(confidence / 100.0)
                    WHEN direction = 'hold' THEN 0.0
                    ELSE 0.0
                END
                WHERE sentiment_score IS NULL AND confidence IS NOT NULL
            """))

            # Set impact_level based on confidence
            logger.info("  → Setting impact_level based on confidence...")
            conn.execute(text("""
                UPDATE predictions
                SET impact_level = CASE
                    WHEN confidence >= 70 THEN 'high'
                    WHEN confidence >= 50 THEN 'medium'
                    ELSE 'low'
                END
                WHERE impact_level IS NULL AND confidence IS NOT NULL
            """))

            # Set default relevance_score
            logger.info("  → Setting default relevance_score...")
            conn.execute(text("""
                UPDATE predictions
                SET relevance_score = 0.8
                WHERE relevance_score IS NULL
            """))

            # Set default urgency_level
            logger.info("  → Setting default urgency_level...")
            conn.execute(text("""
                UPDATE predictions
                SET urgency_level = 'notable'
                WHERE urgency_level IS NULL
            """))

            # Set default impact_analysis
            logger.info("  → Setting default impact_analysis...")
            conn.execute(text("""
                UPDATE predictions
                SET impact_analysis = '{"business_impact": "기존 예측 데이터", "market_sentiment": "마이그레이션됨"}'::json
                WHERE impact_analysis IS NULL
            """))

            # Step 4: Verify migration
            logger.info("✅ Verifying migration...")

            result = conn.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(sentiment_direction) as has_sentiment_direction,
                    COUNT(sentiment_score) as has_sentiment_score,
                    COUNT(impact_level) as has_impact_level,
                    COUNT(relevance_score) as has_relevance_score,
                    COUNT(urgency_level) as has_urgency_level,
                    COUNT(impact_analysis) as has_impact_analysis
                FROM predictions
            """))

            row = result.fetchone()
            logger.info(f"  Total records: {row[0]}")
            logger.info(f"  Has sentiment_direction: {row[1]}")
            logger.info(f"  Has sentiment_score: {row[2]}")
            logger.info(f"  Has impact_level: {row[3]}")
            logger.info(f"  Has relevance_score: {row[4]}")
            logger.info(f"  Has urgency_level: {row[5]}")
            logger.info(f"  Has impact_analysis: {row[6]}")

            if row[0] == row[1] == row[2] == row[3] == row[4] == row[5] == row[6]:
                logger.info("✅ All records migrated successfully!")
            else:
                logger.warning("⚠️  Some records may not have been migrated completely")

            conn.commit()
            logger.info("✅ Migration completed successfully")

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            conn.rollback()
            raise


def downgrade():
    """Rollback impact analysis fields migration."""
    logger.info("🔄 Starting rollback: add_impact_analysis_fields")

    with engine.connect() as conn:
        try:
            # Step 1: Restore NOT NULL constraints
            logger.info("🔧 Restoring NOT NULL constraints...")

            # First, ensure old fields have values
            conn.execute(text("""
                UPDATE predictions
                SET direction = CASE
                    WHEN sentiment_direction = 'positive' THEN 'up'
                    WHEN sentiment_direction = 'negative' THEN 'down'
                    WHEN sentiment_direction = 'neutral' THEN 'hold'
                    ELSE 'hold'
                END
                WHERE direction IS NULL
            """))

            conn.execute(text("""
                UPDATE predictions
                SET confidence = CASE
                    WHEN sentiment_score IS NOT NULL THEN ABS(sentiment_score * 100.0)
                    ELSE 50.0
                END
                WHERE confidence IS NULL
            """))

            conn.execute(text("""
                ALTER TABLE predictions
                ALTER COLUMN direction SET NOT NULL,
                ALTER COLUMN confidence SET NOT NULL
            """))

            # Step 2: Drop new columns
            logger.info("🗑️  Dropping new impact analysis columns...")

            conn.execute(text("""
                ALTER TABLE predictions
                DROP COLUMN IF EXISTS sentiment_direction,
                DROP COLUMN IF EXISTS sentiment_score,
                DROP COLUMN IF EXISTS impact_level,
                DROP COLUMN IF EXISTS relevance_score,
                DROP COLUMN IF EXISTS urgency_level,
                DROP COLUMN IF EXISTS impact_analysis
            """))

            conn.commit()
            logger.info("✅ Rollback completed successfully")

        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            conn.rollback()
            raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
