import AppButton from "@/shared/ui/button/button";
import { CircleAlertIcon, LoaderCircleIcon, MessageCircleMoreIcon, PlayIcon } from "@/shared/ui/icon";
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
  supportsModelParameter,
  VIDEO_ASPECT_RATIO_OPTIONS,
} from "../home.data";
import type { ApiKeyOption, ModelOption, PlaygroundMessage, PlaygroundTask, VoiceOption } from "../home.types";
import { formatPower } from "../lib/home-utils";

type PlaygroundPanelProps = {
  apiKeyOptions: ApiKeyOption[];
  selectedApiKeyOptionId: string;
  activePlaygroundModel: ModelOption;
  playgroundModelOptions: ModelOption[];
  playgroundTask: PlaygroundTask;
  playgroundMessages: PlaygroundMessage[];
  playgroundInput: string;
  playgroundModelCode: Record<PlaygroundTask, string>;
  playgroundWorking: boolean;
  playgroundEstimateText: string;
  playgroundEstimateLoading: boolean;
  playgroundEstimateWarning: boolean;
  playgroundAdvanced: boolean;
  playgroundSystemPrompt: string;
  playgroundTemperature: string;
  playgroundMaxTokens: string;
  playgroundImageReference: string;
  playgroundImageSize: string;
  playgroundImageAspectRatio: string;
  playgroundImageResolution: string;
  playgroundImageResponseFormat: string;
  playgroundImageWatermark: boolean;
  playgroundImageOutputFormat: string;
  playgroundAudioVoice: string;
  playgroundAudioMode: string;
  playgroundAudioFormat: string;
  playgroundVideoReference: string;
  playgroundVideoAudioUrl: string;
  playgroundVideoSize: string;
  playgroundVideoSeconds: string;
  playgroundVideoAspectRatio: string;
  playgroundVideoResolution: string;
  playgroundVideoGenerateAudio: boolean;
  playgroundVideoVideoUrl: string;
  playgroundVideoFirstFrame: string;
  playgroundVideoLastFrame: string;
  playgroundVideoMode: string;
  qwenVoices: VoiceOption[];
  minimaxVoices: VoiceOption[];
  onSetPlaygroundTask: (value: PlaygroundTask) => void;
  onSetPlaygroundModelCode: (value: string) => void;
  onSetPlaygroundInput: (value: string) => void;
  onTogglePlaygroundAdvanced: () => void;
  onSetPlaygroundSystemPrompt: (value: string) => void;
  onSetPlaygroundTemperature: (value: string) => void;
  onSetPlaygroundMaxTokens: (value: string) => void;
  onSetPlaygroundImageReference: (value: string) => void;
  onSetPlaygroundImageSize: (value: string) => void;
  onSetPlaygroundImageAspectRatio: (value: string) => void;
  onSetPlaygroundImageResolution: (value: string) => void;
  onSetPlaygroundImageResponseFormat: (value: string) => void;
  onSetPlaygroundImageWatermark: (value: boolean) => void;
  onSetPlaygroundImageOutputFormat: (value: string) => void;
  onSetPlaygroundAudioVoice: (value: string) => void;
  onSetPlaygroundAudioMode: (value: string) => void;
  onSetPlaygroundAudioFormat: (value: string) => void;
  onSetPlaygroundVideoReference: (value: string) => void;
  onSetPlaygroundVideoAudioUrl: (value: string) => void;
  onSetPlaygroundVideoSize: (value: string) => void;
  onSetPlaygroundVideoSeconds: (value: string) => void;
  onSetPlaygroundVideoAspectRatio: (value: string) => void;
  onSetPlaygroundVideoResolution: (value: string) => void;
  onSetPlaygroundVideoGenerateAudio: (value: boolean) => void;
  onSetPlaygroundVideoVideoUrl: (value: string) => void;
  onSetPlaygroundVideoFirstFrame: (value: string) => void;
  onSetPlaygroundVideoLastFrame: (value: string) => void;
  onSetPlaygroundVideoMode: (value: string) => void;
  onSelectApiKey: (value: string) => void;
  onSubmit: () => void;
  onClearMessages: () => void;
  onNavigateDetail: (requestId: string) => void;
};

function getTaskLabel(task: PlaygroundTask) {
  if (task === "chat") return "问答";
  if (task === "image") return "图片生成";
  if (task === "audio") return "音频生成";
  return "视频生成";
}

const PLAYGROUND_STARTERS: Record<PlaygroundTask, string[]> = {
  chat: ["介绍一下 35m", "写一封商务合作邮件", "帮我整理产品卖点"],
  image: ["生成一张产品海报", "来一张科技感工作台插画", "设计一个简洁的品牌 KV"],
  audio: ["欢迎来到 35m，现在开始你的体验。", "写一段温暖的产品旁白", "生成一段发布会开场白"],
  video: ["做一段未来城市镜头", "生成产品发布会氛围视频", "写一个 5 秒广告分镜提示词"],
};

export function PlaygroundPanel(props: PlaygroundPanelProps) {
  const {
    apiKeyOptions,
    selectedApiKeyOptionId,
    activePlaygroundModel,
    playgroundModelOptions,
    playgroundTask,
    playgroundMessages,
    playgroundInput,
    playgroundModelCode,
    playgroundWorking,
    playgroundEstimateText,
    playgroundEstimateLoading,
    playgroundEstimateWarning,
    playgroundAdvanced,
    playgroundSystemPrompt,
    playgroundTemperature,
    playgroundMaxTokens,
    playgroundImageReference,
    playgroundImageSize,
    playgroundImageAspectRatio,
    playgroundImageResolution,
    playgroundImageResponseFormat,
    playgroundImageWatermark,
    playgroundImageOutputFormat,
    playgroundAudioVoice,
    playgroundAudioMode,
    playgroundAudioFormat,
    playgroundVideoReference,
    playgroundVideoAudioUrl,
    playgroundVideoSize,
    playgroundVideoSeconds,
    playgroundVideoAspectRatio,
    playgroundVideoResolution,
    playgroundVideoGenerateAudio,
    playgroundVideoVideoUrl,
    playgroundVideoFirstFrame,
    playgroundVideoLastFrame,
    playgroundVideoMode,
    qwenVoices,
    minimaxVoices,
    onSetPlaygroundTask,
    onSetPlaygroundModelCode,
    onSetPlaygroundInput,
    onTogglePlaygroundAdvanced,
    onSetPlaygroundSystemPrompt,
    onSetPlaygroundTemperature,
    onSetPlaygroundMaxTokens,
    onSetPlaygroundImageReference,
    onSetPlaygroundImageSize,
    onSetPlaygroundImageAspectRatio,
    onSetPlaygroundImageResolution,
    onSetPlaygroundImageResponseFormat,
    onSetPlaygroundImageWatermark,
    onSetPlaygroundImageOutputFormat,
    onSetPlaygroundAudioVoice,
    onSetPlaygroundAudioMode,
    onSetPlaygroundAudioFormat,
    onSetPlaygroundVideoReference,
    onSetPlaygroundVideoAudioUrl,
    onSetPlaygroundVideoSize,
    onSetPlaygroundVideoSeconds,
    onSetPlaygroundVideoAspectRatio,
    onSetPlaygroundVideoResolution,
    onSetPlaygroundVideoGenerateAudio,
    onSetPlaygroundVideoVideoUrl,
    onSetPlaygroundVideoFirstFrame,
    onSetPlaygroundVideoLastFrame,
    onSetPlaygroundVideoMode,
    onSelectApiKey,
    onSubmit,
    onClearMessages,
    onNavigateDetail,
  } = props;

  const playgroundModelSelectOptions = playgroundModelOptions.map((item) => ({
    label: item.label,
    value: item.code,
  }));
  const apiKeySelectOptions = apiKeyOptions.map((item) => ({
    label: `${item.label}${item.keyPrefix ? ` · ${item.keyPrefix}` : ""}`,
    value: item.optionId,
  }));
  const supportsImageReference =
    supportsModelParameter(activePlaygroundModel, "image") || supportsModelParameter(activePlaygroundModel, "image_urls");
  const supportsImageSize = supportsModelParameter(activePlaygroundModel, "size");
  const supportsImageAspectRatio = supportsModelParameter(activePlaygroundModel, "aspect_ratio");
  const supportsImageResolution = supportsModelParameter(activePlaygroundModel, "resolution");
  const supportsImageResponseFormat = supportsModelParameter(activePlaygroundModel, "response_format");
  const supportsImageWatermark = supportsModelParameter(activePlaygroundModel, "watermark");
  const supportsImageOutputFormat = supportsModelParameter(activePlaygroundModel, "output_format");
  const supportsVideoReference =
    supportsModelParameter(activePlaygroundModel, "input_reference") || supportsModelParameter(activePlaygroundModel, "image");
  const supportsVideoReferenceList =
    supportsModelParameter(activePlaygroundModel, "reference_urls") || supportsModelParameter(activePlaygroundModel, "reference_images");
  const supportsVideoSeconds = supportsModelParameter(activePlaygroundModel, "seconds");
  const supportsVideoAspectRatio = supportsModelParameter(activePlaygroundModel, "aspect_ratio");
  const supportsVideoResolution = supportsModelParameter(activePlaygroundModel, "resolution");
  const supportsVideoGenerateAudio = supportsModelParameter(activePlaygroundModel, "generate_audio");
  const supportsVideoSize = supportsModelParameter(activePlaygroundModel, "size");
  const supportsVideoAudioUrl = supportsModelParameter(activePlaygroundModel, "audio_url");
  const supportsVideoVideoUrl = supportsModelParameter(activePlaygroundModel, "video_url");
  const supportsVideoFirstFrame = supportsModelParameter(activePlaygroundModel, "first_frame");
  const supportsVideoLastFrame = supportsModelParameter(activePlaygroundModel, "last_frame");
  const supportsVideoMode = supportsModelParameter(activePlaygroundModel, "mode");
  const supportsAudioMode = supportsModelParameter(activePlaygroundModel, "mode");
  const supportsAudioInstructions = supportsModelParameter(activePlaygroundModel, "instructions");
  const currentImageSizeOptions = getImageSizeOptionsForModel(activePlaygroundModel);
  const currentImageAspectRatioOptions = getImageAspectRatioOptionsForModel(activePlaygroundModel);
  const currentImageResolutionOptions = getImageResolutionOptionsForModel(activePlaygroundModel);
  const currentVideoSecondsOptions = getVideoSecondsOptionsForModel(activePlaygroundModel);
  const currentVideoResolutionOptions = getVideoResolutionOptionsForModel(activePlaygroundModel);

  const renderAdvanced = () => {
    if (!playgroundAdvanced) {
      return null;
    }
    if (playgroundTask === "chat") {
      return (
        <div className="home-advanced-panel home-form-stack">
          <label className="home-field">
            <span>system prompt</span>
            <textarea
              value={playgroundSystemPrompt}
              onChange={(event) => onSetPlaygroundSystemPrompt(event.target.value)}
              placeholder="可选的 system prompt"
            />
          </label>
          <div className="home-inline-grid two">
            <label className="home-field">
              <span>temperature</span>
              <input
                value={playgroundTemperature}
                onChange={(event) => onSetPlaygroundTemperature(event.target.value)}
                placeholder="留空则不传"
              />
            </label>
            <label className="home-field">
              <span>max_tokens</span>
              <input
                value={playgroundMaxTokens}
                onChange={(event) => onSetPlaygroundMaxTokens(event.target.value)}
                placeholder="留空则不传"
              />
            </label>
          </div>
        </div>
      );
    }
    if (playgroundTask === "image") {
      return (
        <div className="home-advanced-panel home-form-stack">
          <div
            className={`home-inline-grid ${
              supportsImageReference && (supportsImageSize || supportsImageAspectRatio || supportsImageResolution) ? "two" : "one"
            }`}
          >
            {supportsImageReference ? (
              <label className="home-field">
                <span>{activePlaygroundModel.routeFamily === "banana" ? "参考图 URL（可多行）" : "参考图 URL"}</span>
                {activePlaygroundModel.routeFamily === "banana" ? (
                  <textarea
                    value={playgroundImageReference}
                    onChange={(event) => onSetPlaygroundImageReference(event.target.value)}
                    placeholder="每行一个 https://..."
                  />
                ) : (
                  <input
                    value={playgroundImageReference}
                    onChange={(event) => onSetPlaygroundImageReference(event.target.value)}
                    placeholder="https://..."
                  />
                )}
              </label>
            ) : null}
            {supportsImageSize && activePlaygroundModel.routeFamily !== "banana" ? (
              <label className="home-field">
                <span>size</span>
                <AppSelect
                  currentValue={playgroundImageSize}
                  optionList={currentImageSizeOptions}
                  label="label"
                  value="value"
                  onSelectCall={onSetPlaygroundImageSize}
                  classNames="home-app-select"
                  triggerTestId="playground-image-size-select"
                />
              </label>
            ) : null}
          </div>
          {activePlaygroundModel.routeFamily === "banana" ? (
            <div className={`home-inline-grid ${supportsImageAspectRatio && supportsImageResolution ? "two" : "one"}`}>
              {supportsImageAspectRatio ? (
                <label className="home-field">
                  <span>aspect_ratio</span>
                  <AppSelect
                    currentValue={playgroundImageAspectRatio}
                    optionList={currentImageAspectRatioOptions}
                    label="label"
                    value="value"
                    onSelectCall={onSetPlaygroundImageAspectRatio}
                    classNames="home-app-select"
                    triggerTestId="playground-image-aspect-ratio-select"
                  />
                </label>
              ) : null}
              {supportsImageResolution && currentImageResolutionOptions.length ? (
                <label className="home-field">
                  <span>resolution</span>
                  <AppSelect
                    currentValue={playgroundImageResolution}
                    optionList={currentImageResolutionOptions}
                    label="label"
                    value="value"
                    onSelectCall={onSetPlaygroundImageResolution}
                    classNames="home-app-select"
                    triggerTestId="playground-image-resolution-select"
                  />
                </label>
              ) : null}
            </div>
          ) : null}
          {supportsImageResponseFormat ? (
            <label className="home-field">
              <span>response_format</span>
              <AppSelect
                currentValue={playgroundImageResponseFormat}
                optionList={[
                  { label: "url", value: "url" },
                  { label: "b64_json", value: "b64_json" },
                ]}
                label="label"
                value="value"
                onSelectCall={onSetPlaygroundImageResponseFormat}
                classNames="home-app-select"
              />
            </label>
          ) : null}
          {supportsImageOutputFormat ? (
            <label className="home-field">
              <span>output_format</span>
              <AppSelect
                currentValue={playgroundImageOutputFormat}
                optionList={IMAGE_OUTPUT_FORMAT_OPTIONS}
                label="label"
                value="value"
                onSelectCall={onSetPlaygroundImageOutputFormat}
                classNames="home-app-select"
              />
            </label>
          ) : null}
          {supportsImageWatermark ? (
            <label className="home-check home-check--panel">
              <input
                type="checkbox"
                checked={playgroundImageWatermark}
                onChange={(event) => onSetPlaygroundImageWatermark(event.target.checked)}
              />
              <span>watermark</span>
            </label>
          ) : null}
        </div>
      );
    }
    if (playgroundTask === "audio") {
      const voiceOptions = activePlaygroundModel.routeFamily === "minimax_tts" ? minimaxVoices : qwenVoices;
      return (
        <div className="home-advanced-panel home-form-stack">
          <div className="home-inline-grid two">
            <label className="home-field">
              <span>{activePlaygroundModel.routeFamily === "minimax_tts" ? "voice_id" : "voice"}</span>
              <AppSelect
                currentValue={playgroundAudioVoice}
                optionList={voiceOptions}
                label="label"
                value="value"
                onSelectCall={onSetPlaygroundAudioVoice}
                classNames="home-app-select"
                triggerTestId="playground-audio-voice-select"
              />
            </label>
            {activePlaygroundModel.routeFamily === "minimax_tts" ? (
              <label className="home-field">
                <span>format</span>
                <AppSelect
                  currentValue={playgroundAudioFormat}
                  optionList={AUDIO_FORMAT_OPTIONS}
                  label="label"
                  value="value"
                  onSelectCall={onSetPlaygroundAudioFormat}
                  classNames="home-app-select"
                />
              </label>
            ) : supportsAudioMode ? (
              <label className="home-field">
                <span>mode</span>
                <AppSelect
                  currentValue={playgroundAudioMode}
                  optionList={AUDIO_MODE_OPTIONS}
                  label="label"
                  value="value"
                  onSelectCall={onSetPlaygroundAudioMode}
                  classNames="home-app-select"
                  triggerTestId="playground-audio-mode-select"
                />
              </label>
            ) : null}
          </div>
          {supportsAudioInstructions ? (
            <label className="home-field">
              <span>instructions</span>
              <textarea
                value={playgroundSystemPrompt}
                onChange={(event) => onSetPlaygroundSystemPrompt(event.target.value)}
                placeholder="可选自然语言语音控制指令"
              />
            </label>
          ) : null}
        </div>
      );
    }
    return (
      <div className="home-advanced-panel home-form-stack">
        <div className="home-inline-grid two">
          {supportsVideoReference ? (
            <label className="home-field">
              <span>{supportsVideoReferenceList ? "参考素材 URL（可多行）" : "参考图 URL"}</span>
              {supportsVideoReferenceList ? (
                <textarea
                  value={playgroundVideoReference}
                  onChange={(event) => onSetPlaygroundVideoReference(event.target.value)}
                  placeholder="每行一个 https://..."
                />
              ) : (
                <input
                  value={playgroundVideoReference}
                  onChange={(event) => onSetPlaygroundVideoReference(event.target.value)}
                  placeholder="https://..."
                />
              )}
            </label>
          ) : null}
          {supportsVideoSeconds ? (
            <label className="home-field">
              <span>seconds</span>
              <AppSelect
                currentValue={playgroundVideoSeconds}
                optionList={currentVideoSecondsOptions}
                label="label"
                value="value"
                onSelectCall={onSetPlaygroundVideoSeconds}
                classNames="home-app-select"
                triggerTestId="playground-video-seconds-select"
              />
            </label>
          ) : null}
        </div>
        <div className={`home-inline-grid ${supportsVideoGenerateAudio ? "three" : "two"}`}>
          {supportsVideoAspectRatio ? (
            <label className="home-field">
              <span>aspect_ratio</span>
              <AppSelect
                currentValue={playgroundVideoAspectRatio}
                optionList={VIDEO_ASPECT_RATIO_OPTIONS}
                label="label"
                value="value"
                onSelectCall={onSetPlaygroundVideoAspectRatio}
                classNames="home-app-select"
                triggerTestId="playground-video-aspect-ratio-select"
              />
            </label>
          ) : null}
          {supportsVideoResolution ? (
            <label className="home-field">
              <span>resolution</span>
              <AppSelect
                currentValue={playgroundVideoResolution}
                optionList={currentVideoResolutionOptions}
                label="label"
                value="value"
                onSelectCall={onSetPlaygroundVideoResolution}
                classNames="home-app-select"
                triggerTestId="playground-video-resolution-select"
              />
            </label>
          ) : null}
          {supportsVideoGenerateAudio ? (
            <label className="home-check home-check--panel">
              <input
                type="checkbox"
                checked={playgroundVideoGenerateAudio}
                onChange={(event) => onSetPlaygroundVideoGenerateAudio(event.target.checked)}
              />
              <span>同时生成音频</span>
            </label>
          ) : null}
        </div>
        <div className={`home-inline-grid ${supportsVideoSize && supportsVideoMode ? "two" : "one"}`}>
          {supportsVideoSize ? (
            <label className="home-field">
              <span>size</span>
              <input
                value={playgroundVideoSize}
                onChange={(event) => onSetPlaygroundVideoSize(event.target.value)}
                placeholder="例如 1280*720"
              />
            </label>
          ) : null}
          {supportsVideoMode ? (
            <label className="home-field">
              <span>mode</span>
              <AppSelect
                currentValue={playgroundVideoMode}
                optionList={KLING_MODE_OPTIONS}
                label="label"
                value="value"
                onSelectCall={onSetPlaygroundVideoMode}
                classNames="home-app-select"
              />
            </label>
          ) : null}
        </div>
        <div className={`home-inline-grid ${supportsVideoAudioUrl && supportsVideoVideoUrl ? "two" : "one"}`}>
          {supportsVideoAudioUrl ? (
            <label className="home-field">
              <span>audio_url</span>
              <input
                value={playgroundVideoAudioUrl}
                onChange={(event) => onSetPlaygroundVideoAudioUrl(event.target.value)}
                placeholder="https://..."
              />
            </label>
          ) : null}
          {supportsVideoVideoUrl ? (
            <label className="home-field">
              <span>video_url</span>
              <input
                value={playgroundVideoVideoUrl}
                onChange={(event) => onSetPlaygroundVideoVideoUrl(event.target.value)}
                placeholder="https://..."
              />
            </label>
          ) : null}
        </div>
        <div className={`home-inline-grid ${supportsVideoFirstFrame && supportsVideoLastFrame ? "two" : "one"}`}>
          {supportsVideoFirstFrame ? (
            <label className="home-field">
              <span>first_frame</span>
              <input
                value={playgroundVideoFirstFrame}
                onChange={(event) => onSetPlaygroundVideoFirstFrame(event.target.value)}
                placeholder="https://..."
              />
            </label>
          ) : null}
          {supportsVideoLastFrame ? (
            <label className="home-field">
              <span>last_frame</span>
              <input
                value={playgroundVideoLastFrame}
                onChange={(event) => onSetPlaygroundVideoLastFrame(event.target.value)}
                placeholder="https://..."
              />
            </label>
          ) : null}
        </div>
      </div>
    );
  };

  const renderMessage = (item: PlaygroundMessage) => {
    if (item.role === "user") {
      return (
        <div key={item.id} className="playground-message playground-message--user">
          <div className="playground-bubble">
            <strong>你</strong>
            <p>{item.content}</p>
          </div>
        </div>
      );
    }

    return (
      <div key={item.id} className="playground-message playground-message--assistant">
        <div className="playground-bubble">
          <div className="playground-message-head">
            <strong>{item.modelLabel}</strong>
            <span>{getTaskLabel(item.task)}</span>
          </div>
          {item.errorMessage ? <div className="home-result-error">{item.errorMessage}</div> : null}
          {item.content ? <p>{item.content}</p> : null}
          {item.imageUrl ? <img src={item.imageUrl} alt="生成结果" className="playground-image" /> : null}
          {item.audioUrl ? <audio controls src={item.audioUrl} className="home-audio-player" /> : null}
          {item.videoUrl ? <video controls src={item.videoUrl} className="home-video-player" /> : null}
          {item.taskStatus && !item.videoUrl && !item.audioUrl ? (
            <div className="home-task-card compact">
              <strong>任务状态</strong>
              <span>{item.taskStatus}</span>
            </div>
          ) : null}
          {item.meta?.requestId ? (
            <div className="playground-meta">
              <span>算力 {formatPower(item.meta.powerAmount)}</span>
              <span>{item.meta.providerSummary}</span>
              <span>{item.meta.requestId}</span>
              <button type="button" onClick={() => onNavigateDetail(item.meta?.requestId as string)}>
                详情
              </button>
            </div>
          ) : null}
        </div>
      </div>
    );
  };

  return (
    <article className="home-panel workbench-panel" data-testid="playground-panel">
      <div className="workbench-panel-head">
        <div>
          <span className="section-kicker">Playground</span>
          <h2>直接体验下吧</h2>
        </div>
        <AppButton variant="outline" size="sm" leftIcon={<MessageCircleMoreIcon />} data-testid="playground-new-chat-button" onClick={onClearMessages}>
          新对话
        </AppButton>
      </div>

      <div className="playground-topline">
        <label className="home-field">
          <span>API Key</span>
          <AppSelect
            currentValue={selectedApiKeyOptionId}
            optionList={apiKeySelectOptions}
            label="label"
            value="value"
            onSelectCall={onSelectApiKey}
            classNames="home-app-select"
            triggerTestId="playground-api-key-select"
          />
        </label>
        <div className="task-pills playground-task-pills">
          <button type="button" data-testid="playground-task-chat" className={playgroundTask === "chat" ? "active" : ""} onClick={() => onSetPlaygroundTask("chat")}>
            问答
          </button>
          <button type="button" data-testid="playground-task-image" className={playgroundTask === "image" ? "active" : ""} onClick={() => onSetPlaygroundTask("image")}>
            图片
          </button>
          <button type="button" data-testid="playground-task-audio" className={playgroundTask === "audio" ? "active" : ""} onClick={() => onSetPlaygroundTask("audio")}>
            音频
          </button>
          <button type="button" data-testid="playground-task-video" className={playgroundTask === "video" ? "active" : ""} onClick={() => onSetPlaygroundTask("video")}>
            视频
          </button>
        </div>
      </div>

      <div className="playground-stream">
        {playgroundMessages.length === 0 ? (
          <div className="playground-empty">
            <strong>从这里开始一次真实体验</strong>
            <span>先挑一个方向，再直接发送，结果会沿着对话流往下长。</span>
            <div className="playground-starters">
              {PLAYGROUND_STARTERS[playgroundTask].map((item) => (
                <button key={item} type="button" data-testid={`playground-starter-${playgroundTask}`} onClick={() => onSetPlaygroundInput(item)}>
                  {item}
                </button>
              ))}
            </div>
          </div>
        ) : (
          playgroundMessages.map((item) => renderMessage(item))
        )}
      </div>

      <div className="playground-composer">
        <label className="home-field">
          <span>输入</span>
          <textarea
            data-testid="playground-input"
            value={playgroundInput}
            onChange={(event) => onSetPlaygroundInput(event.target.value)}
            placeholder={
              playgroundTask === "chat"
                ? "问点什么，或继续这段对话……"
                : playgroundTask === "image"
                  ? "输入图片生成提示词……"
                  : playgroundTask === "audio"
                    ? "输入要合成的配音文本……"
                    : "输入视频提示词……"
            }
          />
        </label>

        {renderAdvanced()}

        <div className="playground-action-row">
          <div className="playground-model-field">
            <AppSelect
              currentValue={playgroundModelCode[playgroundTask]}
              optionList={playgroundModelSelectOptions}
              label="label"
              value="value"
              onSelectCall={onSetPlaygroundModelCode}
              classNames="home-app-select"
              triggerTestId="playground-model-select"
            />
          </div>
          <div className="playground-action-buttons">
            <AppButton variant="link" size="sm" className="playground-advanced-link" data-testid="playground-advanced-toggle" onClick={onTogglePlaygroundAdvanced}>
              {playgroundAdvanced ? "收起高级设置" : "高级设置"}
            </AppButton>
            <AppButton
              variant="primary"
              size="md"
              className="workbench-primary-action"
              data-testid="playground-submit-button"
              onClick={onSubmit}
              disabled={playgroundWorking}
            >
              <span className="workbench-primary-action__content">
                <span className="workbench-primary-action__main">
                  {playgroundWorking ? <LoaderCircleIcon className="spin" /> : <PlayIcon />}
                  <span className="workbench-primary-action__title">
                    {playgroundWorking ? "运行中..." : playgroundTask === "chat" ? "发送" : "生成"}
                  </span>
                </span>
                {playgroundEstimateText || playgroundEstimateLoading ? (
                  <span className="workbench-primary-action__subline" data-testid="playground-estimate-hint">
                    <span>{playgroundEstimateText || "计算中…"}</span>
                    {playgroundEstimateWarning ? <CircleAlertIcon aria-label="余额不足" /> : null}
                  </span>
                ) : null}
              </span>
            </AppButton>
          </div>
        </div>
      </div>
    </article>
  );
}
