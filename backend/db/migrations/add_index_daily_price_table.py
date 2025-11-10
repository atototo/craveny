"""
업종/지수 일자별 가격 테이블 추가 Migration

Usage:
    uv run python backend/db/migrations/add_index_daily_price_table.py
"""
import logging
from sqlalchemy import text

from backend.db.session import SessionLocal


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def upgrade():
    """Migration 실행"""
    logger.info("=" * 80)
    logger.info("🚀 Migration: index_daily_price 테이블 생성")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 테이블 생성
        logger.info("\n1. 테이블 생성 중...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS index_daily_price (
                id SERIAL PRIMARY KEY,
                index_code VARCHAR(10) NOT NULL,
                index_name VARCHAR(50),
                date DATE NOT NULL,

                -- OHLC
                open FLOAT,
                high FLOAT,
                low FLOAT,
                close FLOAT NOT NULL,

                -- 거래량/거래대금
                volume BIGINT,
                trading_value BIGINT,

                -- 등락 정보
                change FLOAT,
                change_rate FLOAT,
                change_sign VARCHAR(1),

                -- 메타데이터
                created_at TIMESTAMP DEFAULT NOW(),

                CONSTRAINT uk_index_daily_code_date UNIQUE (index_code, date)
            );
        """))
        logger.info("   ✅ index_daily_price 테이블 생성 완료")

        # 인덱스 생성
        logger.info("\n2. 인덱스 생성 중...")

        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_index_daily_code_date
            ON index_daily_price(index_code, date DESC);
        """))
        logger.info("   ✅ idx_index_daily_code_date 인덱스 생성")

        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_index_daily_date
            ON index_daily_price(date DESC);
        """))
        logger.info("   ✅ idx_index_daily_date 인덱스 생성")

        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_index_daily_code
            ON index_daily_price(index_code);
        """))
        logger.info("   ✅ idx_index_daily_code 인덱스 생성")

        # 테이블 및 컬럼 코멘트 추가
        logger.info("\n3. 테이블/컬럼 코멘트 추가 중...")

        db.execute(text("""
            COMMENT ON TABLE index_daily_price IS '업종/지수 일자별 데이터 (KIS API, 매일 18:00 수집)';

            COMMENT ON COLUMN index_daily_price.id IS 'Primary key';
            COMMENT ON COLUMN index_daily_price.index_code IS '지수 코드 (0001:KOSPI, 1001:KOSDAQ, 2001:KOSPI200 등)';
            COMMENT ON COLUMN index_daily_price.index_name IS '지수명 (KOSPI, KOSDAQ, 에너지, 화학 등)';
            COMMENT ON COLUMN index_daily_price.date IS '영업일자';
            COMMENT ON COLUMN index_daily_price.open IS '시가';
            COMMENT ON COLUMN index_daily_price.high IS '최고가';
            COMMENT ON COLUMN index_daily_price.low IS '최저가';
            COMMENT ON COLUMN index_daily_price.close IS '종가';
            COMMENT ON COLUMN index_daily_price.volume IS '누적 거래량';
            COMMENT ON COLUMN index_daily_price.trading_value IS '누적 거래대금';
            COMMENT ON COLUMN index_daily_price.change IS '전일 대비';
            COMMENT ON COLUMN index_daily_price.change_rate IS '전일 대비율 (%)';
            COMMENT ON COLUMN index_daily_price.change_sign IS '전일 대비 부호 (1:상한, 2:상승, 3:보합, 4:하한, 5:하락)';
            COMMENT ON COLUMN index_daily_price.created_at IS '생성일시';
        """))
        logger.info("   ✅ 테이블/컬럼 코멘트 추가 완료")

        db.commit()

        logger.info("\n" + "=" * 80)
        logger.info("✅ Migration 완료!")
        logger.info("=" * 80)

        # 테이블 정보 출력
        logger.info("\n📊 테이블 정보:")
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'index_daily_price'
            ORDER BY ordinal_position;
        """))

        for row in result:
            logger.info(f"   {row[0]}: {row[1]} (NULL: {row[2]})")

        # 인덱스 정보 출력
        logger.info("\n📊 인덱스 정보:")
        result = db.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'index_daily_price';
        """))

        for row in result:
            logger.info(f"   {row[0]}")

    except Exception as e:
        db.rollback()
        logger.error(f"\n❌ Migration 실패: {e}", exc_info=True)
        raise

    finally:
        db.close()


def downgrade():
    """Migration 롤백"""
    logger.info("=" * 80)
    logger.info("🔙 Rollback: index_daily_price 테이블 삭제")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        db.execute(text("DROP TABLE IF EXISTS index_daily_price CASCADE;"))
        db.commit()
        logger.info("\n✅ Rollback 완료!")

    except Exception as e:
        db.rollback()
        logger.error(f"\n❌ Rollback 실패: {e}", exc_info=True)
        raise

    finally:
        db.close()


if __name__ == "__main__":
    upgrade()
