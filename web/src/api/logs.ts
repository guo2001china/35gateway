import { api35Request } from "./api35";

export type UsageLogListItem = {
  request_id: string;
  created_at: string | null;
  model: string;
  status: string;
  power_amount: string | null;
  duration_ms: number | null;
};

export type UsageLogListResponse = {
  total: number;
  page: number;
  size: number;
  items: UsageLogListItem[];
};

export type UsageProviderAttempt = {
  attempt_no: number;
  provider_code: string;
  provider_account_id: number | null;
  provider_account_short_id: string | null;
  provider_account_owner_type: string | null;
  model_code: string;
  provider_request_id: string | null;
  http_status_code: number | null;
  status: string;
  duration_ms: number | null;
  fallback_reason: string | null;
  error_message: string | null;
};

export type UsageTaskSummary = {
  platform_task_id: string;
  provider_code: string;
  provider_account_id: number | null;
  provider_account_short_id: string | null;
  provider_account_owner_type: string | null;
  provider_task_id: string | null;
  status: string;
  created_at: string | null;
  updated_at: string | null;
  finished_at: string | null;
};

export type UsageLogDetailResponse = {
  request_id: string;
  model: string;
  route_group: string;
  request_path: string;
  status: string;
  created_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  power_amount: string | null;
  sale_amount: string | null;
  request_headers: Record<string, unknown>;
  request_summary: Record<string, unknown> | null;
  response_summary: Record<string, unknown> | null;
  chain: UsageProviderAttempt[];
  task: UsageTaskSummary | null;
  error_message: string | null;
};

type ListUsageLogsParams = {
  page?: number;
  size?: number;
  status?: string;
  model?: string;
  request_id?: string;
};

export async function listUsageLogs(params: ListUsageLogsParams = {}) {
  const search = new URLSearchParams();
  if (params.page) {
    search.set("page", String(params.page));
  }
  if (params.size) {
    search.set("size", String(params.size));
  }
  if (params.status && params.status !== "all") {
    search.set("status", params.status);
  }
  if (params.model) {
    search.set("model", params.model);
  }
  if (params.request_id) {
    search.set("request_id", params.request_id);
  }
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return api35Request<UsageLogListResponse>(`/v1/logs${suffix}`);
}

export async function getUsageLogDetail(requestId: string) {
  return api35Request<UsageLogDetailResponse>(`/v1/logs/${requestId}`);
}
