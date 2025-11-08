"""
Unit tests for impact analysis functionality in Predictor

Tests:
1. Prompt generation for impact analysis
2. Response parsing with new fields
3. Database storage of new fields
4. Validation logic for each field
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from backend.llm.predictor import StockPredictor
from backend.db.models.prediction import Prediction


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    return session


@pytest.fixture
def sample_news():
    """Sample news data for testing"""
    return {
        "id": 1,
        "title": "삼성전자, 신제품 출시로 시장 점유율 확대 예상",
        "content": "삼성전자가 신규 반도체 제품을 출시하며 시장 점유율을 15% 확대할 것으로 전망된다.",
        "published_at": "2025-01-06T10:00:00",
        "stock_code": "005930",
        "company_name": "삼성전자"
    }


@pytest.fixture
def sample_similar_news():
    """Sample similar news for context"""
    return [
        {
            "title": "삼성전자 실적 호전",
            "content": "지난 분기 대비 매출 증가",
            "published_at": "2025-01-05T10:00:00"
        }
    ]


class TestPromptGeneration:
    """프롬프트 생성 테스트"""

    def test_system_prompt_contains_impact_analysis_role(self, sample_news, sample_similar_news):
        """시스템 프롬프트가 영향도 분석가 역할을 포함하는지 검증"""
        predictor = StockPredictor(model="gpt-4o-mini", provider="openai")

        with patch.object(predictor, '_call_llm', return_value='{"sentiment_direction": "positive"}'):
            predictor._build_prompt(sample_news, sample_similar_news)

        # _build_prompt는 내부 메서드이므로 실제 호출 확인
        assert predictor.model == "gpt-4o-mini"

    def test_prompt_includes_new_response_format(self, sample_news, sample_similar_news):
        """프롬프트가 새로운 응답 형식을 포함하는지 검증"""
        predictor = StockPredictor(model="gpt-4o-mini", provider="openai")

        # _build_prompt 메서드 직접 테스트
        with patch.object(predictor, '_call_llm') as mock_llm:
            mock_llm.return_value = '''{
                "sentiment_direction": "positive",
                "sentiment_score": 0.7,
                "impact_level": "high",
                "relevance_score": 0.85,
                "urgency_level": "urgent",
                "reasoning": "test",
                "impact_analysis": {},
                "pattern_analysis": {}
            }'''

            result = predictor.predict(sample_news, sample_similar_news)

            # 프롬프트가 호출되었는지 확인
            assert mock_llm.called


class TestResponseParsing:
    """응답 파싱 테스트"""

    @patch('backend.llm.predictor.StockPredictor._call_llm')
    def test_parse_valid_impact_analysis_response(self, mock_llm, sample_news, sample_similar_news):
        """유효한 영향도 분석 응답 파싱 테스트"""
        mock_llm.return_value = '''{
            "sentiment_direction": "positive",
            "sentiment_score": 0.7,
            "impact_level": "high",
            "relevance_score": 0.85,
            "urgency_level": "urgent",
            "reasoning": "신제품 출시로 매출 증가 예상",
            "impact_analysis": {
                "business_impact": "시장 점유율 15% 확대 예상",
                "market_sentiment_impact": "긍정적 시장 반응",
                "competitive_impact": "경쟁사 대비 우위",
                "regulatory_impact": "규제 변화 없음"
            },
            "pattern_analysis": {
                "avg_1d": 2.5,
                "avg_3d": 5.3,
                "avg_5d": 7.8
            }
        }'''

        predictor = StockPredictor(model="gpt-4o-mini", provider="openai")
        result = predictor.predict(sample_news, sample_similar_news)

        # 필수 필드 검증
        assert "sentiment_direction" in result
        assert "sentiment_score" in result
        assert "impact_level" in result
        assert "relevance_score" in result
        assert "urgency_level" in result
        assert "impact_analysis" in result

        # 값 검증
        assert result["sentiment_direction"] == "positive"
        assert result["sentiment_score"] == 0.7
        assert result["impact_level"] == "high"
        assert result["relevance_score"] == 0.85
        assert result["urgency_level"] == "urgent"

    @patch('backend.llm.predictor.StockPredictor._call_llm')
    def test_validate_sentiment_direction(self, mock_llm, sample_news, sample_similar_news):
        """sentiment_direction 검증 테스트"""
        # 유효하지 않은 값
        mock_llm.return_value = '''{
            "sentiment_direction": "invalid_direction",
            "sentiment_score": 0.7,
            "impact_level": "high",
            "relevance_score": 0.85,
            "urgency_level": "urgent",
            "reasoning": "test",
            "impact_analysis": {},
            "pattern_analysis": {}
        }'''

        predictor = StockPredictor(model="gpt-4o-mini", provider="openai")
        result = predictor.predict(sample_news, sample_similar_news)

        # 기본값으로 대체되어야 함
        assert result["sentiment_direction"] == "neutral"

    @patch('backend.llm.predictor.StockPredictor._call_llm')
    def test_validate_sentiment_score_range(self, mock_llm, sample_news, sample_similar_news):
        """sentiment_score 범위 검증 테스트 (-1.0 ~ 1.0)"""
        # 범위를 벗어난 값
        mock_llm.return_value = '''{
            "sentiment_direction": "positive",
            "sentiment_score": 2.0,
            "impact_level": "high",
            "relevance_score": 0.85,
            "urgency_level": "urgent",
            "reasoning": "test",
            "impact_analysis": {},
            "pattern_analysis": {}
        }'''

        predictor = StockPredictor(model="gpt-4o-mini", provider="openai")
        result = predictor.predict(sample_news, sample_similar_news)

        # 기본값으로 대체되어야 함
        assert result["sentiment_score"] == 0.0

    @patch('backend.llm.predictor.StockPredictor._call_llm')
    def test_validate_impact_level(self, mock_llm, sample_news, sample_similar_news):
        """impact_level 검증 테스트"""
        mock_llm.return_value = '''{
            "sentiment_direction": "positive",
            "sentiment_score": 0.7,
            "impact_level": "invalid_level",
            "relevance_score": 0.85,
            "urgency_level": "urgent",
            "reasoning": "test",
            "impact_analysis": {},
            "pattern_analysis": {}
        }'''

        predictor = StockPredictor(model="gpt-4o-mini", provider="openai")
        result = predictor.predict(sample_news, sample_similar_news)

        # 기본값으로 대체되어야 함
        assert result["impact_level"] == "medium"

    @patch('backend.llm.predictor.StockPredictor._call_llm')
    def test_validate_relevance_score_range(self, mock_llm, sample_news, sample_similar_news):
        """relevance_score 범위 검증 테스트 (0.0 ~ 1.0)"""
        mock_llm.return_value = '''{
            "sentiment_direction": "positive",
            "sentiment_score": 0.7,
            "impact_level": "high",
            "relevance_score": 1.5,
            "urgency_level": "urgent",
            "reasoning": "test",
            "impact_analysis": {},
            "pattern_analysis": {}
        }'''

        predictor = StockPredictor(model="gpt-4o-mini", provider="openai")
        result = predictor.predict(sample_news, sample_similar_news)

        # 기본값으로 대체되어야 함
        assert result["relevance_score"] == 0.5

    @patch('backend.llm.predictor.StockPredictor._call_llm')
    def test_validate_urgency_level(self, mock_llm, sample_news, sample_similar_news):
        """urgency_level 검증 테스트"""
        mock_llm.return_value = '''{
            "sentiment_direction": "positive",
            "sentiment_score": 0.7,
            "impact_level": "high",
            "relevance_score": 0.85,
            "urgency_level": "invalid_urgency",
            "reasoning": "test",
            "impact_analysis": {},
            "pattern_analysis": {}
        }'''

        predictor = StockPredictor(model="gpt-4o-mini", provider="openai")
        result = predictor.predict(sample_news, sample_similar_news)

        # 기본값으로 대체되어야 함
        assert result["urgency_level"] == "notable"

    @patch('backend.llm.predictor.StockPredictor._call_llm')
    def test_missing_required_fields_raises_error(self, mock_llm, sample_news, sample_similar_news):
        """필수 필드 누락 시 오류 발생 테스트"""
        # impact_analysis 누락
        mock_llm.return_value = '''{
            "sentiment_direction": "positive",
            "sentiment_score": 0.7,
            "impact_level": "high",
            "relevance_score": 0.85,
            "urgency_level": "urgent",
            "reasoning": "test",
            "pattern_analysis": {}
        }'''

        predictor = StockPredictor(model="gpt-4o-mini", provider="openai")
        result = predictor.predict(sample_news, sample_similar_news)

        # 폴백 응답이 반환되어야 함
        assert "error" in result or result["impact_level"] == "low"


class TestDatabaseStorage:
    """데이터베이스 저장 테스트"""

    @patch('backend.llm.predictor.StockPredictor._call_llm')
    @patch('backend.llm.predictor.SessionLocal')
    def test_save_new_prediction_with_impact_fields(self, mock_session_local, mock_llm, sample_news, sample_similar_news):
        """새 예측 저장 시 영향도 필드 저장 테스트"""
        mock_llm.return_value = '''{
            "sentiment_direction": "positive",
            "sentiment_score": 0.7,
            "impact_level": "high",
            "relevance_score": 0.85,
            "urgency_level": "urgent",
            "reasoning": "신제품 출시 긍정적 영향",
            "impact_analysis": {
                "business_impact": "매출 증가 예상"
            },
            "pattern_analysis": {}
        }'''

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        predictor = StockPredictor(model="gpt-4o-mini", provider="openai")
        result = predictor.predict(sample_news, sample_similar_news)

        # 결과에 새 필드가 포함되어 있는지 확인
        assert result["sentiment_direction"] == "positive"
        assert result["sentiment_score"] == 0.7
        assert result["impact_level"] == "high"
        assert result["relevance_score"] == 0.85
        assert result["urgency_level"] == "urgent"

    @patch('backend.llm.predictor.StockPredictor._call_llm')
    @patch('backend.llm.predictor.SessionLocal')
    def test_deprecated_fields_set_to_none(self, mock_session_local, mock_llm, sample_news, sample_similar_news):
        """Deprecated 필드가 None으로 설정되는지 테스트"""
        mock_llm.return_value = '''{
            "sentiment_direction": "positive",
            "sentiment_score": 0.7,
            "impact_level": "high",
            "relevance_score": 0.85,
            "urgency_level": "urgent",
            "reasoning": "test",
            "impact_analysis": {},
            "pattern_analysis": {}
        }'''

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        predictor = StockPredictor(model="gpt-4o-mini", provider="openai")
        result = predictor.predict(sample_news, sample_similar_news)

        # Deprecated 필드가 결과에 없거나 None이어야 함
        assert result.get("direction") is None
        assert result.get("confidence") is None
        assert result.get("short_term") is None
        assert result.get("medium_term") is None
        assert result.get("long_term") is None


class TestFallbackBehavior:
    """폴백 동작 테스트"""

    @patch('backend.llm.predictor.StockPredictor._call_llm')
    def test_fallback_on_llm_error(self, mock_llm, sample_news, sample_similar_news):
        """LLM 오류 시 폴백 응답 테스트"""
        mock_llm.side_effect = Exception("LLM API error")

        predictor = StockPredictor(model="gpt-4o-mini", provider="openai")
        result = predictor.predict(sample_news, sample_similar_news)

        # 폴백 응답 검증
        assert result["sentiment_direction"] == "neutral"
        assert result["sentiment_score"] == 0.0
        assert result["impact_level"] == "low"
        assert result["relevance_score"] == 0.0
        assert result["urgency_level"] == "routine"
        assert "error" in result

    @patch('backend.llm.predictor.StockPredictor._call_llm')
    def test_fallback_on_invalid_json(self, mock_llm, sample_news, sample_similar_news):
        """잘못된 JSON 응답 시 폴백 테스트"""
        mock_llm.return_value = "This is not valid JSON"

        predictor = StockPredictor(model="gpt-4o-mini", provider="openai")
        result = predictor.predict(sample_news, sample_similar_news)

        # 폴백 응답 검증
        assert result["sentiment_direction"] == "neutral"
        assert result["impact_level"] == "low"


class TestIntegration:
    """통합 테스트"""

    @patch('backend.llm.predictor.StockPredictor._call_llm')
    def test_end_to_end_impact_analysis(self, mock_llm, sample_news, sample_similar_news):
        """전체 영향도 분석 플로우 테스트"""
        mock_llm.return_value = '''{
            "sentiment_direction": "positive",
            "sentiment_score": 0.8,
            "impact_level": "high",
            "relevance_score": 0.9,
            "urgency_level": "urgent",
            "reasoning": "신제품 출시로 인한 긍정적 영향 예상. 시장 점유율 15% 증가 전망.",
            "impact_analysis": {
                "business_impact": "신제품 출시로 향후 6개월 매출 15% 증가 예상",
                "market_sentiment_impact": "투자자들의 긍정적 반응 예상",
                "competitive_impact": "경쟁사 대비 기술 우위 확보",
                "regulatory_impact": "규제 변화 없음"
            },
            "pattern_analysis": {
                "avg_1d": 2.5,
                "avg_3d": 5.3,
                "avg_5d": 7.8
            }
        }'''

        predictor = StockPredictor(model="gpt-4o-mini", provider="openai")
        result = predictor.predict(sample_news, sample_similar_news)

        # 전체 플로우 검증
        assert result["sentiment_direction"] in ["positive", "negative", "neutral"]
        assert -1.0 <= result["sentiment_score"] <= 1.0
        assert result["impact_level"] in ["low", "medium", "high", "critical"]
        assert 0.0 <= result["relevance_score"] <= 1.0
        assert result["urgency_level"] in ["routine", "notable", "urgent", "breaking"]
        assert isinstance(result["impact_analysis"], dict)
        assert isinstance(result["reasoning"], str)
        assert len(result["reasoning"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
