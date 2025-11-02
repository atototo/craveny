"""
모든 종목의 AI 투자 분석 리포트 배치 업데이트

정기적으로 실행하여 모든 종목의 리포트를 최신 상태로 유지합니다.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func
from backend.db.session import SessionLocal
from backend.db.models.prediction import Prediction
from backend.services.stock_analysis_service import update_stock_analysis_summary
import asyncio
import logging
from datetime import datetime


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def update_all_stock_analysis(force_update: bool = False, stock_codes: list = None):
    """
    모든 종목 또는 특정 종목들의 AI 투자 분석 리포트를 업데이트합니다.

    Args:
        force_update: 기존 리포트가 있어도 강제 업데이트 여부 (기본값: False)
        stock_codes: 업데이트할 특정 종목 코드 리스트 (None이면 모든 종목)
    """
    db = SessionLocal()

    try:
        # 예측 데이터가 있는 종목 조회
        if stock_codes:
            # 특정 종목만 업데이트
            stock_code_list = stock_codes
            logger.info(f"특정 종목 {len(stock_code_list)}개 업데이트 시작: {stock_code_list}")
        else:
            # 모든 종목 조회
            stock_code_list = (
                db.query(Prediction.stock_code)
                .distinct()
                .all()
            )
            stock_code_list = [code[0] for code in stock_code_list if code[0]]
            logger.info(f"전체 종목 {len(stock_code_list)}개 업데이트 시작")

        if not stock_code_list:
            logger.warning("업데이트할 종목이 없습니다.")
            return

        # 통계
        success_count = 0
        fail_count = 0
        skip_count = 0

        start_time = datetime.now()

        for i, stock_code in enumerate(stock_code_list, 1):
            try:
                logger.info(f"\n[{i}/{len(stock_code_list)}] 종목 {stock_code} 리포트 업데이트 중...")

                summary = await update_stock_analysis_summary(
                    stock_code=stock_code,
                    db=db,
                    force_update=force_update
                )

                if summary:
                    success_count += 1
                    logger.info(f"✅ 종목 {stock_code} 업데이트 완료")
                else:
                    skip_count += 1
                    logger.warning(f"⏭️  종목 {stock_code} 스킵 (예측 데이터 없음)")

            except Exception as e:
                fail_count += 1
                logger.error(f"❌ 종목 {stock_code} 업데이트 실패: {e}")

        end_time = datetime.now()
        elapsed_time = (end_time - start_time).total_seconds()

        # 결과 요약
        logger.info(f"\n{'='*60}")
        logger.info("배치 업데이트 완료!")
        logger.info(f"{'='*60}")
        logger.info(f"총 종목 수: {len(stock_code_list)}")
        logger.info(f"성공: {success_count}")
        logger.info(f"스킵: {skip_count}")
        logger.info(f"실패: {fail_count}")
        logger.info(f"소요 시간: {elapsed_time:.2f}초")
        logger.info(f"{'='*60}")

    except Exception as e:
        logger.error(f"배치 업데이트 중 오류 발생: {e}", exc_info=True)
    finally:
        db.close()


async def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='모든 종목의 AI 투자 분석 리포트 배치 업데이트')
    parser.add_argument(
        '--force',
        action='store_true',
        help='기존 리포트가 있어도 강제 업데이트'
    )
    parser.add_argument(
        '--stocks',
        nargs='+',
        help='특정 종목 코드만 업데이트 (예: --stocks 005930 000660)'
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("모든 종목 AI 투자 분석 리포트 배치 업데이트")
    logger.info("=" * 60)
    logger.info(f"강제 업데이트: {args.force}")
    logger.info(f"특정 종목: {args.stocks or '전체'}")
    logger.info("=" * 60)

    await update_all_stock_analysis(
        force_update=args.force,
        stock_codes=args.stocks
    )


if __name__ == "__main__":
    asyncio.run(main())
