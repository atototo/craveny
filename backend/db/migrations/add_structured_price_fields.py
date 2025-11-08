"""
Migration: Add structured price fields to stock_analysis_summaries table.

Adds 6 new columns to enable structured price target/support queries:
- short_term_target_price, short_term_support_price
- medium_term_target_price, medium_term_support_price
- long_term_target_price
- base_price (analysis baseline)

Run: python backend/db/migrations/add_structured_price_fields.py
"""
import logging
from sqlalchemy import text
from backend.db.session import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def upgrade():
    """Add structured price fields to stock_analysis_summaries."""
    logger.info("🚀 Starting migration: add_structured_price_fields")

    with engine.connect() as conn:
        try:
            logger.info("📊 Adding structured price columns to stock_analysis_summaries...")

            # Add short-term price fields
            conn.execute(text("""
                ALTER TABLE stock_analysis_summaries
                ADD COLUMN IF NOT EXISTS short_term_target_price FLOAT
            """))
            conn.execute(text("""
                ALTER TABLE stock_analysis_summaries
                ADD COLUMN IF NOT EXISTS short_term_support_price FLOAT
            """))

            # Add medium-term price fields
            conn.execute(text("""
                ALTER TABLE stock_analysis_summaries
                ADD COLUMN IF NOT EXISTS medium_term_target_price FLOAT
            """))
            conn.execute(text("""
                ALTER TABLE stock_analysis_summaries
                ADD COLUMN IF NOT EXISTS medium_term_support_price FLOAT
            """))

            # Add long-term price field
            conn.execute(text("""
                ALTER TABLE stock_analysis_summaries
                ADD COLUMN IF NOT EXISTS long_term_target_price FLOAT
            """))

            # Add base price field
            conn.execute(text("""
                ALTER TABLE stock_analysis_summaries
                ADD COLUMN IF NOT EXISTS base_price FLOAT
            """))

            conn.commit()
            logger.info("✅ Migration completed successfully")
            logger.info("   Added 6 price columns: short/medium/long term target/support + base_price")

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            conn.rollback()
            raise


def downgrade():
    """Remove structured price fields from stock_analysis_summaries."""
    logger.info("🔄 Starting rollback: add_structured_price_fields")

    with engine.connect() as conn:
        try:
            logger.info("🗑️  Removing structured price columns...")

            conn.execute(text("""
                ALTER TABLE stock_analysis_summaries
                DROP COLUMN IF EXISTS short_term_target_price,
                DROP COLUMN IF EXISTS short_term_support_price,
                DROP COLUMN IF EXISTS medium_term_target_price,
                DROP COLUMN IF EXISTS medium_term_support_price,
                DROP COLUMN IF EXISTS long_term_target_price,
                DROP COLUMN IF EXISTS base_price
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
