import type {
  RatioResponse,
  AttributionResponse,
  FileRatioResponse,
  DashboardSummary,
} from './types';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8081';

async function fetchJson<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export const api = {
  health: () => fetchJson<{ status: string }>('/api/health'),
  summary: () => fetchJson<DashboardSummary>('/api/summary'),
  globalRatio: () => fetchJson<RatioResponse>('/api/ratio'),
  fileRatio: (file: string) => fetchJson<FileRatioResponse>(`/api/ratio/${encodeURIComponent(file)}`),
  attributions: (params?: { file?: string; limit?: number; offset?: number }) => {
    const search = new URLSearchParams();
    if (params?.file) search.set('file', params.file);
    if (params?.limit) search.set('limit', String(params.limit));
    if (params?.offset) search.set('offset', String(params.offset));
    return fetchJson<AttributionResponse[]>(`/api/attributions?${search.toString()}`);
  },
  files: () => fetchJson<string[]>('/api/files'),
  trends: (days = 30) => fetchJson<Record<string, unknown>>(`/api/trends?days=${days}`),
};