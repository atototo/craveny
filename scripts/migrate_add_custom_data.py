"""
DB 마이그레이션: stock_analysis_summaries 테이블에 custom_data 컬럼 추가
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from backend.db.session import SessionLocal


def migrate():
    """custom_data 컬럼 추가"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("DB 마이그레이션: custom_data 컬럼 추가")
        print("=" * 80)

        # 1. 컬럼 존재 여부 확인
        result = db.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'stock_analysis_summaries'
            AND column_name = 'custom_data'
        """))

        if result.fetchone():
            print("\n✅ custom_data 컬럼이 이미 존재합니다.")
            return True

        # 2. 컬럼 추가
        print("\n📝 custom_data 컬럼 추가 중...")
        db.execute(text("""
            ALTER TABLE stock_analysis_summaries
            ADD COLUMN custom_data JSON NULL
        """))
        db.commit()

        print("✅ custom_data 컬럼 추가 완료!")
        print("\n" + "=" * 80)
        print("마이그레이션 성공")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n❌ 마이그레이션 실패: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
