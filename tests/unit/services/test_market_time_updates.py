"""
시장 시간 기반 동적 업데이트 시스템 통합 테스트

STORY-002: 5가지 시장 단계별 업데이트 트리거 검증
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from freezegun import freeze_time

from backend.services.stock_analysis_service import update_stock_analysis_summary
from backend.db.models.stock_analysis import StockAnalysisSummary
from backend.db.models.stock import StockPrice
from tests.conftest import create_predictions


@freeze_time("2025-11-04 00:15:00")  # KST 09:15 = UTC 00:15 (UTC+9)
@pytest.mark.asyncio
async def test_market_open_ttl_1hour(db_session, sample_stock_code):
    """
    Test: 장 시작 시 1시간 TTL 적용 확인

    Given: 1.5시간 전 리포트
    When: 장 시작 (09:00-09:30)
    Then: TTL 1시간 초과로 업데이트 (예측 개수 동일해도)
    """
    with patch('backend.services.stock_analysis_service.get_report_generator') as mock_generator:
        mock_gen = MagicMock()
        mock_gen.generate_report.return_value = {
            "overall_summary": "Market open update",
            "short_term_scenario": "Short",
            "medium_term_scenario": "Medium",
            "long_term_scenario": "Long",
            "risk_factors": [],
            "opportunity_factors": [],
            "recommendation": "Hold"
        }
        mock_gen.dual_generate_report.return_value = {
            "analysis_summary_a": {"overall_summary": "Test A", "short_term_scenario": "Short A", "medium_term_scenario": "Medium A", "long_term_scenario": "Long A", "risk_factors": [], "opportunity_factors": [], "recommendation": "Hold"},
            "analysis_summary_b": {"overall_summary": "Test B", "short_term_scenario": "Short B", "medium_term_scenario": "Medium B", "long_term_scenario": "Long B", "risk_factors": [], "opportunity_factors": [], "recommendation": "Buy"}
        }
        mock_generator.return_value = mock_gen

        # Given: 1.5시간 전 리포트
        old_time = datetime.now() - timedelta(hours=1, minutes=30)
        create_predictions(db_session, sample_stock_code, count=20, start_time=old_time)

        summary1 = StockAnalysisSummary(
            stock_code=sample_stock_code,
            overall_summary="Old summary",
            last_updated=old_time,
            based_on_prediction_count=20,
            total_predictions=20,
            up_count=10,
            down_count=5,
            hold_count=5,
            avg_confidence=0.75
        )
        db_session.add(summary1)
        db_session.commit()

        # When: 업데이트 시도 (market_open: TTL 1시간)
        summary2 = await update_stock_analysis_summary(sample_stock_code, db_session, force_update=False)

        # Then: TTL 초과로 업데이트
        assert summary2 is not None
        assert summary2.last_updated > old_time, "Should update due to 1h TTL in market_open"


@freeze_time("2025-11-04 02:30:00")  # 정규 장중
@pytest.mark.asyncio
async def test_trading_price_change_3percent(db_session, sample_stock_code):
    """
    Test: 장중 주가 3% 변동 시 즉시 업데이트

    Given: 30분 전 리포트 (TTL 2시간 미만)
    When: 주가 +5% 급등
    Then: 주가 임계값 3% 초과로 즉시 업데이트
    """
    with patch('backend.services.stock_analysis_service.get_report_generator') as mock_generator:
        mock_gen = MagicMock()
        mock_gen.generate_report.return_value = {
            "overall_summary": "Price surge update",
            "short_term_scenario": "Short",
            "medium_term_scenario": "Medium",
            "long_term_scenario": "Long",
            "risk_factors": [],
            "opportunity_factors": [],
            "recommendation": "Buy"
        }
        mock_gen.dual_generate_report.return_value = {
            "analysis_summary_a": {"overall_summary": "Test A", "short_term_scenario": "Short A", "medium_term_scenario": "Medium A", "long_term_scenario": "Long A", "risk_factors": [], "opportunity_factors": [], "recommendation": "Hold"},
            "analysis_summary_b": {"overall_summary": "Test B", "short_term_scenario": "Short B", "medium_term_scenario": "Medium B", "long_term_scenario": "Long B", "risk_factors": [], "opportunity_factors": [], "recommendation": "Buy"}
        }
        mock_generator.return_value = mock_gen

        # Given: 30분 전 리포트 + 주가 +5% 변동
        recent_time = datetime.now() - timedelta(minutes=30)
        create_predictions(db_session, sample_stock_code, count=20, start_time=recent_time)

        # 주가 데이터 추가 (+5% 변동)
        yesterday = datetime.now() - timedelta(days=1)
        prev_price = StockPrice(
            stock_code=sample_stock_code,
            date=yesterday.date(),
            open=100000,
            high=105000,
            low=98000,
            close=100000,
            volume=1000000
        )
        curr_price = StockPrice(
            stock_code=sample_stock_code,
            date=datetime.now().date(),
            open=100000,
            high=107000,
            low=103000,
            close=105000,  # +5%
            volume=1500000
        )
        db_session.add_all([prev_price, curr_price])
        db_session.commit()

        summary1 = StockAnalysisSummary(
            stock_code=sample_stock_code,
            overall_summary="Before surge",
            last_updated=recent_time,
            based_on_prediction_count=20,
            total_predictions=20,
            up_count=10,
            down_count=5,
            hold_count=5,
            avg_confidence=0.75
        )
        db_session.add(summary1)
        db_session.commit()

        # When: 업데이트 시도 (trading: 주가 임계값 3%)
        summary2 = await update_stock_analysis_summary(sample_stock_code, db_session, force_update=False)

        # Then: 주가 급변으로 업데이트
        assert summary2 is not None
        assert summary2.last_updated > recent_time, "Should update due to 5% price change (threshold: 3%)"


@freeze_time("2025-11-04 09:00:00")  # 장 마감 후
@pytest.mark.asyncio
async def test_after_hours_ttl_6hours(db_session, sample_stock_code):
    """
    Test: 장 마감 후 6시간 TTL 적용

    Given: 3시간 전 리포트
    When: 장 마감 후 (15:36-23:59)
    Then: TTL 6시간 미만이므로 업데이트 안 함
    """
    with patch('backend.services.stock_analysis_service.get_report_generator') as mock_generator:
        mock_gen = MagicMock()
        mock_generator.return_value = mock_gen

        # Given: 3시간 전 리포트
        recent_time = datetime.now() - timedelta(hours=3)
        create_predictions(db_session, sample_stock_code, count=20, start_time=recent_time)

        summary1 = StockAnalysisSummary(
            stock_code=sample_stock_code,
            overall_summary="After hours summary",
            last_updated=recent_time,
            based_on_prediction_count=20,
            total_predictions=20,
            up_count=10,
            down_count=5,
            hold_count=5,
            avg_confidence=0.75
        )
        db_session.add(summary1)
        db_session.commit()
        db_session.refresh(summary1)

        # When: 업데이트 시도 (after_hours: TTL 6시간)
        summary2 = await update_stock_analysis_summary(sample_stock_code, db_session, force_update=False)

        # Then: TTL 미만이므로 업데이트 안 함
        assert summary2 is not None
        assert summary2.id == summary1.id
        assert summary2.last_updated == summary1.last_updated, "Should not update (3h < 6h TTL)"

        # LLM 호출 안 됨
        mock_gen.generate_report.assert_not_called()
        mock_gen.dual_generate_report.assert_not_called()


@freeze_time("2025-11-04 03:00:00")  # 정규 장중
@pytest.mark.asyncio
async def test_direction_change_15percent(db_session, sample_stock_code):
    """
    Test: 장중 예측 방향 15%p 변화 시 업데이트

    Given: 1시간 전 리포트 (상승: 50%)
    When: 새 예측으로 상승 비율 70%로 변화 (+20%p)
    Then: 방향 임계값 15%p 초과로 업데이트
    """
    with patch('backend.services.stock_analysis_service.get_report_generator') as mock_generator:
        mock_gen = MagicMock()
        mock_gen.generate_report.return_value = {
            "overall_summary": "Direction change update",
            "short_term_scenario": "Short",
            "medium_term_scenario": "Medium",
            "long_term_scenario": "Long",
            "risk_factors": [],
            "opportunity_factors": [],
            "recommendation": "Buy"
        }
        mock_gen.dual_generate_report.return_value = {
            "analysis_summary_a": {"overall_summary": "Test A", "short_term_scenario": "Short A", "medium_term_scenario": "Medium A", "long_term_scenario": "Long A", "risk_factors": [], "opportunity_factors": [], "recommendation": "Hold"},
            "analysis_summary_b": {"overall_summary": "Test B", "short_term_scenario": "Short B", "medium_term_scenario": "Medium B", "long_term_scenario": "Long B", "risk_factors": [], "opportunity_factors": [], "recommendation": "Buy"}
        }
        mock_generator.return_value = mock_gen

        # Given: 1시간 전 리포트 (상승 50%)
        recent_time = datetime.now() - timedelta(hours=1)
        
        # 기존 예측: 상승 10개, 하락 5개, 보합 5개 (총 20개, 상승 50%)
        summary1 = StockAnalysisSummary(
            stock_code=sample_stock_code,
            overall_summary="Before direction change",
            last_updated=recent_time,
            based_on_prediction_count=20,
            total_predictions=20,
            up_count=10,  # 50%
            down_count=5,
            hold_count=5,
            avg_confidence=0.75
        )
        db_session.add(summary1)
        db_session.commit()

        # 새 예측: 상승 14개, 하락 3개, 보합 3개 (총 20개, 상승 70% = +20%p)
        create_predictions(db_session, sample_stock_code, count=14, direction="up", start_time=recent_time)
        create_predictions(db_session, sample_stock_code, count=3, direction="down", start_time=recent_time)
        create_predictions(db_session, sample_stock_code, count=3, direction="hold", start_time=recent_time)

        # When: 업데이트 시도 (trading: 방향 임계값 15%p)
        summary2 = await update_stock_analysis_summary(sample_stock_code, db_session, force_update=False)

        # Then: 방향 변화로 업데이트
        assert summary2 is not None
        assert summary2.last_updated > recent_time, "Should update due to direction change (50% → 70% = 20%p > 15%p)"


@freeze_time("2025-11-03 23:30:00")  # 장 시작 전
@pytest.mark.asyncio
async def test_pre_market_ttl_3hours(db_session, sample_stock_code):
    """
    Test: 장 시작 전 3시간 TTL 적용

    Given: 4시간 전 리포트
    When: 장 시작 전 (00:00-08:59)
    Then: TTL 3시간 초과로 업데이트
    """
    with patch('backend.services.stock_analysis_service.get_report_generator') as mock_generator:
        mock_gen = MagicMock()
        mock_gen.generate_report.return_value = {
            "overall_summary": "Pre-market update",
            "short_term_scenario": "Short",
            "medium_term_scenario": "Medium",
            "long_term_scenario": "Long",
            "risk_factors": [],
            "opportunity_factors": [],
            "recommendation": "Hold"
        }
        mock_gen.dual_generate_report.return_value = {
            "analysis_summary_a": {"overall_summary": "Test A", "short_term_scenario": "Short A", "medium_term_scenario": "Medium A", "long_term_scenario": "Long A", "risk_factors": [], "opportunity_factors": [], "recommendation": "Hold"},
            "analysis_summary_b": {"overall_summary": "Test B", "short_term_scenario": "Short B", "medium_term_scenario": "Medium B", "long_term_scenario": "Long B", "risk_factors": [], "opportunity_factors": [], "recommendation": "Buy"}
        }
        mock_generator.return_value = mock_gen

        # Given: 4시간 전 리포트
        old_time = datetime.now() - timedelta(hours=4)
        create_predictions(db_session, sample_stock_code, count=20, start_time=old_time)

        summary1 = StockAnalysisSummary(
            stock_code=sample_stock_code,
            overall_summary="Yesterday summary",
            last_updated=old_time,
            based_on_prediction_count=20,
            total_predictions=20,
            up_count=10,
            down_count=5,
            hold_count=5,
            avg_confidence=0.75
        )
        db_session.add(summary1)
        db_session.commit()

        # When: 업데이트 시도 (pre_market: TTL 3시간)
        summary2 = await update_stock_analysis_summary(sample_stock_code, db_session, force_update=False)

        # Then: TTL 초과로 업데이트
        assert summary2 is not None
        assert summary2.last_updated > old_time, "Should update due to 3h TTL in pre_market (4h > 3h)"
