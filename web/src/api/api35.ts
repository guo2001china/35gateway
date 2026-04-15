const API35_BASE = (import.meta.env.VITE_API35_BASE || "").trim();
import { appPath } from '@/utils/appBase';

type Api35RequestOptions = RequestInit & {
  skipAuth?: boolean;
};

function handleApi35Unauthorized() {
  localStorage.removeItem('session_token');
  window.dispatchEvent(new Event('user-logout'));
  const loginPath = appPath('/login');
  if (typeof window !== 'undefined' && window.location.pathname !== loginPath) {
    window.location.href = loginPath;
  }
}

function shouldHandleApi35Unauthorized(detail: string | undefined) {
  return detail === 'missing_session_token' || detail === 'invalid_session_token' || detail === 'missing_user_auth';
}

export async function api35Request<T>(path: string, options: Api35RequestOptions = {}): Promise<T> {
  const { skipAuth = false, headers, ...rest } = options;
  const requestHeaders = new Headers(headers || {});
  requestHeaders.set('Accept-Language', 'zh-CN');

  const hasJsonBody = rest.body !== undefined && !(rest.body instanceof FormData);
  if (hasJsonBody && !requestHeaders.has('Content-Type')) {
    requestHeaders.set('Content-Type', 'application/json');
  }

  if (!skipAuth) {
    const sessionToken = localStorage.getItem('session_token');
    if (sessionToken) {
      requestHeaders.set('Authorization', `Bearer ${sessionToken}`);
    }
  }

  const response = await fetch(`${API35_BASE}${path}`, {
    ...rest,
    headers: requestHeaders,
  });

  let payload: any = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail = typeof payload?.detail === 'string' ? payload.detail : undefined;
    const message = detail || payload?.message || `请求失败: ${response.status}`;
    if (response.status === 401 && shouldHandleApi35Unauthorized(detail)) {
      handleApi35Unauthorized();
    }
    throw new Error(message);
  }

  return payload as T;
}

export function getApi35Base() {
  if (API35_BASE) {
    return API35_BASE;
  }
  if (typeof window !== "undefined") {
    return window.location.origin;
  }
  return "";
}
