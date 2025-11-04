# 멀티모델 A/B 테스트 시스템 구현 완료

## 개요

기존의 하드코딩된 A/B 테스트 시스템을 동적 멀티모델 관리 시스템으로 전환했습니다.

### 주요 변경 사항

1. **동적 모델 관리**: 환경변수 대신 데이터베이스 기반 모델 관리
2. **멀티모델 예측**: 모든 활성 모델이 동시에 예측 생성
3. **즉시 모델 전환**: A/B 설정 변경 시 재생성 없이 즉시 적용
4. **데이터 영속성**: 모든 모델의 예측 결과를 DB에 저장

## 시스템 아키텍처

### 데이터베이스 스키마

```sql
-- 모델 관리 테이블
CREATE TABLE models (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model_identifier VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 모델별 예측 결과 테이블
CREATE TABLE model_predictions (
    id SERIAL PRIMARY KEY,
    news_id INTEGER NOT NULL REFERENCES news_articles(id) ON DELETE CASCADE,
    model_id INTEGER NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    stock_code VARCHAR(10) NOT NULL,
    prediction_data JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(news_id, model_id)
);

-- A/B 설정 테이블
CREATE TABLE ab_test_config (
    id SERIAL PRIMARY KEY,
    model_a_id INTEGER NOT NULL REFERENCES models(id),
    model_b_id INTEGER NOT NULL REFERENCES models(id),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 초기 데이터

4개의 모델이 자동으로 생성됩니다:
- GPT-4o (OpenAI)
- DeepSeek V3.2 (OpenRouter)
- Qwen 2.5 72B (OpenRouter)
- Claude 3.5 Sonnet (OpenRouter)

기본 A/B 설정: GPT-4o vs DeepSeek V3.2

## API 엔드포인트

### 모델 관리 API

#### 1. 모델 목록 조회
```bash
GET /api/models?active_only=true
```

**응답 예시:**
```json
[
  {
    "id": 1,
    "name": "GPT-4o",
    "provider": "openai",
    "model_identifier": "gpt-4o",
    "is_active": true,
    "description": "OpenAI GPT-4 Optimized model",
    "created_at": "2025-01-15T10:00:00"
  }
]
```

#### 2. 모델 추가
```bash
POST /api/models
Content-Type: application/json

{
  "name": "GPT-4 Turbo",
  "provider": "openai",
  "model_identifier": "gpt-4-turbo",
  "description": "Latest GPT-4 Turbo model"
}
```

#### 3. 모델 활성화/비활성화 토글
```bash
PATCH /api/models/{model_id}/toggle
```

#### 4. 모델 삭제
```bash
DELETE /api/models/{model_id}
```

### A/B 설정 API

#### 1. 현재 A/B 설정 조회
```bash
GET /api/ab-test/config
```

**응답 예시:**
```json
{
  "id": 1,
  "model_a": {
    "id": 1,
    "name": "GPT-4o",
    "provider": "openai",
    "model_identifier": "gpt-4o"
  },
  "model_b": {
    "id": 2,
    "name": "DeepSeek V3.2",
    "provider": "openrouter",
    "model_identifier": "deepseek/deepseek-v3.2-exp"
  },
  "is_active": true,
  "created_at": "2025-01-15T10:00:00"
}
```

#### 2. A/B 설정 변경
```bash
POST /api/ab-test/config
Content-Type: application/json

{
  "model_a_id": 1,
  "model_b_id": 3
}
```

#### 3. A/B 설정 이력 조회
```bash
GET /api/ab-test/history
```

## 백엔드 구현

### StockPredictor 클래스 주요 메서드

#### 1. `predict_all_models(current_news, similar_news, news_id)`
모든 활성 모델로 예측을 생성하고 DB에 저장합니다.

```python
def predict_all_models(
    self,
    current_news: Dict[str, Any],
    similar_news: List[Dict[str, Any]],
    news_id: int
) -> Dict[int, Dict[str, Any]]:
    """
    모든 활성 모델로 예측을 생성하고 DB에 저장합니다.

    Returns:
        {model_id: prediction_data}
    """
```

**특징:**
- 모든 활성 모델을 순회하며 예측 생성
- UPSERT 패턴으로 중복 방지
- 실패한 모델이 있어도 계속 진행

#### 2. `get_ab_predictions(news_id)`
현재 A/B 설정에 따라 두 모델의 예측을 조회합니다.

```python
def get_ab_predictions(self, news_id: int) -> Dict[str, Any]:
    """
    현재 A/B 설정에 따라 두 모델의 예측을 조회합니다.

    Returns:
        {
            "ab_test_enabled": True,
            "model_a": {...},
            "model_b": {...},
            "comparison": {
                "agreement": "상승" | "하락" | "불일치",
                "confidence_diff": 15.5
            }
        }
    """
```

**특징:**
- DB에서 저장된 예측 조회 (재생성 불필요)
- 텔레그램 알림 호환성 유지
- 두 모델 간 비교 데이터 자동 생성

### 알림 시스템 통합

`backend/notifications/auto_notify.py`에서 자동 예측 및 알림 전송:

```python
# 1. 모든 활성 모델로 예측 생성
all_predictions = predictor.predict_all_models(
    current_news=current_news_data,
    similar_news=similar_news,
    news_id=news.id,
)

# 2. A/B 설정에 따라 표시할 두 모델 예측 조회
prediction = predictor.get_ab_predictions(news_id=news.id)

# 3. 텔레그램 알림 전송
if notifier.send_prediction(
    news_title=news.title,
    stock_code=news.stock_code,
    prediction=prediction,
):
    news.notified_at = datetime.utcnow()
    db.commit()
```

## 프론트엔드 UI

### 1. 모델 관리 페이지 (`/models`)

**기능:**
- 등록된 모델 목록 확인
- 새 모델 추가 (이름, 프로바이더, 모델 식별자, 설명)
- 모델 활성화/비활성화 토글
- 모델 삭제

**파일:** `frontend/app/models/page.tsx`

### 2. A/B 설정 페이지 (`/ab-config`)

**기능:**
- 현재 A/B 설정 확인
- Model A, Model B 선택 (드롭다운)
- A/B 설정 변경
- 설정 변경 이력 확인

**파일:** `frontend/app/ab-config/page.tsx`

### 3. 네비게이션 메뉴

새로 추가된 메뉴 항목:
- 🤖 모델 관리 (`/models`)
- 🔬 A/B 설정 (`/ab-config`)

**파일:** `frontend/app/components/Navigation.tsx`

## 동작 흐름

### 1. 뉴스 수집 및 예측 생성

```
새 뉴스 저장
    ↓
auto_notify.py 실행 (15분 간격)
    ↓
predictor.predict_all_models() 호출
    ↓
모든 활성 모델로 예측 생성 (병렬 처리)
    ↓
model_predictions 테이블에 저장 (UPSERT)
    ↓
predictor.get_ab_predictions() 호출
    ↓
현재 A/B 설정에 따라 두 모델 예측 조회
    ↓
텔레그램 알림 전송 (A vs B 비교)
```

### 2. 모델 추가 시나리오

```
웹 UI에서 새 모델 추가
    ↓
POST /api/models
    ↓
models 테이블에 INSERT (is_active=true)
    ↓
predictor._load_active_models() 재실행 (다음 예측 시)
    ↓
새 모델 포함하여 예측 생성 시작
```

### 3. A/B 설정 변경 시나리오

```
웹 UI에서 A/B 설정 변경
    ↓
POST /api/ab-test/config
    ↓
기존 활성 설정 is_active=false
    ↓
새 설정 INSERT (is_active=true)
    ↓
다음 알림부터 새 A/B 모델로 전송
    ↓
기존 예측 데이터 재사용 (재생성 불필요)
```

## 테스트 결과

### 통합 테스트

```bash
uv run python scripts/test_integration.py
```

**결과:**
```
✅ PASS: 모델 로딩
✅ PASS: A/B 설정
✅ PASS: Predictor 메서드
✅ PASS: 데이터베이스 스키마

총 4개 테스트 중 4개 통과 (100.0%)
🎉 모든 테스트 통과!
```

### API 테스트

#### 모델 목록 조회
```bash
curl http://localhost:8000/api/models
```
✅ 4개 모델 정상 반환

#### A/B 설정 조회
```bash
curl http://localhost:8000/api/ab-test/config
```
✅ 활성 설정 정상 반환 (GPT-4o vs DeepSeek V3.2)

## 성능 최적화

### 1. UPSERT 패턴
```sql
INSERT INTO model_predictions (news_id, model_id, stock_code, prediction_data)
VALUES (:news_id, :model_id, :stock_code, :prediction_data)
ON CONFLICT (news_id, model_id)
DO UPDATE SET prediction_data = EXCLUDED.prediction_data, created_at = NOW()
```

**효과:**
- 중복 예측 방지
- 동일 뉴스에 대한 재예측 시 UPDATE로 처리

### 2. 인덱스 최적화
```sql
CREATE INDEX idx_model_predictions_news_model ON model_predictions(news_id, model_id);
CREATE INDEX idx_model_predictions_created ON model_predictions(created_at DESC);
```

**효과:**
- 예측 조회 속도 향상
- A/B 비교 성능 개선

### 3. 싱글톤 패턴
```python
@lru_cache(maxsize=1)
def get_predictor() -> "StockPredictor":
    return StockPredictor()
```

**효과:**
- 모델 클라이언트 재사용
- 메모리 효율성 향상

## 마이그레이션 가이드

### 기존 시스템에서 전환

1. **DB 마이그레이션 실행**
```bash
uv run python scripts/migrate_add_dynamic_ab_test.py
```

2. **환경변수 제거** (선택사항)
```bash
# .env에서 제거 가능 (하위 호환성 유지)
# MODEL_A_PROVIDER=openai
# MODEL_A_NAME=gpt-4o
# MODEL_B_PROVIDER=openrouter
# MODEL_B_NAME=deepseek/deepseek-v3.2-exp
```

3. **백엔드 재시작**
```bash
uv run uvicorn backend.main:app --reload
```

4. **프론트엔드 재시작**
```bash
cd frontend && npm run dev
```

## 운영 가이드

### 새 모델 추가 방법

1. 웹 UI에서 `/models` 페이지 접속
2. "➕ 모델 추가" 버튼 클릭
3. 모델 정보 입력:
   - 모델 이름: 예) "GPT-4 Turbo"
   - 프로바이더: "openai" 또는 "openrouter"
   - 모델 식별자: 예) "gpt-4-turbo"
   - 설명: (선택사항)
4. "추가하기" 버튼 클릭

### A/B 테스트 모델 변경 방법

1. 웹 UI에서 `/ab-config` 페이지 접속
2. Model A 선택 드롭다운에서 원하는 모델 선택
3. Model B 선택 드롭다운에서 원하는 모델 선택
4. "A/B 설정 변경" 버튼 클릭
5. 다음 알림부터 새 설정 적용

### 모델 비활성화 방법

1. 웹 UI에서 `/models` 페이지 접속
2. 비활성화할 모델의 "✓ 활성" 버튼 클릭
3. 상태가 "○ 비활성"으로 변경
4. 해당 모델은 더 이상 예측 생성하지 않음

## 주의사항

### 1. A/B 설정 변경 시
- 두 모델은 서로 달라야 합니다
- 비활성화된 모델은 선택할 수 없습니다
- 변경 즉시 다음 알림부터 적용됩니다

### 2. 모델 삭제 시
- 해당 모델의 모든 예측 데이터가 삭제됩니다 (CASCADE)
- 현재 A/B 설정에 포함된 모델은 삭제할 수 없습니다
- 삭제 전 확인 메시지가 표시됩니다

### 3. 모델 비활성화 시
- 비활성화된 모델은 새로운 예측을 생성하지 않습니다
- 기존 예측 데이터는 유지됩니다
- 언제든지 다시 활성화할 수 있습니다

## 트러블슈팅

### 문제: 모델이 예측을 생성하지 않음

**원인:**
- 모델이 비활성화 상태
- API 키가 올바르지 않음
- 네트워크 연결 문제

**해결방법:**
```bash
# 1. 모델 상태 확인
curl http://localhost:8000/api/models

# 2. 로그 확인
tail -f logs/app.log

# 3. 환경변수 확인
echo $OPENAI_API_KEY
echo $OPENROUTER_API_KEY
```

### 문제: A/B 설정 변경이 적용되지 않음

**원인:**
- 캐시 문제
- DB 연결 오류

**해결방법:**
```bash
# 1. 백엔드 재시작
pkill -f uvicorn
uv run uvicorn backend.main:app --reload

# 2. DB 설정 확인
uv run python -c "from backend.db.models.ab_test_config import ABTestConfig; from backend.db.session import SessionLocal; db = SessionLocal(); print(db.query(ABTestConfig).filter(ABTestConfig.is_active == True).first())"
```

## 향후 개선 사항

### 1. 모델 성능 추적
- 각 모델의 예측 정확도 추적
- 모델별 승률 통계
- 최적 모델 자동 추천

### 2. 배치 처리 최적화
- 여러 뉴스에 대한 예측을 배치로 처리
- 병렬 처리로 성능 향상

### 3. 모델 앙상블
- 여러 모델의 예측을 조합
- 가중치 기반 최종 예측

### 4. 실시간 모델 성능 모니터링
- 대시보드에 모델별 통계 표시
- 응답 시간, 오류율 추적

## 참고 문서

- [MULTI_MODEL_DESIGN.md](./MULTI_MODEL_DESIGN.md) - 초기 설계 문서
- [backend/db/models/model.py](../backend/db/models/model.py) - Model 스키마
- [backend/db/models/ab_test_config.py](../backend/db/models/ab_test_config.py) - ABTestConfig 스키마
- [backend/llm/predictor.py](../backend/llm/predictor.py) - StockPredictor 구현
- [backend/api/models.py](../backend/api/models.py) - 모델 관리 API
- [backend/api/ab_test.py](../backend/api/ab_test.py) - A/B 설정 API

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2025-01-15 | 1.0 | 초기 구현 완료 |

---

**구현 완료일:** 2025-01-15
**작성자:** Claude Code
**상태:** ✅ Production Ready
