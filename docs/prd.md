# craveny - Product Requirements Document

**Author:** young
**Date:** 2025-11-11
**Version:** 1.0

---

## Executive Summary

개인 투자자와 소규모 팀이 언제든 접속해 최신 AI 예측과 뉴스 인사이트를 받아볼 수 있도록 Craveny 전체 스택을 24시간 운용 가능한 형태로 배포한다. Next.js 대시보드·FastAPI 백엔드·텔레그램 알림·데이터 파이프라인을 t3.small 수준의 EC2 + Docker Compose 환경에서 경제적으로 제공하는 것이 핵심이다.

### What Makes This Special

모델별 AI 분석을 한눈에 비교해 투자자가 자신만의 전략을 즉시 세울 수 있는 경험.

---

## Project Classification

**Technical Type:** saas_b2b
**Domain:** fintech
**Complexity:** high

- 구성: Next.js 15 대시보드 + FastAPI 백엔드 + Telegram 알림 + Postgres/Redis/Milvus 데이터 스택
- 운영 목표: 단일 t3.small 기반에서 24시간 무중단 운영
- 배포 범위: EC2 + Docker Compose, 텔레그램 연결, 스케줄러 + 크롤러 + 알림 파이프라인 포함

### Domain Context

국내 증권 뉴스·거래 데이터를 다루는 서비스로서 KRX/KIS 등 금융 데이터 소스와 규제(개인정보, 투자자 보호)를 염두에 둬야 한다. 실시간 신뢰도가 중요하므로 데이터 품질·보안·로그 추적이 필수다.

---

## Success Criteria

- EC2(t3.small) + Docker Compose 환경에서 백엔드·프론트·DB·알림·데이터 파이프 전체를 24시간 무중단으로 가동한다.
- 외부에서 대시보드 접속/로그인 후 모델별 비교 화면이 끊김 없이 로딩된다.
- 예측 API 및 헬스체크 엔드포인트가 200 응답을 유지한다.
- 텔레그램 알림 테스트 메시지가 정상 발송된다.

### Business Metrics

- 비용 효율성: 단일 t3.small(or 동급) 인스턴스만으로 운영 가능해야 함.

---

## Product Scope

### MVP - Minimum Viable Product

- 현재 구현된 모든 기능(대시보드, 예측 API, 알림, 스케줄러, 크롤러)을 그대로 안정적으로 배포
- Compose 스택(Postgres, Redis, Milvus 등) 포함하여 운영 자동화 스크립트 정비

### Growth Features (Post-MVP)

- 스케줄 조정 UI/자동화를 추가하여 크롤러·알림 주기를 대시보드에서 관리

### Vision (Future)

- 현재 별도 확장 아이디어 없음 (추후 필요 시 정의)

---

## Functional Requirements

1. 사용자는 웹 대시보드에 로그인하고 관심 종목을 선택해 모델별 비교 화면을 본다.
2. 텔레그램 봇 구독자는 동일한 분석 결과를 실시간으로 알림으로 수신한다.
3. 백엔드 스케줄러는 데이터 크롤링·예측 연산을 주기적으로 실행하고 결과를 캐시/DB에 적재한다.
4. 배포 스크립트/문서가 제공되어 언제든 동일한 환경을 재현 가능해야 한다.

---

## Non-Functional Requirements

### Performance

- 대시보드 주요 화면 로딩 시간을 3초 이내로 유지 (모델 비교 테이블 기준).

### Reliability

- 모든 서비스 컨테이너가 재시작 정책을 가지며, 장애 시 자동 복구된다.
- 헬스체크/로그를 통해 24시간 가동 여부를 확인할 수 있다.

### Security

- SSH 접근은 제한하며, 환경 변수·토큰(OPENAI/OpenRouter/Telegram 등)은 `.env`나 SSM에서 안전하게 관리한다.

---

## Implementation Planning

### Epic Breakdown Required

요구사항은 추후 epics-stories 워크플로를 통해 세부 에픽/스토리로 분해한다.

---

## References

- 문서화 인덱스: docs/index.md
- 인프라 노트: docs/deployment-infrastructure.md
- 통합 구조: docs/integration-architecture.md

---

## Next Steps

1. **Epic & Story Breakdown** - Run: `workflow epics-stories`
2. **UX Design** (필요 시) - Run: `workflow ux-design`
3. **Architecture** - Run: `workflow create-architecture`

---

_이 PRD는 Craveny가 제공하는 “모델별 AI 분석 비교 경험”을 24시간 안정적으로 배포하기 위한 요구사항을 담고 있다._
