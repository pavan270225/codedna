import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import type { RatioResponse } from '../types';

interface RatioChartProps {
  data: RatioResponse;
  size?: number;
}

const COLORS = {
  human: '#22c55e',
  ai: '#3b82f6',
  ambiguous: '#a855f7',
};

interface ChartDataEntry {
  name: string;
  value: number;
  color: string;
}

function CustomTooltip({ active, payload, chartData }: { active?: boolean; payload?: Array<{ name: string; value: number; color: string }>; chartData: ChartDataEntry[] }) {
  if (!active || !payload || !payload.length) return null;

  const entry = payload[0];
  const dataEntry = chartData.find(d => d.name === entry.name);
  const value = dataEntry?.value ?? 0;

  return (
    <div style={{
      background: 'var(--vscode-editor-background)',
      border: '1px solid var(--vscode-panel-border)',
      borderRadius: '6px',
      padding: '8px 12px',
      boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
      color: 'var(--vscode-foreground)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: entry.color }} />
        <span style={{ fontWeight: '500' }}>{entry.name}</span>
      </div>
      <div style={{ marginTop: '4px', fontSize: '13px' }}>
        {value} lines ({(value / (chartData.reduce((s, d) => s + d.value, 0) || 1) * 100).toFixed(1)}%)
      </div>
    </div>
  );
}

export function RatioChart({ data, size = 200 }: RatioChartProps) {
  const chartData: ChartDataEntry[] = [
    { name: 'Human', value: data.human, color: COLORS.human },
    { name: 'AI', value: data.ai, color: COLORS.ai },
  ].filter(d => d.value > 0);

  if (chartData.length === 0) {
    return (
      <div style={{ width: size, height: size, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#888' }}>
        No data
      </div>
    );
  }

  return (
    <div style={{ width: size, height: size }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={size * 0.35}
            outerRadius={size * 0.45}
            paddingAngle={2}
            dataKey="value"
            nameKey="name"
            label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(1)}%`}
            labelLine={false}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip chartData={chartData} />} labelFormatter={(name) => name} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}