# Story 003.1: KIS API 인증 및 설정 관리 시스템 구축

**Epic**: Epic 003 - 한국투자증권 API Phase 1 Infrastructure
**Status**: 📋 Ready
**Priority**: ⭐⭐⭐⭐⭐ (Critical - 모든 후속 스토리의 기반)
**Estimated Effort**: 3-5일
**Assignee**: TBD
**Sprint**: TBD

---

## 📋 Story Overview

**As a** 개발자,
**I want** KIS API 인증 시스템(OAuth 2.0)과 설정 관리 시스템을 구축하여,
**so that** 안전하게 API를 호출하고 토큰을 자동으로 관리할 수 있다.

---

## 🎯 Acceptance Criteria

### 필수 기준 (Must Have)

1. ✅ **KIS API 계정 등록 및 앱 키 발급**
   - 실전투자 계정 생성 완료
   - App Key, App Secret 발급 완료
   - `.env` 파일에 안전하게 저장

2. ✅ **OAuth 2.0 인증 구현**
   - Access Token 자동 발급 (유효기간: 24시간)
   - Token 만료 시 자동 갱신 (Refresh Token 사용)
   - 인증 실패 시 재시도 로직 (exponential backoff)

3. ✅ **설정 관리 시스템**
   - `backend/config/kis_config.py` 생성
   - 환경별 설정 분리 (mock/real)
   - Rate limit 설정 (20 req/sec real, 5 req/sec mock)

4. ✅ **KIS API 클라이언트 라이브러리**
   - `backend/kis/client.py` 구현
   - 공통 메서드: `request()`, `get()`, `post()`
   - 자동 인증 헤더 추가
   - Rate limiting 적용

5. ✅ **헬스체크 및 연결 테스트**
   - `/api/kis/health` 엔드포인트 구현
   - KIS API 연결 상태 확인
   - Token 유효성 검증

### 선택 기준 (Nice to Have)

- 🔹 Token 캐싱 (Redis)으로 성능 최적화
- 🔹 API 호출 로그 상세 기록
- 🔹 Grafana 대시보드 연동

---

## 📐 Technical Design

### 1. 아키텍처 다이어그램

```
┌─────────────────┐
│  FastAPI App    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  KIS Client     │◄────►│  KIS API Server  │
│  (Singleton)    │      │  (openapi.kr.com)│
└────────┬────────┘      └──────────────────┘
         │
         ▼
┌─────────────────┐
│  Token Manager  │
│  (Redis Cache)  │
└─────────────────┘
```

### 2. 파일 구조

```
backend/
├── config/
│   └── kis_config.py          # KIS API 설정
├── kis/
│   ├── __init__.py
│   ├── client.py              # KIS API 클라이언트
│   ├── auth.py                # OAuth 2.0 인증
│   └── exceptions.py          # 커스텀 예외
└── api/
    └── endpoints/
        └── kis_health.py      # 헬스체크 엔드포인트

.env
├── KIS_APP_KEY=...
├── KIS_APP_SECRET=...
├── KIS_BASE_URL=...
└── KIS_MODE=mock              # mock or real
```

### 3. 데이터 모델

#### 3.1 Token Model (Redis 저장)
```python
{
    "access_token": "eyJhbGc...",
    "token_type": "Bearer",
    "expires_in": 86400,          # 24시간 (초)
    "expires_at": "2024-11-09T10:30:00",
    "created_at": "2024-11-08T10:30:00"
}
```

#### 3.2 KIS Config Model
```python
@dataclass
class KISConfig:
    app_key: str
    app_secret: str
    base_url: str
    mode: str  # "mock" or "real"
    rate_limit_real: int = 20      # req/sec
    rate_limit_mock: int = 5       # req/sec
    timeout: int = 10              # seconds
    max_retries: int = 3
```

### 4. API 스펙

#### 4.1 KIS OAuth 2.0 Token 발급
```http
POST https://openapi.koreainvestment.com:9443/oauth2/tokenP
Content-Type: application/json

{
    "grant_type": "client_credentials",
    "appkey": "{APP_KEY}",
    "appsecret": "{APP_SECRET}"
}

Response:
{
    "access_token": "eyJhbGc...",
    "token_type": "Bearer",
    "expires_in": 86400
}
```

#### 4.2 헬스체크 엔드포인트
```http
GET /api/kis/health

Response:
{
    "status": "healthy",
    "token_valid": true,
    "token_expires_at": "2024-11-09T10:30:00",
    "mode": "mock",
    "rate_limit": 5,
    "last_api_call": "2024-11-08T14:25:30"
}
```

---

## 🔧 Implementation Tasks

### Task 1: KIS API 계정 등록 및 환경 설정 (0.5일)

**목표**: KIS API 사용을 위한 계정 및 인증 정보 준비

**Steps**:
1. [ ] 한국투자증권 홈페이지 접속
   - URL: https://www.koreainvestment.com
   - "오픈API" 메뉴 이동

2. [ ] 실전투자 계정 생성
   - 이메일 인증
   - 약관 동의
   - 앱 등록 (앱 이름: "Craveny Stock Analysis")

3. [ ] App Key 및 App Secret 발급
   - 앱 상세 페이지에서 키 발급
   - 안전한 곳에 임시 저장 (복사)

4. [ ] `.env` 파일 업데이트
   ```bash
   # .env
   KIS_APP_KEY=PSxxxxxxxxxxxxxxxxxxxxxx
   KIS_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   KIS_BASE_URL=https://openapi.koreainvestment.com:9443
   KIS_MODE=mock  # mock: 모의투자, real: 실전투자
   ```

5. [ ] `.env.example` 업데이트
   ```bash
   # .env.example (템플릿)
   KIS_APP_KEY=your_app_key_here
   KIS_APP_SECRET=your_app_secret_here
   KIS_BASE_URL=https://openapi.koreainvestment.com:9443
   KIS_MODE=mock
   ```

**검증 기준**:
- ✅ `.env` 파일에 유효한 App Key/Secret 저장
- ✅ `.gitignore`에 `.env` 포함 확인
- ✅ `.env.example`이 템플릿으로 제공됨

---

### Task 2: KIS 설정 관리 모듈 구현 (0.5일)

**목표**: 환경별 설정을 관리하는 Config 클래스 구현

**Code**: `backend/config/kis_config.py`

```python
"""
KIS API 설정 관리 모듈
"""
import os
from dataclasses import dataclass
from typing import Literal
from functools import lru_cache


@dataclass
class KISConfig:
    """KIS API 설정 클래스"""

    app_key: str
    app_secret: str
    base_url: str
    mode: Literal["mock", "real"]

    # Rate Limiting
    rate_limit_per_sec: int

    # Timeout & Retry
    timeout: int = 10
    max_retries: int = 3
    retry_backoff_factor: float = 2.0

    # Token
    token_cache_ttl: int = 86400  # 24시간

    def __post_init__(self):
        """설정 검증"""
        if not self.app_key or not self.app_secret:
            raise ValueError("KIS_APP_KEY and KIS_APP_SECRET must be set")

        if self.mode not in ["mock", "real"]:
            raise ValueError(f"Invalid mode: {self.mode}. Must be 'mock' or 'real'")

        # Rate limit 설정
        if self.mode == "real":
            self.rate_limit_per_sec = 20
        else:  # mock
            self.rate_limit_per_sec = 5

    @property
    def is_mock(self) -> bool:
        """모의투자 모드 여부"""
        return self.mode == "mock"

    @property
    def token_url(self) -> str:
        """OAuth 토큰 발급 URL"""
        return f"{self.base_url}/oauth2/tokenP"


@lru_cache()
def get_kis_config() -> KISConfig:
    """
    KIS 설정 싱글톤 인스턴스 반환

    환경 변수에서 설정을 로드합니다.
    """
    return KISConfig(
        app_key=os.getenv("KIS_APP_KEY", ""),
        app_secret=os.getenv("KIS_APP_SECRET", ""),
        base_url=os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443"),
        mode=os.getenv("KIS_MODE", "mock"),
    )


# 싱글톤 인스턴스
kis_config = get_kis_config()
```

**검증 기준**:
- ✅ 환경 변수 로드 성공
- ✅ mode별 rate_limit 자동 설정
- ✅ 설정 검증 로직 작동

---

### Task 3: OAuth 2.0 인증 모듈 구현 (1일)

**목표**: Access Token 자동 발급 및 갱신

**Code**: `backend/kis/auth.py`

```python
"""
KIS API OAuth 2.0 인증 모듈
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx
from redis import Redis

from backend.config.kis_config import kis_config


logger = logging.getLogger(__name__)


class KISAuthManager:
    """KIS API 인증 관리자"""

    def __init__(self, redis_client: Optional[Redis] = None):
        self.config = kis_config
        self.redis = redis_client
        self._token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    async def get_access_token(self) -> str:
        """
        Access Token 반환 (자동 갱신)

        Returns:
            유효한 Access Token
        """
        # 1. 캐시된 토큰 확인
        if self._is_token_valid():
            logger.debug("Using cached access token")
            return self._token

        # 2. Redis 캐시 확인
        if self.redis:
            cached_token = self._get_token_from_redis()
            if cached_token:
                logger.debug("Using Redis cached access token")
                return cached_token

        # 3. 새 토큰 발급
        logger.info("Requesting new access token from KIS API")
        return await self._request_new_token()

    def _is_token_valid(self) -> bool:
        """토큰 유효성 검사"""
        if not self._token or not self._token_expires_at:
            return False

        # 만료 10분 전에 갱신
        return datetime.now() < (self._token_expires_at - timedelta(minutes=10))

    def _get_token_from_redis(self) -> Optional[str]:
        """Redis에서 토큰 조회"""
        if not self.redis:
            return None

        try:
            token_data = self.redis.get("kis:access_token")
            if token_data:
                # JSON 파싱
                import json
                data = json.loads(token_data)

                expires_at = datetime.fromisoformat(data["expires_at"])
                if datetime.now() < expires_at:
                    self._token = data["access_token"]
                    self._token_expires_at = expires_at
                    return self._token
        except Exception as e:
            logger.error(f"Failed to get token from Redis: {e}")

        return None

    async def _request_new_token(self) -> str:
        """
        KIS API에 새 토큰 요청

        Returns:
            Access Token

        Raises:
            httpx.HTTPError: API 호출 실패
        """
        url = self.config.token_url
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.config.app_key,
            "appsecret": self.config.app_secret
        }

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()

            data = response.json()

            # 토큰 저장
            self._token = data["access_token"]
            expires_in = data.get("expires_in", 86400)  # 기본 24시간
            self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)

            # Redis에 캐싱
            if self.redis:
                self._cache_token_to_redis(data)

            logger.info(f"New access token issued. Expires at: {self._token_expires_at}")

            return self._token

    def _cache_token_to_redis(self, token_data: dict):
        """Redis에 토큰 캐싱"""
        try:
            import json

            cache_data = {
                "access_token": token_data["access_token"],
                "expires_at": self._token_expires_at.isoformat(),
                "created_at": datetime.now().isoformat()
            }

            # TTL: 토큰 만료 시간
            ttl = int((self._token_expires_at - datetime.now()).total_seconds())

            self.redis.setex(
                "kis:access_token",
                ttl,
                json.dumps(cache_data)
            )

            logger.debug("Token cached to Redis")
        except Exception as e:
            logger.error(f"Failed to cache token to Redis: {e}")


# 싱글톤 인스턴스
_auth_manager: Optional[KISAuthManager] = None


def get_auth_manager(redis_client: Optional[Redis] = None) -> KISAuthManager:
    """
    KISAuthManager 싱글톤 반환
    """
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = KISAuthManager(redis_client)
    return _auth_manager
```

**검증 기준**:
- ✅ 토큰 발급 성공
- ✅ 토큰 만료 10분 전 자동 갱신
- ✅ Redis 캐싱 작동

---

### Task 4: KIS API 클라이언트 구현 (1.5일)

**목표**: 공통 HTTP 클라이언트 및 Rate Limiting 구현

**Code**: `backend/kis/client.py`

```python
"""
KIS API 클라이언트
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

import httpx
from redis import Redis

from backend.config.kis_config import kis_config
from backend.kis.auth import get_auth_manager
from backend.kis.exceptions import (
    KISAPIError,
    KISRateLimitError,
    KISAuthenticationError
)


logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate Limiter (Sliding Window)"""

    def __init__(self, max_requests_per_sec: int):
        self.max_requests = max_requests_per_sec
        self.requests: list[datetime] = []

    async def acquire(self):
        """Rate limit 획득 (필요 시 대기)"""
        now = datetime.now()

        # 1초 이전 요청 제거
        self.requests = [
            req_time for req_time in self.requests
            if (now - req_time).total_seconds() < 1.0
        ]

        # Rate limit 초과 시 대기
        if len(self.requests) >= self.max_requests:
            sleep_time = 1.0 - (now - self.requests[0]).total_seconds()
            if sleep_time > 0:
                logger.debug(f"Rate limit reached. Sleeping {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
                return await self.acquire()

        # 요청 기록
        self.requests.append(now)


class KISClient:
    """KIS API HTTP 클라이언트"""

    def __init__(self, redis_client: Optional[Redis] = None):
        self.config = kis_config
        self.auth_manager = get_auth_manager(redis_client)
        self.rate_limiter = RateLimiter(self.config.rate_limit_per_sec)

        self.base_url = self.config.base_url
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager 진입"""
        self.client = httpx.AsyncClient(
            timeout=self.config.timeout,
            limits=httpx.Limits(max_connections=100)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager 종료"""
        if self.client:
            await self.client.aclose()

    async def request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        KIS API 요청

        Args:
            method: HTTP 메서드 (GET, POST 등)
            endpoint: API 엔드포인트 (예: /uapi/domestic-stock/v1/quotations/inquire-price)
            headers: 추가 헤더
            params: 쿼리 파라미터
            json_data: JSON 바디
            retry_count: 재시도 횟수

        Returns:
            API 응답 JSON

        Raises:
            KISAPIError: API 호출 실패
            KISRateLimitError: Rate limit 초과
            KISAuthenticationError: 인증 실패
        """
        # Rate limiting
        await self.rate_limiter.acquire()

        # 인증 헤더 추가
        access_token = await self.auth_manager.get_access_token()

        request_headers = {
            "authorization": f"Bearer {access_token}",
            "appkey": self.config.app_key,
            "appsecret": self.config.app_secret,
            "content-type": "application/json; charset=utf-8"
        }

        if headers:
            request_headers.update(headers)

        # URL 구성
        url = f"{self.base_url}{endpoint}"

        logger.debug(f"{method} {url}")

        try:
            if not self.client:
                raise RuntimeError("Client not initialized. Use async context manager.")

            response = await self.client.request(
                method=method,
                url=url,
                headers=request_headers,
                params=params,
                json=json_data
            )

            # 응답 처리
            response.raise_for_status()

            data = response.json()

            # KIS API 에러 체크 (rt_cd)
            rt_cd = data.get("rt_cd")
            if rt_cd and rt_cd != "0":
                msg = data.get("msg1", "Unknown error")
                logger.error(f"KIS API Error: rt_cd={rt_cd}, msg={msg}")
                raise KISAPIError(f"KIS API Error: {msg} (code: {rt_cd})")

            return data

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                # 인증 오류 → 토큰 무효화 후 재시도
                logger.warning("Authentication failed. Invalidating token and retrying...")
                self.auth_manager._token = None

                if retry_count < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_backoff_factor ** retry_count)
                    return await self.request(
                        method, endpoint, headers, params, json_data, retry_count + 1
                    )

                raise KISAuthenticationError(f"Authentication failed after {retry_count} retries")

            elif e.response.status_code == 429:
                raise KISRateLimitError("Rate limit exceeded")

            else:
                logger.error(f"HTTP Error: {e.response.status_code} - {e.response.text}")
                raise KISAPIError(f"HTTP {e.response.status_code}: {e.response.text}")

        except httpx.RequestError as e:
            logger.error(f"Request Error: {e}")

            # 재시도
            if retry_count < self.config.max_retries:
                await asyncio.sleep(self.config.retry_backoff_factor ** retry_count)
                return await self.request(
                    method, endpoint, headers, params, json_data, retry_count + 1
                )

            raise KISAPIError(f"Request failed after {retry_count} retries: {e}")

    async def get(self, endpoint: str, headers: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict:
        """GET 요청"""
        return await self.request("GET", endpoint, headers=headers, params=params)

    async def post(self, endpoint: str, headers: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Dict:
        """POST 요청"""
        return await self.request("POST", endpoint, headers=headers, json_data=json_data)


# 싱글톤 팩토리
def get_kis_client(redis_client: Optional[Redis] = None) -> KISClient:
    """KIS Client 인스턴스 생성"""
    return KISClient(redis_client)
```

**Code**: `backend/kis/exceptions.py`

```python
"""
KIS API 커스텀 예외
"""


class KISAPIError(Exception):
    """KIS API 일반 에러"""
    pass


class KISAuthenticationError(KISAPIError):
    """인증 오류"""
    pass


class KISRateLimitError(KISAPIError):
    """Rate Limit 초과"""
    pass
```

**검증 기준**:
- ✅ Rate limiting 작동 (초당 5회/20회 제한)
- ✅ 인증 헤더 자동 추가
- ✅ 재시도 로직 작동 (exponential backoff)

---

### Task 5: 헬스체크 엔드포인트 구현 (0.5일)

**목표**: KIS API 연결 상태 확인 엔드포인트

**Code**: `backend/api/endpoints/kis_health.py`

```python
"""
KIS API 헬스체크 엔드포인트
"""
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.kis.client import get_kis_client
from backend.kis.auth import get_auth_manager
from backend.config.kis_config import kis_config


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/kis", tags=["KIS Health"])


class KISHealthResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str
    token_valid: bool
    token_expires_at: str | None
    mode: str
    rate_limit: int
    last_check: str


@router.get("/health", response_model=KISHealthResponse)
async def kis_health_check():
    """
    KIS API 연결 상태 확인

    Returns:
        KIS API 헬스 상태
    """
    try:
        auth_manager = get_auth_manager()

        # 토큰 발급 테스트
        token = await auth_manager.get_access_token()

        token_valid = auth_manager._is_token_valid()
        token_expires_at = (
            auth_manager._token_expires_at.isoformat()
            if auth_manager._token_expires_at
            else None
        )

        return KISHealthResponse(
            status="healthy",
            token_valid=token_valid,
            token_expires_at=token_expires_at,
            mode=kis_config.mode,
            rate_limit=kis_config.rate_limit_per_sec,
            last_check=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"KIS health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"KIS API unhealthy: {str(e)}"
        )
```

**Code**: `backend/main.py` (라우터 등록)

```python
# 기존 imports...
from backend.api.endpoints import kis_health

# FastAPI 앱
app = FastAPI(title="Craveny Stock Analysis API")

# 라우터 등록
app.include_router(kis_health.router)

# ... 기존 코드
```

**검증 기준**:
- ✅ `GET /api/kis/health` 호출 시 200 OK 응답
- ✅ 토큰 상태 정확히 반환

---

### Task 6: 통합 테스트 및 문서화 (1일)

**목표**: 전체 인증 플로우 테스트 및 문서 작성

**Code**: `tests/kis/test_auth.py`

```python
"""
KIS API 인증 테스트
"""
import pytest
from backend.kis.auth import get_auth_manager
from backend.kis.client import get_kis_client


@pytest.mark.asyncio
async def test_get_access_token():
    """Access Token 발급 테스트"""
    auth_manager = get_auth_manager()

    token = await auth_manager.get_access_token()

    assert token is not None
    assert len(token) > 0
    assert auth_manager._is_token_valid()


@pytest.mark.asyncio
async def test_token_caching():
    """토큰 캐싱 테스트"""
    auth_manager = get_auth_manager()

    # 첫 번째 호출
    token1 = await auth_manager.get_access_token()

    # 두 번째 호출 (캐시 사용)
    token2 = await auth_manager.get_access_token()

    assert token1 == token2


@pytest.mark.asyncio
async def test_kis_client_request():
    """KIS Client 기본 요청 테스트"""
    async with get_kis_client() as client:
        # 간단한 API 호출 (예: 주식 현재가 조회)
        response = await client.get(
            endpoint="/uapi/domestic-stock/v1/quotations/inquire-price",
            params={
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": "005930"  # 삼성전자
            },
            headers={
                "tr_id": "FHKST01010100"
            }
        )

        assert response is not None
        assert response.get("rt_cd") == "0"  # 성공
```

**Code**: `tests/api/test_kis_health.py`

```python
"""
KIS 헬스체크 엔드포인트 테스트
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app


client = TestClient(app)


def test_kis_health_endpoint():
    """헬스체크 엔드포인트 테스트"""
    response = client.get("/api/kis/health")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "token_valid" in data
    assert data["mode"] in ["mock", "real"]
```

**문서**: `docs/guides/kis-api-setup.md`

```markdown
# KIS API 설정 가이드

## 1. 계정 등록

1. [한국투자증권 홈페이지](https://www.koreainvestment.com) 접속
2. 오픈API 메뉴 → 앱 등록
3. App Key, App Secret 발급

## 2. 환경 변수 설정

`.env` 파일 생성:

\`\`\`bash
KIS_APP_KEY=your_app_key
KIS_APP_SECRET=your_app_secret
KIS_BASE_URL=https://openapi.koreainvestment.com:9443
KIS_MODE=mock  # mock: 모의투자, real: 실전투자
\`\`\`

## 3. 인증 테스트

\`\`\`bash
# 헬스체크
curl http://localhost:8000/api/kis/health

# 예상 응답
{
  "status": "healthy",
  "token_valid": true,
  "mode": "mock"
}
\`\`\`

## 4. Python 코드 예시

\`\`\`python
from backend.kis.client import get_kis_client

async with get_kis_client() as client:
    response = await client.get(
        endpoint="/uapi/domestic-stock/v1/quotations/inquire-price",
        params={"FID_INPUT_ISCD": "005930"},
        headers={"tr_id": "FHKST01010100"}
    )
    print(response)
\`\`\`
```

**검증 기준**:
- ✅ 모든 테스트 통과
- ✅ 문서 작성 완료

---

## 🧪 Testing Strategy

### Unit Tests
- `test_kis_config.py`: 설정 로드 및 검증
- `test_auth.py`: 토큰 발급, 갱신, 캐싱
- `test_client.py`: Rate limiting, 재시도 로직
- `test_exceptions.py`: 커스텀 예외

### Integration Tests
- `test_kis_health.py`: 헬스체크 엔드포인트
- `test_end_to_end_auth.py`: 전체 인증 플로우

### Manual Tests
- Mock 환경에서 실제 API 호출 테스트
- Rate limit 테스트 (초당 5회 제한 확인)
- Token 만료 시나리오 테스트

---

## 🚧 Known Issues & Risks

### 이슈 1: KIS API 서버 불안정
**Impact**: Medium | **Probability**: Low
**완화**: 재시도 로직, Circuit Breaker 패턴 적용

### 이슈 2: Token 만료 처리 지연
**Impact**: Low | **Probability**: Low
**완화**: 만료 10분 전 자동 갱신

### 이슈 3: Rate Limit 초과
**Impact**: High | **Probability**: Medium
**완화**: Sliding Window Rate Limiter, 요청 큐잉

---

## 📚 References

- [한국투자증권 OpenAPI 문서](https://apiportal.koreainvestment.com)
- [OAuth 2.0 스펙](https://oauth.net/2/)
- [httpx 공식 문서](https://www.python-httpx.org/)

---

## ✅ Definition of Done

- [x] KIS API 계정 등록 및 키 발급 완료
- [x] `.env` 파일 설정 완료 (KIS_APP_KEY, KIS_APP_SECRET 추가)
- [x] `backend/config.py` KIS 설정 추가
- [x] `backend/crawlers/kis_client.py` 구현 (OAuth 2.0 + Rate Limiting)
  - [x] TokenManager 클래스 (자동 토큰 갱신)
  - [x] RateLimiter 클래스 (Sliding Window)
  - [x] KISClient 클래스 (HTTP 요청, 재시도 로직)
- [x] `scripts/test_kis_auth.py` 테스트 스크립트 작성
- [x] 테스트 통과 확인
  - [x] Token 발급 성공
  - [x] 현재가 조회 성공 (삼성전자: 97,900원)
  - [x] Rate Limiting 정상 작동 (초당 5건, 1.00초 소요)
- [ ] 문서 작성 (`docs/guides/kis-api-setup.md`) - Optional
- [ ] 코드 리뷰 - 다음 Story와 함께 진행
- [ ] main 브랜치 머지 - 다음 Story와 함께 진행
