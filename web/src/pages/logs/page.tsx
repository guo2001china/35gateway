import "./page.scss";
import { Input } from "antd";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { listUsageLogs, type UsageLogListItem } from "@/api/logs";
import AppButton from "@/shared/ui/button/button";
import {
  HistoryIcon,
  SearchIcon,
} from "@/shared/ui/icon";

const PAGE_SIZE = 20;

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

export default function LogsPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<UsageLogListItem[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("all");
  const [requestIdInput, setRequestIdInput] = useState("");
  const [modelInput, setModelInput] = useState("");
  const [filters, setFilters] = useState({ request_id: "", model: "", status: "all" });

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
        const data = await listUsageLogs({
          page,
          size: PAGE_SIZE,
          ...filters,
        });
        setItems(data.items);
        setTotal(data.total);
      } catch (err) {
        setError(err instanceof Error ? err.message : "日志加载失败");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [filters, navigate, page]);

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / PAGE_SIZE)), [total]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFilters({
      request_id: requestIdInput.trim(),
      model: modelInput.trim(),
      status,
    });
    setPage(1);
  }

  return (
    <div className="logs-page">
      <section className="logs-hero">
        <div className="logs-copy">
          <span className="logs-kicker">Requests</span>
          <h1>请求</h1>
          <p>这里按 request 展示每次调用的状态、耗时和请求链路，用于排障和追踪，不等于最终消耗账单。</p>
        </div>
        <div className="logs-summary">
          <HistoryIcon />
          <div>
            <strong>{loading ? "加载中" : `${total} 条请求`}</strong>
            <span>按 request 维度查看调用与执行状态</span>
          </div>
        </div>
      </section>

      <section className="logs-panel">
        <form className="logs-toolbar" onSubmit={handleSubmit}>
          <div className="logs-toolbar-grid">
            <Input
              value={requestIdInput}
              onChange={(event) => setRequestIdInput(event.target.value)}
              placeholder="搜索 request_id"
              rootClassName="app-input-root"
              prefix={<SearchIcon className="app-icon" />}
            />
            <Input
              value={modelInput}
              onChange={(event) => setModelInput(event.target.value)}
              placeholder="搜索模型名"
              rootClassName="app-input-root"
              prefix={<SearchIcon className="app-icon" />}
            />
            <div className="logs-select-wrap">
              <select value={status} onChange={(event) => setStatus(event.target.value)}>
                <option value="all">全部状态</option>
                <option value="succeeded">成功</option>
                <option value="failed">失败</option>
                <option value="started">进行中</option>
              </select>
            </div>
          </div>
          <div className="logs-toolbar-actions">
            <AppButton variant="outline" size="md" type="button" onClick={() => {
              setRequestIdInput("");
              setModelInput("");
              setStatus("all");
              setFilters({ request_id: "", model: "", status: "all" });
              setPage(1);
            }}>
              重置
            </AppButton>
            <AppButton variant="primary" size="md" type="submit">
              查询
            </AppButton>
          </div>
        </form>

        {error ? <div className="logs-feedback error">{error}</div> : null}
        {loading ? <div className="logs-feedback">请求加载中...</div> : null}

        {!loading && !error && items.length > 0 ? (
          <>
            <div className="logs-table-wrap">
              <table className="logs-table">
                <thead>
                  <tr>
                    <th>Request ID</th>
                    <th>时间</th>
                    <th>模型</th>
                    <th>状态</th>
                    <th>关联算力</th>
                    <th>耗时</th>
                    <th>详情</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.request_id}>
                      <td>
                        <div className="logs-request-id">{item.request_id}</div>
                      </td>
                      <td>{formatDateTime(item.created_at)}</td>
                      <td>{item.model}</td>
                      <td>
                        <span className={`logs-status logs-status--${item.status || "unknown"}`}>
                          {statusText(item.status)}
                        </span>
                      </td>
                      <td>{formatPower(item.power_amount)}</td>
                      <td>{formatDuration(item.duration_ms)}</td>
                      <td>
                        <button
                          type="button"
                          className="logs-detail-link"
                          onClick={() => navigate(`/logs/${item.request_id}`)}
                        >
                          查看详情
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="logs-pagination">
              <span>共 {total} 条请求</span>
              <div className="logs-pagination-actions">
                <AppButton
                  variant="outline"
                  size="sm"
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((current) => Math.max(1, current - 1))}
                >
                  上一页
                </AppButton>
                <span>{page} / {totalPages}</span>
                <AppButton
                  variant="outline"
                  size="sm"
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                >
                  下一页
                </AppButton>
              </div>
            </div>
          </>
        ) : null}

        {!loading && !error && items.length === 0 ? (
          <div className="logs-empty">
            <HistoryIcon className="logs-empty-icon" />
            <strong>还没有请求</strong>
            <span>当前账号下暂无调用请求，运行内容后会在这里按 request 展示。</span>
          </div>
        ) : null}
      </section>
    </div>
  );
}
