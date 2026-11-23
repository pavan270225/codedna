import { useEffect, useState } from 'react';
import { Brain, User, HelpCircle, FileText, RefreshCw } from 'lucide-react';
import { RatioChart } from './components/RatioChart';
import { StatCard } from './components/StatCard';
import { api } from './api';
import type { DashboardSummary, RatioResponse, AttributionResponse, FileRatioResponse } from './types';
import './App.css';

function App() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [globalRatio, setGlobalRatio] = useState<RatioResponse | null>(null);
  const [fileRatios, setFileRatios] = useState<FileRatioResponse[]>([]);
  const [attributions, setAttributions] = useState<AttributionResponse[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    try {
      setLoading(true);
      setError(null);
      const [summaryData, ratioData, filesData] = await Promise.all([
        api.summary(),
        api.globalRatio(),
        api.files(),
      ]);
      setSummary(summaryData);
      setGlobalRatio(ratioData);

      // Load file ratios
      const fileRatiosData = await Promise.all(
        filesData.map(f => api.fileRatio(f))
      );
      setFileRatios(fileRatiosData);

      // Load attributions for first file or all
      if (filesData.length > 0) {
        const attrs = await api.attributions({ limit: 50 });
        setAttributions(attrs);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }

  const handleRefresh = () => {
    loadData();
  };

  const handleFileSelect = async (file: string) => {
    setSelectedFile(file);
    try {
      const attrs = await api.attributions({ file, limit: 100 });
      setAttributions(attrs);
    } catch (e) {
      console.error('Failed to load attributions:', e);
    }
  };

  const getLabelColor = (label: string) => {
    switch (label.toLowerCase()) {
      case 'human': return '#22c55e';
      case 'ai-generated': return '#3b82f6';
      case 'ai-modified': return '#f97316';
      case 'ambiguous': return '#a855f7';
      default: return '#888';
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <div style={{ fontSize: '18px', color: 'var(--vscode-descriptionForeground)' }}>
          Loading CodeDNA Dashboard...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', padding: '20px' }}>
        <div style={{ textAlign: 'center', color: 'var(--vscode-errorForeground)' }}>
          <h2>Error loading dashboard</h2>
          <p>{error}</p>
          <button onClick={handleRefresh} style={{ marginTop: '16px', padding: '8px 16px' }}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--vscode-editor-background)',
      color: 'var(--vscode-foreground)',
      fontFamily: 'var(--vscode-font-family)',
      padding: '24px',
    }}>
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Brain style={{ width: 32, height: 32, color: '#3b82f6' }} />
          <h1 style={{ margin: 0, fontSize: '24px', fontWeight: '600' }}>CodeDNA Dashboard</h1>
        </div>
        <button onClick={handleRefresh} disabled={loading} style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          padding: '8px 16px', background: 'var(--vscode-button-background)',
          color: 'var(--vscode-button-foreground)', border: 'none',
          borderRadius: '6px', cursor: loading ? 'not-allowed' : 'pointer',
          opacity: loading ? 0.6 : 1,
        }}>
          <RefreshCw style={{ width: 16, height: 16 }} />
          Refresh
        </button>
      </header>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '16px',
        marginBottom: '24px',
      }}>
        <StatCard
          title="Human Lines"
          value={summary?.human_lines.toLocaleString() ?? 0}
          icon={<User size={20} />}
          color="#22c55e"
          subtitle={`${summary?.human_pct?.toFixed(1) ?? 0}%`}
        />
        <StatCard
          title="AI Lines"
          value={summary?.ai_lines.toLocaleString() ?? 0}
          icon={<Brain size={20} />}
          color="#3b82f6"
        />
        <StatCard
          title="Ambiguous"
          value={summary?.ambiguous_lines.toLocaleString() ?? 0}
          icon={<HelpCircle size={20} />}
          color="#a855f7"
        />
        <StatCard
          title="Files Tracked"
          value={summary?.total_files ?? 0}
          icon={<FileText size={20} />}
          color="#eab308"
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
        <div>
          <h2 style={{ marginBottom: '16px', fontSize: '18px' }}>Global H/AI Ratio</h2>
          <div style={{
            background: 'var(--vscode-editor-background)',
            border: '1px solid var(--vscode-panel-border)',
            borderRadius: '8px',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '16px',
            minHeight: '300px',
          }}>
            <RatioChart data={globalRatio ?? { human: 0, ai: 0, total: 0, human_pct: 0 }} size={240} />
            <div style={{ textAlign: 'center', color: 'var(--vscode-descriptionForeground)' }}>
              <p style={{ margin: 0, fontSize: '14px' }}>
                {globalRatio?.human_pct?.toFixed(1) ?? 0}% human-written
              </p>
            </div>
          </div>
        </div>

        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h2 style={{ margin: 0, fontSize: '18px' }}>File Breakdown</h2>
            <span style={{ fontSize: '12px', color: 'var(--vscode-descriptionForeground)' }}>
              {fileRatios.length} files tracked
            </span>
          </div>
          <div style={{
            background: 'var(--vscode-editor-background)',
            border: '1px solid var(--vscode-panel-border)',
            borderRadius: '8px',
            overflow: 'hidden',
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: 'var(--vscode-editor-inactiveSelectionBackground)' }}>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--vscode-panel-border)' }}>File</th>
                  <th style={{ padding: '12px', textAlign: 'right', borderBottom: '1px solid var(--vscode-panel-border)' }}>Human</th>
                  <th style={{ padding: '12px', textAlign: 'right', borderBottom: '1px solid var(--vscode-panel-border)' }}>AI</th>
                  <th style={{ padding: '12px', textAlign: 'right', borderBottom: '1px solid var(--vscode-panel-border)' }}>Amb.</th>
                  <th style={{ padding: '12px', textAlign: 'right', borderBottom: '1px solid var(--vscode-panel-border)' }}>Human %</th>
                </tr>
              </thead>
              <tbody>
                {fileRatios.map((fr, i) => (
                  <tr key={fr.file} style={{
                    cursor: 'pointer',
                    background: selectedFile === fr.file ? 'var(--vscode-list-activeSelectionBackground)' : i % 2 === 0 ? 'transparent' : 'var(--vscode-editor-inactiveSelectionBackground)',
                  }} onClick={() => handleFileSelect(fr.file)}>
                    <td style={{ padding: '10px 12px', borderBottom: '1px solid var(--vscode-panel-border)', fontFamily: 'var(--vscode-editor-font-family)', fontSize: '12px' }}>
                      {fr.file.split('/').pop() || fr.file}
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'right', borderBottom: '1px solid var(--vscode-panel-border)', color: '#22c55e' }}>
                      {fr.human}
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'right', borderBottom: '1px solid var(--vscode-panel-border)', color: '#3b82f6' }}>
                      {fr.ai}
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'right', borderBottom: '1px solid var(--vscode-panel-border)', color: '#a855f7' }}>
                      {fr.ambiguous}
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'right', borderBottom: '1px solid var(--vscode-panel-border)', fontWeight: '500' }}>
                      {fr.human_pct.toFixed(1)}%
                    </td>
                  </tr>
                ))}
                {fileRatios.length === 0 && (
                  <tr>
                    <td colSpan={5} style={{ padding: '40px', textAlign: 'center', color: 'var(--vscode-descriptionForeground)' }}>
                      No attribution data yet. Open files in VS Code with CodeDNA extension.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {selectedFile && (
        <div style={{ marginTop: '24px' }}>
          <h2 style={{ marginBottom: '16px', fontSize: '18px' }}>Attributions for {selectedFile}</h2>
          <div style={{
            background: 'var(--vscode-editor-background)',
            border: '1px solid var(--vscode-panel-border)',
            borderRadius: '8px',
            overflow: 'hidden',
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr style={{ background: 'var(--vscode-editor-inactiveSelectionBackground)' }}>
                  <th style={{ padding: '10px', textAlign: 'left', borderBottom: '1px solid var(--vscode-panel-border)' }}>Lines</th>
                  <th style={{ padding: '10px', textAlign: 'left', borderBottom: '1px solid var(--vscode-panel-border)' }}>Label</th>
                  <th style={{ padding: '10px', textAlign: 'right', borderBottom: '1px solid var(--vscode-panel-border)' }}>Confidence</th>
                  <th style={{ padding: '10px', textAlign: 'left', borderBottom: '1px solid var(--vscode-panel-border)' }}>Source</th>
                </tr>
              </thead>
              <tbody>
                {attributions.map((a, i) => (
                  <tr key={`${a.file}-${a.start_line}-${a.end_line}`} style={{ background: i % 2 === 0 ? 'transparent' : 'var(--vscode-editor-inactiveSelectionBackground)' }}>
                    <td style={{ padding: '8px', borderBottom: '1px solid var(--vscode-panel-border)', fontFamily: 'var(--vscode-editor-font-family)' }}>
                      {a.start_line}–{a.end_line}
                    </td>
                    <td style={{ padding: '8px', borderBottom: '1px solid var(--vscode-panel-border)' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontWeight: '500',
                        background: `${getLabelColor(a.label)}20`,
                        color: getLabelColor(a.label),
                      }}>
                        {a.label}
                      </span>
                    </td>
                    <td style={{ padding: '8px', textAlign: 'right', borderBottom: '1px solid var(--vscode-panel-border)' }}>
                      {(a.confidence * 100).toFixed(0)}%
                    </td>
                    <td style={{ padding: '8px', borderBottom: '1px solid var(--vscode-panel-border)', color: 'var(--vscode-descriptionForeground)', fontSize: '11px' }}>
                      {a.source_hint || '—'}
                    </td>
                  </tr>
                ))}
                {attributions.length === 0 && (
                  <tr>
                    <td colSpan={4} style={{ padding: '40px', textAlign: 'center', color: 'var(--vscode-descriptionForeground)' }}>
                      No attributions for this file
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  );
}

export default App;