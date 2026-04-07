// 统一的 API 配置和工具函数
import { forceClearSession, getAuthToken } from './auth';

// 获取 API 基础地址
const getApiBaseUrl = (): string => {
  // 优先使用环境变量
  const envBase = import.meta.env.VITE_API_BASE_URL;
  if (envBase && envBase.trim()) {
    const normalized = envBase.trim();
    if (normalized.toLowerCase() === 'auto') {
      return window.location.origin;
    }
    return normalized;
  }

  // 开发环境默认走同源 /api（由 Vite 代理转发到后端）
  if (import.meta.env.DEV) {
    return window.location.origin;
  }

  // 生产环境回退
  return window.location.origin;
};

// API 基础地址
export const API_BASE = getApiBaseUrl();

// 构建完整的 API URL
export const joinApiUrl = (path: string): string => {
  if (!path) {
    return API_BASE;
  }
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  const base = API_BASE.endsWith('/') ? API_BASE.slice(0, -1) : API_BASE;
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${base}${normalizedPath}`;
};

// 带错误处理的 fetch 包装函数
export async function fetchApi(
  path: string,
  init?: RequestInit
): Promise<Response> {
  const url = joinApiUrl(path);

  const token = getAuthToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string>),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, {
      ...init,
      headers,
    });

    if (!response.ok) {
      if (response.status === 401) {
        forceClearSession();
        throw new Error('登录状态已失效，请重新登录');
      }

      let errorDetail = `API 请求失败: ${response.status} ${response.statusText}`;
      try {
        const errorData = await response.json();
        errorDetail = errorData.msg || errorData.detail || errorData.error || errorDetail;
      } catch {
        // 保留默认错误信息
      }
      throw new Error(errorDetail);
    }

    return response;
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
      throw new Error(
        `无法连接到后端服务器。请确认后端服务已启动 (${API_BASE || 'http://localhost:8000'})`
      );
    }
    throw error;
  }
}

// JSON 响应的快捷方法
export async function fetchJson<T = any>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const response = await fetchApi(path, init);
  return response.json();
}

// 表单数据的快捷方法
export async function fetchFormData(
  path: string,
  formData: FormData,
  init?: RequestInit
): Promise<Response> {
  const url = joinApiUrl(path);
  return fetch(url, {
    ...init,
    method: init?.method || 'POST',
    body: formData,
  });
}
