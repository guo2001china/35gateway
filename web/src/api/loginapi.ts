import { LoginResponse, VerificationCodeResponse, ChangePhoneResponse, LogoutResponse, UserInfo } from '../models/LoginModels';
import { api35Request } from './api35';

export type GrowthContextPayload = {
  first_touch_source?: string;
  first_touch_medium?: string;
  first_touch_campaign?: string;
  first_touch_referrer?: string;
  landing_path?: string;
};

type Api35ProfileResponse = {
  user_id: number;
  user_no: string;
  name: string;
  balance: string;
  status: string;
  email?: string | null;
  phone?: string | null;
  created_at?: string | null;
};

function mapProfileToUserInfo(profile: Api35ProfileResponse): UserInfo {
  return {
    user_id: profile.user_id,
    user_no: profile.user_no,
    name: profile.name,
    phone: profile.phone || '',
    email: profile.email || '',
    avatar: '',
    balance: profile.balance,
    status: profile.status,
    created_at: profile.created_at || undefined,
    user_tag_hobby_ids: [],
    sex: 0,
    user_hobby_tags: [],
  };
}

/**
 * 发送验证码
 * @param phone 手机号
 * @returns 包含验证码发送状态的响应
 */
export async function sendVerificationCode(phone: string): Promise<VerificationCodeResponse> {
  return api35Request<VerificationCodeResponse>('/auth/phone/send-code', {
    method: 'POST',
    body: JSON.stringify({ phone }),
    skipAuth: true,
  });
}

export async function sendEmailVerificationCode(email: string): Promise<VerificationCodeResponse> {
  return api35Request<VerificationCodeResponse>('/auth/email/send-code', {
    method: 'POST',
    body: JSON.stringify({ email }),
    skipAuth: true,
  });
}

/**
 * 登录
 * @param phone 手机号
 * @param code 验证码
 * @returns 登录成功后的响应
 */
export async function login(phone: string, code: string, growthContext?: GrowthContextPayload | null): Promise<LoginResponse> {
  return api35Request<LoginResponse>('/auth/login/phone', {
    method: 'POST',
    body: JSON.stringify({ phone, code, growth_context: growthContext ?? undefined }),
    skipAuth: true,
  });
}

export async function loginWithEmail(email: string, code: string, growthContext?: GrowthContextPayload | null): Promise<LoginResponse> {
  return api35Request<LoginResponse>('/auth/login/email', {
    method: 'POST',
    body: JSON.stringify({ email, code, growth_context: growthContext ?? undefined }),
    skipAuth: true,
  });
}

export async function loginWithPassword(email: string, password: string, growthContext?: GrowthContextPayload | null): Promise<LoginResponse> {
  return api35Request<LoginResponse>('/auth/login/password', {
    method: 'POST',
    body: JSON.stringify({ email, password, growth_context: growthContext ?? undefined }),
    skipAuth: true,
  });
}

export async function registerWithPassword(
  email: string,
  code: string,
  password: string,
  growthContext?: GrowthContextPayload | null,
): Promise<LoginResponse> {
  return api35Request<LoginResponse>('/auth/register/password', {
    method: 'POST',
    body: JSON.stringify({ email, code, password, growth_context: growthContext ?? undefined }),
    skipAuth: true,
  });
}

/**
 * 退出登录
 * @returns 退出登录成功后的响应
 */
export async function logout(): Promise<LogoutResponse> {
  return api35Request<LogoutResponse>('/auth/session/logout', {
    method: 'POST',
  });
}

/**
 * 修改手机号
 * @param phone 新手机号
 * @param code 验证码
 * @returns 修改手机号成功后的响应
 */
export async function changePhone(newPhone: string, code: string): Promise<ChangePhoneResponse> {
  void newPhone;
  void code;
  throw new Error('当前版本暂未提供修改手机号接口');
}

/**
 * 获取用户信息
 * @returns 用户信息响应
 */
export async function getUserInfo(): Promise<UserInfo> {
  const profile = await api35Request<Api35ProfileResponse>('/v1/profile');
  return mapProfileToUserInfo(profile);
}

export async function syncGrowthContext(growthContext: GrowthContextPayload): Promise<void> {
  await api35Request('/v1/growth-context', {
    method: 'POST',
    body: JSON.stringify({ growth_context: growthContext }),
  });
}

// 更新用户信息
export async function updateUserInfo(info: UserInfo): Promise<UserInfo> {
  const profile = await api35Request<Api35ProfileResponse>('/v1/profile', {
    method: 'PATCH',
    body: JSON.stringify({ name: info.name }),
  });
  return mapProfileToUserInfo(profile);
}



export default {
  sendVerificationCode,
  sendEmailVerificationCode,
  login,
  loginWithEmail,
  loginWithPassword,
  registerWithPassword,
  logout,
  changePhone
};
