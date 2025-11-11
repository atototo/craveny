# Epic 3: 사용자 인증 및 권한 관리 시스템 - PRD

**버전**: 1.0
**작성일**: 2025-11-10
**작성자**: Mary (Business Analyst)
**상태**: Draft

---

## 1. Epic 개요

### 1.1 Epic 목표

기존 Craveny 시스템에 **이메일/비밀번호 기반 사용자 인증 시스템**과 **역할 기반 접근 제어(RBAC)**를 추가하여, 일반 사용자와 관리자를 구분하고 각 권한에 맞는 메뉴 접근을 제어합니다.

**주요 달성 목표**:
- ✅ 이메일/비밀번호 기반 로그인 시스템 구축
- ✅ 세션 쿠키 방식 인증 (24시간 유지)
- ✅ 일반사용자(user) / 관리자(admin) 역할 구분
- ✅ 권한별 메뉴 접근 제어 (일반: 대시보드+종목분석, 관리자: 전체)
- ✅ 관리자 전용 사용자 관리 페이지 (생성/수정/삭제)
- ✅ 기본 관리자 계정 자동 생성

---

## 2. 기능 요구사항 (Functional Requirements)

### FR1: 사용자 인증

**FR1.1**: 시스템은 이메일과 비밀번호를 사용한 로그인 기능을 제공해야 한다.
- 이메일은 주 식별자로 사용 (Unique)
- 비밀번호는 bcrypt 해싱하여 저장 (10 rounds)
- 비밀번호 최소 8자 이상

**FR1.2**: 로그인 성공 시 세션 쿠키를 생성하고, 24시간 동안 유지해야 한다.
- Signed Cookie 방식 (FastAPI 기본 기능 사용)
- HttpOnly, SameSite=Lax 플래그 설정

**FR1.3**: 시스템은 로그아웃 기능을 제공하며, 세션 쿠키를 무효화해야 한다.

**FR1.4**: 비로그인 사용자가 보호된 페이지 접근 시, 자동으로 `/login` 페이지로 리다이렉트해야 한다.

### FR2: 권한 기반 접근 제어 (RBAC)

**FR2.1**: 시스템은 두 가지 사용자 역할을 지원해야 한다:
- `user` (일반사용자): 대시보드(`/`), 종목 분석(`/stocks`) 접근
- `admin` (관리자): 모든 메뉴 접근

**FR2.2**: 각 페이지는 최소 권한 원칙에 따라 접근 제어를 적용해야 한다.

| 페이지 | 일반사용자 (user) | 관리자 (admin) |
|--------|-------------------|----------------|
| `/` (대시보드) | ✅ | ✅ |
| `/stocks` (종목 분석) | ✅ | ✅ |
| `/stocks/[code]` (종목 상세) | ✅ | ✅ |
| `/predictions` | ❌ | ✅ |
| `/models` | ❌ | ✅ |
| `/ab-config` | ❌ | ✅ |
| `/ab-test` | ❌ | ✅ |
| `/admin/*` (모든 관리자 페이지) | ❌ | ✅ |

**FR2.3**: 네비게이션 메뉴는 사용자 역할에 따라 동적으로 필터링되어야 한다.

### FR3: 사용자 관리 (관리자 전용)

**FR3.1**: 관리자는 `/admin/users` 페이지에서 새 사용자를 생성할 수 있어야 한다.
- 필수 입력: 이메일, 닉네임, 비밀번호, 역할(user/admin)
- 이메일 중복 체크
- 비밀번호 최소 8자 검증

**FR3.2**: 관리자는 사용자 목록을 조회할 수 있어야 한다.
- 페이지네이션 지원 (20건/페이지)
- 이메일, 닉네임, 역할, 활성 상태, 생성일 표시

**FR3.3**: 관리자는 사용자의 비밀번호를 변경할 수 있어야 한다.

**FR3.4**: 관리자는 사용자를 삭제하거나 비활성화할 수 있어야 한다.
- 삭제: 물리적 삭제 (DB에서 제거)
- 비활성화: `is_active = false` (소프트 삭제)

### FR4: 기본 관리자 계정

**FR4.1**: 시스템 최초 배포 시 기본 관리자 계정을 자동 생성해야 한다.
- 이메일: `admin@craveny.com`
- 닉네임: `관리자`
- 비밀번호: 환경 변수 `ADMIN_DEFAULT_PASSWORD`에서 로드
- 역할: `admin`
- 계정이 이미 존재하면 생성하지 않음 (멱등성)

---

## 3. 비기능 요구사항 (Non-Functional Requirements)

### NFR1: 보안

**NFR1.1**: 비밀번호는 bcrypt 알고리즘으로 해싱하여 저장해야 한다 (cost factor: 10).

**NFR1.2**: 세션 쿠키는 다음 보안 플래그를 포함해야 한다:
- `HttpOnly`: JavaScript 접근 방지
- `SameSite=Lax`: CSRF 공격 방지
- `Secure`: HTTPS 환경에서만 전송 (프로덕션)

**NFR1.3**: 관리자 API 엔드포인트는 `role='admin'` 검증을 필수로 수행해야 한다.

### NFR2: 성능

**NFR2.1**: 로그인 API 응답 시간은 500ms 이내여야 한다.

**NFR2.2**: 세션 검증 오버헤드는 10ms 이내여야 한다.

### NFR3: 확장성

**NFR3.1**: 시스템은 최소 100명의 사용자를 지원해야 한다 (MVP 목표).

### NFR4: 사용성

**NFR4.1**: 로그인 실패 시 명확한 에러 메시지를 표시해야 한다.
- "이메일 또는 비밀번호가 올바르지 않습니다"

**NFR4.2**: 비밀번호 입력 필드는 마스킹 처리되어야 한다.

---

## 4. User Stories

### Story 3.1: 데이터베이스 스키마 및 기본 관리자 생성

**As a** 시스템 관리자
**I want** 사용자 정보를 저장할 데이터베이스 테이블이 생성되고 기본 관리자 계정이 자동 생성되도록
**so that** 시스템 배포 즉시 관리자가 로그인하여 사용자를 관리할 수 있다.

#### Acceptance Criteria

1. `users` 테이블이 다음 컬럼으로 생성된다:
   - `id` (SERIAL, PRIMARY KEY)
   - `email` (VARCHAR(255), UNIQUE, NOT NULL)
   - `nickname` (VARCHAR(100), NOT NULL)
   - `password_hash` (VARCHAR(255), NOT NULL)
   - `role` (VARCHAR(20), NOT NULL, DEFAULT 'user')
   - `is_active` (BOOLEAN, DEFAULT TRUE)
   - `created_at` (TIMESTAMP WITH TIME ZONE, DEFAULT NOW())
   - `updated_at` (TIMESTAMP WITH TIME ZONE, DEFAULT NOW())

2. 인덱스가 생성된다:
   - `idx_users_email` ON `email`
   - `idx_users_role` ON `role`

3. DB 마이그레이션 스크립트 (`scripts/init_auth_db.py`)가 제공된다.

4. 스크립트 실행 시 기본 관리자 계정이 생성된다:
   - 이메일: `admin@craveny.com`
   - 닉네임: `관리자`
   - 비밀번호: `.env` 파일의 `ADMIN_DEFAULT_PASSWORD`
   - 역할: `admin`
   - 계정이 이미 존재하면 스킵

5. 로컬 테스트: 기본 관리자로 로그인 성공.

---

### Story 3.2: 로그인/로그아웃 API 구현

**As a** 사용자
**I want** 이메일과 비밀번호로 로그인하고 로그아웃할 수 있도록
**so that** 시스템에 안전하게 인증된 상태로 접근할 수 있다.

#### Acceptance Criteria

1. `POST /api/auth/login` 엔드포인트가 구현된다:
   - Request Body: `{"email": "string", "password": "string"}`
   - Response 200: `{"user": {"id": 1, "email": "...", "nickname": "...", "role": "..."}}`
   - Response 401: `{"detail": "이메일 또는 비밀번호가 올바르지 않습니다"}`

2. 로그인 성공 시:
   - 비밀번호 해시 검증 (bcrypt)
   - 세션 쿠키 생성 (24시간 만료)
   - 쿠키 플래그: `HttpOnly`, `SameSite=Lax`

3. `POST /api/auth/logout` 엔드포인트가 구현된다:
   - 세션 쿠키 삭제
   - Response 200: `{"message": "로그아웃 되었습니다"}`

4. `GET /api/auth/me` 엔드포인트가 구현된다:
   - 현재 로그인된 사용자 정보 반환
   - Response 200 (로그인 상태): `{"id": 1, "email": "...", "nickname": "...", "role": "..."}`
   - Response 401 (비로그인): `{"detail": "인증이 필요합니다"}`

5. 인증 미들웨어가 구현된다:
   - `get_current_user()`: 세션 쿠키 검증 및 사용자 조회
   - `require_admin()`: 관리자 권한 검증

6. 로컬 테스트:
   - 유효한 자격 증명으로 로그인 성공
   - 잘못된 비밀번호로 로그인 실패 (401)
   - 로그아웃 후 `/api/auth/me` 호출 시 401 반환

---

### Story 3.3: 로그인 페이지 및 인증 Context (Frontend)

**As a** 사용자
**I want** 로그인 페이지에서 이메일/비밀번호를 입력하여 로그인하고
**so that** 대시보드에 접근할 수 있다.

#### Acceptance Criteria

1. `/login` 페이지가 생성된다:
   - 이메일 입력 필드 (type="email", required)
   - 비밀번호 입력 필드 (type="password", required, 마스킹)
   - 로그인 버튼
   - 로그인 실패 시 에러 메시지 표시

2. 로그인 성공 시:
   - 사용자 정보를 Context에 저장
   - 이전 페이지로 리다이렉트 (또는 `/`)

3. 인증 Context Provider가 구현된다 (`app/contexts/AuthContext.tsx`):
   - `useAuth()` 훅 제공
   - 상태: `user`, `loading`, `login()`, `logout()`
   - `/api/auth/me` 호출하여 초기 인증 상태 확인

4. 루트 레이아웃 (`app/layout.tsx`)에 AuthProvider 적용.

5. 로컬 테스트:
   - 로그인 폼 입력 → 로그인 성공 → 대시보드 이동
   - 잘못된 비밀번호 입력 → 에러 메시지 표시

---

### Story 3.4: Protected Routes 및 권한 체크

**As a** 시스템
**I want** 비로그인 사용자를 로그인 페이지로 리다이렉트하고, 권한 없는 페이지 접근을 차단하도록
**so that** 인증된 사용자만 서비스를 이용할 수 있다.

#### Acceptance Criteria

1. Protected Route 래퍼 컴포넌트가 구현된다 (`app/components/ProtectedRoute.tsx`):
   - 비로그인 사용자 → `/login?redirect={current_path}` 리다이렉트
   - 권한 부족 사용자 → 403 에러 페이지 표시

2. 모든 보호 페이지에 `ProtectedRoute` 적용:
   - `/` (대시보드): `requiredRole: null` (로그인만 필요)
   - `/stocks`: `requiredRole: null`
   - `/admin/*`: `requiredRole: 'admin'`

3. 403 에러 페이지 구현 (`app/forbidden/page.tsx`):
   - "접근 권한이 없습니다" 메시지 표시
   - 대시보드로 돌아가기 버튼

4. 로컬 테스트:
   - 비로그인 상태로 `/` 접근 → `/login` 리다이렉트
   - 일반사용자로 `/admin/dashboard` 접근 → 403 에러
   - 관리자로 모든 페이지 접근 가능

---

### Story 3.5: 관리자 전용 사용자 관리 페이지

**As a** 관리자
**I want** `/admin/users` 페이지에서 사용자를 생성/조회/수정/삭제할 수 있도록
**so that** 시스템 사용자를 효율적으로 관리할 수 있다.

#### Acceptance Criteria

**Backend APIs**:

1. `POST /api/users` (사용자 생성, 관리자 전용):
   - Request Body: `{"email": "...", "nickname": "...", "password": "...", "role": "user|admin"}`
   - 이메일 중복 체크
   - 비밀번호 8자 이상 검증
   - Response 201: 생성된 사용자 정보

2. `GET /api/users` (사용자 목록 조회, 관리자 전용):
   - Query Params: `page` (default: 1), `page_size` (default: 20)
   - Response 200: `{"items": [...], "total": 50, "page": 1, "page_size": 20}`

3. `PATCH /api/users/{user_id}` (사용자 수정, 관리자 전용):
   - Request Body: `{"password": "..."}` (비밀번호 변경)
   - Response 200: `{"message": "비밀번호가 변경되었습니다"}`

4. `DELETE /api/users/{user_id}` (사용자 삭제, 관리자 전용):
   - 물리적 삭제 또는 `is_active = false`
   - Response 200: `{"message": "사용자가 삭제되었습니다"}`

**Frontend UI (`/admin/users`)**:

5. 사용자 목록 테이블:
   - 컬럼: ID, 이메일, 닉네임, 역할, 활성 상태, 생성일, 액션
   - 페이지네이션 (20건/페이지)

6. 사용자 생성 폼 (모달 또는 별도 섹션):
   - 입력: 이메일, 닉네임, 비밀번호, 역할 선택
   - 유효성 검증: 이메일 형식, 비밀번호 8자 이상

7. 사용자 액션 버튼:
   - 비밀번호 변경 (모달)
   - 삭제/비활성화 (확인 다이얼로그)

8. 로컬 테스트:
   - 관리자로 로그인 → 사용자 생성 성공
   - 일반사용자 생성 → 로그인 가능 확인
   - 사용자 비밀번호 변경 → 새 비밀번호로 로그인 성공
   - 사용자 삭제 → 로그인 불가

---

### Story 3.6: 권한별 네비게이션 메뉴 필터링

**As a** 사용자
**I want** 내 권한에 맞는 메뉴만 네비게이션 바에 표시되도록
**so that** 접근할 수 없는 메뉴를 보지 않고 깔끔한 UI를 경험할 수 있다.

#### Acceptance Criteria

1. `Navigation.tsx` 컴포넌트가 수정된다:
   - `useAuth()` 훅으로 현재 사용자 정보 조회
   - 각 메뉴 링크에 `allowedRoles` 속성 추가
   - 사용자 역할에 따라 메뉴 필터링

2. 메뉴 권한 매핑:
   ```typescript
   const links = [
     { href: "/", label: "대시보드", allowedRoles: ["user", "admin"] },
     { href: "/stocks", label: "종목 분석", allowedRoles: ["user", "admin"] },
     { href: "/predictions", label: "예측 이력", allowedRoles: ["admin"] },
     { href: "/models", label: "🤖 모델 관리", allowedRoles: ["admin"] },
     // ... 나머지 관리자 메뉴
   ];
   ```

3. 로그아웃 버튼 추가:
   - 네비게이션 바 오른쪽 끝에 배치
   - 클릭 시 `logout()` 호출 → `/login` 리다이렉트

4. 현재 사용자 정보 표시 (선택적):
   - 네비게이션 바에 "안녕하세요, {닉네임}님" 표시

5. 로컬 테스트:
   - 일반사용자 로그인 → 대시보드, 종목 분석만 표시
   - 관리자 로그인 → 모든 메뉴 표시
   - 로그아웃 버튼 클릭 → 로그인 페이지 이동

---

## 5. API 명세서

### 5.1 인증 API

#### POST /api/auth/login

로그인 요청

**Request**:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response 200**:
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "nickname": "홍길동",
    "role": "user"
  }
}
```

**Response 401**:
```json
{
  "detail": "이메일 또는 비밀번호가 올바르지 않습니다"
}
```

---

#### POST /api/auth/logout

로그아웃 요청

**Response 200**:
```json
{
  "message": "로그아웃 되었습니다"
}
```

---

#### GET /api/auth/me

현재 로그인 사용자 조회

**Response 200** (로그인 상태):
```json
{
  "id": 1,
  "email": "user@example.com",
  "nickname": "홍길동",
  "role": "user"
}
```

**Response 401** (비로그인):
```json
{
  "detail": "인증이 필요합니다"
}
```

---

### 5.2 사용자 관리 API (관리자 전용)

#### POST /api/users

사용자 생성 (관리자 전용)

**Request**:
```json
{
  "email": "newuser@example.com",
  "nickname": "신규사용자",
  "password": "password123",
  "role": "user"
}
```

**Response 201**:
```json
{
  "id": 2,
  "email": "newuser@example.com",
  "nickname": "신규사용자",
  "role": "user",
  "is_active": true,
  "created_at": "2025-11-10T10:00:00+09:00"
}
```

**Response 400** (중복 이메일):
```json
{
  "detail": "이미 존재하는 이메일입니다"
}
```

**Response 403** (권한 없음):
```json
{
  "detail": "관리자 권한이 필요합니다"
}
```

---

#### GET /api/users

사용자 목록 조회 (관리자 전용)

**Query Parameters**:
- `page`: int (default: 1)
- `page_size`: int (default: 20)

**Response 200**:
```json
{
  "items": [
    {
      "id": 1,
      "email": "admin@craveny.com",
      "nickname": "관리자",
      "role": "admin",
      "is_active": true,
      "created_at": "2025-10-01T00:00:00+09:00"
    },
    {
      "id": 2,
      "email": "user@example.com",
      "nickname": "일반사용자",
      "role": "user",
      "is_active": true,
      "created_at": "2025-11-10T09:00:00+09:00"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 20
}
```

---

#### PATCH /api/users/{user_id}

사용자 비밀번호 변경 (관리자 전용)

**Request**:
```json
{
  "password": "newpassword123"
}
```

**Response 200**:
```json
{
  "message": "비밀번호가 변경되었습니다"
}
```

**Response 404**:
```json
{
  "detail": "사용자를 찾을 수 없습니다"
}
```

---

#### DELETE /api/users/{user_id}

사용자 삭제 (관리자 전용)

**Response 200**:
```json
{
  "message": "사용자가 삭제되었습니다"
}
```

**Response 404**:
```json
{
  "detail": "사용자를 찾을 수 없습니다"
}
```

---

## 6. 데이터베이스 스키마

### users 테이블

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    nickname VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',  -- 'user' | 'admin'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
```

---

## 7. 기술 스택 추가 사항

### Backend (Python)

**추가 라이브러리** (`requirements.txt`):
```txt
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
python-multipart==0.0.6  # 이미 있음
```

### Frontend (Next.js)

**추가 라이브러리 없음** - React Context API 사용

---

## 8. 구현 우선순위

### Phase 1: 기본 인증 (핵심, 2-3일)
- ✅ Story 3.1: DB 스키마 및 기본 관리자 생성
- ✅ Story 3.2: 로그인/로그아웃 API
- ✅ Story 3.3: 로그인 페이지 및 인증 Context
- ✅ Story 3.4: Protected Routes 및 권한 체크

### Phase 2: 사용자 관리 (2일)
- ✅ Story 3.5: 관리자 전용 사용자 관리 페이지

### Phase 3: UX 개선 (1일)
- ✅ Story 3.6: 권한별 네비게이션 메뉴 필터링

**총 예상 소요 시간**: 5-6일

---

## 9. 보안 고려사항

1. **비밀번호 보안**:
   - bcrypt 해싱 (cost factor: 10)
   - 평문 비밀번호 절대 로깅 금지

2. **세션 보안**:
   - HttpOnly 쿠키 (XSS 방지)
   - SameSite=Lax (CSRF 방지)
   - Secure 플래그 (HTTPS 환경)

3. **API 보안**:
   - 관리자 API는 `require_admin()` 미들웨어 필수
   - 민감 정보 응답에서 제외 (비밀번호 해시 등)

4. **입력 검증**:
   - Pydantic 모델로 자동 검증
   - 이메일 형식, 비밀번호 길이 체크

---

## 10. 테스팅 전략

### Unit Tests
- `test_password_hashing()`: bcrypt 해싱/검증
- `test_create_user()`: 사용자 생성 로직
- `test_authenticate_user()`: 로그인 검증

### Integration Tests
- `test_login_api()`: 로그인 API 전체 플로우
- `test_protected_endpoint()`: 권한 체크 미들웨어
- `test_admin_user_creation()`: 관리자 전용 API

### E2E Tests (Manual)
- 로그인 → 대시보드 접근
- 일반사용자로 관리자 페이지 접근 시도 (403)
- 관리자로 사용자 생성 → 새 사용자로 로그인

---

## 11. 다음 단계

이 PRD를 검토 후 개발 팀에 전달하여 구현을 시작합니다.

**권장 개발 순서**:
1. Story 3.1 (DB 스키마) - Backend
2. Story 3.2 (로그인 API) - Backend
3. Story 3.3 (로그인 페이지) - Frontend
4. Story 3.4 (Protected Routes) - Frontend
5. Story 3.5 (사용자 관리) - Backend + Frontend
6. Story 3.6 (메뉴 필터링) - Frontend

**예상 일정**: 5-6일 (1명 풀타임 기준)
