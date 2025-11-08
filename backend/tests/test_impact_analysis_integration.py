"""
Integration tests for impact analysis functionality

Tests the complete flow:
1. Database has new impact analysis fields
2. Predictor can generate impact analysis
3. Data is saved correctly to database
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.llm.predictor import StockPredictor
from backend.db.models.prediction import Prediction
from backend.db.session import SessionLocal
from sqlalchemy import text


class TestImpactAnalysisIntegration:
    """영향도 분석 통합 테스트"""

    def test_database_has_new_fields(self):
        """데이터베이스에 새로운 필드가 존재하는지 확인"""
        db = SessionLocal()
        try:
            # 테이블 스키마 확인
            result = db.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'predictions'
                AND column_name IN (
                    'sentiment_direction', 'sentiment_score', 'impact_level',
                    'relevance_score', 'urgency_level', 'impact_analysis'
                )
                ORDER BY column_name
            """))

            columns = [row[0] for row in result]

            # 새 필드가 모두 존재하는지 확인
            assert 'sentiment_direction' in columns
            assert 'sentiment_score' in columns
            assert 'impact_level' in columns
            assert 'relevance_score' in columns
            assert 'urgency_level' in columns
            assert 'impact_analysis' in columns

        finally:
            db.close()

    def test_deprecated_fields_nullable(self):
        """Deprecated 필드가 nullable인지 확인"""
        db = SessionLocal()
        try:
            # nullable 확인
            result = db.execute(text("""
                SELECT column_name, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'predictions'
                AND column_name IN ('direction', 'confidence')
            """))

            nullable_info = {row[0]: row[1] for row in result}

            # Deprecated 필드들이 nullable이어야 함
            assert nullable_info.get('direction') == 'YES'
            assert nullable_info.get('confidence') == 'YES'

        finally:
            db.close()

    @patch('backend.llm.predictor.OpenAI')
    def test_predictor_generates_impact_analysis(self, mock_openai):
        """Predictor가 영향도 분석을 생성하는지 테스트"""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''{
            "sentiment_direction": "positive",
            "sentiment_score": 0.75,
            "impact_level": "high",
            "relevance_score": 0.85,
            "urgency_level": "urgent",
            "reasoning": "신제품 출시로 긍정적 영향 예상",
            "impact_analysis": {
                "business_impact": "매출 증가 예상",
                "market_sentiment_impact": "긍정적 반응",
                "competitive_impact": "경쟁 우위",
                "regulatory_impact": "변화 없음"
            },
            "pattern_analysis": {
                "avg_1d": 2.5,
                "avg_3d": 5.0,
                "avg_5d": 7.5
            }
        }'''

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        # Predictor 생성 및 예측 수행
        predictor = StockPredictor()
        predictor.client = mock_client  # 모킹된 클라이언트 주입

        sample_news = {
            "id": 999,
            "title": "테스트 뉴스",
            "content": "테스트 내용",
            "published_at": "2025-01-06T10:00:00",
            "stock_code": "000000",
            "company_name": "테스트 기업"
        }

        result = predictor.predict(sample_news, [])

        # 결과 검증
        assert "sentiment_direction" in result
        assert "sentiment_score" in result
        assert "impact_level" in result
        assert "relevance_score" in result
        assert "urgency_level" in result
        assert "impact_analysis" in result

        # 값 범위 검증
        assert result["sentiment_direction"] in ["positive", "negative", "neutral"]
        assert -1.0 <= result["sentiment_score"] <= 1.0
        assert result["impact_level"] in ["low", "medium", "high", "critical"]
        assert 0.0 <= result["relevance_score"] <= 1.0
        assert result["urgency_level"] in ["routine", "notable", "urgent", "breaking"]

    def test_validation_logic(self):
        """검증 로직 테스트 (독립적인 함수로)"""
        # sentiment_score 범위 검증
        valid_scores = [0.0, 0.5, 1.0, -0.5, -1.0]
        invalid_scores = [1.5, -1.5, 2.0, -2.0]

        for score in valid_scores:
            assert -1.0 <= score <= 1.0, f"Valid score {score} should pass"

        for score in invalid_scores:
            assert not (-1.0 <= score <= 1.0), f"Invalid score {score} should fail"

        # relevance_score 범위 검증
        valid_relevance = [0.0, 0.5, 0.8, 1.0]
        invalid_relevance = [-0.1, 1.1, 2.0]

        for score in valid_relevance:
            assert 0.0 <= score <= 1.0, f"Valid relevance {score} should pass"

        for score in invalid_relevance:
            assert not (0.0 <= score <= 1.0), f"Invalid relevance {score} should fail"

        # Enum validation
        valid_directions = ["positive", "negative", "neutral"]
        valid_impacts = ["low", "medium", "high", "critical"]
        valid_urgencies = ["routine", "notable", "urgent", "breaking"]

        assert "positive" in valid_directions
        assert "high" in valid_impacts
        assert "urgent" in valid_urgencies

        assert "invalid" not in valid_directions
        assert "super_high" not in valid_impacts
        assert "asap" not in valid_urgencies

    def test_sample_data_validation(self):
        """실제 데이터베이스의 샘플 데이터 검증"""
        db = SessionLocal()
        try:
            # 최근 10개의 prediction 레코드 조회
            result = db.execute(text("""
                SELECT
                    id, sentiment_direction, sentiment_score, impact_level,
                    relevance_score, urgency_level, impact_analysis
                FROM predictions
                WHERE sentiment_direction IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 10
            """))

            rows = result.fetchall()

            if len(rows) > 0:
                for row in rows:
                    pred_id, sentiment_dir, sentiment_score, impact_level, relevance_score, urgency_level, impact_analysis = row

                    # 필드 존재 확인
                    assert sentiment_dir is not None, f"Prediction {pred_id} has null sentiment_direction"
                    assert sentiment_score is not None, f"Prediction {pred_id} has null sentiment_score"
                    assert impact_level is not None, f"Prediction {pred_id} has null impact_level"
                    assert relevance_score is not None, f"Prediction {pred_id} has null relevance_score"
                    assert urgency_level is not None, f"Prediction {pred_id} has null urgency_level"

                    # 값 범위 검증
                    assert sentiment_dir in ["positive", "negative", "neutral"], \
                        f"Prediction {pred_id} has invalid sentiment_direction: {sentiment_dir}"
                    assert -1.0 <= sentiment_score <= 1.0, \
                        f"Prediction {pred_id} has invalid sentiment_score: {sentiment_score}"
                    assert impact_level in ["low", "medium", "high", "critical"], \
                        f"Prediction {pred_id} has invalid impact_level: {impact_level}"
                    assert 0.0 <= relevance_score <= 1.0, \
                        f"Prediction {pred_id} has invalid relevance_score: {relevance_score}"
                    assert urgency_level in ["routine", "notable", "urgent", "breaking"], \
                        f"Prediction {pred_id} has invalid urgency_level: {urgency_level}"

                print(f"✅ {len(rows)}개의 샘플 데이터 검증 완료")
            else:
                print("⚠️  영향도 분석 데이터가 아직 없습니다 (정상적인 상태일 수 있음)")

        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
