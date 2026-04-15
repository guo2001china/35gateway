import "./page.scss";
import { message } from "antd";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getApi35Base } from "@/api/api35";
import { getUsageLogDetail, listUsageLogs, type UsageLogDetailResponse } from "@/api/logs";
import {
  getUserAccount,
  getPublicModelDetail,
  getSystemDefaultApiKey,
  listApiKeys,
  listPublicModels,
  revealApiKey,
  type PublicModelDetailResponse,
  type UserApiKeyResponse,
} from "@/api/platform";
import { getMiniMaxSystemVoicesApi, getQwenSystemVoicesApi } from "@/api/voice";
import { useUser } from "@/contexts/UserContext";
import { ApiLabPanel } from "./components/ApiLabPanel";
import { PlaygroundPanel } from "./components/PlaygroundPanel";
import { WorkbenchHero } from "./components/WorkbenchHero";
import {
  getDefaultImageAspectRatioForModel,
  getDefaultImageResolutionForModel,
  buildTaskModelMap,
  buildModelOptionsByKind,
  enrichModelOptionWithDetail,
  FALLBACK_MODEL_OPTIONS,
  getImageAspectRatioOptionsForModel,
  getImageResolutionOptionsForModel,
  getDefaultVideoResolutionForModel,
  getDefaultVideoSecondsForModel,
  getDefaultImageSizeForModel,
  getImageSizeOptionsForModel,
  getVideoResolutionOptionsForModel,
  getVideoSecondsOptionsForModel,
} from "./home.data";
import type {
  ApiKeyOption,
  CodeLanguage,
  LabKind,
  ModelOption,
  PlaygroundMessage,
  PlaygroundTask,
  RequestMeta,
  RequestTab,
  ResponseTab,
  RunResult,
  VoiceOption,
} from "./home.types";
import { buildCurlSnippet, buildJavaScriptSnippet, buildPythonSnippet } from "./lib/home-snippets";
import {
  buildMessageId,
  copyText,
  extractAudioUrl,
  extractImageUrl,
  extractTextFromResponse,
  extractVideoUrl,
  formatPower,
  normalizeProviderSummary,
  sleep,
  stringifyJson,
} from "./lib/home-utils";

type EstimateSummaryResponse = {
  model: string;
  quote_mode: "exact" | "estimated";
  route_mode: "default" | "chain";
  lowest_price: string;
  highest_price: string;
  currency: string;
  balance: {
    available_amount: string;
    enough_for_highest: boolean;
  };
  request_factors: Record<string, unknown>;
};

type EstimateDisplayState = {
  loading: boolean;
  text: string;
  warning: boolean;
};

const DEFAULT_QWEN_VOICES: VoiceOption[] = [{ value: "Cherry", label: "Cherry" }];
const DEFAULT_MINIMAX_VOICES: VoiceOption[] = [{ value: "male-qn-qingse", label: "青涩青年音色 · male-qn-qingse" }];

function splitUrlList(raw: string) {
  return raw
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function toOptionalNumber(raw: string) {
  const normalized = raw.trim();
  if (!normalized) {
    return undefined;
  }
  const value = Number(normalized);
  return Number.isFinite(value) ? value : undefined;
}

function buildPendingRequestMeta(requestId: string | null): RequestMeta {
  return {
    requestId,
    powerAmount: null,
    durationMs: null,
    providerSummary: "-",
    detail: null,
  };
}

function stripModelField(payload: Record<string, unknown>) {
  const next = { ...payload };
  delete next.model;
  return next;
}

function parseProviderChain(raw: string) {
  return raw
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatEstimateMoney(value: string, currency: string) {
  const amount = Number(value);
  const prefix = currency === "USD" ? "$" : currency === "CNY" || currency === "RMB" ? "¥" : `${currency} `;
  if (Number.isNaN(amount)) {
    return `${prefix}${value}`;
  }
  return `${prefix}${new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(amount)}`;
}

function toEstimateDisplay(raw: EstimateSummaryResponse): EstimateDisplayState {
  const minText = formatEstimateMoney(raw.lowest_price, raw.currency);
  const maxText = formatEstimateMoney(raw.highest_price, raw.currency);
  return {
    loading: false,
    text:
      minText === maxText
        ? raw.quote_mode === "estimated"
          ? `约 ${minText}`
          : minText
        : `${minText} - ${maxText}`,
    warning: !raw.balance.enough_for_highest,
  };
}

function buildImagePayload(
  model: ModelOption,
  params: {
    prompt: string;
    reference: string;
    size: string;
    aspectRatio: string;
    resolution: string;
    responseFormat: string;
    watermark: boolean;
    outputFormat: string;
  },
) {
  const prompt = params.prompt.trim() || "一张干净利落的产品广告图。";
  const references = splitUrlList(params.reference);
  if (model.routeFamily === "banana") {
    return {
      prompt,
      image_urls: references.length ? references : undefined,
      aspect_ratio: params.aspectRatio || undefined,
      resolution: params.resolution || undefined,
    };
  }
  return {
    prompt,
    image: references.length > 1 ? references : references[0] || undefined,
    size: params.size,
    response_format: model.parameterNames.includes("response_format") ? params.responseFormat : undefined,
    watermark: model.parameterNames.includes("watermark") && params.watermark ? true : undefined,
    output_format: model.parameterNames.includes("output_format") ? params.outputFormat || undefined : undefined,
  };
}

function buildVideoPayload(
  model: ModelOption,
  params: {
    prompt: string;
    reference: string;
    audioUrl: string;
    size: string;
    seconds: string;
    aspectRatio: string;
    resolution: string;
    generateAudio: boolean;
    videoUrl: string;
    firstFrame: string;
    lastFrame: string;
    mode: string;
  },
) {
  const references = splitUrlList(params.reference);
  const primaryReference = references[0] || undefined;
  const supportsReferenceList =
    model.parameterNames.includes("reference_urls") || model.parameterNames.includes("reference_images");
  const useReferenceList = supportsReferenceList && references.length > 1;
  const sizeValue = params.size.trim() || undefined;

  return {
    prompt: params.prompt.trim() || "一段电影感镜头。",
    input_reference:
      model.parameterNames.includes("input_reference") && primaryReference && !useReferenceList ? primaryReference : undefined,
    reference_urls: model.parameterNames.includes("reference_urls") && useReferenceList ? references : undefined,
    reference_images: model.parameterNames.includes("reference_images") && useReferenceList ? references : undefined,
    image: model.parameterNames.includes("image") && primaryReference ? { image_uri: primaryReference } : undefined,
    audio_url: model.parameterNames.includes("audio_url") ? params.audioUrl.trim() || undefined : undefined,
    size: model.parameterNames.includes("size") ? sizeValue : undefined,
    seconds: model.parameterNames.includes("seconds") ? Number(params.seconds || "5") : undefined,
    aspect_ratio:
      model.parameterNames.includes("aspect_ratio") && !sizeValue ? params.aspectRatio : undefined,
    resolution:
      model.parameterNames.includes("resolution") && !sizeValue ? params.resolution : undefined,
    generate_audio: model.parameterNames.includes("generate_audio") ? params.generateAudio : undefined,
    video_url: model.parameterNames.includes("video_url") ? params.videoUrl.trim() || undefined : undefined,
    first_frame: model.parameterNames.includes("first_frame") ? params.firstFrame.trim() || undefined : undefined,
    last_frame: model.parameterNames.includes("last_frame") ? params.lastFrame.trim() || undefined : undefined,
    mode: model.parameterNames.includes("mode") ? params.mode : undefined,
  };
}

export default function HomePage() {
  const navigate = useNavigate();
  const { refresh } = useUser();

  const [summary, setSummary] = useState({
    powerBalance: "-",
    logsTotal: 0,
    modelTotal: 0,
  });
  const [loadingSummary, setLoadingSummary] = useState(true);

  const [systemApiKey, setSystemApiKey] = useState<UserApiKeyResponse | null>(null);
  const [userApiKeys, setUserApiKeys] = useState<UserApiKeyResponse[]>([]);
  const [revealedKeys, setRevealedKeys] = useState<Record<number, string>>({});
  const [labApiKeyOptionId, setLabApiKeyOptionId] = useState("system");
  const [playgroundApiKeyOptionId, setPlaygroundApiKeyOptionId] = useState("system");

  const [qwenVoices, setQwenVoices] = useState<VoiceOption[]>(DEFAULT_QWEN_VOICES);
  const [minimaxVoices, setMiniMaxVoices] = useState<VoiceOption[]>(DEFAULT_MINIMAX_VOICES);
  const [modelOptionsByKind, setModelOptionsByKind] = useState(FALLBACK_MODEL_OPTIONS);
  const [modelDetails, setModelDetails] = useState<Record<string, PublicModelDetailResponse>>({});

  const [labKind, setLabKind] = useState<LabKind>("text");
  const [labRequestTab, setLabRequestTab] = useState<RequestTab>("form");
  const [labResponseTab, setLabResponseTab] = useState<ResponseTab>("preview");
  const [labCodeTab, setLabCodeTab] = useState<CodeLanguage>("curl");
  const [labModelCode, setLabModelCode] = useState<Record<LabKind, string>>({
    text: FALLBACK_MODEL_OPTIONS.text[0].code,
    image: FALLBACK_MODEL_OPTIONS.image[0].code,
    audio: FALLBACK_MODEL_OPTIONS.audio[0].code,
    video: FALLBACK_MODEL_OPTIONS.video[0].code,
  });
  const [labRunning, setLabRunning] = useState(false);
  const [labJsonDirty, setLabJsonDirty] = useState(false);
  const [labRawRequest, setLabRawRequest] = useState("");
  const [labResult, setLabResult] = useState<RunResult | null>(null);
  const [labEstimate, setLabEstimate] = useState<EstimateDisplayState>({
    loading: false,
    text: "",
    warning: false,
  });

  const [labAdvanced, setLabAdvanced] = useState(false);
  const [labChain, setLabChain] = useState("");
  const [labStream, setLabStream] = useState(false);
  const [labTextPrompt, setLabTextPrompt] = useState("用一句话介绍 35m 的定位。");
  const [labSystemPrompt, setLabSystemPrompt] = useState("");
  const [labTemperature, setLabTemperature] = useState("");
  const [labMaxTokens, setLabMaxTokens] = useState("");
  const [labImagePrompt, setLabImagePrompt] = useState("一张电影感强烈的产品海报，白底，柔和棚拍光。");
  const [labImageReference, setLabImageReference] = useState("");
  const [labImageSize, setLabImageSize] = useState(getDefaultImageSizeForModel(FALLBACK_MODEL_OPTIONS.image[0]));
  const [labImageAspectRatio, setLabImageAspectRatio] = useState(getDefaultImageAspectRatioForModel(FALLBACK_MODEL_OPTIONS.image[0]));
  const [labImageResolution, setLabImageResolution] = useState(getDefaultImageResolutionForModel(FALLBACK_MODEL_OPTIONS.image[0]));
  const [labImageResponseFormat, setLabImageResponseFormat] = useState("url");
  const [labImageWatermark, setLabImageWatermark] = useState(false);
  const [labImageOutputFormat, setLabImageOutputFormat] = useState("png");
  const [labAudioText, setLabAudioText] = useState("欢迎来到 35m，现在开始你的模型调用体验。");
  const [labAudioVoice, setLabAudioVoice] = useState("");
  const [labAudioMode, setLabAudioMode] = useState("standard");
  const [labAudioFormat, setLabAudioFormat] = useState("mp3");
  const [labVideoPrompt, setLabVideoPrompt] = useState("夕阳下的城市高架桥，镜头缓慢推进，电影感光影。");
  const [labVideoReference, setLabVideoReference] = useState("");
  const [labVideoAudioUrl, setLabVideoAudioUrl] = useState("");
  const [labVideoSize, setLabVideoSize] = useState("");
  const [labVideoSeconds, setLabVideoSeconds] = useState("5");
  const [labVideoAspectRatio, setLabVideoAspectRatio] = useState("16:9");
  const [labVideoResolution, setLabVideoResolution] = useState("720P");
  const [labVideoGenerateAudio, setLabVideoGenerateAudio] = useState(true);
  const [labVideoVideoUrl, setLabVideoVideoUrl] = useState("");
  const [labVideoFirstFrame, setLabVideoFirstFrame] = useState("");
  const [labVideoLastFrame, setLabVideoLastFrame] = useState("");
  const [labVideoMode, setLabVideoMode] = useState("pro");

  const [playgroundTask, setPlaygroundTask] = useState<PlaygroundTask>("chat");
  const [playgroundMessages, setPlaygroundMessages] = useState<PlaygroundMessage[]>([]);
  const [playgroundInput, setPlaygroundInput] = useState("");
  const [playgroundModelCode, setPlaygroundModelCode] = useState<Record<PlaygroundTask, string>>({
    chat: FALLBACK_MODEL_OPTIONS.text[0].code,
    image: FALLBACK_MODEL_OPTIONS.image[0].code,
    audio: FALLBACK_MODEL_OPTIONS.audio[0].code,
    video: FALLBACK_MODEL_OPTIONS.video[0].code,
  });
  const [playgroundWorking, setPlaygroundWorking] = useState(false);
  const [playgroundEstimate, setPlaygroundEstimate] = useState<EstimateDisplayState>({
    loading: false,
    text: "",
    warning: false,
  });
  const [playgroundAdvanced, setPlaygroundAdvanced] = useState(false);
  const [playgroundSystemPrompt, setPlaygroundSystemPrompt] = useState("");
  const [playgroundTemperature, setPlaygroundTemperature] = useState("");
  const [playgroundMaxTokens, setPlaygroundMaxTokens] = useState("");
  const [playgroundImageReference, setPlaygroundImageReference] = useState("");
  const [playgroundImageSize, setPlaygroundImageSize] = useState(getDefaultImageSizeForModel(FALLBACK_MODEL_OPTIONS.image[0]));
  const [playgroundImageAspectRatio, setPlaygroundImageAspectRatio] = useState(
    getDefaultImageAspectRatioForModel(FALLBACK_MODEL_OPTIONS.image[0]),
  );
  const [playgroundImageResolution, setPlaygroundImageResolution] = useState(
    getDefaultImageResolutionForModel(FALLBACK_MODEL_OPTIONS.image[0]),
  );
  const [playgroundImageResponseFormat, setPlaygroundImageResponseFormat] = useState("url");
  const [playgroundImageWatermark, setPlaygroundImageWatermark] = useState(false);
  const [playgroundImageOutputFormat, setPlaygroundImageOutputFormat] = useState("png");
  const [playgroundAudioVoice, setPlaygroundAudioVoice] = useState("");
  const [playgroundAudioMode, setPlaygroundAudioMode] = useState("standard");
  const [playgroundAudioFormat, setPlaygroundAudioFormat] = useState("mp3");
  const [playgroundVideoReference, setPlaygroundVideoReference] = useState("");
  const [playgroundVideoAudioUrl, setPlaygroundVideoAudioUrl] = useState("");
  const [playgroundVideoSize, setPlaygroundVideoSize] = useState("");
  const [playgroundVideoSeconds, setPlaygroundVideoSeconds] = useState("5");
  const [playgroundVideoAspectRatio, setPlaygroundVideoAspectRatio] = useState("16:9");
  const [playgroundVideoResolution, setPlaygroundVideoResolution] = useState("720P");
  const [playgroundVideoGenerateAudio, setPlaygroundVideoGenerateAudio] = useState(true);
  const [playgroundVideoVideoUrl, setPlaygroundVideoVideoUrl] = useState("");
  const [playgroundVideoFirstFrame, setPlaygroundVideoFirstFrame] = useState("");
  const [playgroundVideoLastFrame, setPlaygroundVideoLastFrame] = useState("");
  const [playgroundVideoMode, setPlaygroundVideoMode] = useState("pro");

  const taskModelMap = useMemo(() => buildTaskModelMap(modelOptionsByKind), [modelOptionsByKind]);

  const activeLabModel = useMemo(
    () =>
      modelOptionsByKind[labKind].find((item) => item.code === labModelCode[labKind]) ??
      modelOptionsByKind[labKind][0] ??
      FALLBACK_MODEL_OPTIONS[labKind][0],
    [labKind, labModelCode, modelOptionsByKind],
  );

  const activePlaygroundModel = useMemo(
    () =>
      taskModelMap[playgroundTask].find((item) => item.code === playgroundModelCode[playgroundTask]) ??
      taskModelMap[playgroundTask][0] ??
      FALLBACK_MODEL_OPTIONS[playgroundTask === "chat" ? "text" : playgroundTask][0],
    [playgroundModelCode, playgroundTask, taskModelMap],
  );

  const apiKeyOptions = useMemo<ApiKeyOption[]>(() => {
    const options: ApiKeyOption[] = [];
    if (systemApiKey) {
      options.push({
        optionId: "system",
        keyId: systemApiKey.id,
        label: "系统默认 Key",
        kind: "system",
        keyPrefix: systemApiKey.key_prefix,
        keyValue: systemApiKey.api_key,
      });
    }
    userApiKeys
      .filter((item) => item.status === "active")
      .forEach((item) => {
        options.push({
          optionId: `user-${item.id}`,
          keyId: item.id,
          label: item.key_name || "自定义 Key",
          kind: "user",
          keyPrefix: item.key_prefix,
          keyValue: revealedKeys[item.id] ?? item.api_key ?? null,
        });
      });
    return options;
  }, [revealedKeys, systemApiKey, userApiKeys]);

  const selectedLabApiKeyOption = useMemo(
    () => apiKeyOptions.find((item) => item.optionId === labApiKeyOptionId) ?? apiKeyOptions[0] ?? null,
    [apiKeyOptions, labApiKeyOptionId],
  );

  const selectedPlaygroundApiKeyOption = useMemo(
    () => apiKeyOptions.find((item) => item.optionId === playgroundApiKeyOptionId) ?? apiKeyOptions[0] ?? null,
    [apiKeyOptions, playgroundApiKeyOptionId],
  );

  const generatedLabBody = useMemo(() => {
    switch (labKind) {
      case "text": {
        const prompt = labTextPrompt.trim() || "你好，35m。";
        if (activeLabModel.routeFamily === "responses") {
          return {
            model: activeLabModel.code,
            input: prompt,
            instructions: labSystemPrompt.trim() || undefined,
            max_output_tokens: toOptionalNumber(labMaxTokens),
            stream: activeLabModel.parameterNames.includes("stream") ? labStream || undefined : undefined,
          };
        }
        if (activeLabModel.routeFamily === "gemini") {
          const generationConfig = {
            temperature: toOptionalNumber(labTemperature),
            maxOutputTokens: toOptionalNumber(labMaxTokens),
          };
          return {
            contents: [
              {
                role: "user",
                parts: [
                  {
                    text: labSystemPrompt.trim() ? `${labSystemPrompt.trim()}\n\n${prompt}` : prompt,
                  },
                ],
              },
            ],
            generationConfig:
              generationConfig.temperature !== undefined || generationConfig.maxOutputTokens !== undefined
                ? generationConfig
                : undefined,
          };
        }
        const messages: Array<{ role: string; content: string }> = [];
        if (labSystemPrompt.trim()) {
          messages.push({ role: "system", content: labSystemPrompt.trim() });
        }
        messages.push({ role: "user", content: prompt });
        return {
          model: activeLabModel.code,
          messages,
          temperature: toOptionalNumber(labTemperature),
          max_tokens: toOptionalNumber(labMaxTokens),
          stream: activeLabModel.parameterNames.includes("stream") ? labStream || undefined : undefined,
        };
      }
      case "image": {
        return buildImagePayload(activeLabModel, {
          prompt: labImagePrompt,
          reference: labImageReference,
          size: labImageSize,
          aspectRatio: labImageAspectRatio,
          resolution: labImageResolution,
          responseFormat: labImageResponseFormat,
          watermark: labImageWatermark,
          outputFormat: labImageOutputFormat,
        });
      }
      case "audio":
        if (activeLabModel.routeFamily === "minimax_tts") {
          return {
            text: labAudioText.trim() || "欢迎来到 35m。",
            voice_id: labAudioVoice,
            audio_setting: activeLabModel.parameterNames.includes("audio_setting")
              ? {
                  format: labAudioFormat,
                }
              : undefined,
          };
        }
        return {
          text: labAudioText.trim() || "欢迎来到 35m。",
          voice: labAudioVoice,
          mode: activeLabModel.parameterNames.includes("mode") ? labAudioMode : undefined,
          language_type: activeLabModel.parameterNames.includes("language_type") ? "Chinese" : undefined,
          instructions: activeLabModel.parameterNames.includes("instructions") ? labSystemPrompt.trim() || undefined : undefined,
        };
      case "video":
        return buildVideoPayload(activeLabModel, {
          prompt: labVideoPrompt,
          reference: labVideoReference,
          audioUrl: labVideoAudioUrl,
          size: labVideoSize,
          seconds: labVideoSeconds,
          aspectRatio: labVideoAspectRatio,
          resolution: labVideoResolution,
          generateAudio: labVideoGenerateAudio,
          videoUrl: labVideoVideoUrl,
          firstFrame: labVideoFirstFrame,
          lastFrame: labVideoLastFrame,
          mode: labVideoMode,
        });
    }
  }, [
    activeLabModel.code,
    activeLabModel.parameterNames,
    activeLabModel.routeFamily,
    labAudioFormat,
    labAudioMode,
    labAudioText,
    labAudioVoice,
    labImagePrompt,
    labImageReference,
    labImageResponseFormat,
    labImageAspectRatio,
    labImageResolution,
    labImageSize,
    labImageWatermark,
    labImageOutputFormat,
    labKind,
    labMaxTokens,
    labStream,
    labSystemPrompt,
    labTemperature,
    labTextPrompt,
    labVideoAspectRatio,
    labVideoAudioUrl,
    labVideoFirstFrame,
    labVideoGenerateAudio,
    labVideoLastFrame,
    labVideoMode,
    labVideoPrompt,
    labVideoReference,
    labVideoResolution,
    labVideoSeconds,
    labVideoSize,
    labVideoVideoUrl,
  ]);

  const generatedLabJson = useMemo(() => stringifyJson(generatedLabBody), [generatedLabBody]);

  const currentLabBody = useMemo(() => {
    if (labRequestTab === "json") {
      try {
        return JSON.parse(labRawRequest) as Record<string, unknown>;
      } catch {
        return generatedLabBody;
      }
    }
    return generatedLabBody;
  }, [generatedLabBody, labRawRequest, labRequestTab]);

  const labJsonValid = useMemo(() => {
    if (labRequestTab !== "json") {
      return true;
    }
    try {
      JSON.parse(labRawRequest);
      return true;
    } catch {
      return false;
    }
  }, [labRawRequest, labRequestTab]);

  const currentCodeSnippet = useMemo(() => {
    if (labCodeTab === "python") {
      return buildPythonSnippet(activeLabModel.endpoint, currentLabBody, labChain);
    }
    if (labCodeTab === "javascript") {
      return buildJavaScriptSnippet(activeLabModel.endpoint, currentLabBody, labChain);
    }
    return buildCurlSnippet(activeLabModel.endpoint, currentLabBody, labChain);
  }, [activeLabModel.endpoint, currentLabBody, labChain, labCodeTab]);

  const currentPlaygroundBody = useMemo(() => {
    const content = playgroundInput.trim();
    if (!content) {
      return null;
    }

    if (playgroundTask === "chat") {
      if (activePlaygroundModel.routeFamily === "responses") {
        return {
          model: activePlaygroundModel.code,
          input: content,
          instructions: playgroundSystemPrompt.trim() || undefined,
          max_output_tokens: toOptionalNumber(playgroundMaxTokens),
        };
      }
      if (activePlaygroundModel.routeFamily === "gemini") {
        const generationConfig = {
          temperature: toOptionalNumber(playgroundTemperature),
          maxOutputTokens: toOptionalNumber(playgroundMaxTokens),
        };
        return {
          contents: [
            {
              role: "user",
              parts: [{ text: playgroundSystemPrompt.trim() ? `${playgroundSystemPrompt.trim()}\n\n${content}` : content }],
            },
          ],
          generationConfig:
            generationConfig.temperature !== undefined || generationConfig.maxOutputTokens !== undefined
              ? generationConfig
              : undefined,
        };
      }
      const messages: Array<{ role: string; content: string }> = [];
      if (playgroundSystemPrompt.trim()) {
        messages.push({ role: "system", content: playgroundSystemPrompt.trim() });
      }
      messages.push({ role: "user", content });
      return {
        model: activePlaygroundModel.code,
        messages,
        temperature: toOptionalNumber(playgroundTemperature),
        max_tokens: toOptionalNumber(playgroundMaxTokens),
      };
    }

    if (playgroundTask === "image") {
      return buildImagePayload(activePlaygroundModel, {
        prompt: content,
        reference: playgroundImageReference,
        size: playgroundImageSize,
        aspectRatio: playgroundImageAspectRatio,
        resolution: playgroundImageResolution,
        responseFormat: playgroundImageResponseFormat,
        watermark: playgroundImageWatermark,
        outputFormat: playgroundImageOutputFormat,
      });
    }

    if (playgroundTask === "audio") {
      if (activePlaygroundModel.routeFamily === "minimax_tts") {
        return {
          text: content,
          voice_id: playgroundAudioVoice,
          audio_setting: activePlaygroundModel.parameterNames.includes("audio_setting")
            ? { format: playgroundAudioFormat }
            : undefined,
        };
      }
      return {
        text: content,
        voice: playgroundAudioVoice,
        mode: activePlaygroundModel.parameterNames.includes("mode") ? playgroundAudioMode : undefined,
        language_type: activePlaygroundModel.parameterNames.includes("language_type") ? "Chinese" : undefined,
        instructions: activePlaygroundModel.parameterNames.includes("instructions")
          ? playgroundSystemPrompt.trim() || undefined
          : undefined,
      };
    }

    return buildVideoPayload(activePlaygroundModel, {
      prompt: content,
      reference: playgroundVideoReference,
      audioUrl: playgroundVideoAudioUrl,
      size: playgroundVideoSize,
      seconds: playgroundVideoSeconds,
      aspectRatio: playgroundVideoAspectRatio,
      resolution: playgroundVideoResolution,
      generateAudio: playgroundVideoGenerateAudio,
      videoUrl: playgroundVideoVideoUrl,
      firstFrame: playgroundVideoFirstFrame,
      lastFrame: playgroundVideoLastFrame,
      mode: playgroundVideoMode,
    });
  }, [
    activePlaygroundModel,
    playgroundAudioFormat,
    playgroundAudioMode,
    playgroundAudioVoice,
    playgroundImageAspectRatio,
    playgroundImageOutputFormat,
    playgroundImageReference,
    playgroundImageResolution,
    playgroundImageResponseFormat,
    playgroundImageSize,
    playgroundImageWatermark,
    playgroundInput,
    playgroundMaxTokens,
    playgroundSystemPrompt,
    playgroundTask,
    playgroundTemperature,
    playgroundVideoAspectRatio,
    playgroundVideoAudioUrl,
    playgroundVideoFirstFrame,
    playgroundVideoGenerateAudio,
    playgroundVideoLastFrame,
    playgroundVideoMode,
    playgroundVideoReference,
    playgroundVideoResolution,
    playgroundVideoSeconds,
    playgroundVideoSize,
    playgroundVideoVideoUrl,
  ]);

  useEffect(() => {
    if (!labJsonDirty) {
      setLabRawRequest(generatedLabJson);
    }
  }, [generatedLabJson, labJsonDirty]);

  useEffect(() => {
    const token = localStorage.getItem("session_token");
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }

    async function loadAll() {
      setLoadingSummary(true);
      const [accountResult, systemResult, userKeyResult, logsResult, qwenVoiceResult, minimaxVoiceResult, modelsResult] =
        await Promise.allSettled([
          getUserAccount(),
          getSystemDefaultApiKey(),
          listApiKeys(),
          listUsageLogs({ page: 1, size: 1 }),
          getQwenSystemVoicesApi(),
          getMiniMaxSystemVoicesApi(),
          listPublicModels(),
        ]);

      if (accountResult.status === "fulfilled") {
        setSummary((current) => ({ ...current, powerBalance: formatPower(accountResult.value.balance) }));
      }
      if (systemResult.status === "fulfilled") {
        setSystemApiKey(systemResult.value);
      }
      if (userKeyResult.status === "fulfilled") {
        setUserApiKeys(userKeyResult.value.filter((item) => item.key_kind !== "system_default"));
      }
      if (logsResult.status === "fulfilled") {
        setSummary((current) => ({ ...current, logsTotal: logsResult.value.total }));
      }
      if (modelsResult.status === "fulfilled") {
        setSummary((current) => ({ ...current, modelTotal: modelsResult.value.length }));
        setModelOptionsByKind(buildModelOptionsByKind(modelsResult.value));
      }

      if (qwenVoiceResult.status === "fulfilled") {
        const nextQwenVoices = (qwenVoiceResult.value.items || []).map((item) => ({
            value: item.voice,
            label: item.description ? `${item.voice} · ${item.description}` : item.voice,
          }));
        setQwenVoices(nextQwenVoices.length ? nextQwenVoices : DEFAULT_QWEN_VOICES);
      } else {
        setQwenVoices(DEFAULT_QWEN_VOICES);
      }

      if (minimaxVoiceResult.status === "fulfilled") {
        const nextMiniMaxVoices = (minimaxVoiceResult.value.items || [])
            .filter((item) => item.voice_id)
            .map((item) => ({
              value: String(item.voice_id),
              label: item.voice_name ? `${item.voice_name} · ${item.voice_id}` : String(item.voice_id),
            }));
        setMiniMaxVoices(nextMiniMaxVoices.length ? nextMiniMaxVoices : DEFAULT_MINIMAX_VOICES);
      } else {
        setMiniMaxVoices(DEFAULT_MINIMAX_VOICES);
      }

      setLoadingSummary(false);
    }

    void loadAll();
  }, [navigate]);

  useEffect(() => {
    setLabModelCode((current) => {
      const next = { ...current };
      let changed = false;
      (Object.keys(modelOptionsByKind) as LabKind[]).forEach((kind) => {
        const options = modelOptionsByKind[kind];
        if (!options.length) {
          return;
        }
        if (!options.some((item) => item.code === current[kind])) {
          next[kind] = options[0].code;
          changed = true;
        }
      });
      return changed ? next : current;
    });
  }, [modelOptionsByKind]);

  useEffect(() => {
    setPlaygroundModelCode((current) => {
      const next = { ...current };
      let changed = false;
      (Object.keys(taskModelMap) as PlaygroundTask[]).forEach((task) => {
        const options = taskModelMap[task];
        if (!options.length) {
          return;
        }
        if (!options.some((item) => item.code === current[task])) {
          next[task] = options[0].code;
          changed = true;
        }
      });
      return changed ? next : current;
    });
  }, [taskModelMap]);

  useEffect(() => {
    if (apiKeyOptions.length === 0) {
      return;
    }
    if (!apiKeyOptions.some((item) => item.optionId === labApiKeyOptionId)) {
      setLabApiKeyOptionId(apiKeyOptions[0].optionId);
    }
    if (!apiKeyOptions.some((item) => item.optionId === playgroundApiKeyOptionId)) {
      setPlaygroundApiKeyOptionId(apiKeyOptions[0].optionId);
    }
  }, [apiKeyOptions, labApiKeyOptionId, playgroundApiKeyOptionId]);

  useEffect(() => {
    if (activeLabModel.routeFamily !== "qwen_tts") {
      return;
    }
    const nextVoice = qwenVoices[0]?.value;
    if (!nextVoice) {
      return;
    }
    if (!qwenVoices.some((item) => item.value === labAudioVoice)) {
      setLabAudioVoice(nextVoice);
    }
  }, [activeLabModel.routeFamily, labAudioVoice, qwenVoices]);

  useEffect(() => {
    if (activeLabModel.routeFamily !== "minimax_tts") {
      return;
    }
    const nextVoice = minimaxVoices[0]?.value;
    if (!nextVoice) {
      return;
    }
    if (!minimaxVoices.some((item) => item.value === labAudioVoice)) {
      setLabAudioVoice(nextVoice);
    }
  }, [activeLabModel.routeFamily, labAudioVoice, minimaxVoices]);

  useEffect(() => {
    if (activePlaygroundModel.routeFamily !== "qwen_tts") {
      return;
    }
    const nextVoice = qwenVoices[0]?.value;
    if (!nextVoice) {
      return;
    }
    if (!qwenVoices.some((item) => item.value === playgroundAudioVoice)) {
      setPlaygroundAudioVoice(nextVoice);
    }
  }, [activePlaygroundModel.routeFamily, playgroundAudioVoice, qwenVoices]);

  useEffect(() => {
    if (activePlaygroundModel.routeFamily !== "minimax_tts") {
      return;
    }
    const nextVoice = minimaxVoices[0]?.value;
    if (!nextVoice) {
      return;
    }
    if (!minimaxVoices.some((item) => item.value === playgroundAudioVoice)) {
      setPlaygroundAudioVoice(nextVoice);
    }
  }, [activePlaygroundModel.routeFamily, minimaxVoices, playgroundAudioVoice]);

  useEffect(() => {
    const validValues = getImageSizeOptionsForModel(activeLabModel).map((item) => item.value);
    if (validValues.length && !validValues.includes(labImageSize)) {
      setLabImageSize(getDefaultImageSizeForModel(activeLabModel));
    }
  }, [activeLabModel, labImageSize]);

  useEffect(() => {
    const validValues = getImageSizeOptionsForModel(activePlaygroundModel).map((item) => item.value);
    if (validValues.length && !validValues.includes(playgroundImageSize)) {
      setPlaygroundImageSize(getDefaultImageSizeForModel(activePlaygroundModel));
    }
  }, [activePlaygroundModel, playgroundImageSize]);

  useEffect(() => {
    const validAspectRatios = getImageAspectRatioOptionsForModel(activeLabModel).map((item) => item.value);
    const validResolutions = getImageResolutionOptionsForModel(activeLabModel).map((item) => item.value);
    if (validAspectRatios.length && !validAspectRatios.includes(labImageAspectRatio)) {
      setLabImageAspectRatio(getDefaultImageAspectRatioForModel(activeLabModel));
    }
    if (validResolutions.length) {
      if (!validResolutions.includes(labImageResolution)) {
        setLabImageResolution(getDefaultImageResolutionForModel(activeLabModel));
      }
    } else if (labImageResolution) {
      setLabImageResolution("");
    }
  }, [activeLabModel, labImageAspectRatio, labImageResolution]);

  useEffect(() => {
    const validAspectRatios = getImageAspectRatioOptionsForModel(activePlaygroundModel).map((item) => item.value);
    const validResolutions = getImageResolutionOptionsForModel(activePlaygroundModel).map((item) => item.value);
    if (validAspectRatios.length && !validAspectRatios.includes(playgroundImageAspectRatio)) {
      setPlaygroundImageAspectRatio(getDefaultImageAspectRatioForModel(activePlaygroundModel));
    }
    if (validResolutions.length) {
      if (!validResolutions.includes(playgroundImageResolution)) {
        setPlaygroundImageResolution(getDefaultImageResolutionForModel(activePlaygroundModel));
      }
    } else if (playgroundImageResolution) {
      setPlaygroundImageResolution("");
    }
  }, [activePlaygroundModel, playgroundImageAspectRatio, playgroundImageResolution]);

  useEffect(() => {
    const validResolutionValues = getVideoResolutionOptionsForModel(activeLabModel).map((item) => item.value);
    const validSecondValues = getVideoSecondsOptionsForModel(activeLabModel).map((item) => item.value);
    if (!validResolutionValues.includes(labVideoResolution)) {
      setLabVideoResolution(getDefaultVideoResolutionForModel(activeLabModel));
    }
    if (!validSecondValues.includes(labVideoSeconds)) {
      setLabVideoSeconds(getDefaultVideoSecondsForModel(activeLabModel));
    }
  }, [activeLabModel.routeFamily, labVideoResolution, labVideoSeconds]);

  useEffect(() => {
    const validResolutionValues = getVideoResolutionOptionsForModel(activePlaygroundModel).map((item) => item.value);
    const validSecondValues = getVideoSecondsOptionsForModel(activePlaygroundModel).map((item) => item.value);
    if (!validResolutionValues.includes(playgroundVideoResolution)) {
      setPlaygroundVideoResolution(getDefaultVideoResolutionForModel(activePlaygroundModel));
    }
    if (!validSecondValues.includes(playgroundVideoSeconds)) {
      setPlaygroundVideoSeconds(getDefaultVideoSecondsForModel(activePlaygroundModel));
    }
  }, [activePlaygroundModel.routeFamily, playgroundVideoResolution, playgroundVideoSeconds]);

  useEffect(() => {
    const targetCodes = [activeLabModel.code, activePlaygroundModel.code].filter(Boolean);
    const missingCodes = targetCodes.filter((code) => !modelDetails[code]);
    if (!missingCodes.length) {
      return;
    }

    let cancelled = false;

    async function loadDetails() {
      const settled = await Promise.allSettled(missingCodes.map((code) => getPublicModelDetail(code)));
      if (cancelled) {
        return;
      }
      const nextDetails: Record<string, PublicModelDetailResponse> = {};
      settled.forEach((result, index) => {
        if (result.status === "fulfilled") {
          nextDetails[missingCodes[index]] = result.value;
        }
      });
      if (!Object.keys(nextDetails).length) {
        return;
      }
      setModelDetails((current) => ({ ...current, ...nextDetails }));
      setModelOptionsByKind((current) => {
        let changed = false;
        const next = { ...current };
        (Object.keys(current) as LabKind[]).forEach((kind) => {
          next[kind] = current[kind].map((item) => {
            const detail = nextDetails[item.code];
            if (!detail) {
              return item;
            }
            changed = true;
            return enrichModelOptionWithDetail(item, detail);
          });
        });
        return changed ? next : current;
      });
    }

    void loadDetails();

    return () => {
      cancelled = true;
    };
  }, [activeLabModel.code, activePlaygroundModel.code, modelDetails]);

  async function ensureActiveApiKeyValue(selectedOption: ApiKeyOption | null) {
    if (!selectedOption) {
      throw new Error("请先选择可用 API Key。");
    }
    if (selectedOption.kind === "system") {
      if (!selectedOption.keyValue) {
        throw new Error("系统默认 Key 暂不可用，请前往 API Keys 页面重置。");
      }
      return selectedOption.keyValue;
    }
    if (selectedOption.keyValue) {
      return selectedOption.keyValue;
    }
    if (!selectedOption.keyId) {
      throw new Error("当前 Key 无法使用。");
    }
    const revealed = await revealApiKey(selectedOption.keyId);
    if (!revealed.api_key) {
      throw new Error("当前 Key 明文不可见。");
    }
    setRevealedKeys((current) => ({ ...current, [selectedOption.keyId as number]: revealed.api_key as string }));
    return revealed.api_key;
  }

  async function resolveRequestMeta(requestId: string | null): Promise<RequestMeta> {
    if (!requestId) {
      return buildPendingRequestMeta(null);
    }

    let detail: UsageLogDetailResponse | null = null;
    for (let index = 0; index < 4; index += 1) {
      try {
        detail = await getUsageLogDetail(requestId);
        break;
      } catch {
        await sleep(250 * (index + 1));
      }
    }

    return {
      requestId,
      powerAmount: detail?.power_amount ?? null,
      durationMs: detail?.duration_ms ?? null,
      providerSummary: normalizeProviderSummary(detail),
      detail,
    };
  }

  async function hydrateLabRequestMeta(requestId: string) {
    try {
      const meta = await resolveRequestMeta(requestId);
      setLabResult((current) => {
        if (!current || current.meta.requestId !== requestId) {
          return current;
        }
        return { ...current, meta };
      });
    } catch {
      // Keep the immediate response visible even if log detail is late or unavailable.
    }
  }

  async function hydratePlaygroundMessageMeta(messageId: string, requestId: string) {
    try {
      const meta = await resolveRequestMeta(requestId);
      setPlaygroundMessages((current) =>
        current.map((item) => (item.id === messageId ? { ...item, meta } : item)),
      );
    } catch {
      // Keep the immediate response visible even if log detail is late or unavailable.
    }
  }

  async function executeWithSelectedKey(
    selectedOption: ApiKeyOption | null,
    endpoint: string,
    body: Record<string, unknown>,
    chain = "",
  ): Promise<RunResult> {
    const apiKey = await ensureActiveApiKeyValue(selectedOption);
    const headers = new Headers({
      "Accept-Language": "zh-CN",
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    });

    if (chain.trim()) {
      headers.set("x-api35-chain", chain.trim());
    }

    const response = await fetch(`${getApi35Base()}${endpoint}`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    const requestId = response.headers.get("X-API35-Request-Id");
    const raw = await response.text();
    let data: unknown = null;
    try {
      data = raw ? JSON.parse(raw) : null;
    } catch {
      data = raw;
    }
    const meta = buildPendingRequestMeta(requestId);

    if (!response.ok) {
      const detailMessage =
        typeof (data as Record<string, unknown> | null)?.detail === "string"
          ? String((data as Record<string, unknown>).detail)
          : `请求失败: ${response.status}`;
      return {
        ok: false,
        statusCode: response.status,
        data,
        raw,
        meta,
        errorMessage: detailMessage,
      };
    }

    return {
      ok: true,
      statusCode: response.status,
      data,
      raw,
      meta,
      errorMessage: null,
    };
  }

  async function executeEstimateWithSelectedKey(
    selectedOption: ApiKeyOption | null,
    {
      model,
      payload,
      chain = "",
    }: {
      model: string;
      payload: Record<string, unknown>;
      chain?: string;
    },
  ): Promise<EstimateSummaryResponse> {
    const apiKey = await ensureActiveApiKeyValue(selectedOption);
    const response = await fetch(`${getApi35Base()}/v1/estimates`, {
      method: "POST",
      headers: {
        "Accept-Language": "zh-CN",
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        payload: stripModelField(payload),
        chain: chain.trim() ? parseProviderChain(chain) : undefined,
      }),
    });

    const raw = await response.text();
    let data: unknown = null;
    try {
      data = raw ? JSON.parse(raw) : null;
    } catch {
      data = null;
    }

    if (!response.ok) {
      const detail =
        typeof (data as Record<string, unknown> | null)?.detail === "string"
          ? String((data as Record<string, unknown>).detail)
          : `请求失败: ${response.status}`;
      throw new Error(detail);
    }

    return data as EstimateSummaryResponse;
  }

  useEffect(() => {
    if (!selectedLabApiKeyOption || !activeLabModel.code || !labJsonValid) {
      setLabEstimate({ loading: false, text: "", warning: false });
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(() => {
      setLabEstimate((current) => ({ ...current, loading: true }));
      void executeEstimateWithSelectedKey(selectedLabApiKeyOption, {
        model: activeLabModel.code,
        payload: currentLabBody,
        chain: labChain,
      })
        .then((data) => {
          if (cancelled) {
            return;
          }
          setLabEstimate(toEstimateDisplay(data));
        })
        .catch(() => {
          if (cancelled) {
            return;
          }
          setLabEstimate({ loading: false, text: "", warning: false });
        });
    }, 360);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [activeLabModel.code, currentLabBody, labChain, labJsonValid, selectedLabApiKeyOption]);

  useEffect(() => {
    if (!selectedPlaygroundApiKeyOption || !activePlaygroundModel.code || !currentPlaygroundBody) {
      setPlaygroundEstimate({ loading: false, text: "", warning: false });
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(() => {
      setPlaygroundEstimate((current) => ({ ...current, loading: true }));
      void executeEstimateWithSelectedKey(selectedPlaygroundApiKeyOption, {
        model: activePlaygroundModel.code,
        payload: currentPlaygroundBody,
      })
        .then((data) => {
          if (cancelled) {
            return;
          }
          setPlaygroundEstimate(toEstimateDisplay(data));
        })
        .catch(() => {
          if (cancelled) {
            return;
          }
          setPlaygroundEstimate({ loading: false, text: "", warning: false });
        });
    }, 360);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [activePlaygroundModel.code, currentPlaygroundBody, selectedPlaygroundApiKeyOption]);

  async function refreshSummaryAfterRun() {
    const [accountResult, logsResult] = await Promise.allSettled([
      getUserAccount(),
      listUsageLogs({ page: 1, size: 1 }),
      refresh(1, 300),
    ]);
    if (accountResult.status === "fulfilled") {
      setSummary((current) => ({ ...current, powerBalance: formatPower(accountResult.value.balance) }));
    }
    if (logsResult.status === "fulfilled") {
      setSummary((current) => ({ ...current, logsTotal: logsResult.value.total }));
    }
  }

  async function handleRunLab() {
    setLabRunning(true);
    try {
      if (labRequestTab === "json") {
        JSON.parse(labRawRequest);
      }
      const result = await executeWithSelectedKey(selectedLabApiKeyOption, activeLabModel.endpoint, currentLabBody, labChain);
      setLabResult(result);
      if (!result.ok) {
        message.error(result.errorMessage || "请求失败");
      } else {
        if (result.meta.requestId) {
          void hydrateLabRequestMeta(result.meta.requestId);
        }
        void refreshSummaryAfterRun();
        message.success("API 调用完成");
      }
    } catch (error) {
      const detail = error instanceof Error ? error.message : "请求失败";
      setLabResult({
        ok: false,
        statusCode: null,
        data: null,
        raw: "",
        meta: buildPendingRequestMeta(null),
        errorMessage: detail,
      });
      message.error(detail);
    } finally {
      setLabRunning(false);
    }
  }

  async function handlePlaygroundSubmit() {
    const content = playgroundInput.trim();
    if (!content) {
      message.warning("请先输入内容。");
      return;
    }

    const userMessage: PlaygroundMessage = {
      id: buildMessageId(),
      role: "user",
      task: playgroundTask,
      modelLabel: activePlaygroundModel.label,
      content,
      meta: null,
    };
    setPlaygroundMessages((current) => [...current, userMessage]);
    setPlaygroundWorking(true);

    try {
      const payload = currentPlaygroundBody;
      if (!payload) {
        throw new Error("当前输入暂时无法计算请求内容。");
      }

      const result = await executeWithSelectedKey(selectedPlaygroundApiKeyOption, activePlaygroundModel.endpoint, payload);

      const assistantMessage: PlaygroundMessage = {
        id: buildMessageId(),
        role: "assistant",
        task: playgroundTask,
        modelLabel: activePlaygroundModel.label,
        content: playgroundTask === "chat" ? extractTextFromResponse(result.data) : undefined,
        imageUrl: playgroundTask === "image" ? extractImageUrl(result.data) : null,
        audioUrl: playgroundTask === "audio" ? extractAudioUrl(result.data) : null,
        videoUrl: playgroundTask === "video" ? extractVideoUrl(result.data) : null,
        taskStatus:
          playgroundTask === "video" || (playgroundTask === "audio" && activePlaygroundModel.routeFamily === "minimax_tts")
            ? (result.data as Record<string, any> | null)?.status ?? null
            : null,
        meta: result.meta,
        errorMessage: result.ok ? null : result.errorMessage,
      };

      setPlaygroundMessages((current) => [...current, assistantMessage]);
      setPlaygroundInput("");
      if (!result.ok) {
        message.error(result.errorMessage || "生成失败");
      } else {
        if (assistantMessage.meta?.requestId) {
          void hydratePlaygroundMessageMeta(assistantMessage.id, assistantMessage.meta.requestId);
        }
        void refreshSummaryAfterRun();
      }
    } catch (error) {
      const assistantMessage: PlaygroundMessage = {
        id: buildMessageId(),
        role: "assistant",
        task: playgroundTask,
        modelLabel: activePlaygroundModel.label,
        meta: null,
        errorMessage: error instanceof Error ? error.message : "生成失败",
      };
      setPlaygroundMessages((current) => [...current, assistantMessage]);
      message.error(error instanceof Error ? error.message : "生成失败");
    } finally {
      setPlaygroundWorking(false);
    }
  }

  return (
    <div className="workbench-home">
      <WorkbenchHero
        powerBalance={loadingSummary ? "-" : summary.powerBalance}
        logsTotal={loadingSummary ? "-" : summary.logsTotal}
        modelTotal={loadingSummary ? "-" : summary.modelTotal}
      />

      <section className="workbench-grid">
        <ApiLabPanel
          apiKeyOptions={apiKeyOptions}
          selectedApiKeyOptionId={labApiKeyOptionId}
          activeLabModel={activeLabModel}
          labModelOptions={modelOptionsByKind[labKind]}
          currentCodeSnippet={currentCodeSnippet}
          currentLabBody={currentLabBody}
          labKind={labKind}
          labModelCode={labModelCode}
          labRunning={labRunning}
          labEstimateText={labEstimate.text}
          labEstimateLoading={labEstimate.loading}
          labEstimateWarning={labEstimate.warning}
          labAdvanced={labAdvanced}
          labRequestTab={labRequestTab}
          labResponseTab={labResponseTab}
          labCodeTab={labCodeTab}
          labRawRequest={labRawRequest}
          labResult={labResult}
          labChain={labChain}
          labStream={labStream}
          labTextPrompt={labTextPrompt}
          labSystemPrompt={labSystemPrompt}
          labTemperature={labTemperature}
          labMaxTokens={labMaxTokens}
          labImagePrompt={labImagePrompt}
          labImageReference={labImageReference}
          labImageSize={labImageSize}
          labImageAspectRatio={labImageAspectRatio}
          labImageResolution={labImageResolution}
          labImageResponseFormat={labImageResponseFormat}
          labImageWatermark={labImageWatermark}
          labImageOutputFormat={labImageOutputFormat}
          labAudioText={labAudioText}
          labAudioVoice={labAudioVoice}
          labAudioMode={labAudioMode}
          labAudioFormat={labAudioFormat}
          labVideoPrompt={labVideoPrompt}
          labVideoReference={labVideoReference}
          labVideoAudioUrl={labVideoAudioUrl}
          labVideoSize={labVideoSize}
          labVideoSeconds={labVideoSeconds}
          labVideoAspectRatio={labVideoAspectRatio}
          labVideoResolution={labVideoResolution}
          labVideoGenerateAudio={labVideoGenerateAudio}
          labVideoVideoUrl={labVideoVideoUrl}
          labVideoFirstFrame={labVideoFirstFrame}
          labVideoLastFrame={labVideoLastFrame}
          labVideoMode={labVideoMode}
          qwenVoices={qwenVoices}
          minimaxVoices={minimaxVoices}
          onSetLabKind={(value) => {
            setLabKind(value);
            setLabResult(null);
          }}
          onSetLabModelCode={(value) => {
            setLabModelCode((current) => ({ ...current, [labKind]: value }));
            setLabResult(null);
          }}
          onSetLabRequestTab={setLabRequestTab}
          onSetLabResponseTab={setLabResponseTab}
          onSetLabCodeTab={setLabCodeTab}
          onToggleLabAdvanced={() => setLabAdvanced((current) => !current)}
          onSetLabRawRequest={setLabRawRequest}
          onSetLabJsonDirty={setLabJsonDirty}
          onSetLabChain={setLabChain}
          onSetLabStream={setLabStream}
          onSetLabTextPrompt={setLabTextPrompt}
          onSetLabSystemPrompt={setLabSystemPrompt}
          onSetLabTemperature={setLabTemperature}
          onSetLabMaxTokens={setLabMaxTokens}
          onSetLabImagePrompt={setLabImagePrompt}
          onSetLabImageReference={setLabImageReference}
          onSetLabImageSize={setLabImageSize}
          onSetLabImageAspectRatio={setLabImageAspectRatio}
          onSetLabImageResolution={setLabImageResolution}
          onSetLabImageResponseFormat={setLabImageResponseFormat}
          onSetLabImageWatermark={setLabImageWatermark}
          onSetLabImageOutputFormat={setLabImageOutputFormat}
          onSetLabAudioText={setLabAudioText}
          onSetLabAudioVoice={setLabAudioVoice}
          onSetLabAudioMode={setLabAudioMode}
          onSetLabAudioFormat={setLabAudioFormat}
          onSetLabVideoPrompt={setLabVideoPrompt}
          onSetLabVideoReference={setLabVideoReference}
          onSetLabVideoAudioUrl={setLabVideoAudioUrl}
          onSetLabVideoSize={setLabVideoSize}
          onSetLabVideoSeconds={setLabVideoSeconds}
          onSetLabVideoAspectRatio={setLabVideoAspectRatio}
          onSetLabVideoResolution={setLabVideoResolution}
          onSetLabVideoGenerateAudio={setLabVideoGenerateAudio}
          onSetLabVideoVideoUrl={setLabVideoVideoUrl}
          onSetLabVideoFirstFrame={setLabVideoFirstFrame}
          onSetLabVideoLastFrame={setLabVideoLastFrame}
          onSetLabVideoMode={setLabVideoMode}
          onSelectApiKey={setLabApiKeyOptionId}
          onRun={handleRunLab}
          onCopyText={copyText}
          onOpenDocs={() => window.open(activeLabModel.docsHref, "_blank", "noopener,noreferrer")}
          onNavigateDetail={(requestId) => navigate(`/logs/${requestId}`)}
        />

        <PlaygroundPanel
          apiKeyOptions={apiKeyOptions}
          selectedApiKeyOptionId={playgroundApiKeyOptionId}
          activePlaygroundModel={activePlaygroundModel}
          playgroundModelOptions={taskModelMap[playgroundTask]}
          playgroundTask={playgroundTask}
          playgroundMessages={playgroundMessages}
          playgroundInput={playgroundInput}
          playgroundModelCode={playgroundModelCode}
          playgroundWorking={playgroundWorking}
          playgroundEstimateText={playgroundEstimate.text}
          playgroundEstimateLoading={playgroundEstimate.loading}
          playgroundEstimateWarning={playgroundEstimate.warning}
          playgroundAdvanced={playgroundAdvanced}
          playgroundSystemPrompt={playgroundSystemPrompt}
          playgroundTemperature={playgroundTemperature}
          playgroundMaxTokens={playgroundMaxTokens}
          playgroundImageReference={playgroundImageReference}
          playgroundImageSize={playgroundImageSize}
          playgroundImageAspectRatio={playgroundImageAspectRatio}
          playgroundImageResolution={playgroundImageResolution}
          playgroundImageResponseFormat={playgroundImageResponseFormat}
          playgroundImageWatermark={playgroundImageWatermark}
          playgroundImageOutputFormat={playgroundImageOutputFormat}
          playgroundAudioVoice={playgroundAudioVoice}
          playgroundAudioMode={playgroundAudioMode}
          playgroundAudioFormat={playgroundAudioFormat}
          playgroundVideoReference={playgroundVideoReference}
          playgroundVideoAudioUrl={playgroundVideoAudioUrl}
          playgroundVideoSize={playgroundVideoSize}
          playgroundVideoSeconds={playgroundVideoSeconds}
          playgroundVideoAspectRatio={playgroundVideoAspectRatio}
          playgroundVideoResolution={playgroundVideoResolution}
          playgroundVideoGenerateAudio={playgroundVideoGenerateAudio}
          playgroundVideoVideoUrl={playgroundVideoVideoUrl}
          playgroundVideoFirstFrame={playgroundVideoFirstFrame}
          playgroundVideoLastFrame={playgroundVideoLastFrame}
          playgroundVideoMode={playgroundVideoMode}
          qwenVoices={qwenVoices}
          minimaxVoices={minimaxVoices}
          onSetPlaygroundTask={setPlaygroundTask}
          onSetPlaygroundModelCode={(value) => {
            setPlaygroundModelCode((current) => ({ ...current, [playgroundTask]: value }));
          }}
          onSetPlaygroundInput={setPlaygroundInput}
          onTogglePlaygroundAdvanced={() => setPlaygroundAdvanced((current) => !current)}
          onSetPlaygroundSystemPrompt={setPlaygroundSystemPrompt}
          onSetPlaygroundTemperature={setPlaygroundTemperature}
          onSetPlaygroundMaxTokens={setPlaygroundMaxTokens}
          onSetPlaygroundImageReference={setPlaygroundImageReference}
          onSetPlaygroundImageSize={setPlaygroundImageSize}
          onSetPlaygroundImageAspectRatio={setPlaygroundImageAspectRatio}
          onSetPlaygroundImageResolution={setPlaygroundImageResolution}
          onSetPlaygroundImageResponseFormat={setPlaygroundImageResponseFormat}
          onSetPlaygroundImageWatermark={setPlaygroundImageWatermark}
          onSetPlaygroundImageOutputFormat={setPlaygroundImageOutputFormat}
          onSetPlaygroundAudioVoice={setPlaygroundAudioVoice}
          onSetPlaygroundAudioMode={setPlaygroundAudioMode}
          onSetPlaygroundAudioFormat={setPlaygroundAudioFormat}
          onSetPlaygroundVideoReference={setPlaygroundVideoReference}
          onSetPlaygroundVideoAudioUrl={setPlaygroundVideoAudioUrl}
          onSetPlaygroundVideoSize={setPlaygroundVideoSize}
          onSetPlaygroundVideoSeconds={setPlaygroundVideoSeconds}
          onSetPlaygroundVideoAspectRatio={setPlaygroundVideoAspectRatio}
          onSetPlaygroundVideoResolution={setPlaygroundVideoResolution}
          onSetPlaygroundVideoGenerateAudio={setPlaygroundVideoGenerateAudio}
          onSetPlaygroundVideoVideoUrl={setPlaygroundVideoVideoUrl}
          onSetPlaygroundVideoFirstFrame={setPlaygroundVideoFirstFrame}
          onSetPlaygroundVideoLastFrame={setPlaygroundVideoLastFrame}
          onSetPlaygroundVideoMode={setPlaygroundVideoMode}
          onSelectApiKey={setPlaygroundApiKeyOptionId}
          onSubmit={handlePlaygroundSubmit}
          onClearMessages={() => setPlaygroundMessages([])}
          onNavigateDetail={(requestId) => navigate(`/logs/${requestId}`)}
        />
      </section>
    </div>
  );
}
