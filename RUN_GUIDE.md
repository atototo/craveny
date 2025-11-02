# 🚀 Craveny 실행 가이드

주가 예측 및 텔레그램 알림 시스템 실행 방법

---

## 전체 시스템 구조

```
┌─────────────────┐
│  FastAPI 서버   │  ← API 엔드포인트 제공
└─────────────────┘

┌─────────────────┐
│ 크롤러 스케줄러 │  ← 자동화 작업 (10분마다)
│                 │     1. 뉴스 크롤링
│                 │     2. 종목 코드 매칭
│                 │     3. 임베딩 생성
│                 │     4. 자동 알림
└─────────────────┘
```

두 개를 **별도 터미널**에서 실행해야 합니다.

---

## 📌 실행 방법

### Backend 서버 실행 (크롤러 포함)

**방법 1: uv 사용 (가장 간단, 권장)** ⭐
```bash
uv run craveny
```

**방법 2: Python 모듈로 실행**
```bash
uv run python -m backend.main
```

**방법 3: 전통적인 방법**
```bash
source .venv/bin/activate
python -m backend.main
```

**참고:** Backend 시작 시 크롤러 스케줄러가 자동으로 함께 실행됩니다!

**확인:**
- http://localhost:8000/docs ← API 문서 확인
- http://localhost:8000/health ← Health Check

---

### Frontend 서버 실행

```bash
cd frontend
npm run dev
```

**확인:**
- http://localhost:3000 ← 웹 대시보드

**자동으로 실행되는 작업:**

1. **최신 뉴스 크롤링** (10분 간격)
   - 네이버 증권
   - 한국경제
   - 매일경제

2. **종목별 뉴스 검색** (10분 간격) ⭐ 신규
   - DB에 등록된 활성 종목 대상
   - 우선순위별 차등 수집 (P1-2: 10건, P3: 5건, P4-5: 3건)

3. **DART 공시 크롤링** (5분 간격) ⭐ 신규
   - Priority 1-2 종목만 대상
   - 최근 3일 공시 수집
   - DART_API_KEY 필요

4. **주가 수집** (1분 간격, 장 시간에만)
   - Priority 1 종목 대상

5. **뉴스-주가 매칭** (매일 15:40)
   - 최근 7일 뉴스 대상

6. **뉴스 임베딩** (매일 16:00)
   - OpenAI 임베딩
   - Milvus 벡터 DB 저장

7. **자동 알림** (10분 간격)
   - 새 뉴스 발견 시
   - GPT-4o-mini 예측 수행
   - 텔레그램 알림 전송

**중지하려면:** `Ctrl+C`

---

## ✅ 시스템 상태 확인

```bash
# 뉴스 저장 현황 확인
uv run python scripts/check_status.py
```

**정상 상태:**
```
✅ 크롤러 정상 작동 중 (최근 1시간 이내 뉴스 수집)
✅ 실시간 수집 중 (30분 이내 뉴스)
```

---

## 🔧 개별 작업 실행 (테스트용)

### 1. 뉴스 크롤링만 실행
```bash
uv run python scripts/test_crawler.py
```

### 2. 초기 데이터 수집
```bash
uv run python scripts/collect_initial_data.py
```

### 3. 텔레그램 알림 테스트
```bash
uv run python scripts/test_telegram.py
```

### 4. 예측 API 테스트
```bash
uv run python scripts/test_api.py
```

---

## 📊 모니터링

### 로그 확인
크롤러 스케줄러 터미널에서:
```
✅ 뉴스 크롤링 완료: 5건
✅ 종목 매칭 완료: 3건
✅ 임베딩 저장 완료: 3건
🔔 자동 알림 완료: 성공 2건, 실패 0건
```

### 텔레그램 확인
- 봇: @issueton_bot
- 새 뉴스 발견 시 자동 알림
- 예측 결과, 신뢰도, 기간별 예측 포함

---

## ⚠️ 문제 해결

### 크롤러가 뉴스를 가져오지 못할 때
1. 인터넷 연결 확인
2. 뉴스 사이트 접근 가능 여부 확인
3. 로그에서 에러 메시지 확인

### 텔레그램 알림이 안 올 때
1. `.env` 파일의 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 확인
2. `uv run python scripts/test_telegram.py` 실행
3. 봇이 활성화되어 있는지 확인

### 예측이 느릴 때
- Redis 캐시 동작 확인
- OpenAI API 키 할당량 확인
- 로그에서 캐시 히트율 확인

---

## 🎯 권장 실행 순서 (처음 시작할 때)

1. **.env 파일 설정 확인**
   ```bash
   cat .env
   ```

2. **데이터베이스 마이그레이션**
   ```bash
   uv run python scripts/migrate_add_notified_at.py
   ```

3. **초기 데이터 수집** (선택사항)
   ```bash
   uv run python scripts/collect_initial_data.py
   ```

4. **FastAPI 서버 시작** (터미널 1)
   ```bash
   uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. **크롤러 스케줄러 시작** (터미널 2)
   ```bash
   uv run python scripts/start_crawler.py
   ```

6. **시스템 상태 확인** (터미널 3)
   ```bash
   uv run python scripts/check_status.py
   ```

---

## 📱 텔레그램 알림 예시

```
📈 주가 예측 알림 📈

📰 뉴스: 삼성전자, 신형 반도체 공정 개발 성공으로 실적 개선 기대

🏢 종목: 005930

📊 예측 방향: 상승
🟢 신뢰도: 80%

📅 기간별 예측:
  • T+1일: 2.5% 상승 예상
  • T+3일: 5.3% 상승 예상
  • T+5일: 7.8% 상승 예상

💡 예측 근거:
과거 유사 뉴스에서 T+5일 7.8% 상승 패턴이 확인되었습니다...

📌 참고 뉴스: 2건
🤖 모델: gpt-4o
🕐 예측 시각: 2025-11-01 15:00:00
```

---

## 💡 팁

- 크롤러는 백그라운드에서 계속 실행
- 10분마다 자동으로 새 뉴스 확인
- 중복 알림은 자동 방지됨 (`notified_at` 필드 활용)
- 장 운영 시간만 크롤링하도록 설정 가능 (`market_check=True`)

---

이제 **터미널 2개**를 열어서:
1. FastAPI 서버 (이미 실행 중이면 그대로 두기)
2. 크롤러 스케줄러 (`uv run python scripts/start_crawler.py`)

실행하면 전체 시스템이 작동합니다! 🚀
