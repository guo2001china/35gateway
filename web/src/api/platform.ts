import { api35Request } from './api35';

export type UserApiKeyResponse = {
  id: number;
  key_name: string;
  key_kind: string;
  key_prefix: string | null;
  api_key: string | null;
  status: string;
  created_at: string | null;
  last_used_at: string | null;
};

export type ProviderAccountAuthFieldResponse = {
  field_name: string;
  label: string;
  required: boolean;
  secret: boolean;
};

export type ProviderAccountProviderOptionResponse = {
  provider_code: string;
  provider_name: string;
  supports_balance_sync: boolean;
  auth_fields: ProviderAccountAuthFieldResponse[];
};

export type ProviderAccountResponse = {
  id: number;
  short_id: string;
  owner_type: string;
  user_id: number | null;
  provider_code: string;
  provider_name: string;
  display_name: string;
  status: string;
  routing_enabled: boolean;
  priority: number;
  base_url_override: string | null;
  verification_status: string;
  last_verified_at: string | null;
  last_verification_error: string | null;
  balance_status: string;
  balance_amount: string | null;
  balance_currency: string | null;
  balance_updated_at: string | null;
  notes: string | null;
  supports_balance_sync: boolean;
};

export type UserAuthIdentityResponse = {
  provider: string;
  email: string | null;
  phone: string | null;
  last_login_at: string | null;
};

export type UserProfileResponse = {
  user_id: number;
  user_no: string;
  name: string;
  balance: string;
  status: string;
  email: string | null;
  phone: string | null;
  identities: UserAuthIdentityResponse[];
  password_login_enabled: boolean;
  password_updated_at: string | null;
  created_at: string | null;
};

export type UserAccountResponse = {
  user_id: number;
  balance: string;
  status: string;
};

export type UserFileResponse = {
  file_id: string;
  filename: string;
  content_type: string | null;
  size: number | null;
  kind: string;
  status: string;
  bucket: string;
  object_key: string;
  url: string | null;
  etag: string | null;
  created_at: string | null;
  completed_at: string | null;
};

export type UserFileListResponse = {
  total: number;
  page: number;
  size: number;
  items: UserFileResponse[];
};

export type ModelPricingLine = {
  label: string;
  value: string;
};

export type ModelPricingSnapshot = {
  currency: string | null;
  billing_unit: string | null;
  price_lines: ModelPricingLine[];
};

export type ModelAvailabilitySnapshot = {
  window: string;
  sample_count: number;
  success_rate: number;
};

export type ModelPricingItem = {
  model_code: string;
  display_name: string;
  category: string;
  summary: string;
  supported_input_modes: string[];
  pricing: ModelPricingSnapshot;
  availability: ModelAvailabilitySnapshot | null;
};

export type PublicModelListPricing = {
  currency: string | null;
  billing_unit: string | null;
  price_lines: ModelPricingLine[];
};

export type PublicModelListItem = {
  model_code: string;
  display_name: string;
  status: string;
  category: string;
  summary: string;
  create_endpoint: string | null;
  pricing: PublicModelListPricing;
  provider_count: number;
};

export type PublicModelProviderMetricsLatency = {
  avg_ms: number | null;
  p50_ms: number | null;
  p95_ms: number | null;
  sample_count: number;
};

export type PublicModelProviderMetrics = {
  window: string;
  sample_count: number;
  success_count: number;
  success_rate: number | null;
  sample_ready: boolean;
  latency: PublicModelProviderMetricsLatency;
};

export type PublicModelProviderItem = {
  provider_code: string;
  provider_name: string;
  lane: string;
  billing_unit: string;
  is_async: boolean;
  is_streaming: boolean;
  route_group: string;
  execution_model_code: string;
  metrics: PublicModelProviderMetrics | null;
};

export type PublicModelDetailPricing = {
  currency: string | null;
  source_url: string | null;
  billing_unit: string | null;
  price_lines: ModelPricingLine[];
};

export type PublicModelRouteItem = {
  route_group: string;
  endpoints: Record<string, string>;
  api_doc: Record<string, unknown>;
  supported_input_modes: string[];
  public_api_visible: boolean;
  is_primary: boolean;
};

export type PublicModelDetailResponse = {
  model_code: string;
  display_name: string;
  status: string;
  route_group: string;
  category: string;
  summary: string;
  supported_input_modes: string[];
  endpoints: Record<string, string>;
  api_doc: Record<string, unknown>;
  docs_url: string | null;
  pricing: PublicModelDetailPricing;
  providers: PublicModelProviderItem[];
  routes: PublicModelRouteItem[];
};

type ListFileParams = {
  page?: number;
  size?: number;
  kind?: string;
};

function buildQuery(params: Record<string, string | number | undefined>, skipValue = 'all') {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === '' || value === skipValue) {
      return;
    }
    search.set(key, String(value));
  });
  const query = search.toString();
  return query ? `?${query}` : '';
}

export function getProfile() {
  return api35Request<UserProfileResponse>('/v1/profile');
}

export function listModelPricing() {
  return api35Request<ModelPricingItem[]>('/v1/model-pricing');
}

export function listPublicModels() {
  return api35Request<PublicModelListItem[]>('/v1/models');
}

export function getPublicModelDetail(modelCode: string) {
  return api35Request<PublicModelDetailResponse>(`/v1/models/${encodeURIComponent(modelCode)}`);
}

export function updateProfile(payload: { name: string }) {
  return api35Request<UserProfileResponse>('/v1/profile', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function listApiKeys() {
  return api35Request<UserApiKeyResponse[]>('/v1/api-keys');
}

export function createApiKey(payload: { key_name: string }) {
  return api35Request<UserApiKeyResponse>('/v1/api-keys', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function revealApiKey(apiKeyId: number) {
  return api35Request<UserApiKeyResponse>(`/v1/api-keys/${apiKeyId}/reveal`, {
    method: 'POST',
  });
}

export function getSystemDefaultApiKey() {
  return api35Request<UserApiKeyResponse>('/v1/api-keys/system-default');
}

export function resetSystemDefaultApiKey() {
  return api35Request<UserApiKeyResponse>('/v1/api-keys/system-default/reset', {
    method: 'POST',
  });
}

export function updateApiKey(apiKeyId: number, payload: { key_name?: string; status?: string }) {
  return api35Request<UserApiKeyResponse>(`/v1/api-keys/${apiKeyId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function deleteApiKey(apiKeyId: number) {
  return api35Request<UserApiKeyResponse>(`/v1/api-keys/${apiKeyId}`, {
    method: 'DELETE',
  });
}

export function listProviderAccountProviders() {
  return api35Request<ProviderAccountProviderOptionResponse[]>('/v1/provider-accounts/providers');
}

export function listProviderAccounts() {
  return api35Request<ProviderAccountResponse[]>('/v1/provider-accounts');
}

export function createProviderAccount(payload: {
  provider_code: string;
  display_name: string;
  base_url_override?: string | null;
  credential_payload: Record<string, string>;
  status?: string;
  priority?: number;
  notes?: string | null;
}) {
  return api35Request<ProviderAccountResponse>('/v1/provider-accounts', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateProviderAccount(
  accountId: number,
  payload: {
    display_name?: string;
    base_url_override?: string | null;
    credential_payload?: Record<string, string>;
    status?: string;
    priority?: number;
    notes?: string | null;
  },
) {
  return api35Request<ProviderAccountResponse>(`/v1/provider-accounts/${accountId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function deleteProviderAccount(accountId: number) {
  return api35Request<ProviderAccountResponse>(`/v1/provider-accounts/${accountId}`, {
    method: 'DELETE',
  });
}

export function verifyProviderAccount(accountId: number) {
  return api35Request<ProviderAccountResponse>(`/v1/provider-accounts/${accountId}/verify`, {
    method: 'POST',
  });
}

export function syncProviderAccountBalance(accountId: number) {
  return api35Request<ProviderAccountResponse>(`/v1/provider-accounts/${accountId}/sync-balance`, {
    method: 'POST',
  });
}

export function getUserAccount() {
  return api35Request<UserAccountResponse>('/v1/account');
}

export function listFiles(params: ListFileParams = {}) {
  const suffix = buildQuery({
    page: params.page,
    size: params.size,
    kind: params.kind,
  });
  return api35Request<UserFileListResponse>(`/v1/files${suffix}`);
}

export function getFileDetail(fileId: string) {
  return api35Request<UserFileResponse>(`/v1/files/${fileId}`);
}

export function uploadFile(file: File) {
  const form = new FormData();
  form.append('file', file);
  return api35Request<UserFileResponse>('/v1/files/upload', {
    method: 'POST',
    body: form,
  });
}

export function importFileFromUrl(payload: { url: string; filename?: string; content_type?: string }) {
  return api35Request<UserFileResponse>('/v1/files/import-url', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
