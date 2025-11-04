"""
Unit tests for stock_analysis_service.py

Tests for emergency bug fix: update skip logic removal
- Test 1: New predictions should trigger update
- Test 2: 24-hour staleness should trigger update
- Test 3: Fresh reports should skip update
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from backend.services.stock_analysis_service import update_stock_analysis_summary
from backend.db.models.stock_analysis import StockAnalysisSummary
from backend.db.models.prediction import Prediction
from tests.conftest import create_predictions


@pytest.mark.asyncio
async def test_update_on_new_predictions(db_session, sample_stock_code):
    """
    Test: 새 예측 추가 시 리포트 업데이트 확인

    Given: 20개 예측 기반 리포트 생성
    When: 새 예측 5개 추가
    Then: 리포트 자동 업데이트 (total_count: 20 → 25)
    """
    # Mock LLM report generator
    with patch('backend.services.stock_analysis_service.get_report_generator') as mock_generator:
        mock_gen = MagicMock()
        mock_gen.generate_report.return_value = {
            "overall_summary": "Test summary",
            "short_term_scenario": "Short term",
            "medium_term_scenario": "Medium term",
            "long_term_scenario": "Long term",
            "risk_factors": ["Risk 1"],
            "opportunity_factors": ["Opp 1"],
            "recommendation": "Hold"
        }
        mock_gen.dual_generate_report.return_value = {
            "analysis_summary_a": {"overall_summary": "Test A"},
            "analysis_summary_b": {"overall_summary": "Test B"}
        }
        mock_generator.return_value = mock_gen

        # Given: 20개 예측 기반 리포트 생성
        create_predictions(db_session, sample_stock_code, count=20)
        summary1 = await update_stock_analysis_summary(sample_stock_code, db_session, force_update=True)

        assert summary1 is not None
        assert summary1.based_on_prediction_count == 20
        initial_update_time = summary1.last_updated

        # When: 새 예측 5개 추가
        create_predictions(db_session, sample_stock_code, count=5)

        # Then: 리포트 자동 업데이트 (함수는 여전히 최근 20개만 사용하지만, 총 개수 변화를 감지하여 업데이트 트리거)
        summary2 = await update_stock_analysis_summary(sample_stock_code, db_session, force_update=False)

        assert summary2 is not None
        # Note: based_on_prediction_count는 limit(20)로 인해 20이지만, 업데이트는 발생함 (총 개수 20→25 감지)
        assert summary2.based_on_prediction_count == 20, f"Expected 20 predictions (limit), got {summary2.based_on_prediction_count}"
        assert summary2.last_updated > initial_update_time, "Report should have been updated with new timestamp"


@pytest.mark.asyncio
async def test_update_on_24h_staleness(db_session, sample_stock_code):
    """
    Test: 24시간 경과 시 리포트 업데이트 확인

    Given: 25시간 전 리포트 생성
    When: 리포트 업데이트 시도 (예측 개수 변화 없음)
    Then: 리포트 자동 업데이트 (24시간 TTL 초과)
    """
    # Mock LLM report generator
    with patch('backend.services.stock_analysis_service.get_report_generator') as mock_generator:
        mock_gen = MagicMock()
        mock_gen.generate_report.return_value = {
            "overall_summary": "Updated summary",
            "short_term_scenario": "Short term",
            "medium_term_scenario": "Medium term",
            "long_term_scenario": "Long term",
            "risk_factors": ["Risk 1"],
            "opportunity_factors": ["Opp 1"],
            "recommendation": "Buy"
        }
        mock_gen.dual_generate_report.return_value = {
            "analysis_summary_a": {"overall_summary": "Test A"},
            "analysis_summary_b": {"overall_summary": "Test B"}
        }
        mock_generator.return_value = mock_gen

        # Given: 25시간 전 리포트 생성
        old_time = datetime.now() - timedelta(hours=25)
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
        db_session.refresh(summary1)

        # When: 리포트 업데이트 시도 (force_update=False)
        summary2 = await update_stock_analysis_summary(sample_stock_code, db_session, force_update=False)

        # Then: 리포트 자동 업데이트 (24시간 초과로 인한 갱신)
        assert summary2 is not None
        assert summary2.last_updated > old_time, "Report should have been updated due to 24h staleness"

        # Verify staleness calculation
        staleness_hours = (summary2.last_updated - old_time).total_seconds() / 3600
        assert staleness_hours > 24, f"Expected staleness > 24h, got {staleness_hours:.1f}h"


@pytest.mark.asyncio
async def test_no_update_when_fresh(db_session, sample_stock_code):
    """
    Test: 예측 변화 없고 24시간 미만 시 업데이트 안 함

    Given: 2시간 전 리포트 생성 (20개 예측)
    When: 리포트 업데이트 시도 (예측 변화 없음, force_update=False)
    Then: 업데이트 스킵 (기존 리포트 반환)
    """
    # Mock LLM report generator (should NOT be called)
    with patch('backend.services.stock_analysis_service.get_report_generator') as mock_generator:
        mock_gen = MagicMock()
        mock_generator.return_value = mock_gen

        # Given: 2시간 전 리포트 생성 (20개 예측)
        recent_time = datetime.now() - timedelta(hours=2)
        create_predictions(db_session, sample_stock_code, count=20, start_time=recent_time)

        summary1 = StockAnalysisSummary(
            stock_code=sample_stock_code,
            overall_summary="Recent summary",
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

        # When: 리포트 업데이트 시도 (예측 변화 없음)
        summary2 = await update_stock_analysis_summary(sample_stock_code, db_session, force_update=False)

        # Then: 업데이트 스킵 (기존 리포트 반환)
        assert summary2 is not None
        assert summary2.id == summary1.id, "Should return the same summary instance"
        assert summary2.last_updated == summary1.last_updated, "Timestamp should not change"

        # Verify LLM was NOT called
        mock_gen.generate_report.assert_not_called()
        mock_gen.dual_generate_report.assert_not_called()

        # Verify staleness is under 24h
        staleness_hours = (datetime.now() - summary2.last_updated).total_seconds() / 3600
        assert staleness_hours < 24, f"Expected staleness < 24h, got {staleness_hours:.1f}h"


@pytest.mark.asyncio
async def test_force_update_bypasses_checks(db_session, sample_stock_code):
    """
    Test: force_update=True 시 항상 업데이트

    Given: 최근 리포트 (1시간 전, 예측 개수 변화 없음)
    When: force_update=True로 업데이트 시도
    Then: 체크 우회하고 즉시 업데이트
    """
    # Mock LLM report generator
    with patch('backend.services.stock_analysis_service.get_report_generator') as mock_generator:
        mock_gen = MagicMock()
        mock_gen.generate_report.return_value = {
            "overall_summary": "Forced update",
            "short_term_scenario": "Short term",
            "medium_term_scenario": "Medium term",
            "long_term_scenario": "Long term",
            "risk_factors": [],
            "opportunity_factors": [],
            "recommendation": "Hold"
        }
        mock_gen.dual_generate_report.return_value = {
            "analysis_summary_a": {"overall_summary": "Forced A"},
            "analysis_summary_b": {"overall_summary": "Forced B"}
        }
        mock_generator.return_value = mock_gen

        # Given: 1시간 전 리포트
        recent_time = datetime.now() - timedelta(hours=1)
        create_predictions(db_session, sample_stock_code, count=20, start_time=recent_time)

        summary1 = StockAnalysisSummary(
            stock_code=sample_stock_code,
            overall_summary="Old summary",
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

        # When: force_update=True로 업데이트
        summary2 = await update_stock_analysis_summary(sample_stock_code, db_session, force_update=True)

        # Then: 체크 우회하고 즉시 업데이트
        assert summary2 is not None
        assert summary2.last_updated > recent_time, "Report should have been force-updated"

        # Verify LLM was called
        assert mock_gen.generate_report.called or mock_gen.dual_generate_report.called, "LLM should have been called for force update"
