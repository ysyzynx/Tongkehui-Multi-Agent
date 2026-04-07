const SESSION_TOKEN_KEY = 'tk_auth_token_v1';
const SESSION_USER_KEY = 'tk_auth_user_v1';
const SESSION_EXPIRES_KEY = 'tk_auth_exp_v1';

export type AuthResult = { ok: boolean; message?: string };

type AuthPayload = {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: {
    id: number;
    username: string;
  };
};

type ApiResponse<T> = {
  code: number;
  msg: string;
  data: T;
};

function joinUrl(path: string): string {
  const envBase = import.meta.env.VITE_API_BASE_URL;
  const apiBase = envBase && envBase.trim()
    ? (envBase.trim().toLowerCase() === 'auto' ? window.location.origin : envBase.trim())
    : window.location.origin;

  const base = apiBase.endsWith('/') ? apiBase.slice(0, -1) : apiBase;
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${base}${normalizedPath}`;
}

function setSession(payload: AuthPayload) {
  localStorage.setItem(SESSION_TOKEN_KEY, payload.access_token);
  localStorage.setItem(SESSION_USER_KEY, payload.user.username);
  localStorage.setItem(SESSION_EXPIRES_KEY, payload.expires_at);
}

function clearSession() {
  localStorage.removeItem(SESSION_TOKEN_KEY);
  localStorage.removeItem(SESSION_USER_KEY);
  localStorage.removeItem(SESSION_EXPIRES_KEY);
}

async function parseErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const errorData = await response.json();
    return String(errorData?.detail || errorData?.msg || errorData?.error || fallback);
  } catch {
    return fallback;
  }
}

async function postAuth(path: string, body: { username: string; password: string }): Promise<AuthResult> {
  try {
    const response = await fetch(joinUrl(path), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      return { ok: false, message: await parseErrorMessage(response, '认证失败') };
    }

    const data = await response.json() as ApiResponse<AuthPayload>;
    if (data.code !== 200 || !data.data?.access_token) {
      return { ok: false, message: data.msg || '认证失败' };
    }

    setSession(data.data);
    return { ok: true };
  } catch (err: any) {
    return { ok: false, message: err?.message || '无法连接后端服务' };
  }
}

export function getAuthToken(): string {
  return String(localStorage.getItem(SESSION_TOKEN_KEY) || '').trim();
}

export function isLoggedIn(): boolean {
  const token = getAuthToken();
  const expRaw = String(localStorage.getItem(SESSION_EXPIRES_KEY) || '').trim();
  if (!token || !expRaw) return false;
  const expMs = Date.parse(expRaw);
  if (Number.isNaN(expMs)) return false;
  if (Date.now() >= expMs) {
    clearSession();
    return false;
  }
  return true;
}

export function getCurrentUsername(): string {
  return String(localStorage.getItem(SESSION_USER_KEY) || '').trim();
}

export async function logout(): Promise<void> {
  const token = getAuthToken();
  if (token) {
    try {
      await fetch(joinUrl('/api/auth/logout'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      });
    } catch {
      // 忽略网络异常，前端仍会清理本地会话
    }
  }
  clearSession();
}

export function forceClearSession() {
  clearSession();
}

export async function registerAndLogin(username: string, password: string): Promise<AuthResult> {
  return postAuth('/api/auth/register', {
    username: String(username || '').trim(),
    password: String(password || ''),
  });
}

export async function login(username: string, password: string): Promise<AuthResult> {
  return postAuth('/api/auth/login', {
    username: String(username || '').trim(),
    password: String(password || ''),
  });
}
