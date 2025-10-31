# Craveny Product Requirements Document (PRD)

**Version:** 1.1
**Date:** 2025-10-27
**Status:** Validated - Ready for Architecture

---

## PRD Sections

이 PRD는 다음 Epic 섹션으로 분할되었습니다:

- [Epic 1: 데이터 수집 및 저장 인프라](./epic-1-data-infrastructure.md)
- [Epic 2: LLM 기반 예측 및 알림 시스템](./epic-2-llm-prediction-notifications.md)

전체 문서는 [docs/prd.md](../prd.md)를 참조하세요.

## Epic Overview

### Epic 1: 데이터 수집 및 저장 인프라

**목표:** 프로젝트 기반 설정을 완료하고, 뉴스/주가 데이터를 자동으로 수집하여 벡터 DB에 저장하는 안정적인 파이프라인을 구축한다. 최소한의 헬스체크 엔드포인트를 제공하여 시스템이 작동 중임을 확인할 수 있다.

**Stories:** 1.1 ~ 1.9 (9개 스토리)

### Epic 2: LLM 기반 예측 및 알림 시스템

**목표:** 수집된 데이터를 기반으로 LLM + RAG 예측 엔진을 구현하고, 시간대별 맞춤 전략 메시지를 생성하여 텔레그램으로 자동 알림을 전송하는 완전한 end-to-end 시스템을 완성한다.

**Stories:** 2.1 ~ 2.8 (8개 스토리)

---

*PRD v1.1 검증 완료 - 2025-10-27*
*BMAD-METHOD™ 프레임워크 사용*
