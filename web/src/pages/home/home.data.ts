import { getApi35Base } from "@/api/api35";
import type { PublicModelDetailResponse, PublicModelListItem } from "@/api/platform";
import type { LabKind, ModelOption, ModelRouteFamily, PlaygroundTask, SelectOption } from "./home.types";

const SITE_BASE_URL = String(import.meta.env.VITE_SITE_URL || "").trim().replace(/\/$/, "");
export const DOCS_HREF = SITE_BASE_URL ? `${SITE_BASE_URL}/docs` : "/docs";

function normalizeDocsHref(rawHref: string | null | undefined): string {
  const value = String(rawHref || "").trim();
  if (!value) {
    return DOCS_HREF;
  }
  if (/^https?:\/\//i.test(value)) {
    return value;
  }
  if (SITE_BASE_URL) {
    return `${SITE_BASE_URL}${value.startsWith("/") ? value : `/${value}`}`;
  }
  return value.startsWith("/") ? value : `/${value}`;
}

const PREFERRED_MODEL_CODES: Record<LabKind, string[]> = {
  text: ["gpt-5.4", "MiniMax-M2.7", "gpt-5.4-pro", "gemini-2.5-pro", "DeepSeek-V3.2"],
  image: ["nano-banana-2", "nano-banana-pro", "nano-banana", "doubao-seedream-4.5"],
  audio: ["qwen3-tts-flash", "speech-2.8-hd", "speech-2.8-turbo", "qwen3-tts-instruct-flash"],
  video: ["wan2.6", "veo-3", "minimax-hailuo-2.3", "kling-o1"],
};

export const FALLBACK_MODEL_OPTIONS: Record<LabKind, ModelOption[]> = {
  text: [
    {
      code: "gpt-5.4",
      label: "GPT-5.4",
      endpoint: "/v1/chat/completions",
      docsHref: DOCS_HREF,
      routeGroup: "openai",
      category: "text",
      supportedInputModes: ["chat"],
      parameterNames: ["model", "messages", "stream"],
      isAsync: false,
      routeFamily: "chat",
    },
    {
      code: "MiniMax-M2.7",
      label: "MiniMax M2.7",
      endpoint: "/v1/chat/completions",
      docsHref: DOCS_HREF,
      routeGroup: "openai",
      category: "text",
      supportedInputModes: ["chat"],
      parameterNames: ["model", "messages", "stream"],
      isAsync: false,
      routeFamily: "chat",
    },
    {
      code: "MiniMax-M2.7-highspeed",
      label: "MiniMax M2.7 Highspeed",
      endpoint: "/v1/chat/completions",
      docsHref: DOCS_HREF,
      routeGroup: "openai",
      category: "text",
      supportedInputModes: ["chat"],
      parameterNames: ["model", "messages", "stream"],
      isAsync: false,
      routeFamily: "chat",
    },
    {
      code: "gpt-5.4-pro",
      label: "GPT-5.4 Pro",
      endpoint: "/v1/responses",
      docsHref: DOCS_HREF,
      routeGroup: "responses",
      category: "text",
      supportedInputModes: ["text"],
      parameterNames: ["model", "input", "instructions", "stream"],
      isAsync: false,
      routeFamily: "responses",
    },
  ],
  image: [
    {
      code: "doubao-seedream-4.5",
      label: "Doubao Seedream 4.5",
      endpoint: "/v1/doubao-seedream-4.5",
      docsHref: DOCS_HREF,
      routeGroup: "seedream",
      category: "image",
      supportedInputModes: ["text", "image"],
      parameterNames: ["prompt", "image", "size", "response_format", "watermark"],
      isAsync: false,
      routeFamily: "seedream",
    },
  ],
  audio: [
    {
      code: "qwen3-tts-flash",
      label: "Qwen TTS Flash",
      endpoint: "/v1/qwen/system-tts",
      docsHref: DOCS_HREF,
      routeGroup: "qwen_tts",
      category: "audio",
      supportedInputModes: ["text_to_speech"],
      parameterNames: ["text", "voice", "mode", "language_type"],
      isAsync: false,
      routeFamily: "qwen_tts",
    },
    {
      code: "speech-2.8-hd",
      label: "MiniMax Speech 2.8 HD",
      endpoint: "/v1/minimax/system-tts",
      docsHref: DOCS_HREF,
      routeGroup: "minimax_t2a_async",
      category: "audio",
      supportedInputModes: ["text_to_speech"],
      parameterNames: ["text", "voice_id"],
      isAsync: true,
      routeFamily: "minimax_tts",
    },
    {
      code: "speech-2.8-turbo",
      label: "MiniMax Speech 2.8 Turbo",
      endpoint: "/v1/minimax/system-tts",
      docsHref: DOCS_HREF,
      routeGroup: "minimax_t2a_async",
      category: "audio",
      supportedInputModes: ["text_to_speech"],
      parameterNames: ["model", "text", "voice_id"],
      isAsync: true,
      routeFamily: "minimax_tts",
    },
  ],
  video: [
    {
      code: "wan2.6",
      label: "Wan 2.6",
      endpoint: "/v1/wan2.6",
      docsHref: DOCS_HREF,
      routeGroup: "wan_video",
      category: "video",
      supportedInputModes: ["text", "image", "reference"],
      parameterNames: ["prompt", "input_reference", "resolution", "aspect_ratio", "seconds"],
      isAsync: true,
      routeFamily: "wan_video",
    },
  ],
};

export const LAB_KIND_OPTIONS: SelectOption[] = [
  { value: "text", label: "问答" },
  { value: "image", label: "图片" },
  { value: "audio", label: "音频" },
  { value: "video", label: "视频" },
];

export const AUDIO_FORMAT_OPTIONS: SelectOption[] = [
  { label: "mp3", value: "mp3" },
  { label: "wav", value: "wav" },
];

export const AUDIO_MODE_OPTIONS: SelectOption[] = [
  { label: "standard", value: "standard" },
  { label: "instruct", value: "instruct" },
];

export const IMAGE_OUTPUT_FORMAT_OPTIONS: SelectOption[] = [
  { label: "png", value: "png" },
  { label: "jpeg", value: "jpeg" },
];

export const KLING_MODE_OPTIONS: SelectOption[] = [
  { label: "pro", value: "pro" },
  { label: "std", value: "std" },
];

export const VIDEO_ASPECT_RATIO_OPTIONS: SelectOption[] = [
  { label: "16:9", value: "16:9" },
  { label: "9:16", value: "9:16" },
  { label: "1:1", value: "1:1" },
];

const NANO_BANANA_ASPECT_RATIO_OPTIONS: SelectOption[] = [
  { label: "1:1", value: "1:1" },
  { label: "2:3", value: "2:3" },
  { label: "3:2", value: "3:2" },
  { label: "3:4", value: "3:4" },
  { label: "4:3", value: "4:3" },
  { label: "4:5", value: "4:5" },
  { label: "5:4", value: "5:4" },
  { label: "9:16", value: "9:16" },
  { label: "16:9", value: "16:9" },
  { label: "21:9", value: "21:9" },
];

const NANO_BANANA_2_ASPECT_RATIO_OPTIONS: SelectOption[] = [
  { label: "1:1", value: "1:1" },
  { label: "1:4", value: "1:4" },
  { label: "1:8", value: "1:8" },
  { label: "2:3", value: "2:3" },
  { label: "3:2", value: "3:2" },
  { label: "3:4", value: "3:4" },
  { label: "4:1", value: "4:1" },
  { label: "4:3", value: "4:3" },
  { label: "4:5", value: "4:5" },
  { label: "5:4", value: "5:4" },
  { label: "8:1", value: "8:1" },
  { label: "9:16", value: "9:16" },
  { label: "16:9", value: "16:9" },
  { label: "21:9", value: "21:9" },
];

const NANO_BANANA_BASE_RESOLUTION_OPTIONS: SelectOption[] = [];
const NANO_BANANA_PRO_RESOLUTION_OPTIONS: SelectOption[] = [
  { label: "1K", value: "1K" },
  { label: "2K", value: "2K" },
  { label: "4K", value: "4K" },
];
const NANO_BANANA_2_RESOLUTION_OPTIONS: SelectOption[] = [
  { label: "512", value: "512" },
  { label: "1K", value: "1K" },
  { label: "2K", value: "2K" },
  { label: "4K", value: "4K" },
];

const GENERIC_IMAGE_SIZE_OPTIONS: SelectOption[] = [
  { label: "1024x1024", value: "1024x1024" },
  { label: "1536x1024", value: "1536x1024" },
  { label: "1024x1536", value: "1024x1536" },
  { label: "2048x2048", value: "2048x2048" },
];

const SEEDREAM_45_SIZE_OPTIONS: SelectOption[] = [
  { label: "1:1 · 2K", value: "2048x2048" },
  { label: "4:3 · 2K", value: "2560x1920" },
  { label: "16:9 · 2K", value: "2560x1440" },
  { label: "9:16 · 2K", value: "1440x2560" },
  { label: "1:1 · 4K", value: "4096x4096" },
  { label: "4:3 · 4K", value: "4096x3072" },
  { label: "16:9 · 4K", value: "4096x2304" },
  { label: "9:16 · 4K", value: "2304x4096" },
];

const SEEDREAM_50_LITE_SIZE_OPTIONS: SelectOption[] = [
  { label: "1:1 · 2K", value: "2048x2048" },
  { label: "4:3 · 2K", value: "2560x1920" },
  { label: "16:9 · 2K", value: "2560x1440" },
  { label: "9:16 · 2K", value: "1440x2560" },
  { label: "1:1 · 3K", value: "3072x3072" },
  { label: "4:3 · 3K", value: "3072x2304" },
  { label: "16:9 · 3K", value: "3072x1728" },
  { label: "9:16 · 3K", value: "1728x3072" },
];

const VIDEO_SECONDS_OPTIONS: SelectOption[] = [
  { label: "5", value: "5" },
  { label: "6", value: "6" },
  { label: "8", value: "8" },
  { label: "10", value: "10" },
];

const VIDEO_RESOLUTION_OPTIONS: SelectOption[] = [
  { label: "720P", value: "720P" },
  { label: "1080P", value: "1080P" },
];

const MINIMAX_VIDEO_RESOLUTION_OPTIONS: SelectOption[] = [
  { label: "512P", value: "512P" },
  { label: "768P", value: "768P" },
  { label: "1080P", value: "1080P" },
];

const MINIMAX_VIDEO_SECONDS_OPTIONS: SelectOption[] = [
  { label: "6", value: "6" },
  { label: "10", value: "10" },
];

const VEO_VIDEO_RESOLUTION_OPTIONS: SelectOption[] = [
  { label: "720p", value: "720p" },
  { label: "1080p", value: "1080p" },
  { label: "4k", value: "4k" },
];

const VEO_VIDEO_SECONDS_OPTIONS: SelectOption[] = [
  { label: "4", value: "4" },
  { label: "6", value: "6" },
  { label: "8", value: "8" },
];

export function buildTaskModelMap(optionsByKind: Record<LabKind, ModelOption[]>): Record<PlaygroundTask, ModelOption[]> {
  return {
    chat: optionsByKind.text,
    image: optionsByKind.image,
    audio: optionsByKind.audio,
    video: optionsByKind.video,
  };
}

export function getImageSizeOptionsForModel(model: ModelOption): SelectOption[] {
  if (model.routeFamily === "seedream") {
    if (model.code === "doubao-seedream-5.0-lite") {
      return SEEDREAM_50_LITE_SIZE_OPTIONS;
    }
    return SEEDREAM_45_SIZE_OPTIONS;
  }
  return GENERIC_IMAGE_SIZE_OPTIONS;
}

export function getDefaultImageSizeForModel(model: ModelOption): string {
  return getImageSizeOptionsForModel(model)[0]?.value || "1024x1024";
}

export function getImageAspectRatioOptionsForModel(model: ModelOption): SelectOption[] {
  if (model.routeFamily !== "banana") {
    return [];
  }
  if (model.code === "nano-banana-2") {
    return NANO_BANANA_2_ASPECT_RATIO_OPTIONS;
  }
  return NANO_BANANA_ASPECT_RATIO_OPTIONS;
}

export function getDefaultImageAspectRatioForModel(model: ModelOption): string {
  return getImageAspectRatioOptionsForModel(model)[0]?.value || "";
}

export function getImageResolutionOptionsForModel(model: ModelOption): SelectOption[] {
  if (model.routeFamily !== "banana") {
    return [];
  }
  if (model.code === "nano-banana") {
    return NANO_BANANA_BASE_RESOLUTION_OPTIONS;
  }
  if (model.code === "nano-banana-2") {
    return NANO_BANANA_2_RESOLUTION_OPTIONS;
  }
  return NANO_BANANA_PRO_RESOLUTION_OPTIONS;
}

export function getDefaultImageResolutionForModel(model: ModelOption): string {
  return getImageResolutionOptionsForModel(model)[0]?.value || "";
}

export function getVideoSecondsOptionsForModel(model: ModelOption): SelectOption[] {
  if (model.routeFamily === "veo_video") {
    return VEO_VIDEO_SECONDS_OPTIONS;
  }
  if (model.routeFamily === "minimax_video") {
    return MINIMAX_VIDEO_SECONDS_OPTIONS;
  }
  return VIDEO_SECONDS_OPTIONS;
}

export function getDefaultVideoSecondsForModel(model: ModelOption): string {
  return getVideoSecondsOptionsForModel(model)[0]?.value || "5";
}

export function getVideoResolutionOptionsForModel(model: ModelOption): SelectOption[] {
  if (model.routeFamily === "veo_video") {
    return VEO_VIDEO_RESOLUTION_OPTIONS;
  }
  if (model.routeFamily === "minimax_video") {
    return MINIMAX_VIDEO_RESOLUTION_OPTIONS;
  }
  return VIDEO_RESOLUTION_OPTIONS;
}

export function getDefaultVideoResolutionForModel(model: ModelOption): string {
  return getVideoResolutionOptionsForModel(model)[0]?.value || "720P";
}

export function supportsModelParameter(model: ModelOption, parameter: string): boolean {
  return model.parameterNames.includes(parameter);
}

function normalizeCreateEndpoint(createEndpoint: string | null | undefined, modelCode: string) {
  if (!createEndpoint) {
    return "";
  }
  return createEndpoint.replace(/^POST\s+/i, "").trim().replace("{model}", modelCode);
}

function mapCategoryToLabKind(category: string): LabKind | null {
  if (category === "text" || category === "image" || category === "audio" || category === "video") {
    return category;
  }
  return null;
}

function detectRouteFamily(endpoint: string, routeGroup: string | null): ModelRouteFamily {
  if (endpoint === "/v1/chat/completions") return "chat";
  if (endpoint === "/v1/responses") return "responses";
  if (endpoint.includes(":generateContent")) return "gemini";
  if (endpoint.startsWith("/v1/nano-banana")) return "banana";
  if (endpoint === "/v1/qwen/system-tts") return "qwen_tts";
  if (endpoint === "/v1/minimax/system-tts") return "minimax_tts";
  if (endpoint.startsWith("/v1/veo-")) return "veo_video";
  if (endpoint.startsWith("/v1/minimax-hailuo-")) return "minimax_video";
  if (endpoint.startsWith("/v1/wan2.6")) return "wan_video";
  if (endpoint.startsWith("/v1/kling-")) return "kling_video";
  if (routeGroup === "seedream") return "seedream";
  if (routeGroup === "banana") return "banana";
  if (routeGroup === "qwen_tts") return "qwen_tts";
  if (routeGroup === "minimax_t2a_async") return "minimax_tts";
  if (routeGroup === "veo3" || routeGroup === "veo31") return "veo_video";
  if (routeGroup === "minimax_video") return "minimax_video";
  if (routeGroup === "wan_video") return "wan_video";
  if (routeGroup === "kling_video") return "kling_video";
  return "generic";
}

function rankPreferred(kind: LabKind, code: string) {
  const index = PREFERRED_MODEL_CODES[kind].indexOf(code);
  return index === -1 ? Number.MAX_SAFE_INTEGER : index;
}

function buildModelOptionBase(params: {
  code: string;
  label: string;
  category: LabKind;
  endpoint: string;
  docsHref: string | null;
  routeGroup: string | null;
  supportedInputModes?: string[];
  parameterNames?: string[];
  isAsync?: boolean;
}): ModelOption {
  const endpoint = params.endpoint || "";
  return {
    code: params.code,
    label: params.label,
    endpoint,
    docsHref: normalizeDocsHref(params.docsHref),
    routeGroup: params.routeGroup,
    category: params.category,
    supportedInputModes: params.supportedInputModes ?? [],
    parameterNames: params.parameterNames ?? [],
    isAsync: params.isAsync ?? false,
    routeFamily: detectRouteFamily(endpoint, params.routeGroup),
  };
}

function isHomepageSupportedModel(option: ModelOption): boolean {
  if (option.category === "text") {
    return option.routeFamily === "chat" || option.routeFamily === "responses" || option.routeFamily === "gemini";
  }
  if (option.category === "image") {
    return option.routeFamily === "seedream" || option.routeFamily === "banana" || option.routeFamily === "generic";
  }
  if (option.category === "audio") {
    return option.endpoint === "/v1/qwen/system-tts" || option.endpoint === "/v1/minimax/system-tts";
  }
  return (
    option.routeFamily === "veo_video" ||
    option.routeFamily === "minimax_video" ||
    option.routeFamily === "wan_video" ||
    option.routeFamily === "kling_video"
  );
}

export function buildModelOptionsByKind(items: PublicModelListItem[]): Record<LabKind, ModelOption[]> {
  const grouped: Record<LabKind, ModelOption[]> = {
    text: [],
    image: [],
    audio: [],
    video: [],
  };

  items.forEach((item) => {
    const kind = mapCategoryToLabKind(item.category);
    if (!kind) {
      return;
    }
    const endpoint = normalizeCreateEndpoint(item.create_endpoint, item.model_code);
    if (!endpoint) {
      return;
    }
    const option = buildModelOptionBase({
      code: item.model_code,
      label: item.display_name,
      category: kind,
      endpoint,
      docsHref: DOCS_HREF,
      routeGroup: null,
    });
    if (!isHomepageSupportedModel(option)) {
      return;
    }
    grouped[kind].push(option);
  });

  (Object.keys(grouped) as LabKind[]).forEach((kind) => {
    grouped[kind].sort((left, right) => {
      const rankDiff = rankPreferred(kind, left.code) - rankPreferred(kind, right.code);
      if (rankDiff !== 0) {
        return rankDiff;
      }
      return left.label.localeCompare(right.label);
    });
    if (grouped[kind].length === 0) {
      grouped[kind] = FALLBACK_MODEL_OPTIONS[kind];
    }
  });

  return grouped;
}

export function enrichModelOptionWithDetail(option: ModelOption, detail: PublicModelDetailResponse): ModelOption {
  const parameters = Array.isArray(detail.api_doc?.parameters)
    ? (detail.api_doc.parameters as Array<Record<string, unknown>>)
    : [];
  const parameterNames = parameters
    .map((item) => (typeof item?.name === "string" ? item.name : ""))
    .filter(Boolean);
  const endpoint = normalizeCreateEndpoint(detail.endpoints?.create || option.endpoint, detail.model_code) || option.endpoint;
  return buildModelOptionBase({
    code: detail.model_code,
    label: detail.display_name,
    category: option.category,
    endpoint,
    docsHref: normalizeDocsHref(detail.docs_url || option.docsHref),
    routeGroup: detail.route_group,
    supportedInputModes: detail.supported_input_modes,
    parameterNames,
    isAsync: Boolean(detail.api_doc?.async),
  });
}
