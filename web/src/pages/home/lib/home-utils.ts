import { message } from "antd";
import type { UsageLogDetailResponse } from "@/api/logs";

export function formatPower(value?: string | null) {
  if (!value) return "-";
  const amount = Number(value);
  if (Number.isNaN(amount)) return value;
  return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 6 }).format(amount);
}

export function formatDuration(value?: number | null) {
  if (typeof value !== "number" || Number.isNaN(value)) return "-";
  if (value < 1000) return `${value} ms`;
  return `${(value / 1000).toFixed(value >= 10_000 ? 0 : 1)} s`;
}

export function stringifyJson(value: unknown) {
  if (value === null || value === undefined) return "{}";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function normalizeProviderSummary(detail: UsageLogDetailResponse | null) {
  if (!detail || detail.chain.length === 0) {
    return "-";
  }
  const providers: string[] = [];
  detail.chain.forEach((item) => {
    if (!providers.includes(item.provider_code)) {
      providers.push(item.provider_code);
    }
  });
  return providers.join(" → ");
}

export function extractTextFromResponse(payload: unknown): string {
  if (!payload || typeof payload !== "object") {
    return stringifyJson(payload);
  }
  const data = payload as Record<string, any>;
  const choiceMessage = data.choices?.[0]?.message?.content;
  if (typeof choiceMessage === "string" && choiceMessage.trim()) {
    return choiceMessage;
  }
  if (Array.isArray(choiceMessage)) {
    const text = choiceMessage
      .map((item) => (typeof item?.text === "string" ? item.text : typeof item?.content === "string" ? item.content : ""))
      .filter(Boolean)
      .join("\n");
    if (text) {
      return text;
    }
  }
  if (typeof data.output_text === "string" && data.output_text.trim()) {
    return data.output_text;
  }
  const geminiText = data.candidates?.[0]?.content?.parts
    ?.map((part: { text?: string }) => part?.text || "")
    .filter(Boolean)
    .join("\n");
  if (typeof geminiText === "string" && geminiText.trim()) {
    return geminiText;
  }
  const finishReason = data.choices?.[0]?.finish_reason;
  const totalTokens = data.usage?.total_tokens;
  if (typeof finishReason === "string" && finishReason) {
    if (finishReason === "length") {
      return `模型本次没有返回可展示文本，响应在生成阶段被长度限制提前截断了。你可以增大 max_tokens 后重试。${typeof totalTokens === "number" ? `（本次总 tokens: ${totalTokens}）` : ""}`;
    }
    return `模型本次没有返回可展示文本，finish_reason=${finishReason}。请查看详情日志确认完整响应。`;
  }
  if (typeof data.object === "string" && data.object.includes("chat.completion")) {
    return "模型本次没有返回可展示文本。请查看详情日志确认完整响应。";
  }
  return stringifyJson(payload);
}

export function extractImageUrl(payload: unknown): string | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  const data = payload as Record<string, any>;
  const first = data.images?.[0];
  if (typeof first?.url === "string" && first.url) {
    return first.url;
  }
  if (typeof first?.b64_json === "string" && first.b64_json) {
    return `data:image/png;base64,${first.b64_json}`;
  }
  return null;
}

export function extractAudioUrl(payload: unknown): string | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  const data = payload as Record<string, any>;
  if (typeof data.output?.audio?.url === "string" && data.output.audio.url) {
    return data.output.audio.url;
  }
  if (typeof data.url === "string" && data.url) {
    return data.url;
  }
  return null;
}

export function extractVideoUrl(payload: unknown): string | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  const data = payload as Record<string, any>;
  if (typeof data.url === "string" && data.url) {
    return data.url;
  }
  if (typeof data.video?.url === "string" && data.video.url) {
    return data.video.url;
  }
  return null;
}

export function buildMessageId() {
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export async function copyText(value: string, successText: string) {
  try {
    await navigator.clipboard.writeText(value);
    message.success(successText);
  } catch {
    message.error("复制失败，请检查浏览器权限。");
  }
}

export async function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
