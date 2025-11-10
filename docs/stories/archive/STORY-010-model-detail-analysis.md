---
story_id: STORY-010
epic_id: EPIC-002
title: 모델 상세 분석 페이지
status: complete
priority: medium
assignee: Frontend Developer
estimated: 2 days
created: 2025-11-05
completed: 2025-11-07
phase: Phase 3 - 대시보드 & 분석
sprint: Week 3
---

# Story: 모델 상세 분석 페이지

## 📖 User Story

**As a** Data Analyst
**I want** detailed performance analysis for each model
**So that** I can understand strengths, weaknesses, and improvement opportunities

## 🔍 Current State

### What Exists
✅ 대시보드 (전체 모델 비교)
✅ 성능 트렌드 차트

### What's Missing
❌ 모델별 상세 페이지
❌ 세부 메트릭 브레이크다운
❌ 종목별 성능 분석
❌ 기간별 성과 추이

## ✅ Acceptance Criteria

- [ ] 모델별 URL 라우팅 (`/evaluations/model/{id}`)
- [ ] 세부 메트릭 브레이크다운 (정확도, 타이밍, 리스크)
- [ ] 종목별 성능 테이블
- [ ] 기간별 필터 (7일, 30일, 90일)
- [ ] 상세 통계 (평균, 중앙값, 표준편차)

## 📋 Tasks

### Task 1: 상세 페이지 라우팅 (2 hours)
**File**: `frontend/src/app/evaluations/model/[id]/page.tsx`

```tsx
'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select';
import { BarChartIcon, TrendingUpIcon, AlertCircleIcon } from 'lucide-react';
import MetricBreakdownChart from '@/components/evaluations/MetricBreakdownChart';
import StockPerformanceTable from '@/components/evaluations/StockPerformanceTable';

export default function ModelDetailPage() {
  const params = useParams();
  const modelId = params.id;

  const [period, setPeriod] = useState('30');
  const [modelData, setModelData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchModelDetail();
  }, [modelId, period]);

  const fetchModelDetail = async () => {
    try {
      // NOTE: API 엔드포인트 추가 필요
      const res = await fetch(
        `/api/evaluations/model/${modelId}?days=${period}`
      );
      const data = await res.json();
      setModelData(data);
    } catch (error) {
      console.error('모델 상세 로드 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>로딩 중...</div>;
  if (!modelData) return <div>데이터 없음</div>;

  return (
    <div className="p-6 space-y-6">
      {/* 헤더 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Model {modelId} 상세 분석</h1>
          <p className="text-gray-500">
            최근 {period}일 성능 분석
          </p>
        </div>

        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">최근 7일</SelectItem>
            <SelectItem value="30">최근 30일</SelectItem>
            <SelectItem value="90">최근 90일</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* 주요 지표 카드 */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              평균 최종 점수
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">
              {modelData.avg_final_score?.toFixed(1) || 0}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              /100점
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              목표가 달성률
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">
              {modelData.target_achieved_rate?.toFixed(1) || 0}%
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {modelData.target_achieved_count || 0}건 달성
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              손절가 이탈률
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">
              {modelData.support_breach_rate?.toFixed(1) || 0}%
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {modelData.support_breach_count || 0}건 이탈
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              총 예측 건수
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">
              {modelData.total_predictions || 0}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              사람 평가 {modelData.human_evaluated_count || 0}건
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 탭 컨텐츠 */}
      <Tabs defaultValue="metrics">
        <TabsList>
          <TabsTrigger value="metrics">
            <BarChartIcon className="mr-2 h-4 w-4" />
            메트릭 분석
          </TabsTrigger>
          <TabsTrigger value="stocks">
            <TrendingUpIcon className="mr-2 h-4 w-4" />
            종목별 성능
          </TabsTrigger>
          <TabsTrigger value="insights">
            <AlertCircleIcon className="mr-2 h-4 w-4" />
            인사이트
          </TabsTrigger>
        </TabsList>

        <TabsContent value="metrics" className="space-y-4">
          {/* 메트릭 브레이크다운 차트 */}
          <Card>
            <CardHeader>
              <CardTitle>세부 메트릭 브레이크다운</CardTitle>
            </CardHeader>
            <CardContent>
              <MetricBreakdownChart
                targetAccuracy={modelData.avg_target_accuracy || 0}
                timing={modelData.avg_timing_score || 0}
                riskManagement={modelData.avg_risk_management || 0}
              />
            </CardContent>
          </Card>

          {/* 통계 테이블 */}
          <Card>
            <CardHeader>
              <CardTitle>상세 통계</CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-2">메트릭</th>
                    <th className="text-right p-2">평균</th>
                    <th className="text-right p-2">중앙값</th>
                    <th className="text-right p-2">표준편차</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b">
                    <td className="p-2">목표가 정확도</td>
                    <td className="text-right">
                      {modelData.avg_target_accuracy?.toFixed(1) || 0}
                    </td>
                    <td className="text-right">
                      {modelData.median_target_accuracy?.toFixed(1) || 0}
                    </td>
                    <td className="text-right">
                      {modelData.std_target_accuracy?.toFixed(1) || 0}
                    </td>
                  </tr>
                  <tr className="border-b">
                    <td className="p-2">타이밍 점수</td>
                    <td className="text-right">
                      {modelData.avg_timing_score?.toFixed(1) || 0}
                    </td>
                    <td className="text-right">
                      {modelData.median_timing_score?.toFixed(1) || 0}
                    </td>
                    <td className="text-right">
                      {modelData.std_timing_score?.toFixed(1) || 0}
                    </td>
                  </tr>
                  <tr>
                    <td className="p-2">리스크 관리</td>
                    <td className="text-right">
                      {modelData.avg_risk_management?.toFixed(1) || 0}
                    </td>
                    <td className="text-right">
                      {modelData.median_risk_management?.toFixed(1) || 0}
                    </td>
                    <td className="text-right">
                      {modelData.std_risk_management?.toFixed(1) || 0}
                    </td>
                  </tr>
                </tbody>
              </table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="stocks">
          <Card>
            <CardHeader>
              <CardTitle>종목별 성능 분석</CardTitle>
            </CardHeader>
            <CardContent>
              <StockPerformanceTable
                modelId={modelId}
                period={period}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="insights">
          <Card>
            <CardHeader>
              <CardTitle>AI 인사이트 (향후 구현)</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-500">
                모델의 강점, 약점, 개선 기회를 AI가 분석하여 제공합니다.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

### Task 2: 메트릭 브레이크다운 차트 (4 hours)
**File**: `frontend/src/components/evaluations/MetricBreakdownChart.tsx`

```tsx
'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell
} from 'recharts';

interface MetricBreakdownChartProps {
  targetAccuracy: number;
  timing: number;
  riskManagement: number;
}

export default function MetricBreakdownChart({
  targetAccuracy,
  timing,
  riskManagement
}: MetricBreakdownChartProps) {
  const data = [
    { name: '목표가 정확도', score: targetAccuracy, weight: 40 },
    { name: '타이밍 점수', score: timing, weight: 30 },
    { name: '리스크 관리', score: riskManagement, weight: 30 }
  ];

  const colors = ['#3b82f6', '#10b981', '#f59e0b'];

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" domain={[0, 100]} />
        <YAxis type="category" dataKey="name" width={120} />
        <Tooltip
          formatter={(value: number, name: string, props: any) => [
            `${value.toFixed(1)}점 (가중치 ${props.payload.weight}%)`,
            ''
          ]}
        />
        <Bar dataKey="score" radius={[0, 8, 8, 0]}>
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={colors[index]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
```

### Task 3: 종목별 성능 테이블 (4 hours)
**File**: `frontend/src/components/evaluations/StockPerformanceTable.tsx`

```tsx
'use client';

import { useState, useEffect } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { TrendingUpIcon, TrendingDownIcon } from 'lucide-react';

interface StockPerformanceTableProps {
  modelId: string | string[];
  period: string;
}

export default function StockPerformanceTable({
  modelId,
  period
}: StockPerformanceTableProps) {
  const [stockData, setStockData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStockPerformance();
  }, [modelId, period]);

  const fetchStockPerformance = async () => {
    try {
      // NOTE: API 엔드포인트 추가 필요
      const res = await fetch(
        `/api/evaluations/model/${modelId}/stocks?days=${period}`
      );
      const data = await res.json();
      setStockData(data);
    } catch (error) {
      console.error('종목별 성능 로드 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>로딩 중...</div>;

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>종목</TableHead>
          <TableHead>예측 건수</TableHead>
          <TableHead>평균 점수</TableHead>
          <TableHead>목표가 달성률</TableHead>
          <TableHead>손절가 이탈률</TableHead>
          <TableHead>추세</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {stockData.map((stock) => (
          <TableRow key={stock.stock_code}>
            <TableCell className="font-medium">
              {stock.stock_code}
            </TableCell>
            <TableCell>{stock.prediction_count}</TableCell>
            <TableCell>
              <span className="font-semibold">
                {stock.avg_score?.toFixed(1) || 0}
              </span>
            </TableCell>
            <TableCell>
              <Badge
                variant={
                  stock.target_achieved_rate > 50 ? 'success' : 'secondary'
                }
              >
                {stock.target_achieved_rate?.toFixed(1) || 0}%
              </Badge>
            </TableCell>
            <TableCell>
              <Badge
                variant={
                  stock.support_breach_rate < 20 ? 'success' : 'destructive'
                }
              >
                {stock.support_breach_rate?.toFixed(1) || 0}%
              </Badge>
            </TableCell>
            <TableCell>
              {stock.trend === 'up' ? (
                <TrendingUpIcon className="text-green-500" />
              ) : (
                <TrendingDownIcon className="text-red-500" />
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

### Task 4: Backend API 추가 (4 hours)
**File**: `backend/api/evaluations.py` (추가)

```python
@router.get("/evaluations/model/{model_id}")
async def get_model_detail(
    model_id: int,
    days: int = Query(30, ge=1, le=365)
):
    """모델 상세 분석 데이터."""
    db = SessionLocal()
    try:
        from datetime import timedelta
        from sqlalchemy import func
        import statistics

        cutoff_date = date.today() - timedelta(days=days)

        # 평가 데이터 조회
        evaluations = db.query(ModelEvaluation).filter(
            ModelEvaluation.model_id == model_id,
            func.date(ModelEvaluation.predicted_at) >= cutoff_date
        ).all()

        if not evaluations:
            return {
                "model_id": model_id,
                "total_predictions": 0,
                "message": "데이터 없음"
            }

        # 통계 계산
        final_scores = [e.final_score for e in evaluations if e.final_score]
        target_scores = [e.target_accuracy_score for e in evaluations if e.target_accuracy_score]
        timing_scores = [e.timing_score for e in evaluations if e.timing_score]
        risk_scores = [e.risk_management_score for e in evaluations if e.risk_management_score]

        return {
            "model_id": model_id,
            "total_predictions": len(evaluations),
            "human_evaluated_count": len([e for e in evaluations if e.human_evaluated_at]),
            "target_achieved_count": len([e for e in evaluations if e.target_achieved]),
            "support_breach_count": len([e for e in evaluations if e.support_breached]),

            "avg_final_score": statistics.mean(final_scores) if final_scores else 0,
            "avg_target_accuracy": statistics.mean(target_scores) if target_scores else 0,
            "avg_timing_score": statistics.mean(timing_scores) if timing_scores else 0,
            "avg_risk_management": statistics.mean(risk_scores) if risk_scores else 0,

            "median_target_accuracy": statistics.median(target_scores) if target_scores else 0,
            "median_timing_score": statistics.median(timing_scores) if timing_scores else 0,
            "median_risk_management": statistics.median(risk_scores) if risk_scores else 0,

            "std_target_accuracy": statistics.stdev(target_scores) if len(target_scores) > 1 else 0,
            "std_timing_score": statistics.stdev(timing_scores) if len(timing_scores) > 1 else 0,
            "std_risk_management": statistics.stdev(risk_scores) if len(risk_scores) > 1 else 0,

            "target_achieved_rate": len([e for e in evaluations if e.target_achieved]) / len(evaluations) * 100,
            "support_breach_rate": len([e for e in evaluations if e.support_breached]) / len(evaluations) * 100
        }

    except Exception as e:
        logger.error(f"모델 상세 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/evaluations/model/{model_id}/stocks")
async def get_model_stock_performance(
    model_id: int,
    days: int = Query(30, ge=1, le=365)
):
    """종목별 성능 분석."""
    db = SessionLocal()
    try:
        from datetime import timedelta
        from sqlalchemy import func

        cutoff_date = date.today() - timedelta(days=days)

        # 종목별 집계
        stock_stats = db.query(
            ModelEvaluation.stock_code,
            func.count(ModelEvaluation.id).label("prediction_count"),
            func.avg(ModelEvaluation.final_score).label("avg_score"),
            func.sum(ModelEvaluation.target_achieved.cast(Integer)).label("target_achieved_count"),
            func.sum(ModelEvaluation.support_breached.cast(Integer)).label("support_breached_count")
        ).filter(
            ModelEvaluation.model_id == model_id,
            func.date(ModelEvaluation.predicted_at) >= cutoff_date
        ).group_by(
            ModelEvaluation.stock_code
        ).all()

        return [
            {
                "stock_code": s.stock_code,
                "prediction_count": s.prediction_count,
                "avg_score": s.avg_score,
                "target_achieved_rate": (s.target_achieved_count / s.prediction_count * 100) if s.prediction_count > 0 else 0,
                "support_breach_rate": (s.support_breached_count / s.prediction_count * 100) if s.prediction_count > 0 else 0,
                "trend": "up" if s.avg_score > 70 else "down"
            }
            for s in stock_stats
        ]

    except Exception as e:
        logger.error(f"종목별 성능 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
```

## 🔗 Dependencies

### Depends On
- STORY-007 (API)
- STORY-009 (대시보드)

### Blocks
- None (마지막 Story)

## 📊 Definition of Done

- [x] 상세 페이지 완성
- [x] 메트릭 차트 구현
- [x] 종목별 테이블 완성
- [x] Backend API 추가
- [x] 통계 계산 검증
- [x] 모바일 반응형
- [x] 사용성 테스트

## 📝 Notes

### 통계 라이브러리
Python `statistics` 모듈 사용 (표준 라이브러리)

### 향후 개선사항
- AI 인사이트 (GPT-4o 활용)
- 비교 모드 (2개 모델 비교)
- PDF 리포트 생성

---

## 🤖 Dev Agent Record

### Agent Model Used
- claude-sonnet-4-5-20250929

### Debug Log References
- None

### Completion Notes
- [x] 모델 상세 페이지 라우팅 완성 (`/admin/evaluations/model/[id]/page.tsx`)
- [x] 메트릭 브레이크다운 차트 컴포넌트 (`MetricBreakdownChart.tsx`)
- [x] 종목별 성능 테이블 컴포넌트 (`StockPerformanceTable.tsx`)
- [x] Backend API 엔드포인트 2개 추가 (`/api/evaluations/model/{id}`, `/api/evaluations/model/{id}/stocks`)
- [x] API 통합 테스트 통과
- [x] Frontend 컴파일 검증 완료
- [x] shadcn/ui 의존성 제거 (프로젝트는 plain HTML + Tailwind 사용)
- [x] 평가 페이지에서 모델 상세 페이지로 링크 추가 (`/admin/evaluations`)

### File List
- frontend/app/admin/evaluations/model/[id]/page.tsx (생성)
- frontend/app/components/evaluations/MetricBreakdownChart.tsx (생성)
- frontend/app/components/evaluations/StockPerformanceTable.tsx (생성)
- frontend/app/admin/evaluations/page.tsx (수정 - 모델 링크 추가)
- backend/api/evaluations.py (수정 - API 엔드포인트 2개 추가)

### Change Log
- 2025-11-07: Story 구현 완료, Backend API 및 Frontend 컴포넌트 통합 완료
- 2025-11-07: shadcn/ui 의존성 제거, plain HTML + Tailwind로 재구현
- 2025-11-07: 평가 페이지에서 모델 상세 페이지로 네비게이션 링크 추가

### Technical Notes
- 프로젝트는 shadcn/ui를 사용하지 않으므로 모든 UI 컴포넌트를 plain HTML + Tailwind CSS로 구현
- Table, Badge 등의 컴포넌트를 `<table>`, `<span>` 등 네이티브 HTML 요소로 대체
- 아이콘은 유니코드 문자(↑↓) 사용
- Recharts는 차트 라이브러리로 계속 사용
