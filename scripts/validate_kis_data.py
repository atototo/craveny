"""
KIS API 데이터 일회성 검증 스크립트

샘플 종목에 대해 FDR vs KIS 데이터 비교를 수행합니다.

Usage:
    uv run python scripts/validate_kis_data.py
"""
import logging
from datetime import datetime, timedelta

from backend.validators.kis_validator import get_validator


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def validate_kis_data():
    """
    KIS vs FDR 데이터 검증
    """
    logger.info("=" * 80)
    logger.info("KIS 데이터 검증 시작")
    logger.info("=" * 80)

    # DB에 있는 종목 조회 (FDR과 KIS 모두 있는 종목)
    from backend.db.session import SessionLocal
    from backend.db.models.stock import StockPrice
    from sqlalchemy import func

    db = SessionLocal()

    # FDR과 KIS 모두 데이터가 있는 종목 조회
    fdr_stocks = set(
        row[0] for row in
        db.query(StockPrice.stock_code).filter(StockPrice.source.in_(["FDR", "fdr"])).distinct()
    )
    kis_stocks = set(
        row[0] for row in
        db.query(StockPrice.stock_code).filter(StockPrice.source.in_(["KIS", "kis"])).distinct()
    )

    sample_stocks = sorted(list(fdr_stocks & kis_stocks))[:10]  # 공통 종목 중 10개
    db.close()

    if not sample_stocks:
        logger.error("비교 가능한 종목이 없습니다. FDR과 KIS 데이터를 모두 수집하세요.")
        return False

    # 검증 기간: 최근 30일
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)

    logger.info(f"\n검증 기간: {start_date} ~ {end_date}")
    logger.info(f"대상 종목: {len(sample_stocks)}개\n")

    validator = get_validator()

    all_results = []
    all_metrics = []

    for stock_code in sample_stocks:
        logger.info(f"검증 중: {stock_code}")

        results = validator.validate_stock(stock_code, start_date, end_date)
        all_results.extend(results)

        if not results:
            logger.warning(f"  ⚠️  {stock_code}: 비교할 데이터 없음")
            continue

        metrics = validator.calculate_metrics(results)
        metrics["stock_code"] = stock_code
        all_metrics.append(metrics)

        logger.info(
            f"  일치율: {metrics['match_rate']:.2f}%, "
            f"평균 차이: {metrics['avg_diff_close_pct']:.3f}%"
        )

    if not all_results:
        logger.error("\n❌ 비교할 데이터가 없습니다. FDR과 KIS 데이터를 모두 수집했는지 확인하세요.")
        return False

    # 전체 통계
    total_metrics = validator.calculate_metrics(all_results)

    print("\n" + "=" * 80)
    print("검증 결과 요약")
    print("=" * 80)

    print(f"\n총 비교 건수: {total_metrics['total_count']}건")
    print(f"일치 건수: {total_metrics['match_count']}건")
    print(f"일치율: {total_metrics['match_rate']:.2f}%")
    print(f"이상치 건수: {total_metrics['anomaly_count']}건 ({total_metrics['anomaly_rate']:.2f}%)")
    print(f"평균 차이 (종가): {total_metrics['avg_diff_close_pct']:.3f}%")
    print(f"최대 차이: {total_metrics['max_diff_close_pct']:.2f}% ({total_metrics['max_diff_stock']} {total_metrics['max_diff_date']})")

    # 종목별 결과 테이블
    print("\n종목별 검증 결과:")
    print(f"{'종목코드':<10} {'비교 건수':>10} {'일치율':>10} {'평균 차이':>10} {'이상치':>10}")
    print("=" * 60)
    for m in all_metrics:
        print(
            f"{m['stock_code']:<10} "
            f"{m['total_count']:>10} "
            f"{m['match_rate']:>9.2f}% "
            f"{m['avg_diff_close_pct']:>9.3f}% "
            f"{m['anomaly_count']:>10}"
        )

    # 이상치 상세
    anomalies = [r for r in all_results if r.is_anomaly]

    if anomalies:
        print(f"\n⚠️  이상치 발견: {len(anomalies)}건")
        print(f"{'종목코드':<10} {'날짜':<12} {'차이':>10} {'가격':<30}")
        print("=" * 70)
        for a in anomalies[:10]:  # 최대 10건만 표시
            print(
                f"{a.stock_code:<10} "
                f"{str(a.date):<12} "
                f"{a.diff_close_pct:>9.2f}% "
                f"FDR={a.fdr_close:,.0f}, KIS={a.kis_close:,.0f}"
            )

        if len(anomalies) > 10:
            print(f"\n... 외 {len(anomalies) - 10}건 더 있음")

    # 승인 기준 체크
    print("\n" + "=" * 80)
    print("승인 기준 체크")
    print("=" * 80)

    criteria = {
        "일치율 ≥99.5%": total_metrics['match_rate'] >= 99.5,
        "평균 오차 ≤0.1%": total_metrics['avg_diff_close_pct'] <= 0.1,
        "이상치 ≤0.5%": total_metrics['anomaly_rate'] <= 0.5
    }

    for criterion, passed in criteria.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{criterion}: {status}")

    all_passed = all(criteria.values())

    if all_passed:
        print("\n🎉 모든 승인 기준 통과! KIS API 데이터 사용 승인.")
    else:
        print("\n⚠️  일부 기준 미달. 추가 검토 필요.")

    print("\n" + "=" * 80)

    return all_passed


if __name__ == "__main__":
    success = validate_kis_data()
    exit(0 if success else 1)
