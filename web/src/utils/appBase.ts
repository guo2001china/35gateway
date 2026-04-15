const RAW_BASE_URL = import.meta.env.BASE_URL || "/";

function normalizeBasePath(baseUrl: string): string {
  const trimmed = (baseUrl || "/").trim();
  if (!trimmed || trimmed === "/") {
    return "";
  }
  return `/${trimmed.replace(/^\/+|\/+$/g, "")}`;
}

export const APP_BASE_PATH = normalizeBasePath(RAW_BASE_URL);
export const APP_ROUTER_BASENAME = APP_BASE_PATH || "/";

export function appPath(path: string = "/"): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  if (!APP_BASE_PATH) {
    return normalizedPath;
  }
  if (normalizedPath === "/") {
    return `${APP_BASE_PATH}/`;
  }
  return `${APP_BASE_PATH}${normalizedPath}`;
}

export function assetPath(path: string): string {
  const normalized = path.replace(/^\/+/, "");
  return `${RAW_BASE_URL}${normalized}`;
}
