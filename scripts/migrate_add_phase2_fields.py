"""
Phase 2 필드 추가 마이그레이션 스크립트

predictions 테이블에 Phase 2 개선사항 필드를 추가합니다:
- short_term: 단기 예측 (T+1일)
- medium_term: 중기 예측 (T+3일)
- long_term: 장기 예측 (T+5일)
- confidence_breakdown: 신뢰도 구성 요소 (JSON)
- pattern_analysis: 패턴 분석 통계 (JSON)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from backend.db.session import SessionLocal, engine


def migrate():
    """마이그레이션 실행"""
    db = SessionLocal()

    try:
        print("Phase 2 필드 추가 마이그레이션 시작...")

        # 1. short_term 컬럼 추가
        try:
            db.execute(text(
                "ALTER TABLE predictions ADD COLUMN short_term TEXT"
            ))
            print("✅ short_term 컬럼 추가 완료")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("⏭️  short_term 컬럼 이미 존재")
            else:
                raise

        # 2. medium_term 컬럼 추가
        try:
            db.execute(text(
                "ALTER TABLE predictions ADD COLUMN medium_term TEXT"
            ))
            print("✅ medium_term 컬럼 추가 완료")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("⏭️  medium_term 컬럼 이미 존재")
            else:
                raise

        # 3. long_term 컬럼 추가
        try:
            db.execute(text(
                "ALTER TABLE predictions ADD COLUMN long_term TEXT"
            ))
            print("✅ long_term 컬럼 추가 완료")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("⏭️  long_term 컬럼 이미 존재")
            else:
                raise

        # 4. confidence_breakdown 컬럼 추가 (JSON)
        try:
            db.execute(text(
                "ALTER TABLE predictions ADD COLUMN confidence_breakdown JSON"
            ))
            print("✅ confidence_breakdown 컬럼 추가 완료")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("⏭️  confidence_breakdown 컬럼 이미 존재")
            else:
                raise

        # 5. pattern_analysis 컬럼 추가 (JSON)
        try:
            db.execute(text(
                "ALTER TABLE predictions ADD COLUMN pattern_analysis JSON"
            ))
            print("✅ pattern_analysis 컬럼 추가 완료")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("⏭️  pattern_analysis 컬럼 이미 존재")
            else:
                raise

        db.commit()
        print("\n✅ 마이그레이션 성공!")

        # 테이블 구조 확인
        result = db.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'predictions' ORDER BY ordinal_position"))
        print("\n현재 predictions 테이블 구조:")
        for row in result:
            print(f"  - {row[0]}: {row[1]}")

    except Exception as e:
        db.rollback()
        print(f"\n❌ 마이그레이션 실패: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
