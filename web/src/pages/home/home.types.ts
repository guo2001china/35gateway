import type { UsageLogDetailResponse } from "@/api/logs";

export type LabKind = "text" | "image" | "audio" | "video";
export type PlaygroundTask = "chat" | "image" | "audio" | "video";
export type CodeLanguage = "curl" | "python" | "javascript";
export type ResponseTab = "preview" | "raw" | "metrics";
export type RequestTab = "form" | "json";
export type ModelRouteFamily = "chat" | "responses" | "gemini" | "seedream" | "banana" | "qwen_tts" | "minimax_tts" | "veo_video" | "minimax_video" | "wan_video" | "kling_video" | "generic";

export type ModelOption = {
  code: string;
  label: string;
  endpoint: string;
  docsHref: string;
  routeGroup: string | null;
  category: LabKind;
  supportedInputModes: string[];
  parameterNames: string[];
  isAsync: boolean;
  routeFamily: ModelRouteFamily;
};

export type ApiKeyOption = {
  optionId: string;
  keyId: number | null;
  label: string;
  kind: "system" | "user";
  keyPrefix: string | null;
  keyValue: string | null;
};

export type VoiceOption = {
  value: string;
  label: string;
};

export type SelectOption = {
  value: string;
  label: string;
};

export type RequestMeta = {
  requestId: string | null;
  powerAmount: string | null;
  durationMs: number | null;
  providerSummary: string;
  detail: UsageLogDetailResponse | null;
};

export type RunResult = {
  ok: boolean;
  statusCode: number | null;
  data: unknown;
  raw: string;
  meta: RequestMeta;
  errorMessage: string | null;
};

export type PlaygroundMessage = {
  id: string;
  role: "user" | "assistant";
  task: PlaygroundTask;
  modelLabel: string;
  content?: string;
  imageUrl?: string | null;
  audioUrl?: string | null;
  videoUrl?: string | null;
  taskStatus?: string | null;
  meta: RequestMeta | null;
  errorMessage?: string | null;
};
