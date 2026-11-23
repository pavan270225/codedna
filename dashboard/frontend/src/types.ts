export interface RatioResponse {
  human: number;
  ai: number;
  total: number;
  human_pct: number;
}

export interface AttributionResponse {
  file: string;
  start_line: number;
  end_line: number;
  label: string;
  confidence: number;
  timestamp: string;
  source_hint: string | null;
}

export interface FileRatioResponse {
  file: string;
  human: number;
  ai: number;
  ambiguous: number;
  human_pct: number;
}

export interface DashboardSummary {
  total_files: number;
  total_attributions: number;
  human_lines: number;
  ai_lines: number;
  ambiguous_lines: number;
  by_label: Record<string, number>;
  human_pct: number;
}