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
