#!/usr/bin/env python
"""
JSON 파일에서 DB로 종목 데이터 마이그레이션

target_stocks.json의 모든 종목을 stocks 테이블로 이전합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
import logging
from datetime import datetime

from backend.db.session import SessionLocal, engine
from backend.db.base import Base
from backend.db.models.stock import Stock

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_tables():
    """테이블 생성"""
    logger.info("테이블 생성 중...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ 테이블 생성 완료")


def migrate_stocks_from_json():
    """JSON에서 종목 데이터를 DB로 마이그레이션"""
    logger.info("=" * 70)
    logger.info("🚀 종목 데이터 마이그레이션 시작")
    logger.info("=" * 70)

    # JSON 파일 읽기
    json_file = project_root / "data" / "target_stocks.json"

    if not json_file.exists():
        logger.error(f"❌ JSON 파일을 찾을 수 없습니다: {json_file}")
        return

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        stocks_data = data.get("stocks", [])

    logger.info(f"📊 JSON에서 {len(stocks_data)}개 종목 발견")
    logger.info("")

    # DB 세션
    db = SessionLocal()

    try:
        migrated_count = 0
        skipped_count = 0

        for stock_data in stocks_data:
            code = stock_data["code"]
            name = stock_data["name"]
            priority = stock_data.get("priority", 5)

            # 중복 체크
            existing = db.query(Stock).filter(Stock.code == code).first()

            if existing:
                logger.info(f"⏭️  {name} ({code}): 이미 존재 - 스킵")
                skipped_count += 1
                continue

            # 새 종목 추가
            stock = Stock(
                code=code,
                name=name,
                priority=priority,
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            db.add(stock)
            logger.info(f"✅ {name} ({code}): 우선순위 {priority} - 추가됨")
            migrated_count += 1

        # 커밋
        db.commit()

        # 결과 요약
        logger.info("")
        logger.info("=" * 70)
        logger.info("✅ 마이그레이션 완료")
        logger.info("=" * 70)
        logger.info(f"✨ 추가된 종목: {migrated_count}개")
        logger.info(f"⏭️  스킵된 종목: {skipped_count}개")
        logger.info(f"📊 전체 종목: {migrated_count + skipped_count}개")
        logger.info("")

        # 최종 DB 상태 확인
        total_stocks = db.query(Stock).count()
        active_stocks = db.query(Stock).filter(Stock.is_active == True).count()

        logger.info(f"💾 DB 저장 상태:")
        logger.info(f"   - 전체 종목: {total_stocks}개")
        logger.info(f"   - 활성 종목: {active_stocks}개")

    except Exception as e:
        logger.error(f"❌ 마이그레이션 실패: {e}", exc_info=True)
        db.rollback()

    finally:
        db.close()


def main():
    """메인 실행 함수"""
    # 테이블 생성
    create_tables()

    # 데이터 마이그레이션
    migrate_stocks_from_json()


if __name__ == "__main__":
    main()
