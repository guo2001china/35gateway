// 验证码响应接口
export interface VerificationCodeResponse {
  provider: string;
  phone?: string | null;
  email?: string | null;
  expires_in_seconds: number;
  debug_code?: string | null;
}

export interface SessionUser {
  user_id: number;
  user_no: string;
  name: string;
  status: string;
  phone?: string | null;
  email?: string | null;
}

// 登录响应接口
export interface LoginResponse {
  provider: string;
  session_token: string;
  expires_in_seconds: number;
  user: SessionUser;
}

// 退出登录响应接口
export interface LogoutResponse {
  revoked: boolean;
}

// 修改手机号响应接口
export interface ChangePhoneResponse {
  message: string;
}

// 用户信息接口
export interface UserInfo {
  user_id: number;
  user_no: string;
  name: string;
  phone: string;
  email?: string;
  avatar?: string;
  balance: string;
  status: string;
  created_at?: string;
  user_tag_hobby_ids: number[];
  sex?: number;
  user_hobby_tags?: {
    id: number;
    name: string;
  }[];
}
