import "./page.scss";
import { message } from "antd";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listModelPricing, type ModelPricingItem } from "@/api/platform";
import { BoxesIcon } from "@/shared/ui/icon";

const CATEGORY_OPTIONS = [
  { value: "all", label: "全部模型" },
  { value: "text", label: "文本" },
  { value: "image", label: "图片" },
  { value: "video", label: "视频" },
  { value: "audio", label: "配音" },
] as const;

function categoryLabel(category: string) {
  switch (category) {
    case "text":
      return "文本";
    case "image":
      return "图片";
    case "video":
      return "视频";
    case "audio":
      return "配音";
    default:
      return "其他";
  }
}

function inputModeLabel(mode: string) {
  switch (mode) {
    case "chat":
      return "对话";
    case "web_search":
      return "联网搜索";
    case "text":
      return "文生";
    case "edit":
      return "改图";
    case "image":
      return "图生";
    case "reference":
      return "多图参考";
    case "reference_images":
      return "参考图";
    case "first_last_frame":
    case "start_end":
      return "首尾帧";
    case "extend_video":
      return "视频延展";
    case "video_reference":
      return "视频参考";
    case "text_to_speech":
      return "文本配音";
    default:
      return mode;
  }
}

function formatAvailabilityRate(successRate: number) {
  return `${successRate.toFixed(2).replace(/\.?0+$/, "")}%`;
}

export default function ModelPricingPage() {
  const navigate = useNavigate();
  const [category, setCategory] = useState<(typeof CATEGORY_OPTIONS)[number]["value"]>("all");
  const [keyword, setKeyword] = useState("");
  const [items, setItems] = useState<ModelPricingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("session_token");
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const data = await listModelPricing();
        setItems(data);
      } catch (err) {
        console.error("模型目录加载失败", err);
        const detail = "模型目录加载失败，请稍后重试。";
        setError(detail);
        message.error(detail);
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [navigate]);

  const filteredItems = useMemo(() => {
    const normalizedKeyword = keyword.trim().toLowerCase();
    return items.filter((item) => {
      if (category !== "all" && item.category !== category) {
        return false;
      }
      if (!normalizedKeyword) {
        return true;
      }
      return [item.display_name, item.model_code, item.summary]
        .join(" ")
        .toLowerCase()
        .includes(normalizedKeyword);
    });
  }, [category, items, keyword]);

  const textCount = useMemo(() => items.filter((item) => item.category === "text").length, [items]);
  const mediaCount = useMemo(() => items.filter((item) => item.category !== "text").length, [items]);

  return (
    <div className="settings-page model-pricing-page">
      <section className="settings-hero">
        <div className="settings-copy">
          <span className="settings-kicker">模型目录</span>
          <h1>模型价格</h1>
          <p>查看当前对外开放模型的参考价格、支持能力和最近可用率。实际扣费以请求结果为准，运行前可在首页查看本次预估区间。</p>
        </div>
        <div className="settings-summary-grid">
          <div className="settings-summary-card">
            <span>开放模型</span>
            <strong>{items.length || "-"}</strong>
          </div>
          <div className="settings-summary-card">
            <span>文本模型</span>
            <strong>{textCount || "-"}</strong>
          </div>
          <div className="settings-summary-card">
            <span>多媒体模型</span>
            <strong>{mediaCount || "-"}</strong>
          </div>
        </div>
      </section>

      <section className="settings-panel">
        <div className="model-pricing-toolbar">
          <input
            className="model-pricing-search"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            placeholder="搜索模型名 / 模型码"
          />
          <div className="model-pricing-filter-row">
            {CATEGORY_OPTIONS.map((option) => (
              <button
                key={option.value}
                className={`model-pricing-filter-chip${category === option.value ? " is-active" : ""}`}
                type="button"
                onClick={() => setCategory(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        {error ? <div className="settings-feedback error">{error}</div> : null}
        {loading ? <div className="settings-feedback">模型目录加载中...</div> : null}

        {!loading && !error && filteredItems.length > 0 ? (
          <div className="model-pricing-card-grid">
            {filteredItems.map((item) => (
              <article key={item.model_code} className="model-pricing-card">
                <div className="model-pricing-card-head">
                  <div className="model-pricing-model-head">
                    <strong>{item.display_name}</strong>
                    <span>{item.model_code}</span>
                  </div>
                  <span className="model-pricing-chip neutral">{categoryLabel(item.category)}</span>
                </div>

                <p className="model-pricing-summary">{item.summary}</p>

                {item.availability ? (
                  <div className="model-pricing-availability">
                    <span>近24h 可用率</span>
                    <strong>{formatAvailabilityRate(item.availability.success_rate)}</strong>
                  </div>
                ) : null}

                <div className="model-pricing-price-block">
                  {item.pricing.price_lines.length > 0 ? (
                    item.pricing.price_lines.map((line) => (
                      <div key={`${item.model_code}-${line.label}`} className="model-pricing-price-line">
                        <span>{line.label}</span>
                        <strong>{line.value}</strong>
                      </div>
                    ))
                  ) : (
                    <span className="model-pricing-empty">暂无价格信息</span>
                  )}
                </div>

                <div className="model-pricing-chip-group">
                  {item.supported_input_modes.length > 0 ? (
                    item.supported_input_modes.map((mode) => (
                      <span key={`${item.model_code}-${mode}`} className="model-pricing-chip">
                        {inputModeLabel(mode)}
                      </span>
                    ))
                  ) : (
                    <span className="model-pricing-empty">未标注支持能力</span>
                  )}
                </div>
              </article>
            ))}
          </div>
        ) : null}

        {!loading && !error && filteredItems.length === 0 ? (
          <div className="model-pricing-empty-state">
            <BoxesIcon className="model-pricing-empty-icon" />
            <strong>当前筛选下没有模型</strong>
            <span>切回全部模型，或者调整搜索条件。</span>
          </div>
        ) : null}
      </section>
    </div>
  );
}
