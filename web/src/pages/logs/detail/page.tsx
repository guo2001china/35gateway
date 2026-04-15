import "./page.scss";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getUsageLogDetail, type UsageLogDetailResponse } from "@/api/logs";
import AppButton from "@/shared/ui/button/button";
import {
  ArrowLeftIcon,
  CircleAlertIcon,
  HistoryIcon,
} from "@/shared/ui/icon";

function formatDateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return `${date.getFullYear()}-${`${date.getMonth() + 1}`.padStart(2, "0")}-${`${date.getDate()}`.padStart(2, "0")} ${`${date.getHours()}`.padStart(2, "0")}:${`${date.getMinutes()}`.padStart(2, "0")}:${`${date.getSeconds()}`.padStart(2, "0")}`;
}

function formatDuration(value?: number | null) {
  if (typeof value !== "number" || Number.isNaN(value)) return "-";
  if (value < 1000) return `${value} ms`;
  return `${(value / 1000).toFixed(value >= 10_000 ? 0 : 1)} s`;
}

function formatPower(value?: string | null) {
  if (!value) return "-";
  const amount = Number(value);
  if (Number.isNaN(amount)) return value;
  return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 6 }).format(amount);
}

function statusText(status: string) {
  switch (status) {
    case "succeeded":
      return "成功";
    case "failed":
      return "失败";
    case "started":
      return "进行中";
    default:
      return status || "未知";
  }
}

function ownerTypeText(value?: string | null) {
  if (value === "user") return "用户账号";
  if (value === "platform") return "平台账号";
  return "-";
}

function providerAttemptErrorText(item: UsageLogDetailResponse["chain"][number]) {
  if (item.status === "succeeded") {
    return "-";
  }
  return item.error_message ?? item.fallback_reason ?? "-";
}

function formatJson(value: unknown) {
  if (value === null || value === undefined) return "{}";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="log-detail-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default function LogDetailPage() {
  const { requestId = "" } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<UsageLogDetailResponse | null>(null);
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
        const data = await getUsageLogDetail(requestId);
        setDetail(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "日志详情加载失败");
      } finally {
        setLoading(false);
      }
    };
    if (requestId) {
      load();
    } else {
      setLoading(false);
      setError("缺少 request_id");
    }
  }, [navigate, requestId]);

  const statusClass = useMemo(
    () => `log-detail-status log-detail-status--${detail?.status || "unknown"}`,
    [detail?.status],
  );

  return (
    <div className="log-detail-page">
      <section className="log-detail-hero">
        <div className="log-detail-hero-top">
          <div className="log-detail-title-group">
            <h1>请求详情</h1>
            <p>{requestId || "当前请求详情"}</p>
          </div>
          <div className="log-detail-hero-actions">
            {detail ? (
              <strong className={statusClass}>{statusText(detail.status)}</strong>
            ) : null}
            <AppButton
              variant="outline"
              size="md"
              leftIcon={<ArrowLeftIcon />}
              onClick={() => navigate("/logs")}
            >
              返回请求
            </AppButton>
          </div>
        </div>
        {detail ? (
          <>
            <div className="log-detail-summary-line">
              <span>模型 {detail.model}</span>
              <span>路由 {detail.route_group}</span>
              <span>耗时 {formatDuration(detail.duration_ms)}</span>
              <span>关联算力 {formatPower(detail.power_amount)}</span>
              <span>销售额 {formatPower(detail.sale_amount)}</span>
            </div>
            <div className="log-detail-summary-line log-detail-summary-line--muted">
              <span>创建于 {formatDateTime(detail.created_at)}</span>
              <span>完成于 {formatDateTime(detail.finished_at)}</span>
            </div>
          </>
        ) : null}
      </section>

      {error ? <div className="log-detail-feedback error">{error}</div> : null}
      {loading ? <div className="log-detail-feedback">请求详情加载中...</div> : null}

      {!loading && !error && detail ? (
        <>

          <section className="log-detail-grid">
            <article className="detail-card">
              <h2>请求信息</h2>
              <div className="log-detail-list">
                <DetailRow label="路径" value={detail.request_path || "-"} />
                <DetailRow label="完成时间" value={formatDateTime(detail.finished_at)} />
              </div>
              <pre className="detail-code-block">{formatJson(detail.request_summary)}</pre>
            </article>

            <article className="detail-card">
              <h2>结果信息</h2>
              <div className="log-detail-list">
                {detail.task ? (
                  <>
                    <DetailRow label="异步任务" value={detail.task.platform_task_id} />
                    <DetailRow label="任务状态" value={detail.task.status} />
                    <DetailRow label="执行账号" value={detail.task.provider_account_short_id || "-"} />
                    <DetailRow label="资源归属" value={ownerTypeText(detail.task.provider_account_owner_type)} />
                  </>
                ) : (
                  <DetailRow label="异步任务" value="-" />
                )}
              </div>
              <pre className="detail-code-block">{formatJson(detail.response_summary)}</pre>
            </article>
          </section>

          <section className="detail-card">
            <h2>供应商链路</h2>
            {detail.chain.length > 0 ? (
              <div className="provider-table-wrap">
                <table className="provider-table">
                  <thead>
                    <tr>
                      <th>尝试</th>
                      <th>供应商</th>
                      <th>执行账号</th>
                      <th>资源归属</th>
                      <th>模型</th>
                      <th>状态</th>
                      <th>耗时</th>
                      <th>错误</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.chain.map((item) => (
                      <tr key={`${item.attempt_no}-${item.provider_code}`}>
                        <td>{item.attempt_no}</td>
                        <td>{item.provider_code}</td>
                        <td>{item.provider_account_short_id || "-"}</td>
                        <td>{ownerTypeText(item.provider_account_owner_type)}</td>
                        <td>{item.model_code}</td>
                        <td>
                          <span className={`provider-status provider-status--${item.status}`}>
                            {statusText(item.status)}
                          </span>
                        </td>
                        <td>{formatDuration(item.duration_ms)}</td>
                        <td>{providerAttemptErrorText(item)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="detail-empty">
                <HistoryIcon className="detail-empty-icon" />
                <span>没有供应商链路信息。</span>
              </div>
            )}
          </section>

          <section className="detail-card">
            <h2>白名单请求头</h2>
            <pre className="detail-code-block">{formatJson(detail.request_headers)}</pre>
          </section>

          {detail.error_message ? (
            <section className="detail-card">
              <h2>错误信息</h2>
              <div className="detail-error">
                <CircleAlertIcon />
                <span>{detail.error_message}</span>
              </div>
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
