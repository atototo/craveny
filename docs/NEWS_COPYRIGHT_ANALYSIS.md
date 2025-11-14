# 뉴스 저작권 이슈 분석 및 전략 방향

## 1. 현재 상황 요약

### 1.1 시스템 구조
Craveny는 뉴스 기사 분석과 임베딩을 통한 주식 예측 서비스를 제공합니다.

**데이터 수집 구조:**
```
크롤러 → PostgreSQL (전체 본문 저장) → Milvus (벡터 임베딩)
                ↓
         뉴스 중심 종목 추적
```

### 1.2 현재 뉴스 소스

#### HTML 스크래퍼 (고위험) - 4개
1. **Naver 증권** (`naver_crawler.py`)
   - 종목별 뉴스 페이지 스크래핑
   - BeautifulSoup 사용

2. **한국경제** (`hankyung_crawler.py`)
   - RSS 피드 파싱 후 본문 스크래핑
   - feedparser + BeautifulSoup

3. **매일경제** (`maeil_crawler.py`)
   - RSS 피드 파싱 후 본문 스크래핑
   - feedparser + BeautifulSoup

4. **Naver 검색** (`naver_search_crawler.py`)
   - Naver 검색 API 사용 (메타데이터)
   - 원본 URL 접속해서 본문 스크래핑

#### API 크롤러 (저위험) - 2개
1. **DART 공시** (`dart_crawler.py`)
   - 공식 DART API 사용
   - 공시 정보는 공개 데이터

2. **Reddit** (`reddit_crawler.py`)
   - PRAW (Reddit API) 사용
   - **현재 문제**: 비동기 환경에서 PRAW 동작 안 함 → 수집 데이터 0건

### 1.3 데이터 저장 방식

**PostgreSQL (`news_articles` 테이블)**
```sql
- title: 제목 (전체 저장)
- content: 본문 (전체 저장) ⚠️ 고위험
- url: 원문 링크
- source: 출처
- published_at: 발행일
- stock_code: 관련 종목
```

**Milvus (벡터 DB)**
- OpenAI text-embedding-3-small (768차원)
- 텍스트 원본은 저장하지 않음 (벡터만 저장)
- 저작권 위험 낮음

### 1.4 수집 현황 (2025-11-14 기준)
```
총 뉴스: 약 4,000건
- Naver: 3,400+ 건
- 매일경제: 393건
- DART: 223건
- Reddit: 0건
```

---

## 2. 법적 위험도 평가

### 2.1 저작권법 위반 가능성

#### 고위험 ⚠️
- **HTML 스크래핑 (4개 크롤러)**
  - 저작권자 허락 없이 전체 본문 복제
  - PostgreSQL에 영구 저장
  - 상업적 서비스에 사용
  - **위반 가능성: 높음**

#### 중위험 ⚠️
- **Naver 검색 API**
  - API는 공식이지만, 본문은 스크래핑
  - API 약관에서 스크래핑 금지 가능성

#### 저위험 ✅
- **DART 공시**: 공공 데이터
- **Reddit**: 공식 API 사용
- **Milvus 벡터**: 원본 텍스트 저장 안 함

### 2.2 한국 저작권법 관련 조항

**제35조의3 (저작물의 공정한 이용)**
- 비영리 목적, 변형적 사용 등에서 공정이용 가능
- **하지만**: Craveny는 상업적 서비스 → 적용 어려움

**제35조의5 (저작물의 공정한 이용을 위한 문화체육관광부장관의 승인)**
- TDM (Text and Data Mining) 예외 규정
- 연구 목적에 한정
- **적용 어려움**: 상업적 주식 예측 서비스

### 2.3 법적 리스크
1. 언론사 측에서 저작권 침해 주장 가능
2. 크롤링 차단 (robots.txt, IP 차단)
3. 손해배상 청구 가능
4. 서비스 중단 요구

---

## 3. 전략적 방향 (5가지 옵션)

### 옵션 1: 뉴스 완전 제거 (Pure Technical Analysis)

**장점:**
- 법적 리스크 완전 제거
- 시스템 단순화
- 운영 비용 절감

**단점:**
- 핵심 차별화 요소 상실
- "뉴스 기반 분석"이라는 가치 제안 포기

**대체 데이터:**
- 가격/거래량 데이터 (야후, KIS API 등)
- 재무제표 (DART)
- 소셜 미디어 감성 분석 (Reddit, Twitter)
- 기술적 지표 (RSI, MACD 등)

### 옵션 2: 메타데이터만 저장 (Title + Keywords Only)

**변경 사항:**
```python
# 현재
content = full_article_text  # 전체 본문 저장

# 변경 후
content = extract_keywords(title)  # 제목에서 키워드만 추출
# 또는
content = title + summary[:100]  # 제목 + 요약 100자
```

**장점:**
- 부분적 법적 리스크 감소
- 뉴스 기반 분석 유지 가능
- 검색 API 계속 사용 가능

**단점:**
- 분석 품질 저하 가능
- 여전히 그레이존

### 옵션 3: 공식 파트너십 체결

**방법:**
- 네이버, 한경, 매경과 API 계약
- 라이선스 비용 지불
- 정식 콘텐츠 제공 계약

**장점:**
- 완전 합법화
- 안정적 데이터 확보
- 신뢰도 증가

**단점:**
- 높은 라이선스 비용
- 계약 협상 복잡
- 스타트업에게 부담

### 옵션 4: 하이브리드 모델

**구조:**
```
무료 티어: 공개 데이터만 (DART, Reddit, 메타데이터)
프리미엄: 라이선스 뉴스 포함
```

**장점:**
- 점진적 확장 가능
- 무료 사용자로 시장 검증
- 법적 리스크 최소화하면서 차별화

**단점:**
- 복잡한 시스템 구조
- 초기 라이선스 비용

### 옵션 5: 가치 제안 전환 (Pivot)

**새로운 방향:**
- 뉴스 분석 → 커뮤니티 기반 분석
- 뉴스 분석 → 기술적 분석 중심
- 뉴스 분석 → 재무제표 분석 중심

**장점:**
- 법적 문제 회피
- 새로운 차별화 요소 발굴

**단점:**
- 기존 시스템 대폭 수정
- 비즈니스 모델 재정립 필요

---

## 4. 뉴스 검색 API 비교 (Naver vs Google)

### 4.1 Naver 검색 API

**장점:**
- 한국 뉴스에 최적화
- 한국어 검색 품질 우수
- 무료 사용량: 25,000건/일

**단점:**
- 메타데이터만 제공 (제목, 요약, URL)
- 본문은 직접 스크래핑 필요

**API 제공 정보:**
```json
{
  "title": "기사 제목",
  "description": "요약 (100자 내외)",
  "link": "원문 URL",
  "pubDate": "발행일"
}
```

### 4.2 Google News API

**장점:**
- 글로벌 뉴스 커버리지
- 다양한 언론사 지원

**단점:**
- 한국 뉴스 커버리지 제한적
- 한국어 검색 품질 낮음
- 비용: 무료 티어 없음 (유료)

### 4.3 결론
**한국 주식 시장**을 대상으로 한다면 → **Naver 검색 API 우선**

---

## 5. 발견된 기술 이슈

### 5.1 Reddit 크롤러 미작동

**문제:**
- PRAW 라이브러리가 비동기 환경에서 작동 안 함
- FastAPI (asyncio 기반) 환경에서 충돌

**경고 메시지:**
```
It appears that you are using PRAW in an asynchronous environment.
It is strongly recommended to use Async PRAW
```

**해결 방안:**
1. Async PRAW로 마이그레이션
2. 별도 동기 프로세스로 분리
3. Reddit 크롤러 제거 (우선순위 낮음)

**현재 수집 데이터:** 0건

### 5.2 종목 관리 페이지 오류 (해결됨 ✅)

**문제:**
- Frontend: `/admin/stocks` 페이지
- Backend: `/admin/stocks` API 엔드포인트
- Next.js 라우팅 충돌 발생

**해결:**
- Backend API prefix를 `/api/admin/stocks`로 변경
- Commit: `c8e4aba - fix: 종목 관리 API 라우팅 경로 수정`

---

## 6. 현재 시스템의 문제점

### 6.1 뉴스 중심 종목 추적 구조

**현재 동작:**
1. 뉴스가 발생한 종목만 추적
2. 사용자가 관심 있는 종목이라도 뉴스가 없으면 추적 안 됨

**문제:**
- 사용자가 임의로 종목 추가해도 뉴스 없으면 의미 없음
- 종목 관리 페이지(49개 종목)와 실제 분석 종목 불일치

**개선 방향:**
- 종목 기반 추적으로 전환
- 뉴스는 부가 정보로 활용

### 6.2 데이터 저장 방식

**고위험:**
```python
# PostgreSQL에 전체 본문 저장
news_article.content = full_article_content  # ⚠️
```

**저위험:**
```python
# Milvus에 벡터만 저장
vector = embedding_model.encode(content)
milvus.insert(vector)  # ✅ 원본 텍스트 없음
```

---

## 7. 다음 분석 방향 (선택지)

### A. 뉴스 없는 대체 데이터 탐색
- 야후 파이낸스 API
- KIS API (한국투자증권)
- 퀀트 데이터 (재무비율, 기술지표)
- 소셜 미디어 (Twitter, Reddit)

### B. 현재 뉴스의 예측 기여도 평가
- 뉴스 있을 때 vs 없을 때 예측 정확도 비교
- 뉴스 임베딩의 실제 영향력 측정
- A/B 테스트 설계

### C. 합법적 뉴스 확보 방법 구체화
- Naver 검색 API 계약 조건 확인
- 언론사 API 제공 여부 조사
- 뉴스 애그리게이터 서비스 탐색
- 라이선스 비용 견적

### D. 시스템 아키텍처 재설계
- 종목 중심 추적 구조로 전환
- 뉴스를 선택적 기능으로 변경
- 메타데이터만 사용하는 경량 버전

---

## 8. 즉시 실행 가능한 조치

### 단기 (1-2주)
1. PostgreSQL에서 `content` 필드 제거 또는 요약본만 저장
2. HTML 스크래퍼 비활성화
3. Naver 검색 API만 사용 (메타데이터)
4. Reddit 크롤러 수정 또는 제거

### 중기 (1개월)
1. 종목 기반 추적으로 시스템 재설계
2. 뉴스 API 파트너십 조사
3. 대체 데이터 소스 통합 (KIS API 등)

### 장기 (3개월)
1. 비즈니스 모델 재정립
2. 합법적 데이터 소싱 확립
3. 차별화 전략 재수립

---

## 9. 의사결정 질문

1. **뉴스 분석이 핵심 가치인가?**
   - YES → 옵션 3 (파트너십) 또는 옵션 4 (하이브리드)
   - NO → 옵션 1 (뉴스 제거) 또는 옵션 5 (피벗)

2. **예산과 시간은?**
   - 예산 있음 → 옵션 3 (파트너십)
   - 예산 없음 → 옵션 1 (제거) 또는 옵션 2 (메타데이터)

3. **사용자가 뉴스를 얼마나 중요하게 생각하는가?**
   - 매우 중요 → 옵션 3, 4
   - 부가 기능 → 옵션 2, 5

---

## 10. 추천 전략

### 즉시 실행 (법적 리스크 최소화)
```
1. HTML 스크래퍼 4개 비활성화
2. PostgreSQL content 필드를 요약 100자로 제한
3. Naver 검색 API 메타데이터만 사용
4. DART + Reddit(수정 후) 유지
```

### 중장기 전략 (비즈니스 성장)
```
옵션 4: 하이브리드 모델
- 무료: 메타데이터 + 공개 데이터
- 유료: 파트너십 뉴스 전체 분석

또는

옵션 5: 피벗
- 뉴스 → 커뮤니티 기반 주식 분석
- Reddit, Twitter 감성 분석 강화
- 사용자 생성 콘텐츠 활용
```

---

## 참고 파일

### 크롤러
- `backend/crawlers/naver_crawler.py`
- `backend/crawlers/hankyung_crawler.py`
- `backend/crawlers/maeil_crawler.py`
- `backend/crawlers/naver_search_crawler.py`
- `backend/crawlers/dart_crawler.py`
- `backend/crawlers/reddit_crawler.py`

### 스케줄러
- `backend/scheduler/crawler_scheduler.py`

### 데이터베이스
- `backend/db/models/news.py`
- PostgreSQL: `news_articles` 테이블
- Milvus: 벡터 임베딩

### 테스트 스크립트
- `test_reddit_crawler.py`
- `check_reddit_data.py`

---

**작성일:** 2025-11-14
**작성자:** Claude Code Analysis
**상태:** 진행 중
