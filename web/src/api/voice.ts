import { request } from "./http";

export type QwenSystemVoiceItem = {
  voice: string;
  locale?: string | null;
  languages?: string[];
  description?: string | null;
  modes?: string[];
};

export type QwenSystemVoiceListResponse = {
  items?: QwenSystemVoiceItem[];
  total?: number;
};

export type MiniMaxSystemVoiceItem = {
  voice_id?: string | null;
  voice_name?: string | null;
  description?: string[] | null;
  created_time?: string | null;
};

export type MiniMaxSystemVoiceListResponse = {
  items?: MiniMaxSystemVoiceItem[];
  total?: number;
};

export async function getQwenSystemVoicesApi(): Promise<QwenSystemVoiceListResponse> {
  return request.get<QwenSystemVoiceListResponse>("/v1/qwen/system-voices");
}

export async function getMiniMaxSystemVoicesApi(): Promise<MiniMaxSystemVoiceListResponse> {
  return request.get<MiniMaxSystemVoiceListResponse>("/v1/minimax/system-voices");
}
