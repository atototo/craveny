"""
일일 데이터 검증 리포트 스크립트

매일 자동 실행되어 FDR vs KIS 데이터 품질을 검증하고 리포트를 생성합니다.

Usage:
    uv run python scripts/daily_validation_report.py [--days N]

Scheduling (cron):
    0 16 * * 1-5  cd /path/to/craveny && uv run python scripts/daily_validation_report.py
    (장 마감 후 16:00, 평일만 실행)
"""
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
import argparse

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.validators.kis_validator import get_validator
from backend.db.session import SessionLocal
from backend.db.models.stock import Stock, StockPrice


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_stocks_with_data(db, start_date, end_date) -> List[str]:
    """
    검증 가능한 종목 리스트 조회 (FDR과 KIS 둘 다 있는 종목)

    Args:
        db: DB 세션
        start_date: 시작 날짜
        end_date: 종료 날짜

    Returns:
        종목 코드 리스트
    """
    # FDR 데이터가 있는 종목
    fdr_stocks = set(
        row[0] for row in
        db.query(StockPrice.stock_code)
        .filter(
            StockPrice.source.in_(["FDR", "fdr"]),
            StockPrice.date >= start_date,
            StockPrice.date <= end_date
        )
        .distinct()
    )

    # KIS 데이터가 있는 종목
    kis_stocks = set(
        row[0] for row in
        db.query(StockPrice.stock_code)
        .filter(
            StockPrice.source.in_(["KIS", "kis"]),
            StockPrice.date >= start_date,
            StockPrice.date <= end_date
        )
        .distinct()
    )

    # 공통 종목
    common_stocks = sorted(list(fdr_stocks & kis_stocks))

    logger.info(f"검증 가능한 종목 수: {len(common_stocks)}개")
    logger.info(f"  - FDR only: {len(fdr_stocks - kis_stocks)}개")
    logger.info(f"  - KIS only: {len(kis_stocks - fdr_stocks)}개")
    logger.info(f"  - 공통: {len(common_stocks)}개")

    return common_stocks


def run_daily_validation(days: int = 1) -> Dict:
    """
    일일 검증 실행

    Args:
        days: 검증 기간 (일)

    Returns:
        검증 결과 딕셔너리
    """
    logger.info("\n" + "="*80)
    logger.info(f"일일 데이터 검증 리포트 ({datetime.now().strftime('%Y-%m-%d')})")
    logger.info("="*80 + "\n")

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    logger.info(f"검증 기간: {start_date} ~ {end_date}")

    db = SessionLocal()
    validator = get_validator(db=db)

    try:
        # 검증 가능한 종목 조회
        stock_codes = get_stocks_with_data(db, start_date, end_date)

        if not stock_codes:
            logger.error("\n❌ 검증 가능한 데이터가 없습니다.")
            logger.error("   FDR과 KIS 데이터를 모두 수집했는지 확인하세요.")
            return {
                "status": "no_data",
                "date": end_date.isoformat()
            }

        # 전체 종목 검증
        all_results = []
        stock_metrics = []

        logger.info(f"\n검증 시작: {len(stock_codes)}개 종목\n")

        for i, stock_code in enumerate(stock_codes, 1):
            logger.info(f"[{i}/{len(stock_codes)}] {stock_code} 검증 중...")

            results = validator.validate_stock(stock_code, start_date, end_date)

            if not results:
                logger.warning(f"  ⚠️  {stock_code}: 비교할 데이터 없음")
                continue

            all_results.extend(results)

            # 종목별 메트릭
            metrics = validator.calculate_metrics(results)
            metrics["stock_code"] = stock_code
            stock_metrics.append(metrics)

            logger.info(
                f"  일치율: {metrics['match_rate']:.2f}%, "
                f"평균 차이: {metrics['avg_diff_close_pct']:.3f}%"
            )

        # 전체 통계
        if not all_results:
            logger.error("\n❌ 검증 결과가 없습니다.")
            return {
                "status": "no_results",
                "date": end_date.isoformat()
            }

        total_metrics = validator.calculate_metrics(all_results)

        # 결과 리포트 출력
        print_validation_report(
            total_metrics=total_metrics,
            stock_metrics=stock_metrics,
            all_results=all_results,
            start_date=start_date,
            end_date=end_date
        )

        # 승인 기준 체크
        approval_status = check_approval_criteria(total_metrics)

        return {
            "status": "success",
            "date": end_date.isoformat(),
            "total_metrics": total_metrics,
            "stock_count": len(stock_codes),
            "approval": approval_status
        }

    finally:
        db.close()


def print_validation_report(
    total_metrics: Dict,
    stock_metrics: List[Dict],
    all_results: List,
    start_date,
    end_date
):
    """검증 결과 리포트 출력"""
    print("\n" + "="*80)
    print("📊 검증 결과 요약")
    print("="*80)

    print(f"\n기간: {start_date} ~ {end_date}")
    print(f"\n총 비교 건수: {total_metrics['total_count']}건")
    print(f"일치 건수: {total_metrics['match_count']}건")
    print(f"일치율: {total_metrics['match_rate']:.2f}%")
    print(f"이상치 건수: {total_metrics['anomaly_count']}건 ({total_metrics['anomaly_rate']:.2f}%)")
    print(f"평균 차이 (종가): {total_metrics['avg_diff_close_pct']:.3f}%")
    print(
        f"최대 차이: {total_metrics['max_diff_close_pct']:.2f}% "
        f"({total_metrics['max_diff_stock']} {total_metrics['max_diff_date']})"
    )

    # 종목별 결과 (상위 10개 + 하위 5개)
    stock_metrics_sorted = sorted(stock_metrics, key=lambda x: x['match_rate'], reverse=True)

    print(f"\n📈 종목별 검증 결과 (상위 10개):")
    print(f"{'종목코드':<10} {'비교 건수':>10} {'일치율':>10} {'평균 차이':>10} {'이상치':>10}")
    print("="*60)
    for m in stock_metrics_sorted[:10]:
        print(
            f"{m['stock_code']:<10} "
            f"{m['total_count']:>10} "
            f"{m['match_rate']:>9.2f}% "
            f"{m['avg_diff_close_pct']:>9.3f}% "
            f"{m['anomaly_count']:>10}"
        )

    # 일치율 낮은 종목
    low_match_stocks = [m for m in stock_metrics if m['match_rate'] < 95.0]
    if low_match_stocks:
        print(f"\n⚠️  일치율 95% 미만 종목 ({len(low_match_stocks)}개):")
        print(f"{'종목코드':<10} {'비교 건수':>10} {'일치율':>10} {'평균 차이':>10}")
        print("="*50)
        for m in sorted(low_match_stocks, key=lambda x: x['match_rate'])[:10]:
            print(
                f"{m['stock_code']:<10} "
                f"{m['total_count']:>10} "
                f"{m['match_rate']:>9.2f}% "
                f"{m['avg_diff_close_pct']:>9.3f}%"
            )

    # 이상치 상세
    anomalies = [r for r in all_results if r.is_anomaly]
    if anomalies:
        print(f"\n🚨 이상치 발견: {len(anomalies)}건")
        print(f"{'종목코드':<10} {'날짜':<12} {'차이':>10} {'가격':<30}")
        print("="*70)
        for a in sorted(anomalies, key=lambda x: x.diff_close_pct, reverse=True)[:10]:
            print(
                f"{a.stock_code:<10} "
                f"{str(a.date):<12} "
                f"{a.diff_close_pct:>9.2f}% "
                f"FDR={a.fdr_close:,.0f}, KIS={a.kis_close:,.0f}"
            )

        if len(anomalies) > 10:
            print(f"\n... 외 {len(anomalies) - 10}건 더 있음")


def check_approval_criteria(metrics: Dict) -> Dict:
    """
    승인 기준 체크

    Args:
        metrics: 전체 검증 메트릭

    Returns:
        승인 기준 체크 결과
    """
    print("\n" + "="*80)
    print("✅ 승인 기준 체크")
    print("="*80)

    criteria = {
        "일치율 ≥99.5%": {
            "passed": metrics['match_rate'] >= 99.5,
            "value": f"{metrics['match_rate']:.2f}%",
            "threshold": "99.5%"
        },
        "평균 오차 ≤0.1%": {
            "passed": metrics['avg_diff_close_pct'] <= 0.1,
            "value": f"{metrics['avg_diff_close_pct']:.3f}%",
            "threshold": "0.1%"
        },
        "이상치 ≤0.5%": {
            "passed": metrics['anomaly_rate'] <= 0.5,
            "value": f"{metrics['anomaly_rate']:.2f}%",
            "threshold": "0.5%"
        }
    }

    all_passed = True

    for criterion_name, criterion_data in criteria.items():
        status = "✅ PASS" if criterion_data["passed"] else "❌ FAIL"
        print(f"{criterion_name}: {status} (현재: {criterion_data['value']})")

        if not criterion_data["passed"]:
            all_passed = False

    print("="*80)

    if all_passed:
        print("\n🎉 모든 승인 기준 통과! KIS API 데이터 품질 양호.")
    else:
        print("\n⚠️  일부 기준 미달. 추가 모니터링 필요.")

    print("\n" + "="*80 + "\n")

    return {
        "all_passed": all_passed,
        "criteria": criteria
    }


def save_report_to_file(result: Dict):
    """
    검증 결과를 파일로 저장

    Args:
        result: 검증 결과
    """
    report_dir = Path(__file__).parent.parent / "logs" / "validation_reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    report_file = report_dir / f"validation_{result['date']}.txt"

    # TODO: 파일 저장 구현 (향후 필요시)
    logger.info(f"리포트 저장 위치: {report_file}")


def main():
    """메인 실행"""
    parser = argparse.ArgumentParser(description="일일 데이터 검증 리포트")
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="검증 기간 (일) - 기본값: 1"
    )

    args = parser.parse_args()

    try:
        result = run_daily_validation(days=args.days)

        if result["status"] == "success":
            logger.info("✅ 일일 검증 완료")
            exit(0)
        else:
            logger.error(f"❌ 일일 검증 실패: {result['status']}")
            exit(1)

    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}")
        raise


if __name__ == "__main__":
    main()
