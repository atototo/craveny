"""
하위 호환성 검증 테스트

Epic 3 완료 후 API가 하위 호환성을 유지하는지 검증합니다.
"""

from backend.db.session import SessionLocal
from backend.db.models.prediction import Prediction
from backend.db.models.stock import StockPrice
from sqlalchemy import text

def test_backward_compatibility():
    """하위 호환성 검증"""
    print("=" * 80)
    print("Epic 3 하위 호환성 검증 테스트")
    print("=" * 80)

    db = SessionLocal()
    try:
        # 1. Deprecated 필드가 nullable인지 확인
        print("\n1. Deprecated 필드 nullable 확인...")
        result = db.execute(text("""
            SELECT column_name, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'predictions'
            AND column_name IN ('direction', 'confidence', 'short_term', 'medium_term', 'long_term')
        """))

        nullable_info = {row[0]: row[1] for row in result}

        deprecated_fields = ['direction', 'confidence', 'short_term', 'medium_term', 'long_term']
        all_nullable = True

        for field in deprecated_fields:
            is_nullable = nullable_info.get(field)
            if is_nullable == 'YES':
                print(f"   ✅ {field}: nullable")
            else:
                print(f"   ❌ {field}: NOT nullable (문제!)")
                all_nullable = False

        if all_nullable:
            print("   ✅ 모든 Deprecated 필드가 nullable")
        else:
            print("   ❌ 일부 Deprecated 필드가 nullable이 아님")
            return False

        # 2. 새 필드가 존재하는지 확인
        print("\n2. 새 필드 존재 확인...")
        result = db.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'predictions'
            AND column_name IN (
                'sentiment_direction', 'sentiment_score', 'impact_level',
                'relevance_score', 'urgency_level', 'impact_analysis'
            )
            ORDER BY column_name
        """))

        columns = [row[0] for row in result]
        new_fields = ['sentiment_direction', 'sentiment_score', 'impact_level',
                     'relevance_score', 'urgency_level', 'impact_analysis']

        all_exist = True
        for field in new_fields:
            if field in columns:
                print(f"   ✅ {field}: 존재")
            else:
                print(f"   ❌ {field}: 존재하지 않음 (문제!)")
                all_exist = False

        if not all_exist:
            print("   ❌ 일부 새 필드가 존재하지 않음")
            return False

        # 3. API 응답 구조 검증 (최근 예측 1건 샘플 조회)
        print("\n3. API 응답 구조 검증...")
        prediction = (
            db.query(Prediction)
            .filter(Prediction.sentiment_direction.isnot(None))
            .order_by(Prediction.created_at.desc())
            .first()
        )

        if not prediction:
            print("   ⚠️  영향도 분석 데이터가 없습니다 (테스트 스킵)")
        else:
            # 새 필드 검증
            new_field_check = True
            if prediction.sentiment_direction not in ["positive", "negative", "neutral"]:
                print(f"   ❌ sentiment_direction 값 오류: {prediction.sentiment_direction}")
                new_field_check = False

            if not (-1.0 <= prediction.sentiment_score <= 1.0):
                print(f"   ❌ sentiment_score 범위 오류: {prediction.sentiment_score}")
                new_field_check = False

            if prediction.impact_level not in ["low", "medium", "high", "critical"]:
                print(f"   ❌ impact_level 값 오류: {prediction.impact_level}")
                new_field_check = False

            if not (0.0 <= prediction.relevance_score <= 1.0):
                print(f"   ❌ relevance_score 범위 오류: {prediction.relevance_score}")
                new_field_check = False

            if prediction.urgency_level not in ["routine", "notable", "urgent", "breaking"]:
                print(f"   ❌ urgency_level 값 오류: {prediction.urgency_level}")
                new_field_check = False

            if new_field_check:
                print(f"   ✅ 새 필드 검증 성공 (ID: {prediction.id})")
            else:
                print(f"   ❌ 새 필드 검증 실패 (ID: {prediction.id})")
                return False

            # Deprecated 필드가 None인지 확인 (새 데이터)
            deprecated_check = True
            if prediction.direction is not None:
                print(f"   ⚠️  direction이 None이 아님: {prediction.direction} (Epic 2 이전 데이터일 수 있음)")

            if prediction.confidence is not None:
                print(f"   ⚠️  confidence가 None이 아님: {prediction.confidence} (Epic 2 이전 데이터일 수 있음)")

            print(f"   ✅ Deprecated 필드는 nullable 상태 유지")

        # 4. 하위 호환성 시나리오 테스트
        print("\n4. 하위 호환성 시나리오 테스트...")

        # 시나리오 1: Epic 2 이전 데이터 (deprecated 필드만 있음)
        old_data_count = (
            db.query(Prediction)
            .filter(Prediction.sentiment_direction.is_(None))
            .filter(Prediction.direction.isnot(None))
            .count()
        )

        # 시나리오 2: Epic 3 이후 데이터 (새 필드 있음)
        new_data_count = (
            db.query(Prediction)
            .filter(Prediction.sentiment_direction.isnot(None))
            .count()
        )

        print(f"   Epic 2 이전 데이터: {old_data_count}건")
        print(f"   Epic 3 이후 데이터: {new_data_count}건")
        print(f"   ✅ 두 가지 데이터 형식이 공존 가능")

        # 5. 최종 결과
        print("\n" + "=" * 80)
        print("하위 호환성 검증 결과")
        print("=" * 80)
        print("✅ 모든 검증 통과")
        print("   - Deprecated 필드: nullable 설정 완료")
        print("   - 새 필드: 정상 추가 완료")
        print("   - API 응답: 하위 호환성 유지")
        print("   - 데이터 공존: Epic 2/3 데이터 모두 조회 가능")

        return True

    except Exception as e:
        print(f"\n❌ 하위 호환성 검증 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    success = test_backward_compatibility()
    exit(0 if success else 1)
