"""
장마감 후 오래된 리포트 강제 업데이트 스크립트

6시간 이상 지난 리포트를 강제로 업데이트합니다.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from backend.db.session import SessionLocal
from backend.db.models.stock_analysis import StockAnalysisSummary
from backend.services.stock_analysis_service import update_stock_analysis_summary
from backend.utils.stock_mapping import get_stock_mapper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def update_stale_reports(ttl_hours: float = 6.0):
    """
    오래된 리포트를 강제 업데이트

    Args:
        ttl_hours: 업데이트 필요 기준 시간 (기본 6시간)
    """
    db = SessionLocal()
    stock_mapper = get_stock_mapper()

    try:
        # 모든 리포트 조회
        summaries = db.query(StockAnalysisSummary).all()

        now = datetime.now()
        stale_stocks = []

        # 오래된 리포트 찾기
        for summary in summaries:
            if summary.last_updated:
                age_hours = (now - summary.last_updated).total_seconds() / 3600
                if age_hours > ttl_hours:
                    stock_name = stock_mapper.get_company_name(summary.stock_code)
                    stale_stocks.append({
                        'code': summary.stock_code,
                        'name': stock_name or summary.stock_code,
                        'age_hours': age_hours,
                        'prediction_count': summary.based_on_prediction_count
                    })
            else:
                stock_name = stock_mapper.get_company_name(summary.stock_code)
                stale_stocks.append({
                    'code': summary.stock_code,
                    'name': stock_name or summary.stock_code,
                    'age_hours': 999,  # 타임스탬프 없음
                    'prediction_count': summary.based_on_prediction_count
                })

        # 나이순으로 정렬 (가장 오래된 것부터)
        stale_stocks.sort(key=lambda x: x['age_hours'], reverse=True)

        logger.info(f"총 {len(summaries)}개 종목 중 {len(stale_stocks)}개 업데이트 필요")
        logger.info("=" * 80)

        if not stale_stocks:
            logger.info("모든 리포트가 최신 상태입니다.")
            return

        # 순차적으로 업데이트
        success_count = 0
        fail_count = 0

        for i, stock in enumerate(stale_stocks, 1):
            logger.info(f"\n[{i}/{len(stale_stocks)}] {stock['name']} ({stock['code']}) 업데이트 중...")
            logger.info(f"  현재 나이: {stock['age_hours']:.1f}시간, 예측 {stock['prediction_count']}건")

            try:
                # 강제 업데이트 실행
                result = await update_stock_analysis_summary(
                    stock['code'],
                    db,
                    force_update=True
                )

                if result:
                    success_count += 1
                    logger.info(f"  ✅ 성공: 새 리포트 생성됨 (예측 {result.based_on_prediction_count}건 기반)")
                else:
                    fail_count += 1
                    logger.warning(f"  ❌ 실패: 리포트 생성 실패 (예측 부족 또는 LLM 오류)")

                # API rate limit 고려하여 짧은 대기
                await asyncio.sleep(1)

            except Exception as e:
                fail_count += 1
                logger.error(f"  ❌ 오류: {e}")

        logger.info("\n" + "=" * 80)
        logger.info(f"업데이트 완료: 성공 {success_count}개, 실패 {fail_count}개")

    except Exception as e:
        logger.error(f"업데이트 프로세스 오류: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(update_stale_reports(ttl_hours=6.0))
