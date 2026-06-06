/**
 * Live evidence agent client for Lovable app.
 *
 * Set in Lovable → Settings → Environment variables:
 *   VITE_AGENT_API_URL = https://your-ngrok-url.ngrok-free.app
 *   VITE_AGENT_API_KEY = same value as AGENT_API_KEY in backend .env
 */

const BASE = import.meta.env.VITE_AGENT_API_URL?.replace(/\/$/, "") ?? "";
const API_KEY = import.meta.env.VITE_AGENT_API_KEY ?? "";

export type AgentStatus = "idle" | "running" | "done" | "complete" | "error" | "busy";

export interface PendingPaper {
  id: string;
  ref: string;
  topic?: string;
  year?: number;
  relevance_score?: number;
  status: "needs_review" | "approved" | "rejected";
  source_url?: string;
  reason?: string;
}

export interface AgentState {
  agent: {
    state?: AgentStatus;
    status?: AgentStatus;
    message: string;
    progress?: number;
    result?: Record<string, unknown>;
  };
  last_run?: string | null;
  counts?: { trials: number; papers: number; pending: number };
  trial_count: number;
  paper_count: number;
  pending_review_count: number;
  pending_papers: PendingPaper[];
  meta?: { version?: string; last_agent_refresh?: string };
}

function agentStateValue(agent: AgentState["agent"]): AgentStatus {
  return (agent.state ?? agent.status ?? "idle") as AgentStatus;
}

function normalizeTrials(data: unknown): unknown {
  if (Array.isArray(data)) return { trials: data, meta: {} };
  return data;
}

function normalizePapers(data: unknown): unknown {
  if (Array.isArray(data)) return { papers: data, updated: "" };
  return data;
}

async function agentFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  if (!BASE) {
    throw new Error("VITE_AGENT_API_URL is not set. Add your ngrok/public agent URL in Lovable env.");
  }
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "ngrok-skip-browser-warning": "1",
    ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
    ...(options.headers as Record<string, string> | undefined),
  };
  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Agent API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function checkAgentHealth(): Promise<{ ok: boolean }> {
  return agentFetch("/api/health");
}

export async function getAgentStatus(): Promise<AgentState> {
  return agentFetch("/api/status");
}

export async function runEvidenceSearch(): Promise<{ status: string; message: string }> {
  return agentFetch("/api/search", { method: "POST", body: "{}" });
}

export async function refreshWatchedTrials(): Promise<{ status: string; updates: unknown[] }> {
  return agentFetch("/api/refresh", { method: "POST", body: "{}" });
}

export async function approvePaper(paperId: string): Promise<PendingPaper> {
  return agentFetch("/api/approve", {
    method: "POST",
    body: JSON.stringify({ paper_id: paperId }),
  });
}

export async function rejectPaper(paperId: string, reason = ""): Promise<{ ok: boolean }> {
  return agentFetch("/api/reject", {
    method: "POST",
    body: JSON.stringify({ paper_id: paperId, reason }),
  });
}

export interface ReviewQueueItem extends PendingPaper {
  title?: string;
  url?: string;
  n?: number;
  nct_id?: string;
  pmid?: string;
  source?: string;
  review?: {
    scope_verdict: string;
    suggestion: string;
    pros: string[];
    cons: string[];
    relevance_score?: number;
  };
}

export async function fetchReviewQueue(): Promise<ReviewQueueItem[]> {
  return agentFetch("/api/pending");
}

export async function fetchPendingPapers(): Promise<PendingPaper[]> {
  return agentFetch("/api/pending");
}

export async function fetchLiveTrials(): Promise<unknown> {
  return normalizeTrials(await agentFetch("/api/trials"));
}

export async function fetchLivePapers(): Promise<unknown> {
  return normalizePapers(await agentFetch("/api/papers"));
}

export async function fetchLiveInterpretations(): Promise<unknown> {
  return agentFetch("/api/interpretations");
}

export async function fetchLivePatientProfile(): Promise<unknown> {
  return agentFetch("/api/patient-profile");
}

export async function fetchGlossaryPathway(): Promise<unknown> {
  return agentFetch("/api/glossary-pathway");
}

export async function fetchPatientsLikeYou(): Promise<unknown> {
  return agentFetch("/api/patients-like-you");
}

export interface DashboardChartSpec {
  id: string;
  order: number;
  title: string;
  question: string;
  what_it_shows: string;
  chart_type: string;
  x_axis?: string;
  y_axis?: string;
  color_meaning?: string;
  data_source?: string;
  caveats?: string[];
  takeaway?: string;
  wrong_setting_banner?: string;
  tooltip_fields?: string[];
  series?: unknown;
  categories?: Record<string, string>;
}

export interface DashboardChartsData {
  page_title?: string;
  page_intro?: string;
  profile_reminder?: string;
  legend?: Record<string, unknown>;
  charts?: DashboardChartSpec[];
}

export async function fetchDashboardCharts(): Promise<DashboardChartsData> {
  return agentFetch("/api/dashboard-charts");
}

export interface GlossaryPathwayData {
  scope?: string;
  pathway?: { title?: string; steps?: Array<{ id: string; label: string; detail: string }>; key_fork?: string };
  glossary?: Array<{ term: string; definition: string }>;
}

export interface LiveDataset {
  trials: unknown;
  papers: unknown;
  interpretations: unknown;
  patientProfile: unknown;
  glossaryPathway: GlossaryPathwayData;
  patientsLikeYou: unknown;
  dashboardCharts: DashboardChartsData;
}

/** True when Lovable env has a backend URL configured. */
export function isLiveDataEnabled(): boolean {
  return Boolean(BASE);
}

/** Load all datasets from your local PC via ngrok (always current). */
export async function fetchAllLiveData(): Promise<LiveDataset> {
  const [trials, papers, interpretations, patientProfile, glossaryPathway, patientsLikeYou, dashboardCharts] =
    await Promise.all([
      fetchLiveTrials(),
      fetchLivePapers(),
      fetchLiveInterpretations(),
      fetchLivePatientProfile(),
      fetchGlossaryPathway(),
      fetchPatientsLikeYou(),
      fetchDashboardCharts(),
    ]);
  return { trials, papers, interpretations, patientProfile, glossaryPathway, patientsLikeYou, dashboardCharts };
}

/** Poll until agent finishes a scan (max ~3 min). */
export async function pollUntilDone(
  onTick?: (state: AgentState) => void,
  intervalMs = 2000,
  maxAttempts = 90
): Promise<AgentState> {
  for (let i = 0; i < maxAttempts; i++) {
    const state = await getAgentStatus();
    onTick?.(state);
    const s = agentStateValue(state.agent);
    if (s === "done" || s === "complete" || s === "error" || s === "idle") {
      return state;
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error("Agent scan timed out");
}
