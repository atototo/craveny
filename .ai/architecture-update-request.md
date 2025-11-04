# Architecture Update Request

**Date:** 2025-11-02
**Requested by:** Sarah (PO Agent)
**Target Document:** `docs/architecture.md`

---

## Context

Epic 1 (데이터 인프라) 및 Epic 2 Phase 2 (LLM 예측, 텔레그램 알림, Frontend 대시보드)가 완료되었습니다. 실제 구현된 시스템 구조를 architecture.md에 반영이 필요합니다.

---

## 구현 완료된 주요 변경사항

### 1. Frontend 구조 추가 (NEW)

**Technology Stack:**
- Next.js 15.1.4 (App Router)
- React 19
- TypeScript
- Tailwind CSS

**Directory Structure:**
```
frontend/
├── app/
│   ├── page.tsx                    # 사용자 대시보드 (/)
│   ├── admin/
│   │   └── dashboard/page.tsx     # 관리자 대시보드 (/admin/dashboard)
│   ├── stocks/
│   │   ├── page.tsx               # 종목 목록 (/stocks)
│   │   └── [stockCode]/page.tsx   # 종목 상세 (/stocks/:code)
│   ├── predictions/page.tsx        # 예측 이력 (/predictions)
│   ├── layout.tsx                  # Root layout
│   ├── globals.css                 # Global styles
│   └── components/
│       └── Navigation.tsx          # 네비게이션 컴포넌트
├── next.config.ts
├── tailwind.config.ts
└── package.json
```

**Key Pages:**
- `/` - 사용자 대시보드: 최신 알림, HOT 종목, 기능 카드
- `/admin/dashboard` - 관리자 대시보드: 예측 통계, 시스템 상태
- `/stocks` - 종목 분석 페이지
- `/stocks/[code]` - 종목 상세 페이지 (뉴스, 예측, 투자 리포트)
- `/predictions` - 예측 이력 페이지

**API Proxy Configuration:**
Next.js rewrites를 통해 `/api/*` → `http://localhost:8000/api/*`로 프록시

---

### 2. Backend API 엔드포인트 확장

**신규 API 모듈:**
```
backend/api/
├── __init__.py
├── dashboard.py         # GET /api/dashboard/stats
├── news.py             # GET /api/news (필터링, 페이징)
├── statistics.py       # GET /api/statistics/summary
├── stocks.py           # GET /api/stocks, /api/stocks/:code
└── prediction.py       # GET /api/predictions
```

**주요 엔드포인트:**
- `GET /api/dashboard/stats` - 대시보드 통계 (예측 수, 평균 신뢰도, 방향 분포)
- `GET /api/news` - 뉴스 목록 (필터: notified, stock_code, 페이징)
- `GET /api/stocks/summary` - HOT 종목 요약 (뉴스 수, 알림 수)
- `GET /api/stocks/:code/analysis` - 종목 분석 리포트 (LLM 생성)
- `GET /api/predictions` - 예측 이력 조회

---

### 3. Backend 디렉토리 구조 확장

**신규 모듈:**
```
backend/
├── api/                    # FastAPI 라우터 (NEW)
│   ├── dashboard.py
│   ├── news.py
│   ├── statistics.py
│   ├── stocks.py
│   └── prediction.py
├── notifications/          # 텔레그램 알림 (NEW)
│   ├── __init__.py
│   ├── telegram.py        # 텔레그램 메시지 전송
│   └── auto_notify.py     # 자동 알림 로직
├── llm/                   # LLM 관련 (NEW)
│   ├── predictor.py       # LLM 예측 생성
│   ├── vector_search.py   # Milvus 유사도 검색
│   ├── investment_report.py  # 투자 리포트 생성
│   └── prediction_cache.py   # Redis 캐싱
├── services/              # 비즈니스 로직 (NEW)
│   └── stock_analysis_service.py
└── scripts/               # 유틸리티 스크립트 (NEW)
    ├── fix_naver_news.py
    ├── check_status.py
    └── start_crawler.py
```

---

### 4. 데이터 모델 추가

**신규 테이블:**
- `predictions` - LLM 예측 결과 저장
  - news_id, stock_code, prediction_json, confidence, created_at
- `stock_analysis_summary` - 종목별 AI 분석 리포트 캐시
  - stock_code, analysis_json, generated_at, expires_at

---

### 5. 시스템 아키텍처 업데이트

**전체 시스템 플로우:**
```
1. 뉴스 크롤링 (APScheduler, 10분 주기)
   ↓
2. 뉴스 임베딩 생성 (OpenAI text-embedding-3-small, 768d)
   ↓
3. Milvus 벡터 저장 및 유사도 검색 (L2 distance)
   ↓
4. LLM 예측 생성 (GPT-4o, RAG 기반 분석)
   ↓
5. 예측 결과 저장 (PostgreSQL predictions 테이블)
   ↓
6. 알림 조건 체크 (영향도 ≥ 8.0, notified_at NULL)
   ↓
7. 텔레그램 알림 전송 (python-telegram-bot)
   ↓
8. Frontend 대시보드 표시 (Next.js SSR)
```

**주요 의존성:**
- PostgreSQL 15 (뉴스, 주가, 예측 저장)
- Milvus 2.3 (768차원 벡터 검색)
- Redis 7 (캐싱, 중복 방지)
- OpenAI API (GPT-4o, text-embedding-3-small)
- Telegram Bot API (알림 전송)
- FastAPI 0.100+ (Backend API)
- Next.js 15 (Frontend)

---

## 요청사항

`docs/architecture.md` 문서에 다음 내용을 반영해주세요:

1. **Frontend 섹션 추가**: Next.js 구조, 페이지, 컴포넌트
2. **API 엔드포인트 문서화**: 신규 API 모듈 및 주요 엔드포인트
3. **Backend 디렉토리 구조 업데이트**: 신규 모듈 (api, notifications, llm, services, scripts)
4. **데이터 모델 추가**: predictions, stock_analysis_summary 테이블
5. **시스템 아키텍처 다이어그램 업데이트**: End-to-end 플로우 반영

---

## 참고 파일

**Frontend:**
- `frontend/app/page.tsx` - 사용자 대시보드
- `frontend/app/admin/dashboard/page.tsx` - 관리자 대시보드
- `frontend/app/components/Navigation.tsx` - 네비게이션

**Backend:**
- `backend/api/*.py` - API 라우터들
- `backend/notifications/telegram.py` - 텔레그램 알림
- `backend/llm/predictor.py` - LLM 예측
- `backend/main.py` - FastAPI 앱 초기화

**Database Models:**
- `backend/db/models/prediction.py`
- `backend/db/models/stock_analysis.py`

---

**End of Request**
