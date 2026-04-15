import NProgress from 'nprogress'
import { appPath } from '@/utils/appBase';
let __activeRequests = 0
function __progressStart() {
  __activeRequests++
  if (__activeRequests === 1) NProgress.start()
}
function __progressDone() {
  __activeRequests = Math.max(0, __activeRequests - 1)
  if (__activeRequests === 0) {
    setTimeout(() => NProgress.done(), 200)
  }
}
// API基础URL配置
export const API_BASE = import.meta.env.VITE_API_BASE || '';

// HTTP请求选项接口
interface RequestOptions extends RequestInit {
  params?: Record<string, any>;
  baseURL?: string;
  retryCount?: number; // 重试次数
  retryDelay?: number; // 重试延迟(ms)
  skipUnauthorizedRedirect?: boolean;
}

// 错误响应接口
interface ErrorResponse {
  code?: string | number;
  message: string;
  data?: any;
}

// 自定义API错误类
export class ApiError extends Error {
  code?: string | number;
  data?: any;
  status?: number;

  constructor(message: string, code?: string | number, data?: any, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.data = data;
    this.status = status;
  }
}

// HTTP状态码错误映射
const HTTP_STATUS_ERRORS: Record<number, string> = {
  400: '请求参数错误',
  401: '未授权，请重新登录',
  403: '拒绝访问',
  404: '请求的资源不存在',
  405: '请求方法不允许',
  429: '请求过于频繁，请稍后再试',
  500: '服务器内部错误',
  502: '网关错误',
  503: '服务不可用',
  504: '网关超时',
};

// 业务错误码映射
const BUSINESS_ERROR_CODES: Record<string | number, string> = {
  'TOKEN_EXPIRED': '登录已过期，请重新登录',
  'INVALID_TOKEN': '无效的令牌',
  'PERMISSION_DENIED': '权限不足',
  'USER_NOT_FOUND': '用户不存在',
  'VALIDATION_ERROR': '数据验证失败',
  // 可以根据实际业务需求添加更多错误码
};

// 处理特定错误码的函数
function handleSpecificErrorCode(
  code?: string | number,
  status?: number,
  detail?: string,
  options?: { skipUnauthorizedRedirect?: boolean },
): void {
  // 处理认证相关错误
  const authDetails = new Set([
    'missing_session_token',
    'invalid_session_token',
    'missing_user_auth',
    'invalid_user_auth',
  ]);
  const shouldClearSession =
    code === 'TOKEN_EXPIRED' ||
    code === 'INVALID_TOKEN' ||
    authDetails.has(String(code)) ||
    authDetails.has(detail || '');

  if (shouldClearSession) {
    if (options?.skipUnauthorizedRedirect) {
      return;
    }
    // 清除本地存储的认证信息
    localStorage.removeItem('session_token');
    
    // 可以在这里添加重定向到登录页面的逻辑
    if (typeof window !== 'undefined') {
      window.location.href = appPath('/login');
    }
  }
}

// 格式化错误信息
function formatErrorMessage(error: any, status?: number): { message: string; code?: string | number; data?: any; detail?: string } {
  // 如果是ApiError，直接返回
  if (error instanceof ApiError) {
    return { message: error.message, code: error.code, data: error.data };
  }

  // 从后端响应体优先取具体文案
  const bodyMsg = (error && (error.detail || error.message || error.msg)) as string | undefined;
  const detail = typeof error?.detail === 'string' ? error.detail : undefined;

  // 处理响应对象错误
  if (typeof error === 'object' && error !== null) {
    // 业务错误码处理
    if ((error as any).code !== undefined) {
      const mapped = BUSINESS_ERROR_CODES[(error as any).code];
      const message = mapped || bodyMsg || '未知错误';
      return { message, code: (error as any).code, data: (error as any).data, detail };
    }
    // HTTP状态码处理
    if (status) {
      const message = bodyMsg || HTTP_STATUS_ERRORS[status] || `HTTP错误: ${status}`;
      return { message, code: status, detail };
    }
    // 其他错误对象
    if (bodyMsg) {
      return { message: bodyMsg, detail };
    }
  }

  // 处理其他未知错误
  if(error === null && status) {
    return { message: HTTP_STATUS_ERRORS[status] || `HTTP错误: ${status}` };
  }

  // 默认错误信息
  return { message: '网络请求失败，请稍后重试' };
}

// 通用的HTTP请求函数
export async function http<T = any>(
  url: string,
  options: RequestOptions = {}
): Promise<T> {
  __progressStart()

  const {
    method = 'GET',
    headers = { 'Accept-Language': 'zh-CN' },
    params,
    baseURL = API_BASE,
    retryCount = 0,
    retryDelay = 1000,
    skipUnauthorizedRedirect = false,
    ...restOptions
  } = options;

  // 构建完整URL
  let fullUrl = `${baseURL}${url}`;
  
  // 添加查询参数
  if (params && Object.keys(params).length > 0) {
    const filteredParams = Object.fromEntries(
      Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== '')
    );
    if (Object.keys(filteredParams).length > 0) {
      const queryString = new URLSearchParams(filteredParams as Record<string, string>).toString();
      fullUrl += `?${queryString}`;
    }
  }

  // 请求头处理
  const requestHeaders: HeadersInit = {
    'Content-Type': 'application/json',
    ...headers,
  };

  // 添加认证token（如果存在）
  const token = localStorage.getItem('session_token');
  if (token) {
    (requestHeaders as any)['Authorization'] = `Bearer ${token}`;
  }

  // 重试逻辑包装的请求函数
  async function makeRequest(attempt = 0): Promise<T> {
    try {
      // 发送请求
      const response = await fetch(fullUrl, {
        method,
        headers: requestHeaders,
        ...restOptions,
      });

      // 检查HTTP状态码
      if (!response.ok) {        
        let errorData: any;        
        try {          
          errorData = await response.json();
        } catch {          
          errorData = null;
        }

        // 格式化错误信息
        const errorInfo = formatErrorMessage(errorData, response.status);
        const apiError = new ApiError(
          errorInfo.message,
          errorInfo.code || response.status,
          errorInfo.data,
          response.status
        );
        
        // 处理特定错误码
        handleSpecificErrorCode(errorInfo.code, response.status, errorInfo.detail, { skipUnauthorizedRedirect });
        
        // 判断是否需要重试（只对服务器错误进行重试）
        if (attempt < retryCount && response.status >= 500 && response.status < 600) {          
          console.warn(`请求失败，${retryDelay}ms后尝试重试 (${attempt + 1}/${retryCount})`);
          await new Promise(resolve => setTimeout(resolve, retryDelay));
          return makeRequest(attempt + 1);
        }
        
        throw apiError;
      }

      // 尝试解析响应
      let data: any;
      try {
        data = await response.json();
      } catch (jsonError) {
        // 处理非JSON响应
        throw new ApiError('无效的响应格式', 'INVALID_RESPONSE', null, response.status);
      }

      // 检查业务响应码（假设接口使用code字段表示业务状态）
      if (data.code && data.code !== 0 && data.code !== '0' && data.code !== 'success'&& data.code !== 200) {
        const errorInfo = formatErrorMessage(data);
        const apiError = new ApiError(
          errorInfo.message,
          errorInfo.code,
          errorInfo.data
        );
        
        handleSpecificErrorCode(errorInfo.code, undefined, errorInfo.detail, { skipUnauthorizedRedirect });
        throw apiError;
      }

      return data.data as T;
    } catch (error) {
      // 网络错误处理
      if (error instanceof TypeError && error.message.includes('Network')) {
        const networkError = new ApiError('网络连接失败，请检查网络设置', 'NETWORK_ERROR');
        
        // 网络错误也可以重试
        if (attempt < retryCount) {
          console.warn(`网络错误，${retryDelay}ms后尝试重试 (${attempt + 1}/${retryCount})`);
          await new Promise(resolve => setTimeout(resolve, retryDelay));
          return makeRequest(attempt + 1);
        }
        
        throw networkError;
      }
      
      // 重新抛出已处理的ApiError或其他错误
      if (error instanceof ApiError) {
        throw error;
      }
      
      // 未预期的错误
      console.error('HTTP请求失败:', error);
      throw new ApiError('请求处理过程中发生错误', 'UNKNOWN_ERROR', error);
    }
  }

  try {
    return await makeRequest();
  } finally {
    __progressDone()
  }
}

// 封装常用的HTTP方法
export const request = {
  get: <T = any>(url: string, options?: Omit<RequestOptions, 'method'>) => 
    http<T>(url, { ...options, method: 'GET' }),
  
  post: <T = any>(url: string, data?: any, options?: Omit<RequestOptions, 'method'>) => 
    http<T>(url, { 
      ...options, 
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  put: <T = any>(url: string, data?: any, options?: Omit<RequestOptions, 'method'>) => 
    http<T>(url, { 
      ...options, 
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  
  delete: <T = any>(url: string, options?: Omit<RequestOptions, 'method'>) => 
    http<T>(url, { ...options, method: 'DELETE' }),
};

export default request;
