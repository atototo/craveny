"""
FDR vs KIS 데이터 비교 스크립트

두 데이터 소스의 정확도를 비교하고 차이를 분석합니다.

Usage:
    uv run python scripts/compare_fdr_kis_data.py
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.db.models.stock import Stock, StockPrice


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def compare_stock_prices(
    stock_code: str,
    date: datetime,
    db: Session
) -> Dict:
    """
    특정 종목의 특정 날짜에 대해 FDR과 KIS 데이터를 비교

    Args:
        stock_code: 종목 코드
        date: 비교할 날짜
        db: DB 세션

    Returns:
        비교 결과 딕셔너리
    """
    # FDR 데이터 조회
    fdr_price = db.query(StockPrice).filter(
        and_(
            StockPrice.stock_code == stock_code,
            StockPrice.source == "fdr",
            StockPrice.date >= date.replace(hour=0, minute=0, second=0),
            StockPrice.date < date.replace(hour=23, minute=59, second=59)
        )
    ).first()

    # KIS 데이터 조회
    kis_price = db.query(StockPrice).filter(
        and_(
            StockPrice.stock_code == stock_code,
            StockPrice.source == "kis",
            StockPrice.date >= date.replace(hour=0, minute=0, second=0),
            StockPrice.date < date.replace(hour=23, minute=59, second=59)
        )
    ).first()

    if not fdr_price or not kis_price:
        return {
            "stock_code": stock_code,
            "date": date.date(),
            "has_fdr": fdr_price is not None,
            "has_kis": kis_price is not None,
            "status": "missing_data"
        }

    # 차이 계산
    close_diff = abs(fdr_price.close - kis_price.close)
    close_diff_pct = (close_diff / fdr_price.close) * 100 if fdr_price.close > 0 else 0

    volume_diff = abs(fdr_price.volume - kis_price.volume) if fdr_price.volume and kis_price.volume else 0
    volume_diff_pct = (volume_diff / fdr_price.volume) * 100 if fdr_price.volume and fdr_price.volume > 0 else 0

    # 일치 여부 판단 (종가 0.1% 이내, 거래량 1% 이내)
    is_close_match = close_diff_pct <= 0.1
    is_volume_match = volume_diff_pct <= 1.0
    is_perfect_match = is_close_match and is_volume_match

    return {
        "stock_code": stock_code,
        "date": date.date(),
        "has_fdr": True,
        "has_kis": True,
        "fdr_close": fdr_price.close,
        "kis_close": kis_price.close,
        "close_diff": close_diff,
        "close_diff_pct": close_diff_pct,
        "fdr_volume": fdr_price.volume,
        "kis_volume": kis_price.volume,
        "volume_diff": volume_diff,
        "volume_diff_pct": volume_diff_pct,
        "is_close_match": is_close_match,
        "is_volume_match": is_volume_match,
        "is_perfect_match": is_perfect_match,
        "status": "compared"
    }


def compare_recent_data(days: int = 7) -> Dict:
    """
    최근 N일간의 데이터를 비교

    Args:
        days: 비교할 일수

    Returns:
        비교 결과 요약
    """
    logger.info("=" * 80)
    logger.info(f"FDR vs KIS 데이터 비교 (최근 {days}일)")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 활성 종목 조회
        stocks = db.query(Stock).filter(Stock.is_active == True).all()
        stock_codes = [stock.code for stock in stocks]

        logger.info(f"비교 대상: {len(stock_codes)}개 종목")

        all_results = []
        perfect_matches = 0
        close_matches = 0
        mismatches = 0
        missing_data_count = 0

        # 날짜별로 비교
        for i in range(days):
            date = datetime.now() - timedelta(days=i)

            # 주말 스킵
            if date.weekday() >= 5:
                continue

            logger.info(f"\n📅 {date.date()} 비교 중...")

            day_results = []

            for stock_code in stock_codes:
                result = compare_stock_prices(stock_code, date, db)
                day_results.append(result)

                if result["status"] == "compared":
                    if result["is_perfect_match"]:
                        perfect_matches += 1
                    elif result["is_close_match"]:
                        close_matches += 1
                    else:
                        mismatches += 1
                        # 불일치 상세 로그
                        logger.warning(
                            f"  ⚠️  {stock_code}: "
                            f"종가 차이 {result['close_diff_pct']:.2f}%, "
                            f"거래량 차이 {result['volume_diff_pct']:.2f}%"
                        )
                else:
                    missing_data_count += 1

            all_results.extend(day_results)

            # 일별 요약
            day_compared = sum(1 for r in day_results if r["status"] == "compared")
            day_perfect = sum(1 for r in day_results if r.get("is_perfect_match", False))

            if day_compared > 0:
                day_accuracy = (day_perfect / day_compared) * 100
                logger.info(f"  완벽 일치: {day_perfect}/{day_compared}개 ({day_accuracy:.1f}%)")

        # 전체 요약
        total_compared = perfect_matches + close_matches + mismatches
        total_accuracy = (perfect_matches / total_compared * 100) if total_compared > 0 else 0
        close_accuracy = ((perfect_matches + close_matches) / total_compared * 100) if total_compared > 0 else 0

        summary = {
            "total_comparisons": len(all_results),
            "perfect_matches": perfect_matches,
            "close_matches": close_matches,
            "mismatches": mismatches,
            "missing_data": missing_data_count,
            "perfect_accuracy": total_accuracy,
            "close_accuracy": close_accuracy,
            "results": all_results
        }

        logger.info("\n" + "=" * 80)
        logger.info("📊 비교 결과 요약")
        logger.info("=" * 80)
        logger.info(f"전체 비교: {len(all_results)}건")
        logger.info(f"완벽 일치: {perfect_matches}건 ({total_accuracy:.1f}%)")
        logger.info(f"근사 일치: {close_matches}건")
        logger.info(f"불일치: {mismatches}건")
        logger.info(f"데이터 누락: {missing_data_count}건")
        logger.info(f"종가 정확도: {close_accuracy:.1f}% (0.1% 이내)")
        logger.info("=" * 80)

        return summary

    finally:
        db.close()


def find_largest_discrepancies(limit: int = 10) -> List[Dict]:
    """
    가장 큰 차이를 보이는 데이터 찾기

    Args:
        limit: 상위 N개

    Returns:
        차이가 큰 데이터 리스트
    """
    logger.info("\n" + "=" * 80)
    logger.info(f"🔍 최대 차이 분석 (상위 {limit}개)")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 최근 7일 데이터
        start_date = datetime.now() - timedelta(days=7)

        discrepancies = []

        # 활성 종목 조회
        stocks = db.query(Stock).filter(Stock.is_active == True).all()

        for stock in stocks:
            for i in range(7):
                date = datetime.now() - timedelta(days=i)

                # 주말 스킵
                if date.weekday() >= 5:
                    continue

                result = compare_stock_prices(stock.code, date, db)

                if result["status"] == "compared" and not result["is_perfect_match"]:
                    discrepancies.append({
                        "stock_code": stock.code,
                        "stock_name": stock.name,
                        "date": result["date"],
                        "close_diff_pct": result["close_diff_pct"],
                        "volume_diff_pct": result["volume_diff_pct"],
                        "fdr_close": result["fdr_close"],
                        "kis_close": result["kis_close"]
                    })

        # 종가 차이 기준 정렬
        discrepancies.sort(key=lambda x: x["close_diff_pct"], reverse=True)

        # 상위 N개 출력
        for i, disc in enumerate(discrepancies[:limit], 1):
            logger.info(
                f"{i}. {disc['stock_name']}({disc['stock_code']}) - {disc['date']}\n"
                f"   FDR 종가: {disc['fdr_close']:,}원, KIS 종가: {disc['kis_close']:,}원\n"
                f"   종가 차이: {disc['close_diff_pct']:.2f}%, "
                f"거래량 차이: {disc['volume_diff_pct']:.2f}%"
            )

        return discrepancies[:limit]

    finally:
        db.close()


def main():
    """메인 실행"""
    logger.info("\n🚀 FDR vs KIS 데이터 비교 시작\n")

    # 1. 최근 7일 데이터 비교
    summary = compare_recent_data(days=7)

    # 2. 최대 차이 분석
    discrepancies = find_largest_discrepancies(limit=10)

    logger.info("\n✅ 분석 완료!\n")

    # 결론
    if summary["perfect_accuracy"] >= 99.0:
        logger.info("🎉 FDR과 KIS 데이터가 99% 이상 일치합니다!")
    elif summary["close_accuracy"] >= 99.0:
        logger.info("✅ FDR과 KIS 데이터가 99% 이상 근사합니다 (0.1% 이내 차이)")
    else:
        logger.warning(f"⚠️  데이터 정확도: {summary['close_accuracy']:.1f}% - 추가 검증 필요")


if __name__ == "__main__":
    main()
