"""
멀티 모델 주가 예측 시스템

모든 활성 모델로 예측을 생성하고, A/B 설정에 따라 표시할 모델을 선택합니다.
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.config import settings
from backend.db.models.model import Model
from backend.db.models.ab_test_config import ABTestConfig
from backend.db.session import SessionLocal


logger = logging.getLogger(__name__)


class MultiModelPredictor:
    """멀티 모델 예측 시스템"""

    def __init__(self):
        """활성 모델 로드"""
        self.active_models = self._load_active_models()
        logger.info(f"✅ 활성 모델 {len(self.active_models)}개 로드 완료")

    def _load_active_models(self) -> Dict[int, Dict[str, Any]]:
        """
        DB에서 활성 모델 목록을 조회하고 클라이언트를 생성합니다.

        Returns:
            {model_id: {"name": "...", "provider": "...", "model_identifier": "...", "client": OpenAI(...)}}
        """
        db = SessionLocal()
        try:
            models = db.query(Model).filter(Model.is_active == True).all()
            result = {}

            for model in models:
                client = self._create_client_for_model(model.provider)
                result[model.id] = {
                    "name": model.name,
                    "provider": model.provider,
                    "model_identifier": model.model_identifier,
                    "client": client,
                    "description": model.description,
                }
                logger.info(f"  📊 Model loaded: {model.name} ({model.provider}/{model.model_identifier})")

            return result

        except Exception as e:
            logger.error(f"활성 모델 로드 실패: {e}")
            return {}
        finally:
            db.close()

    def _create_client_for_model(self, provider: str) -> OpenAI:
        """프로바이더별 OpenAI 클라이언트 생성"""
        if provider == "openrouter":
            return OpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://craveny.ai",
                    "X-Title": "Craveny Multi-Model Predictor",
                }
            )
        else:  # openai
            return OpenAI(api_key=settings.OPENAI_API_KEY)

    def _predict_with_model(
        self,
        model_id: int,
        model_info: Dict[str, Any],
        prompt: str,
        similar_count: int,
    ) -> Dict[str, Any]:
        """
        특정 모델로 예측 수행

        Args:
            model_id: 모델 ID
            model_info: 모델 정보 (client, provider, model_identifier 포함)
            prompt: 예측 프롬프트
            similar_count: 유사 뉴스 개수

        Returns:
            예측 결과
        """
        try:
            client = model_info["client"]
            model_identifier = model_info["model_identifier"]
            provider = model_info["provider"]

            # LLM 호출
            if provider == "openrouter":
                response = client.chat.completions.create(
                    model=model_identifier,
                    messages=[
                        {
                            "role": "system",
                            "content": "당신은 한국 주식 시장 분석 전문가입니다. 뉴스 분석을 통해 주가 예측을 수행합니다. 반드시 JSON 형식으로만 응답하세요.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=1000,
                )
            else:  # openai
                response = client.chat.completions.create(
                    model=model_identifier,
                    messages=[
                        {
                            "role": "system",
                            "content": "당신은 한국 주식 시장 분석 전문가입니다. 뉴스 분석을 통해 주가 예측을 수행합니다.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=1000,
                    response_format={"type": "json_object"},
                )

            # 응답 파싱
            result_text = response.choices[0].message.content

            # OpenRouter 응답에서 JSON 추출
            if provider == "openrouter" and "```json" in result_text:
                import re
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', result_text, re.DOTALL)
                if json_match:
                    result_text = json_match.group(1)

            result = json.loads(result_text)

            # 결과 보강
            result["similar_count"] = similar_count
            result["model"] = model_info["name"]
            result["model_id"] = model_id
            result["provider"] = provider
            result["timestamp"] = datetime.now().isoformat()

            # 하위 호환성 처리
            if "confidence_breakdown" not in result:
                result["confidence_breakdown"] = {
                    "similar_news_quality": result.get("confidence", 0),
                    "pattern_consistency": 0,
                    "disclosure_impact": 0,
                    "explanation": "구 버전 응답"
                }
            if "pattern_analysis" not in result:
                result["pattern_analysis"] = {
                    "avg_1d": None,
                    "avg_3d": None,
                    "avg_5d": None,
                }

            return result

        except Exception as e:
            logger.error(f"모델 {model_info['name']} 예측 실패: {e}")
            return {
                "prediction": "유지",
                "confidence": 0,
                "reasoning": f"예측 실패: {str(e)}",
                "short_term": "예측 불가",
                "medium_term": "예측 불가",
                "long_term": "예측 불가",
                "similar_count": similar_count,
                "model": model_info["name"],
                "model_id": model_id,
                "provider": model_info["provider"],
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            }

    def _save_model_prediction(
        self,
        news_id: int,
        model_id: int,
        stock_code: str,
        prediction_data: Dict[str, Any]
    ) -> None:
        """
        모델 예측 결과를 DB에 저장합니다.

        Args:
            news_id: 뉴스 ID
            model_id: 모델 ID
            stock_code: 종목 코드
            prediction_data: 예측 결과
        """
        db = SessionLocal()
        try:
            # UPSERT (INSERT ... ON CONFLICT UPDATE)
            db.execute(
                text("""
                    INSERT INTO model_predictions (news_id, model_id, stock_code, prediction_data)
                    VALUES (:news_id, :model_id, :stock_code, :prediction_data)
                    ON CONFLICT (news_id, model_id)
                    DO UPDATE SET
                        prediction_data = EXCLUDED.prediction_data,
                        created_at = NOW()
                """),
                {
                    "news_id": news_id,
                    "model_id": model_id,
                    "stock_code": stock_code,
                    "prediction_data": json.dumps(prediction_data, ensure_ascii=False),
                }
            )
            db.commit()
            logger.info(f"✅ 모델 {model_id} 예측 저장 완료: news_id={news_id}")

        except Exception as e:
            logger.error(f"모델 예측 저장 실패: {e}")
            db.rollback()
        finally:
            db.close()

    def _get_prediction_from_db(
        self,
        news_id: int,
        model_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        DB에서 특정 모델의 예측 결과를 조회합니다.

        Args:
            news_id: 뉴스 ID
            model_id: 모델 ID

        Returns:
            예측 결과 또는 None
        """
        db = SessionLocal()
        try:
            result = db.execute(
                text("""
                    SELECT prediction_data
                    FROM model_predictions
                    WHERE news_id = :news_id AND model_id = :model_id
                """),
                {"news_id": news_id, "model_id": model_id}
            ).fetchone()

            if result:
                return json.loads(result[0])
            return None

        except Exception as e:
            logger.error(f"모델 예측 조회 실패: {e}")
            return None
        finally:
            db.close()

    def _get_active_ab_config(self) -> Optional[ABTestConfig]:
        """현재 활성화된 A/B 설정을 조회합니다."""
        db = SessionLocal()
        try:
            config = db.query(ABTestConfig).filter(ABTestConfig.is_active == True).first()
            return config
        except Exception as e:
            logger.error(f"A/B 설정 조회 실패: {e}")
            return None
        finally:
            db.close()

    def predict_all_models(
        self,
        current_news: Dict[str, Any],
        similar_news: List[Dict[str, Any]],
        news_id: int,
        prompt: str
    ) -> Dict[int, Dict[str, Any]]:
        """
        모든 활성 모델로 예측을 생성하고 DB에 저장합니다.

        Args:
            current_news: 현재 뉴스 정보
            similar_news: 유사 뉴스 리스트
            news_id: 뉴스 ID
            prompt: 예측 프롬프트

        Returns:
            {model_id: prediction_result, ...}
        """
        stock_code = current_news.get("stock_code")
        similar_count = len(similar_news)
        results = {}

        logger.info(f"🔬 모든 활성 모델로 예측 시작: news_id={news_id}, models={len(self.active_models)}")

        for model_id, model_info in self.active_models.items():
            logger.info(f"  📊 {model_info['name']} 예측 중...")

            # 예측 실행
            prediction = self._predict_with_model(
                model_id,
                model_info,
                prompt,
                similar_count
            )

            # DB 저장
            self._save_model_prediction(news_id, model_id, stock_code, prediction)

            results[model_id] = prediction

        logger.info(f"✅ 모든 모델 예측 완료: {len(results)}개")
        return results

    def get_ab_predictions(self, news_id: int) -> Dict[str, Any]:
        """
        현재 A/B 설정에 따라 두 모델의 예측을 조회합니다.

        Args:
            news_id: 뉴스 ID

        Returns:
            {
                "model_a": {...},
                "model_b": {...},
                "comparison": {...}
            }
        """
        # 활성 A/B 설정 조회
        ab_config = self._get_active_ab_config()
        if not ab_config:
            logger.warning("활성 A/B 설정 없음")
            return {
                "error": "활성 A/B 설정이 없습니다",
                "model_a": None,
                "model_b": None,
            }

        # 두 모델의 예측 조회
        pred_a = self._get_prediction_from_db(news_id, ab_config.model_a_id)
        pred_b = self._get_prediction_from_db(news_id, ab_config.model_b_id)

        if not pred_a or not pred_b:
            logger.warning(f"예측 결과 없음: model_a={pred_a is not None}, model_b={pred_b is not None}")
            return {
                "error": "예측 결과가 없습니다",
                "model_a": pred_a,
                "model_b": pred_b,
            }

        # 비교 분석
        comparison = {
            "agreement": pred_a.get("prediction") == pred_b.get("prediction"),
            "confidence_diff": abs(pred_a.get("confidence", 0) - pred_b.get("confidence", 0)),
            "stronger_model": "model_a" if pred_a.get("confidence", 0) > pred_b.get("confidence", 0) else "model_b",
            "prediction_match": pred_a.get("prediction") == pred_b.get("prediction"),
        }

        return {
            "model_a": pred_a,
            "model_b": pred_b,
            "comparison": comparison,
            "timestamp": datetime.now().isoformat(),
        }


# 싱글톤 인스턴스
_multi_predictor: Optional[MultiModelPredictor] = None


def get_multi_predictor() -> MultiModelPredictor:
    """
    MultiModelPredictor 싱글톤 인스턴스를 반환합니다.

    Returns:
        MultiModelPredictor 인스턴스
    """
    global _multi_predictor
    if _multi_predictor is None:
        _multi_predictor = MultiModelPredictor()
    return _multi_predictor
