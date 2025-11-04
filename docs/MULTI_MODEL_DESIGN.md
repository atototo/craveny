# 다중 모델 관리 시스템 설계안

## 📋 개요

현재 하드코딩된 Model A/B 구조를 **동적 다중 모델 관리 시스템**으로 확장하여, 여러 LLM 모델을 유연하게 추가/비교/관리할 수 있도록 개선합니다.

## 🎯 목표

- ✅ **모델 동적 관리**: 코드 수정 없이 새 모델 추가/제거
- ✅ **데이터 축적**: 모든 활성 모델의 예측 이력 보존
- ✅ **유연한 A/B 테스트**: 웹에서 비교할 모델 쌍 자유롭게 선택
- ✅ **비용 최적화**: 중요도/우선순위에 따른 실행 제어
- ✅ **OpenRouter 중심**: OpenRouter를 통한 통합 관리

## 🏗️ 아키텍처 설계

### 1. 데이터베이스 구조

#### 1.1 models 테이블 (새 테이블)
```sql
CREATE TABLE models (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,           -- 예: "gpt-4o", "deepseek-v3", "qwen-max"
    provider VARCHAR(50) NOT NULL,               -- "openrouter" (통일)
    model_name VARCHAR(100) NOT NULL,            -- OpenRouter 모델 ID: "openai/gpt-4o", "deepseek/deepseek-chat"
    is_active BOOLEAN DEFAULT true,              -- 활성화 여부
    priority INTEGER DEFAULT 1,                  -- 1=실시간, 2=배치
    api_config JSONB,                            -- {"temperature": 0.7, "max_tokens": 4000} 등
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 초기 데이터
INSERT INTO models (name, provider, model_name, is_active, priority) VALUES
('gpt-4o', 'openrouter', 'openai/gpt-4o', true, 1),
('deepseek-v3', 'openrouter', 'deepseek/deepseek-chat', true, 1),
('qwen-max', 'openrouter', 'qwen/qwen-2.5-72b-instruct', true, 2);
```

#### 1.2 model_predictions 테이블 (새 테이블)
```sql
CREATE TABLE model_predictions (
    id SERIAL PRIMARY KEY,
    news_id INTEGER NOT NULL REFERENCES news(id) ON DELETE CASCADE,
    model_id INTEGER NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    stock_code VARCHAR(10) NOT NULL,
    prediction_data JSONB NOT NULL,              -- 전체 예측 결과 (direction, confidence, reasoning 등)
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(news_id, model_id)                    -- 같은 뉴스에 대해 모델당 1개 예측
);

CREATE INDEX idx_model_predictions_news ON model_predictions(news_id);
CREATE INDEX idx_model_predictions_model ON model_predictions(model_id);
CREATE INDEX idx_model_predictions_stock ON model_predictions(stock_code);
```

#### 1.3 ab_test_config 테이블 (새 테이블)
```sql
CREATE TABLE ab_test_config (
    id SERIAL PRIMARY KEY,
    model_a_id INTEGER NOT NULL REFERENCES models(id),
    model_b_id INTEGER NOT NULL REFERENCES models(id),
    is_active BOOLEAN DEFAULT false,             -- 현재 활성 설정
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT different_models CHECK (model_a_id != model_b_id)
);

-- 초기 데이터 (기존 GPT-4o vs DeepSeek)
INSERT INTO ab_test_config (model_a_id, model_b_id, is_active)
SELECT
    (SELECT id FROM models WHERE name = 'gpt-4o'),
    (SELECT id FROM models WHERE name = 'deepseek-v3'),
    true;
```

#### 1.4 stock_analysis_summaries 테이블 수정
```sql
-- 기존 custom_data 필드를 model_reports로 명확화
ALTER TABLE stock_analysis_summaries
RENAME COLUMN custom_data TO model_reports;

-- model_reports 구조:
{
  "gpt-4o": {
    "overall_summary": "...",
    "short_term_scenario": "...",
    "risk_factors": [...],
    ...
  },
  "deepseek-v3": {
    "overall_summary": "...",
    ...
  }
}
```

### 2. 실행 흐름

#### 2.1 뉴스 예측 생성 흐름
```
새 뉴스 수집 (crawler)
    ↓
auto_notify.py 트리거
    ↓
predict_all_models(news) 호출
    ↓
┌─────────────────────────────────────┐
│ 모든 활성 모델(is_active=true)에 대해 │
│ OpenRouter API 호출                  │
└─────────────────────────────────────┘
    ↓
model_predictions 테이블에 각각 저장
    ↓
get_active_ab_config() 조회
    ↓
Model A & Model B 예측만 가져와서 비교
    ↓
알림 발송 (텔레그램)
```

#### 2.2 종합 리포트 생성 흐름
```
스케줄러 트리거 (예: 매일 오전 9시)
    ↓
각 종목별로 generate_multi_model_report() 호출
    ↓
┌─────────────────────────────────────┐
│ 모든 활성 모델에 대해                │
│ 최근 20건 model_predictions 조회    │
│ → 종합 투자 리포트 생성              │
└─────────────────────────────────────┘
    ↓
stock_analysis_summaries.model_reports에 저장
{
  "gpt-4o": {...},
  "deepseek-v3": {...},
  "qwen-max": {...}
}
    ↓
웹에서는 A/B 설정된 모델만 표시
```

### 3. API 설계

#### 3.1 모델 관리 API
```python
# GET /api/models
# 모든 모델 목록 조회
Response: [
  {
    "id": 1,
    "name": "gpt-4o",
    "provider": "openrouter",
    "model_name": "openai/gpt-4o",
    "is_active": true,
    "priority": 1
  },
  ...
]

# POST /api/models
# 새 모델 추가
Request: {
  "name": "claude-3.5",
  "model_name": "anthropic/claude-3.5-sonnet",
  "priority": 1,
  "api_config": {"temperature": 0.7}
}

# PUT /api/models/{id}
# 모델 활성화/비활성화 또는 설정 변경
Request: {
  "is_active": false,
  "priority": 2
}

# DELETE /api/models/{id}
# 모델 삭제 (soft delete 권장)
```

#### 3.2 A/B 테스트 설정 API
```python
# GET /api/ab-test/config
# 현재 활성 A/B 설정 조회
Response: {
  "model_a": {
    "id": 1,
    "name": "gpt-4o"
  },
  "model_b": {
    "id": 2,
    "name": "deepseek-v3"
  }
}

# PUT /api/ab-test/config
# A/B 테스트 모델 변경
Request: {
  "model_a_id": 1,
  "model_b_id": 3
}
```

#### 3.3 종목 분석 API 수정
```python
# GET /api/stocks/{stock_code}
Response: {
  "stock_code": "005930",
  "stock_name": "삼성전자",
  "analysis_summary": {
    "ab_test_enabled": true,
    "model_a": {
      "name": "gpt-4o",
      "overall_summary": "...",
      ...
    },
    "model_b": {
      "name": "deepseek-v3",
      "overall_summary": "...",
      ...
    },
    "all_models": {  // 관리자 모드용 (선택적)
      "gpt-4o": {...},
      "deepseek-v3": {...},
      "qwen-max": {...}
    }
  }
}
```

### 4. OpenRouter 통합

#### 4.1 통합 클라이언트
```python
# backend/llm/openrouter_client.py
class OpenRouterClient:
    def __init__(self):
        self.base_url = "https://openrouter.ai/api/v1"
        self.api_key = settings.OPENROUTER_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://craveny.ai",
            "X-Title": "Craveny AI Investment"
        }

    def create_client(self, model_name: str) -> OpenAI:
        """OpenRouter를 통한 OpenAI 호환 클라이언트 생성"""
        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            default_headers=self.headers
        )

    async def predict(self, model_name: str, messages: List[dict]) -> dict:
        """통합 예측 API"""
        client = self.create_client(model_name)
        response = await client.chat.completions.create(
            model=model_name,  # "openai/gpt-4o", "deepseek/deepseek-chat" 등
            messages=messages,
            temperature=0.7
        )
        return json.loads(response.choices[0].message.content)
```

#### 4.2 지원 모델 목록 (OpenRouter)
```python
# 초기 지원 모델
SUPPORTED_MODELS = [
    {
        "name": "gpt-4o",
        "model_name": "openai/gpt-4o",
        "cost_per_1m_tokens": {"input": 2.5, "output": 10}
    },
    {
        "name": "deepseek-v3",
        "model_name": "deepseek/deepseek-chat",
        "cost_per_1m_tokens": {"input": 0.27, "output": 1.1}
    },
    {
        "name": "qwen-max",
        "model_name": "qwen/qwen-2.5-72b-instruct",
        "cost_per_1m_tokens": {"input": 0.4, "output": 1.2}
    },
    {
        "name": "claude-3.5",
        "model_name": "anthropic/claude-3.5-sonnet",
        "cost_per_1m_tokens": {"input": 3, "output": 15}
    }
]
```

### 5. 백엔드 구현

#### 5.1 MultiModelPredictor 클래스
```python
# backend/llm/multi_model_predictor.py
class MultiModelPredictor:
    def __init__(self):
        self.openrouter = OpenRouterClient()
        self.db = SessionLocal()

    async def predict_all_models(self, news, similar_news):
        """모든 활성 모델로 예측 생성"""
        active_models = self.db.query(Model).filter(Model.is_active == True).all()

        results = {}
        for model in active_models:
            try:
                pred = await self._predict_single(model, news, similar_news)

                # model_predictions 테이블에 저장
                self._save_prediction(news.id, model.id, pred)
                results[model.name] = pred

                logger.info(f"✅ {model.name} 예측 완료: {pred['direction']}")
            except Exception as e:
                logger.error(f"❌ {model.name} 예측 실패: {e}")
                results[model.name] = None

        return results

    async def _predict_single(self, model: Model, news, similar_news):
        """단일 모델 예측"""
        messages = self._build_prompt(news, similar_news)

        response = await self.openrouter.predict(model.model_name, messages)

        return {
            "direction": response["prediction"],
            "confidence": response["confidence"],
            "reasoning": response["reasoning"],
            "short_term": response.get("short_term"),
            "medium_term": response.get("medium_term"),
            "long_term": response.get("long_term"),
            "confidence_breakdown": response.get("confidence_breakdown"),
            "pattern_analysis": response.get("pattern_analysis")
        }

    def get_ab_predictions(self, news_id: int):
        """A/B 설정된 모델의 예측만 반환"""
        ab_config = (
            self.db.query(ABTestConfig)
            .filter(ABTestConfig.is_active == True)
            .first()
        )

        if not ab_config:
            raise ValueError("활성화된 A/B 테스트 설정이 없습니다")

        pred_a = (
            self.db.query(ModelPrediction)
            .filter(
                ModelPrediction.news_id == news_id,
                ModelPrediction.model_id == ab_config.model_a_id
            )
            .first()
        )

        pred_b = (
            self.db.query(ModelPrediction)
            .filter(
                ModelPrediction.news_id == news_id,
                ModelPrediction.model_id == ab_config.model_b_id
            )
            .first()
        )

        return pred_a, pred_b
```

#### 5.2 auto_notify.py 수정
```python
# backend/notifications/auto_notify.py
async def process_news_prediction(news):
    """뉴스 예측 및 알림"""

    # 1. 모든 활성 모델로 예측 생성
    predictor = MultiModelPredictor()
    all_predictions = await predictor.predict_all_models(news, similar_news)

    # 2. A/B 설정된 모델만 가져오기
    pred_a, pred_b = predictor.get_ab_predictions(news.id)

    # 3. A/B 비교하여 알림 발송
    if should_notify(pred_a, pred_b):
        await send_telegram_notification(news, pred_a, pred_b)
```

### 6. 프론트엔드 구현

#### 6.1 Admin 페이지
```tsx
// frontend/app/admin/models/page.tsx
export default function ModelsAdminPage() {
  const [models, setModels] = useState([]);
  const [abConfig, setAbConfig] = useState({});

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">모델 관리</h1>

      {/* 모델 목록 */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold mb-4">등록된 모델</h2>
        <table className="w-full">
          <thead>
            <tr>
              <th>모델명</th>
              <th>OpenRouter ID</th>
              <th>상태</th>
              <th>우선순위</th>
              <th>액션</th>
            </tr>
          </thead>
          <tbody>
            {models.map(model => (
              <tr key={model.id}>
                <td>{model.name}</td>
                <td>{model.model_name}</td>
                <td>
                  <Toggle
                    checked={model.is_active}
                    onChange={() => toggleModel(model.id)}
                  />
                </td>
                <td>{model.priority === 1 ? '실시간' : '배치'}</td>
                <td>
                  <button onClick={() => deleteModel(model.id)}>삭제</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* A/B 테스트 설정 */}
      <section>
        <h2 className="text-2xl font-bold mb-4">A/B 테스트 설정</h2>
        <div className="flex gap-4">
          <select value={abConfig.model_a_id} onChange={handleModelAChange}>
            {models.filter(m => m.is_active).map(m => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
          <span>vs</span>
          <select value={abConfig.model_b_id} onChange={handleModelBChange}>
            {models.filter(m => m.is_active).map(m => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
          <button onClick={saveAbConfig}>저장</button>
        </div>
      </section>
    </div>
  );
}
```

### 7. 마이그레이션 전략

#### 7.1 단계별 마이그레이션
```python
# scripts/migrate_to_multi_model.py

async def migrate():
    """기존 시스템을 다중 모델 시스템으로 마이그레이션"""

    # Step 1: 새 테이블 생성
    create_models_table()
    create_model_predictions_table()
    create_ab_test_config_table()

    # Step 2: 초기 모델 등록
    gpt4o = insert_model("gpt-4o", "openrouter", "openai/gpt-4o")
    deepseek = insert_model("deepseek-v3", "openrouter", "deepseek/deepseek-chat")

    # Step 3: 기존 predictions → model_predictions 마이그레이션
    # 기존 데이터를 "legacy" 모델로 마이그레이션하거나
    # MODEL_A 기준으로 마이그레이션
    migrate_existing_predictions(gpt4o.id)

    # Step 4: 기본 A/B 설정
    insert_ab_config(gpt4o.id, deepseek.id, is_active=True)

    print("✅ 마이그레이션 완료")
```

### 8. 비용 최적화

#### 8.1 우선순위 기반 실행
```python
# priority=1: 실시간 (중요 뉴스, A/B 테스트 모델)
# priority=2: 배치 (30분마다 또는 야간 배치)

if news.importance == "high" or news.stock_code in MAJOR_STOCKS:
    # 모든 활성 모델 즉시 실행
    await predict_all_models(news)
else:
    # priority=1 모델만 즉시, 나머지는 큐잉
    realtime_models = get_models(priority=1, is_active=True)
    await predict_models(news, realtime_models)

    batch_models = get_models(priority=2, is_active=True)
    queue_batch_prediction(news, batch_models)
```

#### 8.2 비용 모니터링
```sql
-- 모델별 사용량 추적 테이블
CREATE TABLE model_usage_stats (
    id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES models(id),
    date DATE NOT NULL,
    prediction_count INTEGER DEFAULT 0,
    estimated_cost DECIMAL(10, 2),
    UNIQUE(model_id, date)
);
```

### 9. 구현 우선순위

#### Phase 1: 핵심 인프라 (2-3일)
- [ ] 새 테이블 생성 (models, model_predictions, ab_test_config)
- [ ] 마이그레이션 스크립트 작성 및 실행
- [ ] OpenRouterClient 클래스 구현
- [ ] MultiModelPredictor 기본 구조

#### Phase 2: 예측 로직 (2-3일)
- [ ] predict_all_models() 구현
- [ ] auto_notify.py 멀티 모델 지원
- [ ] model_predictions 저장/조회 로직

#### Phase 3: API & Admin UI (3-4일)
- [ ] 모델 관리 API 구현
- [ ] A/B 테스트 설정 API
- [ ] Admin 페이지 구현
- [ ] 모델 추가/삭제/활성화 UI

#### Phase 4: 종합 리포트 (2-3일)
- [ ] generate_multi_model_report() 구현
- [ ] stock_analysis_service.py 멀티 모델 지원
- [ ] 프론트엔드 A/B 비교 UI (이미 구현 완료)

**전체 예상 기간**: 2-3주

## 🤔 검토 요청 사항

1. **데이터베이스 구조**는 적절한가요?
2. **OpenRouter 통합 방식**이 합리적인가요?
3. **우선순위 시스템**(실시간/배치)이 비용 최적화에 효과적일까요?
4. **마이그레이션 전략**이 안전한가요?
5. **Phase 구분**이 적절한가요?
6. 추가로 고려해야 할 사항이 있나요?

## 📝 참고 사항

- 모든 모델은 OpenRouter를 통해 호출 (단일 API 키 관리)
- 기존 시스템과 하위 호환성 유지
- 단계별 배포 및 테스트 가능
- 롤백 시나리오 포함

---

**작성자**: Development Team
**작성일**: 2025-01-03
**검토 요청**: bmad (PO)
