import AppButton from "@/shared/ui/button/button";
import { ArrowUpRightIcon, CircleAlertIcon, CopyIcon, DownloadIcon, LoaderCircleIcon, PlayIcon } from "@/shared/ui/icon";
import AppSelect from "@/shared/ui/select/page";
import {
  AUDIO_FORMAT_OPTIONS,
  AUDIO_MODE_OPTIONS,
  getImageAspectRatioOptionsForModel,
  getImageResolutionOptionsForModel,
  getImageSizeOptionsForModel,
  IMAGE_OUTPUT_FORMAT_OPTIONS,
  KLING_MODE_OPTIONS,
  getVideoResolutionOptionsForModel,
  getVideoSecondsOptionsForModel,
  LAB_KIND_OPTIONS,
  supportsModelParameter,
  VIDEO_ASPECT_RATIO_OPTIONS,
} from "../home.data";
import type { ApiKeyOption, CodeLanguage, LabKind, ModelOption, RequestTab, ResponseTab, RunResult, VoiceOption } from "../home.types";
import {
  extractAudioUrl,
  extractImageUrl,
  extractTextFromResponse,
  extractVideoUrl,
  formatDuration,
  formatPower,
  stringifyJson,
} from "../lib/home-utils";

type ApiLabPanelProps = {
  apiKeyOptions: ApiKeyOption[];
  selectedApiKeyOptionId: string;
  activeLabModel: ModelOption;
  labModelOptions: ModelOption[];
  currentCodeSnippet: string;
  currentLabBody: Record<string, unknown>;
  labKind: LabKind;
  labModelCode: Record<LabKind, string>;
  labRunning: boolean;
  labEstimateText: string;
  labEstimateLoading: boolean;
  labEstimateWarning: boolean;
  labAdvanced: boolean;
  labRequestTab: RequestTab;
  labResponseTab: ResponseTab;
  labCodeTab: CodeLanguage;
  labRawRequest: string;
  labResult: RunResult | null;
  labChain: string;
  labStream: boolean;
  labTextPrompt: string;
  labSystemPrompt: string;
  labTemperature: string;
  labMaxTokens: string;
  labImagePrompt: string;
  labImageReference: string;
  labImageSize: string;
  labImageAspectRatio: string;
  labImageResolution: string;
  labImageResponseFormat: string;
  labImageWatermark: boolean;
  labImageOutputFormat: string;
  labAudioText: string;
  labAudioVoice: string;
  labAudioMode: string;
  labAudioFormat: string;
  labVideoPrompt: string;
  labVideoReference: string;
  labVideoAudioUrl: string;
  labVideoSize: string;
  labVideoSeconds: string;
  labVideoAspectRatio: string;
  labVideoResolution: string;
  labVideoGenerateAudio: boolean;
  labVideoVideoUrl: string;
  labVideoFirstFrame: string;
  labVideoLastFrame: string;
  labVideoMode: string;
  qwenVoices: VoiceOption[];
  minimaxVoices: VoiceOption[];
  onSetLabKind: (value: LabKind) => void;
  onSetLabModelCode: (value: string) => void;
  onSetLabRequestTab: (value: RequestTab) => void;
  onSetLabResponseTab: (value: ResponseTab) => void;
  onSetLabCodeTab: (value: CodeLanguage) => void;
  onToggleLabAdvanced: () => void;
  onSetLabRawRequest: (value: string) => void;
  onSetLabJsonDirty: (value: boolean) => void;
  onSetLabChain: (value: string) => void;
  onSetLabStream: (value: boolean) => void;
  onSetLabTextPrompt: (value: string) => void;
  onSetLabSystemPrompt: (value: string) => void;
  onSetLabTemperature: (value: string) => void;
  onSetLabMaxTokens: (value: string) => void;
  onSetLabImagePrompt: (value: string) => void;
  onSetLabImageReference: (value: string) => void;
  onSetLabImageSize: (value: string) => void;
  onSetLabImageAspectRatio: (value: string) => void;
  onSetLabImageResolution: (value: string) => void;
  onSetLabImageResponseFormat: (value: string) => void;
  onSetLabImageWatermark: (value: boolean) => void;
  onSetLabImageOutputFormat: (value: string) => void;
  onSetLabAudioText: (value: string) => void;
  onSetLabAudioVoice: (value: string) => void;
  onSetLabAudioMode: (value: string) => void;
  onSetLabAudioFormat: (value: string) => void;
  onSetLabVideoPrompt: (value: string) => void;
  onSetLabVideoReference: (value: string) => void;
  onSetLabVideoAudioUrl: (value: string) => void;
  onSetLabVideoSize: (value: string) => void;
  onSetLabVideoSeconds: (value: string) => void;
  onSetLabVideoAspectRatio: (value: string) => void;
  onSetLabVideoResolution: (value: string) => void;
  onSetLabVideoGenerateAudio: (value: boolean) => void;
  onSetLabVideoVideoUrl: (value: string) => void;
  onSetLabVideoFirstFrame: (value: string) => void;
  onSetLabVideoLastFrame: (value: string) => void;
  onSetLabVideoMode: (value: string) => void;
  onSelectApiKey: (value: string) => void;
  onRun: () => void;
  onCopyText: (value: string, successText: string) => Promise<void>;
  onOpenDocs: () => void;
  onNavigateDetail: (requestId: string) => void;
};

export function ApiLabPanel(props: ApiLabPanelProps) {
  const {
    apiKeyOptions,
    selectedApiKeyOptionId,
    activeLabModel,
    labModelOptions,
    currentCodeSnippet,
    currentLabBody,
    labKind,
    labModelCode,
    labRunning,
    labEstimateText,
    labEstimateLoading,
    labEstimateWarning,
    labAdvanced,
    labRequestTab,
    labResponseTab,
    labCodeTab,
    labRawRequest,
    labResult,
    labChain,
    labStream,
    labTextPrompt,
    labSystemPrompt,
    labTemperature,
    labMaxTokens,
    labImagePrompt,
    labImageReference,
    labImageSize,
    labImageAspectRatio,
    labImageResolution,
    labImageResponseFormat,
    labImageWatermark,
    labImageOutputFormat,
    labAudioText,
    labAudioVoice,
    labAudioMode,
    labAudioFormat,
    labVideoPrompt,
    labVideoReference,
    labVideoAudioUrl,
    labVideoSize,
    labVideoSeconds,
    labVideoAspectRatio,
    labVideoResolution,
    labVideoGenerateAudio,
    labVideoVideoUrl,
    labVideoFirstFrame,
    labVideoLastFrame,
    labVideoMode,
    qwenVoices,
    minimaxVoices,
    onSetLabKind,
    onSetLabModelCode,
    onSetLabRequestTab,
    onSetLabResponseTab,
    onSetLabCodeTab,
    onToggleLabAdvanced,
    onSetLabRawRequest,
    onSetLabJsonDirty,
    onSetLabChain,
    onSetLabStream,
    onSetLabTextPrompt,
    onSetLabSystemPrompt,
    onSetLabTemperature,
    onSetLabMaxTokens,
    onSetLabImagePrompt,
    onSetLabImageReference,
    onSetLabImageSize,
    onSetLabImageAspectRatio,
    onSetLabImageResolution,
    onSetLabImageResponseFormat,
    onSetLabImageWatermark,
    onSetLabImageOutputFormat,
    onSetLabAudioText,
    onSetLabAudioVoice,
    onSetLabAudioMode,
    onSetLabAudioFormat,
    onSetLabVideoPrompt,
    onSetLabVideoReference,
    onSetLabVideoAudioUrl,
    onSetLabVideoSize,
    onSetLabVideoSeconds,
    onSetLabVideoAspectRatio,
    onSetLabVideoResolution,
    onSetLabVideoGenerateAudio,
    onSetLabVideoVideoUrl,
    onSetLabVideoFirstFrame,
    onSetLabVideoLastFrame,
    onSetLabVideoMode,
    onSelectApiKey,
    onRun,
    onCopyText,
    onOpenDocs,
    onNavigateDetail,
  } = props;

  const labModelSelectOptions = labModelOptions.map((item) => ({
    label: item.label,
    value: item.code,
  }));
  const apiKeySelectOptions = apiKeyOptions.map((item) => ({
    label: `${item.label}${item.keyPrefix ? ` · ${item.keyPrefix}` : ""}`,
    value: item.optionId,
  }));
  const supportsImageReference = supportsModelParameter(activeLabModel, "image") || supportsModelParameter(activeLabModel, "image_urls");
  const supportsImageSize = supportsModelParameter(activeLabModel, "size");
  const supportsImageAspectRatio = supportsModelParameter(activeLabModel, "aspect_ratio");
  const supportsImageResolution = supportsModelParameter(activeLabModel, "resolution");
  const supportsImageResponseFormat = supportsModelParameter(activeLabModel, "response_format");
  const supportsImageWatermark = supportsModelParameter(activeLabModel, "watermark");
  const supportsImageOutputFormat = supportsModelParameter(activeLabModel, "output_format");
  const supportsVideoReference = supportsModelParameter(activeLabModel, "input_reference") || supportsModelParameter(activeLabModel, "image");
  const supportsVideoReferenceList =
    supportsModelParameter(activeLabModel, "reference_urls") || supportsModelParameter(activeLabModel, "reference_images");
  const supportsVideoSeconds = supportsModelParameter(activeLabModel, "seconds");
  const supportsVideoAspectRatio = supportsModelParameter(activeLabModel, "aspect_ratio");
  const supportsVideoResolution = supportsModelParameter(activeLabModel, "resolution");
  const supportsVideoGenerateAudio = supportsModelParameter(activeLabModel, "generate_audio");
  const supportsVideoSize = supportsModelParameter(activeLabModel, "size");
  const supportsVideoAudioUrl = supportsModelParameter(activeLabModel, "audio_url");
  const supportsVideoVideoUrl = supportsModelParameter(activeLabModel, "video_url");
  const supportsVideoFirstFrame = supportsModelParameter(activeLabModel, "first_frame");
  const supportsVideoLastFrame = supportsModelParameter(activeLabModel, "last_frame");
  const supportsVideoMode = supportsModelParameter(activeLabModel, "mode");
  const supportsAudioMode = supportsModelParameter(activeLabModel, "mode");
  const supportsAudioInstructions = supportsModelParameter(activeLabModel, "instructions");
  const currentImageSizeOptions = getImageSizeOptionsForModel(activeLabModel);
  const currentImageAspectRatioOptions = getImageAspectRatioOptionsForModel(activeLabModel);
  const currentImageResolutionOptions = getImageResolutionOptionsForModel(activeLabModel);
  const currentVideoSecondsOptions = getVideoSecondsOptionsForModel(activeLabModel);
  const currentVideoResolutionOptions = getVideoResolutionOptionsForModel(activeLabModel);
  const labParameterNames = new Set(activeLabModel.parameterNames);

  const renderLabForm = () => {
    if (labKind === "text") {
      return (
        <div className="home-form-stack">
          <label className="home-field">
            <span>系统提示词</span>
            <textarea
              data-testid="lab-system-prompt-input"
              value={labSystemPrompt}
              onChange={(event) => onSetLabSystemPrompt(event.target.value)}
              placeholder="可选的 system prompt"
            />
          </label>
          <label className="home-field">
            <span>用户输入</span>
            <textarea
              data-testid="lab-text-prompt-input"
              value={labTextPrompt}
              onChange={(event) => onSetLabTextPrompt(event.target.value)}
              placeholder="输入一条对话消息"
            />
          </label>
          <div className="home-inline-grid two">
            <label className="home-field">
              <span>temperature</span>
              <input
                value={labTemperature}
                onChange={(event) => onSetLabTemperature(event.target.value)}
                placeholder="留空则不传"
              />
            </label>
            <label className="home-field">
              <span>max_tokens</span>
              <input
                value={labMaxTokens}
                onChange={(event) => onSetLabMaxTokens(event.target.value)}
                placeholder="留空则不传"
              />
            </label>
          </div>
        </div>
      );
    }

    if (labKind === "image") {
      return (
        <div className="home-form-stack">
          <label className="home-field">
            <span>提示词</span>
            <textarea
              data-testid="lab-image-prompt-input"
              value={labImagePrompt}
              onChange={(event) => onSetLabImagePrompt(event.target.value)}
              placeholder="输入图片提示词"
            />
          </label>
          <div
            className={`home-inline-grid ${
              supportsImageReference && (supportsImageSize || supportsImageAspectRatio || supportsImageResolution) ? "two" : "one"
            }`}
          >
            {supportsImageReference ? (
              <label className="home-field">
                <span>{activeLabModel.routeFamily === "banana" ? "参考图 URL（可多行）" : "参考图 URL"}</span>
                {activeLabModel.routeFamily === "banana" ? (
                  <textarea value={labImageReference} onChange={(event) => onSetLabImageReference(event.target.value)} placeholder="每行一个 https://..." />
                ) : (
                  <input value={labImageReference} onChange={(event) => onSetLabImageReference(event.target.value)} placeholder="https://..." />
                )}
              </label>
            ) : null}
            {supportsImageSize && activeLabModel.routeFamily !== "banana" ? (
              <label className="home-field">
                <span>size</span>
                <AppSelect
                  currentValue={labImageSize}
                  optionList={currentImageSizeOptions}
                  label="label"
                  value="value"
                  onSelectCall={onSetLabImageSize}
                  classNames="home-app-select"
                  triggerTestId="lab-image-size-select"
                />
              </label>
            ) : null}
          </div>
          {activeLabModel.routeFamily === "banana" ? (
            <div className={`home-inline-grid ${supportsImageAspectRatio && supportsImageResolution ? "two" : "one"}`}>
              {supportsImageAspectRatio ? (
                <label className="home-field">
                  <span>aspect_ratio</span>
                  <AppSelect
                    currentValue={labImageAspectRatio}
                    optionList={currentImageAspectRatioOptions}
                    label="label"
                    value="value"
                    onSelectCall={onSetLabImageAspectRatio}
                    classNames="home-app-select"
                    triggerTestId="lab-image-aspect-ratio-select"
                  />
                </label>
              ) : null}
              {supportsImageResolution && currentImageResolutionOptions.length ? (
                <label className="home-field">
                  <span>resolution</span>
                  <AppSelect
                    currentValue={labImageResolution}
                    optionList={currentImageResolutionOptions}
                    label="label"
                    value="value"
                    onSelectCall={onSetLabImageResolution}
                    classNames="home-app-select"
                    triggerTestId="lab-image-resolution-select"
                  />
                </label>
              ) : null}
            </div>
          ) : null}
          {supportsImageResponseFormat ? (
            <label className="home-field">
              <span>response_format</span>
              <AppSelect
                currentValue={labImageResponseFormat}
                optionList={[
                  { label: "url", value: "url" },
                  { label: "b64_json", value: "b64_json" },
                ]}
                label="label"
                value="value"
                onSelectCall={onSetLabImageResponseFormat}
                classNames="home-app-select"
              />
            </label>
          ) : null}
          {supportsImageOutputFormat ? (
            <label className="home-field">
              <span>output_format</span>
              <AppSelect
                currentValue={labImageOutputFormat}
                optionList={IMAGE_OUTPUT_FORMAT_OPTIONS}
                label="label"
                value="value"
                onSelectCall={onSetLabImageOutputFormat}
                classNames="home-app-select"
              />
            </label>
          ) : null}
        </div>
      );
    }

    if (labKind === "audio") {
      const voiceOptions = activeLabModel.routeFamily === "minimax_tts" ? minimaxVoices : qwenVoices;
      return (
        <div className="home-form-stack">
          <label className="home-field">
            <span>文本</span>
            <textarea
              data-testid="lab-audio-text-input"
              value={labAudioText}
              onChange={(event) => onSetLabAudioText(event.target.value)}
              placeholder="输入要合成的文本"
            />
          </label>
          <div className="home-inline-grid two">
            <label className="home-field">
              <span>{activeLabModel.routeFamily === "minimax_tts" ? "voice_id" : "voice"}</span>
              <AppSelect
                currentValue={labAudioVoice}
                optionList={voiceOptions}
                label="label"
                value="value"
                onSelectCall={onSetLabAudioVoice}
                classNames="home-app-select"
                triggerTestId="lab-audio-voice-select"
              />
            </label>
            {activeLabModel.routeFamily === "minimax_tts" ? (
              <label className="home-field">
                <span>format</span>
                <AppSelect
                  currentValue={labAudioFormat}
                  optionList={AUDIO_FORMAT_OPTIONS}
                  label="label"
                  value="value"
                  onSelectCall={onSetLabAudioFormat}
                  classNames="home-app-select"
                  triggerTestId="lab-audio-format-select"
                />
              </label>
            ) : supportsAudioMode ? (
              <label className="home-field">
                <span>mode</span>
                <AppSelect
                  currentValue={labAudioMode}
                  optionList={AUDIO_MODE_OPTIONS}
                  label="label"
                  value="value"
                  onSelectCall={onSetLabAudioMode}
                  classNames="home-app-select"
                  triggerTestId="lab-audio-mode-select"
                />
              </label>
            ) : null}
          </div>
          {supportsAudioInstructions ? (
            <label className="home-field">
              <span>instructions</span>
              <textarea
                value={labSystemPrompt}
                onChange={(event) => onSetLabSystemPrompt(event.target.value)}
                placeholder="可选自然语言语音控制指令"
              />
            </label>
          ) : null}
        </div>
      );
    }

    return (
      <div className="home-form-stack">
        <label className="home-field">
          <span>提示词</span>
          <textarea
            data-testid="lab-video-prompt-input"
            value={labVideoPrompt}
            onChange={(event) => onSetLabVideoPrompt(event.target.value)}
            placeholder="输入视频提示词"
          />
        </label>
        <div className="home-inline-grid two">
          {supportsVideoReference ? (
            <label className="home-field">
              <span>{supportsVideoReferenceList ? "参考素材 URL（可多行）" : "参考图 URL"}</span>
              {supportsVideoReferenceList ? (
                <textarea value={labVideoReference} onChange={(event) => onSetLabVideoReference(event.target.value)} placeholder="每行一个 https://..." />
              ) : (
                <input value={labVideoReference} onChange={(event) => onSetLabVideoReference(event.target.value)} placeholder="https://..." />
              )}
            </label>
          ) : null}
          {supportsVideoSeconds ? (
            <label className="home-field">
              <span>seconds</span>
              <AppSelect
                currentValue={labVideoSeconds}
                optionList={currentVideoSecondsOptions}
                label="label"
                value="value"
                onSelectCall={onSetLabVideoSeconds}
                classNames="home-app-select"
                triggerTestId="lab-video-seconds-select"
              />
            </label>
          ) : null}
        </div>
        <div className={`home-inline-grid ${supportsVideoGenerateAudio ? "three" : "two"}`}>
          {supportsVideoAspectRatio ? (
            <label className="home-field">
              <span>aspect_ratio</span>
              <AppSelect
                currentValue={labVideoAspectRatio}
                optionList={VIDEO_ASPECT_RATIO_OPTIONS}
                label="label"
                value="value"
                onSelectCall={onSetLabVideoAspectRatio}
                classNames="home-app-select"
                triggerTestId="lab-video-aspect-ratio-select"
              />
            </label>
          ) : null}
          {supportsVideoResolution ? (
            <label className="home-field">
              <span>resolution</span>
              <AppSelect
                currentValue={labVideoResolution}
                optionList={currentVideoResolutionOptions}
                label="label"
                value="value"
                onSelectCall={onSetLabVideoResolution}
                classNames="home-app-select"
                triggerTestId="lab-video-resolution-select"
              />
            </label>
          ) : null}
          {supportsVideoGenerateAudio ? (
            <label className="home-check home-check--panel">
              <input
                type="checkbox"
                checked={labVideoGenerateAudio}
                onChange={(event) => onSetLabVideoGenerateAudio(event.target.checked)}
              />
              <span>同时生成音频</span>
            </label>
          ) : null}
        </div>
      </div>
    );
  };

  const renderLabAdvanced = () => {
    if (!labAdvanced) {
      return null;
    }

    if (labKind === "text") {
      if (!labParameterNames.has("stream")) {
        return null;
      }
      return (
        <div className="home-advanced-panel lab-advanced-panel">
          <label className="home-check home-check--panel">
            <input type="checkbox" checked={labStream} onChange={(event) => onSetLabStream(event.target.checked)} />
            <span>stream</span>
          </label>
        </div>
      );
    }

    if (labKind === "image") {
      if (!supportsImageWatermark) {
        return null;
      }
      return (
        <div className="home-advanced-panel lab-advanced-panel">
          <label className="home-check home-check--panel">
            <input type="checkbox" checked={labImageWatermark} onChange={(event) => onSetLabImageWatermark(event.target.checked)} />
            <span>watermark</span>
          </label>
        </div>
      );
    }

    if (labKind === "video") {
      if (!(supportsVideoSize || supportsVideoAudioUrl || supportsVideoVideoUrl || supportsVideoFirstFrame || supportsVideoLastFrame || supportsVideoMode)) {
        return null;
      }
      return (
        <div className="home-advanced-panel home-form-stack lab-advanced-panel">
          <div className={`home-inline-grid ${supportsVideoSize && supportsVideoMode ? "two" : "one"}`}>
            {supportsVideoSize ? (
              <label className="home-field">
                <span>size</span>
                <input value={labVideoSize} onChange={(event) => onSetLabVideoSize(event.target.value)} placeholder="例如 1280*720" />
              </label>
            ) : null}
            {supportsVideoMode ? (
              <label className="home-field">
                <span>mode</span>
                <AppSelect
                  currentValue={labVideoMode}
                  optionList={KLING_MODE_OPTIONS}
                  label="label"
                  value="value"
                  onSelectCall={onSetLabVideoMode}
                  classNames="home-app-select"
                />
              </label>
            ) : null}
          </div>
          <div className={`home-inline-grid ${supportsVideoAudioUrl && supportsVideoVideoUrl ? "two" : "one"}`}>
            {supportsVideoAudioUrl ? (
              <label className="home-field">
                <span>audio_url</span>
                <input value={labVideoAudioUrl} onChange={(event) => onSetLabVideoAudioUrl(event.target.value)} placeholder="https://..." />
              </label>
            ) : null}
            {supportsVideoVideoUrl ? (
              <label className="home-field">
                <span>video_url</span>
                <input value={labVideoVideoUrl} onChange={(event) => onSetLabVideoVideoUrl(event.target.value)} placeholder="https://..." />
              </label>
            ) : null}
          </div>
          <div className={`home-inline-grid ${supportsVideoFirstFrame && supportsVideoLastFrame ? "two" : "one"}`}>
            {supportsVideoFirstFrame ? (
              <label className="home-field">
                <span>first_frame</span>
                <input value={labVideoFirstFrame} onChange={(event) => onSetLabVideoFirstFrame(event.target.value)} placeholder="https://..." />
              </label>
            ) : null}
            {supportsVideoLastFrame ? (
              <label className="home-field">
                <span>last_frame</span>
                <input value={labVideoLastFrame} onChange={(event) => onSetLabVideoLastFrame(event.target.value)} placeholder="https://..." />
              </label>
            ) : null}
          </div>
        </div>
      );
    }

    return null;
  };

  const renderLabPreview = () => {
    if (!labResult) {
      return <div className="home-empty-state">运行一次请求后，这里会显示结果预览、原始 JSON 和链路摘要。</div>;
    }

    if (labResponseTab === "raw") {
      return <pre className="home-code-block">{labResult.raw || stringifyJson(labResult.data)}</pre>;
    }

    if (labResponseTab === "metrics") {
      return (
        <div className="home-metrics-grid">
          <div>
            <span>状态</span>
            <strong>{labResult.statusCode ?? "-"}</strong>
          </div>
          <div>
            <span>耗时</span>
            <strong>{formatDuration(labResult.meta.durationMs)}</strong>
          </div>
          <div>
            <span>消耗算力</span>
            <strong>{formatPower(labResult.meta.powerAmount)}</strong>
          </div>
          <div>
            <span>供应商链路</span>
            <strong>{labResult.meta.providerSummary}</strong>
          </div>
        </div>
      );
    }

    if (!labResult.ok) {
      return <div className="home-result-error">{labResult.errorMessage || "请求失败"}</div>;
    }

    if (labKind === "text") {
      return <pre className="home-preview-text">{extractTextFromResponse(labResult.data)}</pre>;
    }
    if (labKind === "image") {
      const url = extractImageUrl(labResult.data);
      return url ? (
        <div className="home-preview-image-wrap">
          <img src={url} alt="生成结果" className="home-preview-image" />
          <div className="home-preview-actions">
            <AppButton variant="outline" size="sm" leftIcon={<DownloadIcon />} onClick={() => window.open(url, "_blank", "noopener,noreferrer")}>
              打开图片
            </AppButton>
            <AppButton variant="outline" size="sm" leftIcon={<CopyIcon />} onClick={() => onCopyText(url, "图片地址已复制")}>
              复制图片 URL
            </AppButton>
          </div>
        </div>
      ) : (
        <pre className="home-code-block">{stringifyJson(labResult.data)}</pre>
      );
    }
    if (labKind === "audio") {
      const url = extractAudioUrl(labResult.data);
      return url ? (
        <div className="home-preview-media-wrap">
          <audio controls src={url} className="home-audio-player" />
          <div className="home-preview-actions">
            <AppButton variant="outline" size="sm" leftIcon={<DownloadIcon />} onClick={() => window.open(url, "_blank", "noopener,noreferrer")}>
              打开音频
            </AppButton>
          </div>
        </div>
      ) : (
        <pre className="home-code-block">{stringifyJson(labResult.data)}</pre>
      );
    }
    const url = extractVideoUrl(labResult.data);
    if (url) {
      return (
        <div className="home-preview-media-wrap">
          <video controls src={url} className="home-video-player" />
          <div className="home-preview-actions">
            <AppButton variant="outline" size="sm" leftIcon={<DownloadIcon />} onClick={() => window.open(url, "_blank", "noopener,noreferrer")}>
              打开视频
            </AppButton>
          </div>
        </div>
      );
    }
    return (
      <div className="home-task-card">
        <strong>视频任务已创建</strong>
        <span>当前状态：{(labResult.data as Record<string, any> | null)?.status || "submitted"}</span>
        <pre className="home-code-block">{stringifyJson(labResult.data)}</pre>
      </div>
    );
  };

  return (
    <article className="home-panel workbench-panel" data-testid="api-lab-panel">
      <div className="workbench-panel-head">
        <div>
          <span className="section-kicker">API Lab</span>
          <h2>跑个接口试试？价格可预测，供应商可用率可知</h2>
        </div>
        <AppButton variant="outline" size="sm" leftIcon={<ArrowUpRightIcon />} onClick={onOpenDocs}>
          查看 API 文档
        </AppButton>
      </div>

      <div className="lab-topline">
        <label className="home-field">
          <span>API Key</span>
          <AppSelect
            currentValue={selectedApiKeyOptionId}
            optionList={apiKeySelectOptions}
            label="label"
            value="value"
            onSelectCall={onSelectApiKey}
            classNames="home-app-select"
            triggerTestId="lab-api-key-select"
          />
        </label>
        <div className="task-pills lab-task-pills" aria-label="API 类型">
          {LAB_KIND_OPTIONS.map((item) => (
            <button
              key={item.value}
              type="button"
              data-testid={`lab-kind-${item.value}`}
              className={labKind === item.value ? "active" : ""}
              onClick={() => {
                onSetLabKind(item.value as LabKind);
                onSetLabRequestTab("form");
                onSetLabJsonDirty(false);
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div className="lab-controls-row">
        <label className="home-field home-field--compact lab-model-field">
          <span>模型</span>
          <AppSelect
            currentValue={labModelCode[labKind]}
            optionList={labModelSelectOptions}
            label="label"
            value="value"
            onSelectCall={onSetLabModelCode}
            classNames="home-app-select"
            triggerTestId="lab-model-select"
          />
        </label>
        <label className="home-field home-field--compact lab-chain-field">
          <span>chain</span>
          <input
            data-testid="lab-chain-input"
            value={labChain}
            onChange={(event) => onSetLabChain(event.target.value)}
            placeholder="可以自己指定供应商的调用顺序"
          />
        </label>
        {labKind === "text" || labKind === "image" || labKind === "video" ? (
          <AppButton variant="link" size="sm" className="lab-advanced-link" data-testid="lab-advanced-toggle" onClick={onToggleLabAdvanced}>
            {labAdvanced ? "收起高级设置" : "高级设置"}
          </AppButton>
        ) : null}
        <AppButton
          variant="primary"
          size="md"
          className="workbench-primary-action"
          data-testid="lab-run-button"
          onClick={onRun}
          disabled={labRunning}
        >
          <span className="workbench-primary-action__content">
            <span className="workbench-primary-action__main">
              {labRunning ? <LoaderCircleIcon className="spin" /> : <PlayIcon />}
              <span className="workbench-primary-action__title">{labRunning ? "运行中..." : "运行"}</span>
            </span>
            {labEstimateText || labEstimateLoading ? (
              <span className="workbench-primary-action__subline" data-testid="lab-estimate-hint">
                <span>{labEstimateText || "计算中…"}</span>
                {labEstimateWarning ? <CircleAlertIcon aria-label="余额不足" /> : null}
              </span>
            ) : null}
          </span>
        </AppButton>
      </div>

      {renderLabAdvanced()}

      <div className="lab-tabs">
        <div className="home-segment">
          <button type="button" className={labRequestTab === "form" ? "active" : ""} onClick={() => { onSetLabRequestTab("form"); onSetLabJsonDirty(false); }}>Form</button>
          <button type="button" className={labRequestTab === "json" ? "active" : ""} onClick={() => onSetLabRequestTab("json")}>JSON</button>
        </div>

        {labRequestTab === "form" ? (
          <div className="lab-form-shell">{renderLabForm()}</div>
        ) : (
          <label className="home-field">
            <span>请求体 JSON</span>
            <textarea
              value={labRawRequest}
              onChange={(event) => {
                onSetLabRawRequest(event.target.value);
                onSetLabJsonDirty(true);
              }}
              className="home-code-editor"
            />
          </label>
        )}
      </div>

      <div className={`lab-code-section${labResult ? "" : " lab-code-section--expanded"}`}>
        <div className="section-row">
          <div className="home-segment">
            <button type="button" className={labCodeTab === "curl" ? "active" : ""} onClick={() => onSetLabCodeTab("curl")}>cURL</button>
            <button type="button" className={labCodeTab === "python" ? "active" : ""} onClick={() => onSetLabCodeTab("python")}>Python</button>
            <button type="button" className={labCodeTab === "javascript" ? "active" : ""} onClick={() => onSetLabCodeTab("javascript")}>JavaScript</button>
          </div>
          <div className="section-actions">
            <AppButton
              variant="outline"
              size="sm"
              className="lab-copy-action"
              leftIcon={<CopyIcon />}
              title="复制代码"
              aria-label="复制代码"
              onClick={() => onCopyText(currentCodeSnippet, "代码已复制")}
            />
          </div>
        </div>
        <pre className={`home-code-block home-code-block--snippet${labResult ? "" : " home-code-block--snippet-expanded"}`}>{currentCodeSnippet}</pre>
      </div>

      {labResult ? (
        <>
          <div className="lab-response-section">
            <div className="section-row">
              <div className="home-segment">
                <button type="button" className={labResponseTab === "preview" ? "active" : ""} onClick={() => onSetLabResponseTab("preview")}>Preview</button>
                <button type="button" className={labResponseTab === "raw" ? "active" : ""} onClick={() => onSetLabResponseTab("raw")}>Raw JSON</button>
                <button type="button" className={labResponseTab === "metrics" ? "active" : ""} onClick={() => onSetLabResponseTab("metrics")}>Metrics</button>
              </div>
              {labResult.raw ? (
                <AppButton variant="outline" size="sm" leftIcon={<CopyIcon />} onClick={() => onCopyText(labResult.raw, "响应已复制")}>
                  复制响应
                </AppButton>
              ) : null}
            </div>
            <div className="lab-preview-shell">{renderLabPreview()}</div>
          </div>

          <div className="workbench-meta">
            <span>{labResult.statusCode ?? "-"} · {formatDuration(labResult.meta.durationMs)}</span>
            <span>算力 {formatPower(labResult.meta.powerAmount)}</span>
            <span>{labResult.meta.providerSummary || "-"}</span>
            {labResult.meta.requestId ? (
              <button type="button" data-testid="lab-detail-button" onClick={() => onNavigateDetail(labResult.meta.requestId as string)}>
                {labResult.meta.requestId} · 详情
              </button>
            ) : (
              <span>未生成 request_id</span>
            )}
          </div>
        </>
      ) : null}
    </article>
  );
}
