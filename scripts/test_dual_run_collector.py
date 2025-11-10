"""
Dual-Run Collector 테스트 스크립트

FDR + KIS 동시 수집 및 자동 검증 테스트
"""
import logging
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.crawlers.dual_run_collector import get_dual_run_collector


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_single_stock():
    """단일 종목 Dual-Run 테스트"""
    logger.info("\n" + "="*80)
    logger.info("테스트 1: 단일 종목 Dual-Run")
    logger.info("="*80 + "\n")

    collector = get_dual_run_collector()

    # SK하이닉스 테스트
    result = await collector.collect_stock_dual(
        stock_code="000660",
        days=3  # 최근 3일
    )

    logger.info("\n결과:")
    logger.info(f"  상태: {result['status']}")
    if result['status'] == 'success':
        logger.info(f"  FDR: {result['fdr_count']}건")
        logger.info(f"  KIS: {result['kis_count']}건")
        logger.info(f"  소요 시간: {result['elapsed_time']:.1f}초")

        if result.get('validation'):
            v = result['validation']
            logger.info(f"  검증:")
            logger.info(f"    - 비교: {v['total_count']}건")
            logger.info(f"    - 일치율: {v['match_rate']:.2f}%")
            logger.info(f"    - 평균 차이: {v['avg_diff_close_pct']:.3f}%")
            logger.info(f"    - 이상치: {v['anomaly_count']}건")

    return result


async def test_batch_collection():
    """소규모 배치 Dual-Run 테스트"""
    logger.info("\n" + "="*80)
    logger.info("테스트 2: 소규모 배치 Dual-Run (5개 종목)")
    logger.info("="*80 + "\n")

    collector = get_dual_run_collector()

    # 5개 종목만 테스트
    summary = await collector.collect_all_dual(
        days=1,
        batch_size=5
    )

    logger.info("\n전체 결과 요약:")
    logger.info(f"  전체: {summary['total_stocks']}개")
    logger.info(f"  성공: {summary['success_count']}개 ({summary['success_rate']:.1f}%)")
    logger.info(f"  FDR 저장: {summary['total_fdr_saved']}건")
    logger.info(f"  KIS 저장: {summary['total_kis_saved']}건")
    logger.info(f"  평균 일치율: {summary['avg_match_rate']:.2f}%")
    logger.info(f"  평균 차이: {summary['avg_diff_pct']:.3f}%")
    logger.info(f"  총 이상치: {summary['total_anomalies']}건")

    return summary


async def main():
    """메인 테스트 실행"""
    import sys

    try:
        # 테스트 1: 단일 종목
        await test_single_stock()

        # 배치 테스트는 커맨드라인 인자로 제어
        if len(sys.argv) > 1 and sys.argv[1] == '--batch':
            # 테스트 2: 소규모 배치
            await test_batch_collection()
        else:
            logger.info("\n💡 배치 테스트를 실행하려면 '--batch' 플래그를 추가하세요.")

        logger.info("\n✅ 모든 테스트 완료!")

    except Exception as e:
        logger.error(f"\n❌ 테스트 실패: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
