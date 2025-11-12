# Epic 1: 데이터 모델 변경

**Epic ID**: PRED-001
**상태**: Ready
**예상 기간**: 1일
**담당**: Backend Team

---

## 개요

Prediction 모델의 스키마를 변경하여 가격 예측 필드를 제거하고 영향도 분석 필드를 추가합니다.

---

## Story 목록

### Story 1.1: Prediction 모델 스키마 업데이트

**Story ID**: PRED-001-1
**우선순위**: P0 (Critical)
**예상 시간**: 2시간

#### 요구사항
- Prediction 모델에 새 필드 추가
- 기존 필드 이름 변경
- Deprecated 필드 표시

#### 상세 작업
1. `backend/db/models/prediction.py` 파일 수정
2. 새 필드 추가:
   - `sentiment_score`: Float, nullable=True
   - `impact_level`: String(20), nullable=True
   - `relevance_score`: Float, nullable=True
   - `urgency_level`: String(20), nullable=True
   - `impact_analysis`: JSON, nullable=True

3. 필드 이름 변경:
   - `direction` → `sentiment_direction`로 변경 (또는 별칭 추가)

4. Deprecated 필드 주석 추가:
   ```python
   # DEPRECATED: Will be removed in v2.0
   short_term = Column(Text, nullable=True)
   medium_term = Column(Text, nullable=True)
   long_term = Column(Text, nullable=True)
   confidence = Column(Float, nullable=True)
   confidence_breakdown = Column(JSON, nullable=True)
   ```

#### 완료 조건
- [ ] 모델 파일 수정 완료
- [ ] SQLAlchemy import 확인
- [ ] 타입 힌트 정확성 확인
- [ ] 주석 및 docstring 업데이트

#### 파일
- `backend/db/models/prediction.py`

---

### Story 1.2: 마이그레이션 스크립트 작성

**Story ID**: PRED-001-2
**우선순위**: P0 (Critical)
**예상 시간**: 3시간

#### 요구사항
- Alembic 마이그레이션 스크립트 작성
- 기존 데이터 변환 로직 포함
- 롤백 스크립트 작성

#### 상세 작업
1. Alembic 마이그레이션 생성
   ```bash
   uv run alembic revision --autogenerate -m "Add impact analysis fields to predictions"
   ```

2. 마이그레이션 스크립트 수정:
   - 새 컬럼 추가 (nullable=True)
   - 기존 컬럼 이름 변경
   - 데이터 변환 로직 추가

3. 데이터 변환 로직:
   ```python
   # direction → sentiment_direction 매핑
   # "up" → "positive"
   # "down" → "negative"
   # "hold" → "neutral"

   # confidence → sentiment_score 변환
   # 0-100 → -1.0 to 1.0 (방향 고려)
   # up이면 positive, down이면 negative로 변환

   # impact_level 기본값 설정
   # confidence > 70: "high"
   # confidence 50-70: "medium"
   # confidence < 50: "low"
   ```

4. 롤백 스크립트 작성:
   ```python
   def downgrade():
       # 새 컬럼 삭제
       # 컬럼 이름 원복
   ```

#### 완료 조건
- [ ] 마이그레이션 스크립트 생성
- [ ] 데이터 변환 로직 구현
- [ ] 롤백 스크립트 작성
- [ ] 스테이징 DB에서 테스트 성공

#### 파일
- `backend/alembic/versions/xxxx_add_impact_analysis_fields.py` (생성)

---

### Story 1.3: 기존 데이터 마이그레이션 실행

**Story ID**: PRED-001-3
**우선순위**: P0 (Critical)
**예상 시간**: 2시간

#### 요구사항
- 프로덕션 DB 백업
- 마이그레이션 실행
- 데이터 무결성 검증

#### 상세 작업
1. DB 백업
   ```bash
   # PostgreSQL 백업
   pg_dump -h localhost -U user -d craveny > backup_before_migration.sql
   ```

2. 스테이징 환경 마이그레이션
   ```bash
   uv run alembic upgrade head
   ```

3. 데이터 검증 쿼리 실행:
   ```sql
   -- 전체 레코드 수 확인
   SELECT COUNT(*) FROM predictions;

   -- 새 필드 null 개수 확인
   SELECT
     COUNT(*) as total,
     COUNT(sentiment_score) as has_sentiment_score,
     COUNT(impact_level) as has_impact_level
   FROM predictions;

   -- direction → sentiment_direction 변환 확인
   SELECT
     direction,
     sentiment_direction,
     COUNT(*)
   FROM predictions
   GROUP BY direction, sentiment_direction;
   ```

4. 프로덕션 마이그레이션 (검증 후)

#### 완료 조건
- [ ] DB 백업 완료
- [ ] 스테이징 마이그레이션 성공
- [ ] 1164개 레코드 모두 마이그레이션 확인
- [ ] 데이터 변환 정확성 검증
- [ ] 프로덕션 마이그레이션 성공

#### 파일
- `scripts/verify_migration.sql` (생성)
- `scripts/rollback_migration.sql` (생성)

---

### Story 1.4: 데이터 무결성 검증

**Story ID**: PRED-001-4
**우선순위**: P1 (High)
**예상 시간**: 2시간

#### 요구사항
- 자동화된 검증 스크립트 작성
- 데이터 품질 확인
- 이상 데이터 리포트 생성

#### 상세 작업
1. 검증 스크립트 작성 (`scripts/verify_prediction_data.py`):
   ```python
   def verify_migration():
       """마이그레이션 후 데이터 검증"""
       db = SessionLocal()

       # 1. 전체 레코드 수 확인
       total = db.query(Prediction).count()
       assert total == 1164, f"Expected 1164, got {total}"

       # 2. sentiment_direction 변환 확인
       positive = db.query(Prediction).filter(
           Prediction.sentiment_direction == "positive"
       ).count()
       negative = db.query(Prediction).filter(
           Prediction.sentiment_direction == "negative"
       ).count()
       neutral = db.query(Prediction).filter(
           Prediction.sentiment_direction == "neutral"
       ).count()

       assert positive + negative + neutral == total

       # 3. sentiment_score 범위 확인
       invalid_scores = db.query(Prediction).filter(
           or_(
               Prediction.sentiment_score < -1.0,
               Prediction.sentiment_score > 1.0
           )
       ).count()

       assert invalid_scores == 0

       # 4. impact_level 값 확인
       valid_levels = ["low", "medium", "high", "critical"]
       invalid_levels = db.query(Prediction).filter(
           ~Prediction.impact_level.in_(valid_levels)
       ).count()

       assert invalid_levels == 0

       print("✅ 모든 검증 통과")
   ```

2. 이상 데이터 리포트 생성:
   ```python
   def generate_anomaly_report():
       """이상 데이터 리포트 생성"""
       # sentiment_score가 극단적인 경우 (< -0.9 or > 0.9)
       # relevance_score가 낮은 경우 (< 0.3)
       # impact_level과 sentiment_score 불일치
   ```

3. 실행 및 결과 확인:
   ```bash
   uv run python scripts/verify_prediction_data.py
   ```

#### 완료 조건
- [ ] 검증 스크립트 작성 완료
- [ ] 모든 검증 항목 통과
- [ ] 이상 데이터 리포트 생성
- [ ] 이상 데이터 < 1% (또는 수정 완료)

#### 파일
- `scripts/verify_prediction_data.py` (생성)
- `scripts/anomaly_report.md` (생성)

---

## Epic 완료 조건

- [ ] Story 1.1 완료 (모델 스키마 업데이트)
- [ ] Story 1.2 완료 (마이그레이션 스크립트)
- [ ] Story 1.3 완료 (데이터 마이그레이션 실행)
- [ ] Story 1.4 완료 (데이터 무결성 검증)
- [ ] 1164개 예측 데이터 100% 마이그레이션 성공
- [ ] 데이터 무결성 검증 통과
- [ ] 롤백 스크립트 준비 완료

---

## 리스크 및 대응

### 리스크 1: 마이그레이션 중 데이터 손실
- **확률**: Low
- **대응**: 전체 DB 백업, 스테이징 먼저 테스트, 롤백 스크립트 준비

### 리스크 2: 데이터 변환 오류
- **확률**: Medium
- **대응**: 변환 로직 철저히 테스트, 검증 스크립트 작성

### 리스크 3: 마이그레이션 시간 초과
- **확률**: Low (1164개 레코드)
- **대응**: 오프피크 시간에 실행, 트랜잭션 배치 처리

---

## 다음 Epic

Epic 1 완료 후 **Epic 2: Predictor 리팩토링** 시작
