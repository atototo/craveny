# 개발 가이드

## 프로세스 관리 (중요!)

**⚠️ 이 프로젝트는 PM2를 사용하여 백그라운드로 실행됩니다.**

코드 변경 후에는 반드시 PM2를 통해 재시작해야 변경사항이 적용됩니다.

### 변경사항 적용 방법

#### 백엔드 코드 변경 시
```bash
# 백엔드만 재시작
pm2 restart craveny-backend

# 로그 확인
pm2 logs craveny-backend
```

#### 프론트엔드 코드 변경 시
```bash
# 프론트엔드만 재시작
pm2 restart craveny-frontend

# 로그 확인
pm2 logs craveny-frontend
```

#### 모든 서비스 재시작
```bash
# 전체 재시작 (백엔드, 프론트엔드, ngrok)
pm2 restart all

# 상태 확인
pm2 status
```

#### 의존성 변경 시 (requirements.txt, package.json)
```bash
# 백엔드 의존성 변경
cd /Users/young/ai-work/craveny
uv sync
pm2 restart craveny-backend

# 프론트엔드 의존성 변경
cd /Users/young/ai-work/craveny/frontend
npm install
pm2 restart craveny-frontend
```

### 개발 서버 URL

- **프론트엔드**: http://localhost:3030
- **백엔드 API**: http://localhost:8000
- **백엔드 Docs**: http://localhost:8000/docs
- **ngrok Public URL**: https://craveny.ngrok.app

### 주요 명령어

```bash
# 서비스 상태 확인
pm2 status

# 실시간 로그 보기
pm2 logs

# 특정 서비스 로그
pm2 logs craveny-backend
pm2 logs craveny-frontend

# 서비스 중지
pm2 stop all

# 서비스 시작
pm2 start ecosystem.config.js

# 서비스 삭제
pm2 delete all
```

### 로그 파일 위치

```
logs/
├── backend-out.log
├── backend-error.log
├── frontend-out.log
├── frontend-error.log
├── ngrok-out.log
└── ngrok-error.log
```

## 일반적인 개발 워크플로우

### 1. 코드 수정
- 백엔드: `backend/` 디렉토리의 Python 파일 수정
- 프론트엔드: `frontend/` 디렉토리의 TypeScript/React 파일 수정

### 2. 변경사항 테스트
```bash
# 서비스 재시작
pm2 restart craveny-backend  # 또는 craveny-frontend

# 로그로 에러 확인
pm2 logs craveny-backend --lines 50
```

### 3. Git 커밋
```bash
git add .
git commit -m "feat: 기능 추가"
git push origin main
```

## 트러블슈팅

### 서비스가 동작하지 않을 때

1. **PM2 상태 확인**
   ```bash
   pm2 status
   ```

2. **로그 확인**
   ```bash
   pm2 logs --lines 100
   ```

3. **포트 충돌 확인**
   ```bash
   lsof -ti:8000  # 백엔드
   lsof -ti:3030  # 프론트엔드
   ```

4. **강제 재시작**
   ```bash
   pm2 delete all
   pm2 start ecosystem.config.js
   ```

### ngrok 연결 끊김

```bash
# ngrok 재시작
pm2 restart craveny-ngrok

# ngrok 상태 확인
curl http://127.0.0.1:4040/api/tunnels
```

## 참고 문서

- **PM2 상세 가이드**: [PM2.md](../PM2.md)
- **백엔드 API 문서**: http://localhost:8000/docs
- **프론트엔드 컴포넌트**: `frontend/app/` 디렉토리
