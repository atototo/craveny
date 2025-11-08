"""
Migration: Add model evaluation tables.

Creates three tables for the model evaluation system:
- model_evaluations: Core evaluation data with automated and human scores
- daily_model_performance: Daily aggregated performance metrics
- evaluation_history: Audit trail for evaluation modifications

Run: python backend/db/migrations/add_evaluation_tables.py
"""
import logging
from sqlalchemy import text
from backend.db.session import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def upgrade():
    """Create evaluation tables with indexes and constraints."""
    logger.info("🚀 Starting migration: add_evaluation_tables")

    with engine.connect() as conn:
        try:
            # Create model_evaluations table
            logger.info("📊 Creating model_evaluations table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS model_evaluations (
                    id SERIAL PRIMARY KEY,
                    prediction_id INTEGER NOT NULL,
                    model_id INTEGER NOT NULL,
                    stock_code VARCHAR(10) NOT NULL,

                    -- 예측 정보 스냅샷
                    predicted_at TIMESTAMP NOT NULL,
                    prediction_period VARCHAR(20),
                    predicted_target_price FLOAT,
                    predicted_support_price FLOAT,
                    predicted_base_price FLOAT NOT NULL,
                    predicted_confidence FLOAT,

                    -- 실제 결과 (1일)
                    actual_high_1d FLOAT,
                    actual_low_1d FLOAT,
                    actual_close_1d FLOAT,

                    -- 실제 결과 (5일)
                    actual_high_5d FLOAT,
                    actual_low_5d FLOAT,
                    actual_close_5d FLOAT,

                    -- 달성 여부
                    target_achieved BOOLEAN,
                    target_achieved_days INTEGER,
                    support_breached BOOLEAN,

                    -- 자동 점수 (0-100)
                    target_accuracy_score FLOAT,
                    timing_score FLOAT,
                    risk_management_score FLOAT,

                    -- 사람 평가 (1-5)
                    human_rating_quality INTEGER,
                    human_rating_usefulness INTEGER,
                    human_rating_overall INTEGER,
                    human_evaluated_by VARCHAR(50),
                    human_evaluated_at TIMESTAMP,

                    -- 종합
                    final_score FLOAT,
                    evaluated_at TIMESTAMP,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
            """))

            # Create indexes for model_evaluations
            logger.info("🔍 Creating indexes for model_evaluations...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_model_evaluations_prediction_id
                ON model_evaluations(prediction_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_model_evaluations_model_id
                ON model_evaluations(model_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_model_evaluations_stock_code
                ON model_evaluations(stock_code)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_model_eval_model_date
                ON model_evaluations(model_id, predicted_at)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_model_eval_stock_date
                ON model_evaluations(stock_code, predicted_at)
            """))

            # Create daily_model_performance table
            logger.info("📈 Creating daily_model_performance table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS daily_model_performance (
                    id SERIAL PRIMARY KEY,
                    model_id INTEGER NOT NULL,
                    date DATE NOT NULL,

                    -- 건수
                    total_predictions INTEGER DEFAULT 0 NOT NULL,
                    evaluated_count INTEGER DEFAULT 0 NOT NULL,
                    human_evaluated_count INTEGER DEFAULT 0 NOT NULL,

                    -- 평균 점수
                    avg_final_score FLOAT,
                    avg_auto_score FLOAT,
                    avg_human_score FLOAT,
                    avg_target_accuracy FLOAT,
                    avg_timing_score FLOAT,
                    avg_risk_management FLOAT,

                    -- 성과 지표 (%)
                    target_achieved_rate FLOAT,
                    support_breach_rate FLOAT,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

                    CONSTRAINT uq_model_date UNIQUE (model_id, date)
                )
            """))

            # Create indexes for daily_model_performance
            logger.info("🔍 Creating indexes for daily_model_performance...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_daily_model_performance_model_id
                ON daily_model_performance(model_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_daily_model_performance_date
                ON daily_model_performance(date)
            """))

            # Create evaluation_history table
            logger.info("📝 Creating evaluation_history table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS evaluation_history (
                    id SERIAL PRIMARY KEY,
                    evaluation_id INTEGER NOT NULL,

                    -- 수정 전 값
                    old_human_rating_quality INTEGER,
                    old_human_rating_usefulness INTEGER,
                    old_human_rating_overall INTEGER,
                    old_final_score FLOAT,

                    -- 수정 후 값
                    new_human_rating_quality INTEGER,
                    new_human_rating_usefulness INTEGER,
                    new_human_rating_overall INTEGER,
                    new_final_score FLOAT,

                    -- 메타데이터
                    modified_by TEXT NOT NULL,
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    reason TEXT
                )
            """))

            # Create index for evaluation_history
            logger.info("🔍 Creating indexes for evaluation_history...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_eval_history_eval_id
                ON evaluation_history(evaluation_id)
            """))

            conn.commit()
            logger.info("✅ Migration completed successfully")

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            conn.rollback()
            raise


def downgrade():
    """Drop evaluation tables."""
    logger.info("🔄 Starting rollback: add_evaluation_tables")

    with engine.connect() as conn:
        try:
            logger.info("🗑️  Dropping evaluation_history table...")
            conn.execute(text("DROP TABLE IF EXISTS evaluation_history CASCADE"))

            logger.info("🗑️  Dropping daily_model_performance table...")
            conn.execute(text("DROP TABLE IF EXISTS daily_model_performance CASCADE"))

            logger.info("🗑️  Dropping model_evaluations table...")
            conn.execute(text("DROP TABLE IF EXISTS model_evaluations CASCADE"))

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
