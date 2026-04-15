import { api35Request } from "./api35";

export type AsyncTaskStats = {
  active_count: number;
  pending_billing_count: number;
  completed_count: number;
  failed_or_waived_count: number;
};

export type AsyncTaskListItem = {
  task_id: string;
  request_id: string;
  model: string;
  route_group: string;
  route_type: string;
  provider_code: string;
  provider_account_id: number | null;
  provider_account_short_id: string | null;
  provider_account_owner_type: string | null;
  provider_task_id: string | null;
  task_status: string;
  billing_status: string | null;
  result_available: boolean;
  created_at: string | null;
  updated_at: string | null;
  finished_at: string | null;
};

export type AsyncTaskListResponse = {
  total: number;
  page: number;
  size: number;
  summary: AsyncTaskStats;
  items: AsyncTaskListItem[];
};

export type AsyncTaskDetailResponse = {
  task_id: string;
  request_id: string;
  model: string;
  route_group: string;
  route_type: string;
  request_path: string;
  provider_code: string;
  provider_account_id: number | null;
  provider_account_short_id: string | null;
  provider_account_owner_type: string | null;
  provider_task_id: string | null;
  task_status: string;
  billing_status: string | null;
  power_amount: string | null;
  sale_amount: string | null;
  created_at: string | null;
  updated_at: string | null;
  finished_at: string | null;
  result_payload: Record<string, unknown> | null;
  result_urls: string[];
  error_message: string | null;
};

type ListAsyncTasksParams = {
  page?: number;
  size?: number;
  status?: string;
  model?: string;
  query?: string;
};

export async function listAsyncTasks(params: ListAsyncTasksParams = {}) {
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
  if (params.query) {
    search.set("query", params.query);
  }
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return api35Request<AsyncTaskListResponse>(`/v1/async-tasks${suffix}`);
}

export async function getAsyncTaskDetail(taskId: string) {
  return api35Request<AsyncTaskDetailResponse>(`/v1/async-tasks/${taskId}`);
}
