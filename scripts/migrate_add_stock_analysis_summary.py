"""
StockAnalysisSummary 테이블 생성 마이그레이션

종목별 AI 투자 분석 요약을 캐싱하는 테이블을 추가합니다.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from backend.db.session import SessionLocal, engine
from backend.db.models.stock_analysis import StockAnalysisSummary
from backend.db.base import Base


def migrate():
    """마이그레이션 실행"""
    print("StockAnalysisSummary 테이블 생성 시작...")

    try:
        # 테이블 생성
        Base.metadata.create_all(bind=engine, tables=[StockAnalysisSummary.__table__])
        print("✅ stock_analysis_summaries 테이블 생성 완료")

        # 테이블 구조 확인
        db = SessionLocal()
        result = db.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'stock_analysis_summaries' ORDER BY ordinal_position"
        ))

        print("\n현재 stock_analysis_summaries 테이블 구조:")
        for row in result:
            print(f"  - {row[0]}: {row[1]}")

        db.close()
        print("\n✅ 마이그레이션 성공!")

    except Exception as e:
        print(f"\n❌ 마이그레이션 실패: {e}")
        raise


if __name__ == "__main__":
    migrate()
