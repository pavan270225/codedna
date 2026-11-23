interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
  subtitle?: string;
}

export function StatCard({ title, value, icon, color, subtitle }: StatCardProps) {
  return (
    <div style={{
      background: 'var(--vscode-editor-background)',
      border: '1px solid var(--vscode-panel-border)',
      borderRadius: '8px',
      padding: '16px',
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div style={{
          background: `${color}20`,
          color,
          padding: '8px',
          borderRadius: '6px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          {icon}
        </div>
        <span style={{ fontSize: '14px', color: 'var(--vscode-descriptionForeground)' }}>
          {title}
        </span>
      </div>
      <div style={{ fontSize: '28px', fontWeight: '600', color: 'var(--vscode-foreground)' }}>
        {value}
      </div>
      {subtitle && (
        <div style={{ fontSize: '12px', color: 'var(--vscode-descriptionForeground)' }}>
          {subtitle}
        </div>
      )}
    </div>
  );
}