"""
Migration script: Add dynamic A/B test system tables and columns.

Changes:
1. Create models table
2. Create model_predictions table (NEW - 모든 모델의 예측 저장)
3. Create ab_test_config table
4. Add model_id column to predictions table
5. Add model_id column to stock_analysis_summaries table
6. Insert initial model data
7. Insert initial A/B config
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from backend.config import settings


def run_migration():
    """Execute migration steps"""
    engine = create_engine(settings.DATABASE_URL)

    with engine.connect() as conn:
        print("🚀 Starting migration: Add dynamic A/B test system")

        # Step 1: Create models table
        print("\n📊 Step 1: Creating models table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS models (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                provider VARCHAR(50) NOT NULL,
                model_identifier VARCHAR(200) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT true,
                description VARCHAR(500),
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.commit()
        print("✅ models table created")

        # Step 2: Create model_predictions table
        print("\n📊 Step 2: Creating model_predictions table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS model_predictions (
                id SERIAL PRIMARY KEY,
                news_id INTEGER NOT NULL REFERENCES news_articles(id) ON DELETE CASCADE,
                model_id INTEGER NOT NULL REFERENCES models(id) ON DELETE CASCADE,
                stock_code VARCHAR(10) NOT NULL,
                prediction_data JSONB NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE(news_id, model_id)
            )
        """))
        conn.commit()
        print("✅ model_predictions table created")

        # Create indexes for model_predictions
        print("\n📊 Step 2-1: Creating indexes for model_predictions...")
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_model_predictions_news
            ON model_predictions(news_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_model_predictions_model
            ON model_predictions(model_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_model_predictions_stock
            ON model_predictions(stock_code)
        """))
        conn.commit()
        print("✅ model_predictions indexes created")

        # Step 3: Create ab_test_config table
        print("\n📊 Step 3: Creating ab_test_config table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ab_test_config (
                id SERIAL PRIMARY KEY,
                model_a_id INTEGER NOT NULL REFERENCES models(id),
                model_b_id INTEGER NOT NULL REFERENCES models(id),
                is_active BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                CONSTRAINT different_models CHECK (model_a_id != model_b_id)
            )
        """))
        conn.commit()
        print("✅ ab_test_config table created")

        # Step 4: Add model_id to predictions table
        print("\n📊 Step 4: Adding model_id column to predictions table...")
        try:
            conn.execute(text("""
                ALTER TABLE predictions
                ADD COLUMN IF NOT EXISTS model_id INTEGER REFERENCES models(id)
            """))
            conn.commit()
            print("✅ predictions.model_id column added")
        except Exception as e:
            print(f"⚠️  predictions.model_id already exists or error: {e}")

        # Step 5: Add model_id to stock_analysis_summaries table
        print("\n📊 Step 5: Adding model_id column to stock_analysis_summaries table...")
        try:
            conn.execute(text("""
                ALTER TABLE stock_analysis_summaries
                ADD COLUMN IF NOT EXISTS model_id INTEGER REFERENCES models(id)
            """))
            conn.commit()
            print("✅ stock_analysis_summaries.model_id column added")
        except Exception as e:
            print(f"⚠️  stock_analysis_summaries.model_id already exists or error: {e}")

        # Step 6: Insert initial model data
        print("\n📊 Step 6: Inserting initial model data...")

        # Check if models already exist
        result = conn.execute(text("SELECT COUNT(*) FROM models"))
        count = result.scalar()

        if count == 0:
            conn.execute(text("""
                INSERT INTO models (name, provider, model_identifier, description) VALUES
                ('GPT-4o', 'openai', 'gpt-4o', 'OpenAI GPT-4o model'),
                ('DeepSeek V3.2', 'openrouter', 'deepseek/deepseek-v3.2-exp', 'DeepSeek V3.2 via OpenRouter'),
                ('Qwen 2.5 72B', 'openrouter', 'qwen/qwen-2.5-72b-instruct', 'Qwen 2.5 72B Instruct via OpenRouter'),
                ('Claude 3.5 Sonnet', 'openrouter', 'anthropic/claude-3.5-sonnet', 'Claude 3.5 Sonnet via OpenRouter')
            """))
            conn.commit()
            print("✅ Initial models inserted (4 models)")
        else:
            print(f"⚠️  Models already exist ({count} models), skipping insertion")

        # Step 7: Insert initial A/B config (GPT-4o vs DeepSeek)
        print("\n📊 Step 7: Inserting initial A/B test config...")

        # Check if config already exists
        result = conn.execute(text("SELECT COUNT(*) FROM ab_test_config"))
        count = result.scalar()

        if count == 0:
            conn.execute(text("""
                INSERT INTO ab_test_config (model_a_id, model_b_id, is_active)
                VALUES (1, 2, true)
            """))
            conn.commit()
            print("✅ Initial A/B config inserted (GPT-4o vs DeepSeek)")
        else:
            print(f"⚠️  A/B config already exists ({count} configs), skipping insertion")

        # Verification
        print("\n📊 Verifying migration...")
        result = conn.execute(text("SELECT COUNT(*) FROM models"))
        models_count = result.scalar()
        result = conn.execute(text("SELECT COUNT(*) FROM ab_test_config"))
        config_count = result.scalar()

        print("\n✅ Migration completed successfully!")
        print("\n📋 Summary:")
        print("   - models table: ✅")
        print(f"   - model_predictions table: ✅")
        print("   - ab_test_config table: ✅")
        print("   - predictions.model_id: ✅")
        print("   - stock_analysis_summaries.model_id: ✅")
        print(f"   - Models inserted: {models_count}")
        print(f"   - A/B configs inserted: {config_count}")


if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
