"""
테이블 및 컬럼 COMMENT 추가 Migration

모든 테이블과 컬럼에 설명을 추가하여 가독성을 높입니다.
"""
import logging
from sqlalchemy import text

from backend.db.session import SessionLocal


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def upgrade():
    """Migration 실행"""
    logger.info("=" * 80)
    logger.info("📝 테이블 및 컬럼 COMMENT 추가")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 1. stocks 테이블
        logger.info("\n1. stocks 테이블 COMMENT 추가...")
        db.execute(text("""
            COMMENT ON TABLE stocks IS '종목 마스터 테이블 (앱 내부 관리용)';
            COMMENT ON COLUMN stocks.id IS 'Primary Key';
            COMMENT ON COLUMN stocks.code IS '종목코드 (예: 005930)';
            COMMENT ON COLUMN stocks.name IS '종목명 (예: 삼성전자)';
            COMMENT ON COLUMN stocks.priority IS '크롤링 우선순위 (1~5, 낮을수록 우선)';
            COMMENT ON COLUMN stocks.is_active IS '활성화 여부';
            COMMENT ON COLUMN stocks.created_at IS '생성일시';
            COMMENT ON COLUMN stocks.updated_at IS '수정일시';
            COMMENT ON COLUMN stocks.market_cap IS '시가총액 (사용안함, stock_info 사용)';
            COMMENT ON COLUMN stocks.sector IS '업종 (사용안함, stock_info 사용)';
            COMMENT ON COLUMN stocks.per IS 'PER (사용안함)';
            COMMENT ON COLUMN stocks.pbr IS 'PBR (사용안함)';
        """))
        logger.info("   ✅ stocks 테이블 완료")

        # 2. stock_prices 테이블
        logger.info("\n2. stock_prices 테이블 COMMENT 추가...")
        db.execute(text("""
            COMMENT ON TABLE stock_prices IS '일봉 주가 데이터 (Historical)';
            COMMENT ON COLUMN stock_prices.id IS 'Primary Key';
            COMMENT ON COLUMN stock_prices.stock_code IS '종목코드';
            COMMENT ON COLUMN stock_prices.date IS '거래일';
            COMMENT ON COLUMN stock_prices.open IS '시가';
            COMMENT ON COLUMN stock_prices.high IS '고가';
            COMMENT ON COLUMN stock_prices.low IS '저가';
            COMMENT ON COLUMN stock_prices.close IS '종가';
            COMMENT ON COLUMN stock_prices.volume IS '거래량';
            COMMENT ON COLUMN stock_prices.source IS '데이터 소스 (fdr/kis)';
        """))
        logger.info("   ✅ stock_prices 테이블 완료")

        # 3. stock_prices_minute 테이블
        logger.info("\n3. stock_prices_minute 테이블 COMMENT 추가...")
        db.execute(text("""
            COMMENT ON TABLE stock_prices_minute IS '1분봉 주가 데이터 (장중 실시간 수집)';
            COMMENT ON COLUMN stock_prices_minute.id IS 'Primary Key';
            COMMENT ON COLUMN stock_prices_minute.stock_code IS '종목코드';
            COMMENT ON COLUMN stock_prices_minute.datetime IS '1분봉 시간';
            COMMENT ON COLUMN stock_prices_minute.open IS '시가';
            COMMENT ON COLUMN stock_prices_minute.high IS '고가';
            COMMENT ON COLUMN stock_prices_minute.low IS '저가';
            COMMENT ON COLUMN stock_prices_minute.close IS '종가';
            COMMENT ON COLUMN stock_prices_minute.volume IS '거래량';
            COMMENT ON COLUMN stock_prices_minute.source IS '데이터 소스 (kis)';
            COMMENT ON COLUMN stock_prices_minute.created_at IS '생성일시';
        """))
        logger.info("   ✅ stock_prices_minute 테이블 완료")

        # 4. stock_orderbook 테이블
        logger.info("\n4. stock_orderbook 테이블 COMMENT 추가...")
        db.execute(text("""
            COMMENT ON TABLE stock_orderbook IS '호가 데이터 (10단계 매수/매도, 장중 5분마다 수집)';
            COMMENT ON COLUMN stock_orderbook.id IS 'Primary Key';
            COMMENT ON COLUMN stock_orderbook.stock_code IS '종목코드';
            COMMENT ON COLUMN stock_orderbook.datetime IS '호가 시간';
            COMMENT ON COLUMN stock_orderbook.askp1 IS '매도 1호가';
            COMMENT ON COLUMN stock_orderbook.askp2 IS '매도 2호가';
            COMMENT ON COLUMN stock_orderbook.askp3 IS '매도 3호가';
            COMMENT ON COLUMN stock_orderbook.askp4 IS '매도 4호가';
            COMMENT ON COLUMN stock_orderbook.askp5 IS '매도 5호가';
            COMMENT ON COLUMN stock_orderbook.askp6 IS '매도 6호가';
            COMMENT ON COLUMN stock_orderbook.askp7 IS '매도 7호가';
            COMMENT ON COLUMN stock_orderbook.askp8 IS '매도 8호가';
            COMMENT ON COLUMN stock_orderbook.askp9 IS '매도 9호가';
            COMMENT ON COLUMN stock_orderbook.askp10 IS '매도 10호가';
            COMMENT ON COLUMN stock_orderbook.askp_rsqn1 IS '매도 1호가 잔량';
            COMMENT ON COLUMN stock_orderbook.askp_rsqn2 IS '매도 2호가 잔량';
            COMMENT ON COLUMN stock_orderbook.askp_rsqn3 IS '매도 3호가 잔량';
            COMMENT ON COLUMN stock_orderbook.askp_rsqn4 IS '매도 4호가 잔량';
            COMMENT ON COLUMN stock_orderbook.askp_rsqn5 IS '매도 5호가 잔량';
            COMMENT ON COLUMN stock_orderbook.askp_rsqn6 IS '매도 6호가 잔량';
            COMMENT ON COLUMN stock_orderbook.askp_rsqn7 IS '매도 7호가 잔량';
            COMMENT ON COLUMN stock_orderbook.askp_rsqn8 IS '매도 8호가 잔량';
            COMMENT ON COLUMN stock_orderbook.askp_rsqn9 IS '매도 9호가 잔량';
            COMMENT ON COLUMN stock_orderbook.askp_rsqn10 IS '매도 10호가 잔량';
            COMMENT ON COLUMN stock_orderbook.bidp1 IS '매수 1호가';
            COMMENT ON COLUMN stock_orderbook.bidp2 IS '매수 2호가';
            COMMENT ON COLUMN stock_orderbook.bidp3 IS '매수 3호가';
            COMMENT ON COLUMN stock_orderbook.bidp4 IS '매수 4호가';
            COMMENT ON COLUMN stock_orderbook.bidp5 IS '매수 5호가';
            COMMENT ON COLUMN stock_orderbook.bidp6 IS '매수 6호가';
            COMMENT ON COLUMN stock_orderbook.bidp7 IS '매수 7호가';
            COMMENT ON COLUMN stock_orderbook.bidp8 IS '매수 8호가';
            COMMENT ON COLUMN stock_orderbook.bidp9 IS '매수 9호가';
            COMMENT ON COLUMN stock_orderbook.bidp10 IS '매수 10호가';
            COMMENT ON COLUMN stock_orderbook.bidp_rsqn1 IS '매수 1호가 잔량';
            COMMENT ON COLUMN stock_orderbook.bidp_rsqn2 IS '매수 2호가 잔량';
            COMMENT ON COLUMN stock_orderbook.bidp_rsqn3 IS '매수 3호가 잔량';
            COMMENT ON COLUMN stock_orderbook.bidp_rsqn4 IS '매수 4호가 잔량';
            COMMENT ON COLUMN stock_orderbook.bidp_rsqn5 IS '매수 5호가 잔량';
            COMMENT ON COLUMN stock_orderbook.bidp_rsqn6 IS '매수 6호가 잔량';
            COMMENT ON COLUMN stock_orderbook.bidp_rsqn7 IS '매수 7호가 잔량';
            COMMENT ON COLUMN stock_orderbook.bidp_rsqn8 IS '매수 8호가 잔량';
            COMMENT ON COLUMN stock_orderbook.bidp_rsqn9 IS '매수 9호가 잔량';
            COMMENT ON COLUMN stock_orderbook.bidp_rsqn10 IS '매수 10호가 잔량';
            COMMENT ON COLUMN stock_orderbook.total_askp_rsqn IS '총 매도 잔량';
            COMMENT ON COLUMN stock_orderbook.total_bidp_rsqn IS '총 매수 잔량';
            COMMENT ON COLUMN stock_orderbook.created_at IS '생성일시';
        """))
        logger.info("   ✅ stock_orderbook 테이블 완료")

        # 5. stock_current_price 테이블
        logger.info("\n5. stock_current_price 테이블 COMMENT 추가...")
        db.execute(text("""
            COMMENT ON TABLE stock_current_price IS '실시간 현재가 시세 (장중 5분마다 수집)';
            COMMENT ON COLUMN stock_current_price.id IS 'Primary Key';
            COMMENT ON COLUMN stock_current_price.stock_code IS '종목코드';
            COMMENT ON COLUMN stock_current_price.datetime IS '시세 시간';
            COMMENT ON COLUMN stock_current_price.stck_prpr IS '주식 현재가';
            COMMENT ON COLUMN stock_current_price.prdy_vrss IS '전일 대비';
            COMMENT ON COLUMN stock_current_price.prdy_vrss_sign IS '전일 대비 부호 (2:상승, 5:하락, 3:보합)';
            COMMENT ON COLUMN stock_current_price.prdy_ctrt IS '전일 대비율 (%)';
            COMMENT ON COLUMN stock_current_price.acml_vol IS '누적 거래량';
            COMMENT ON COLUMN stock_current_price.acml_tr_pbmn IS '누적 거래대금';
            COMMENT ON COLUMN stock_current_price.per IS 'PER (주가수익비율)';
            COMMENT ON COLUMN stock_current_price.pbr IS 'PBR (주가순자산비율)';
            COMMENT ON COLUMN stock_current_price.eps IS 'EPS (주당순이익)';
            COMMENT ON COLUMN stock_current_price.bps IS 'BPS (주당순자산가치)';
            COMMENT ON COLUMN stock_current_price.hts_avls IS 'HTS 시가총액';
            COMMENT ON COLUMN stock_current_price.created_at IS '생성일시';
        """))
        logger.info("   ✅ stock_current_price 테이블 완료")

        # 6. investor_trading 테이블
        logger.info("\n6. investor_trading 테이블 COMMENT 추가...")
        db.execute(text("""
            COMMENT ON TABLE investor_trading IS '투자자별 매매동향 (매일 16:00 수집)';
            COMMENT ON COLUMN investor_trading.id IS 'Primary Key';
            COMMENT ON COLUMN investor_trading.stock_code IS '종목코드';
            COMMENT ON COLUMN investor_trading.date IS '거래일';
            COMMENT ON COLUMN investor_trading.stck_clpr IS '주식 종가';
            COMMENT ON COLUMN investor_trading.prsn_ntby_qty IS '개인 순매수 수량';
            COMMENT ON COLUMN investor_trading.frgn_ntby_qty IS '외국인 순매수 수량';
            COMMENT ON COLUMN investor_trading.orgn_ntby_qty IS '기관계 순매수 수량';
            COMMENT ON COLUMN investor_trading.prsn_ntby_tr_pbmn IS '개인 순매수 거래대금';
            COMMENT ON COLUMN investor_trading.frgn_ntby_tr_pbmn IS '외국인 순매수 거래대금';
            COMMENT ON COLUMN investor_trading.orgn_ntby_tr_pbmn IS '기관계 순매수 거래대금';
            COMMENT ON COLUMN investor_trading.created_at IS '생성일시';
        """))
        logger.info("   ✅ investor_trading 테이블 완료")

        # 7. stock_info 테이블
        logger.info("\n7. stock_info 테이블 COMMENT 추가...")
        db.execute(text("""
            COMMENT ON TABLE stock_info IS '종목 기본정보 (KIS API, 매일 16:10 수집)';
            COMMENT ON COLUMN stock_info.id IS 'Primary Key';
            COMMENT ON COLUMN stock_info.stock_code IS '종목코드';
            COMMENT ON COLUMN stock_info.std_idst_clsf_cd IS '표준산업분류코드';
            COMMENT ON COLUMN stock_info.std_idst_clsf_cd_name IS '업종명';
            COMMENT ON COLUMN stock_info.hts_avls IS '시가총액';
            COMMENT ON COLUMN stock_info.lstn_stcn IS '상장주식수';
            COMMENT ON COLUMN stock_info.cpfn IS '자본금';
            COMMENT ON COLUMN stock_info.updated_at IS '최종 업데이트 시간';
        """))
        logger.info("   ✅ stock_info 테이블 완료")

        # 8. sector_index 테이블
        logger.info("\n8. sector_index 테이블 COMMENT 추가...")
        db.execute(text("""
            COMMENT ON TABLE sector_index IS '업종 지수 (장중 5분마다 수집)';
            COMMENT ON COLUMN sector_index.id IS 'Primary Key';
            COMMENT ON COLUMN sector_index.sector_code IS '업종코드 (0001:KOSPI, 1001:KOSDAQ)';
            COMMENT ON COLUMN sector_index.datetime IS '지수 시간';
            COMMENT ON COLUMN sector_index.bstp_nmix_prpr IS '업종 현재지수';
            COMMENT ON COLUMN sector_index.bstp_nmix_prdy_vrss IS '전일 대비';
            COMMENT ON COLUMN sector_index.bstp_nmix_prdy_ctrt IS '전일 대비율 (%)';
            COMMENT ON COLUMN sector_index.acml_vol IS '누적 거래량';
            COMMENT ON COLUMN sector_index.acml_tr_pbmn IS '누적 거래대금';
            COMMENT ON COLUMN sector_index.created_at IS '생성일시';
        """))
        logger.info("   ✅ sector_index 테이블 완료")

        # 9. stock_overtime_price 테이블
        logger.info("\n9. stock_overtime_price 테이블 COMMENT 추가...")
        db.execute(text("""
            COMMENT ON TABLE stock_overtime_price IS '시간외 거래 가격 (매일 18:00 수집, 08:30~18:00 시간외 거래)';
            COMMENT ON COLUMN stock_overtime_price.id IS 'Primary Key';
            COMMENT ON COLUMN stock_overtime_price.stock_code IS '종목코드';
            COMMENT ON COLUMN stock_overtime_price.date IS '거래일';
            COMMENT ON COLUMN stock_overtime_price.ovtm_untp_prpr IS '시간외 단일가 현재가';
            COMMENT ON COLUMN stock_overtime_price.ovtm_untp_prdy_vrss IS '전일 대비';
            COMMENT ON COLUMN stock_overtime_price.prdy_vrss_sign IS '전일 대비 부호 (2:상승, 5:하락, 3:보합)';
            COMMENT ON COLUMN stock_overtime_price.ovtm_untp_prdy_ctrt IS '전일 대비율 (%)';
            COMMENT ON COLUMN stock_overtime_price.acml_vol IS '누적 거래량';
            COMMENT ON COLUMN stock_overtime_price.acml_tr_pbmn IS '누적 거래대금';
            COMMENT ON COLUMN stock_overtime_price.ovtm_untp_antc_cnpr IS '예상 체결가';
            COMMENT ON COLUMN stock_overtime_price.ovtm_untp_antc_cntg_vrss IS '예상 체결 대비';
            COMMENT ON COLUMN stock_overtime_price.ovtm_untp_antc_cntg_vrss_sign IS '예상 체결 대비 부호';
            COMMENT ON COLUMN stock_overtime_price.ovtm_untp_antc_cntg_ctrt IS '예상 체결 대비율 (%)';
            COMMENT ON COLUMN stock_overtime_price.ovtm_untp_antc_vol IS '예상 거래량';
            COMMENT ON COLUMN stock_overtime_price.created_at IS '생성일시';
        """))
        logger.info("   ✅ stock_overtime_price 테이블 완료")

        # 10. news_articles 테이블
        logger.info("\n10. news_articles 테이블 COMMENT 추가...")
        db.execute(text("""
            COMMENT ON TABLE news_articles IS '뉴스 기사 (10분마다 크롤링)';
            COMMENT ON COLUMN news_articles.id IS 'Primary Key';
            COMMENT ON COLUMN news_articles.title IS '기사 제목';
            COMMENT ON COLUMN news_articles.url IS '기사 URL';
            COMMENT ON COLUMN news_articles.source IS '출처 (네이버, DART 등)';
            COMMENT ON COLUMN news_articles.published_at IS '발행 시간';
            COMMENT ON COLUMN news_articles.stock_code IS '관련 종목코드';
            COMMENT ON COLUMN news_articles.content IS '기사 본문';
            COMMENT ON COLUMN news_articles.notified_at IS '텔레그램 알림 발송 시간';
            COMMENT ON COLUMN news_articles.created_at IS '생성일시';
        """))
        logger.info("   ✅ news_articles 테이블 완료")

        # 11. predictions 테이블
        logger.info("\n11. predictions 테이블 COMMENT 추가...")
        db.execute(text("""
            COMMENT ON TABLE predictions IS 'AI 뉴스 영향도 예측 결과';
            COMMENT ON COLUMN predictions.id IS 'Primary Key';
            COMMENT ON COLUMN predictions.news_id IS '뉴스 ID (news_articles 참조)';
            COMMENT ON COLUMN predictions.stock_code IS '종목코드';
            COMMENT ON COLUMN predictions.sentiment_direction IS '감성 방향 (positive/negative/neutral)';
            COMMENT ON COLUMN predictions.sentiment_score IS '감성 점수 (-1.0 ~ 1.0)';
            COMMENT ON COLUMN predictions.impact_level IS '영향 수준 (high/medium/low)';
            COMMENT ON COLUMN predictions.relevance_score IS '관련성 점수 (0.0 ~ 1.0)';
            COMMENT ON COLUMN predictions.urgency_level IS '긴급도 (urgent/notable/routine)';
            COMMENT ON COLUMN predictions.impact_analysis IS '영향 분석 JSON';
            COMMENT ON COLUMN predictions.reasoning IS 'AI 추론 근거';
            COMMENT ON COLUMN predictions.created_at IS '생성일시';
        """))
        logger.info("   ✅ predictions 테이블 완료")

        db.commit()

        logger.info("\n" + "=" * 80)
        logger.info("✅ 모든 테이블 COMMENT 추가 완료!")
        logger.info("=" * 80)

    except Exception as e:
        db.rollback()
        logger.error(f"\n❌ COMMENT 추가 실패: {e}", exc_info=True)
        raise

    finally:
        db.close()


def downgrade():
    """Migration 롤백"""
    logger.info("=" * 80)
    logger.info("🔙 Rollback: 테이블 COMMENT 제거")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 모든 테이블의 COMMENT 제거
        tables = [
            'stocks', 'stock_prices', 'stock_prices_minute',
            'stock_orderbook', 'stock_current_price', 'investor_trading',
            'stock_info', 'sector_index', 'stock_overtime_price',
            'news_articles', 'predictions'
        ]

        for table in tables:
            db.execute(text(f"COMMENT ON TABLE {table} IS NULL;"))

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
