import "./page.scss";
import { Drawer, Input } from "antd";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  getAsyncTaskDetail,
  listAsyncTasks,
  type AsyncTaskDetailResponse,
  type AsyncTaskListItem,
  type AsyncTaskStats,
} from "@/api/tasks";
import AppButton from "@/shared/ui/button/button";
import {
  ArrowUpRightIcon,
  LoaderCircleIcon,
  SearchIcon,
} from "@/shared/ui/icon";

const PAGE_SIZE = 20;
const EMPTY_STATS: AsyncTaskStats = {
  active_count: 0,
  pending_billing_count: 0,
  completed_count: 0,
  failed_or_waived_count: 0,
};

function formatDateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return `${date.getFullYear()}-${`${date.getMonth() + 1}`.padStart(2, "0")}-${`${date.getDate()}`.padStart(2, "0")} ${`${date.getHours()}`.padStart(2, "0")}:${`${date.getMinutes()}`.padStart(2, "0")}:${`${date.getSeconds()}`.padStart(2, "0")}`;
}

function formatNumber(value?: string | null, fractionDigits = 6) {
  if (!value) return "-";
  const amount = Number(value);
  if (Number.isNaN(amount)) return value;
  return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: fractionDigits }).format(amount);
}

function taskStatusText(status?: string | null) {
  switch (status) {
    case "submitted":
      return "已提交";
    case "queued":
      return "排队中";
    case "processing":
      return "处理中";
    case "completed":
      return "已完成";
    case "failed":
      return "失败";
    case "cancelled":
    case "canceled":
      return "已取消";
    default:
      return status || "未知";
  }
}

function billingStatusText(status?: string | null) {
  switch (status) {
    case "pending":
      return "待结算";
    case "succeeded":
      return "已扣费";
    case "waived":
      return "已免单";
    case "failed":
      return "失败";
    default:
      return status || "-";
  }
}

function routeTypeText(value?: string | null) {
  switch (value) {
    case "video":
      return "视频";
    case "audio":
      return "音频";
    case "image":
      return "图片";
    default:
      return "任务";
  }
}

function ownerTypeText(value?: string | null) {
  if (value === "user") return "用户账号";
  if (value === "platform") return "平台账号";
  return "-";
}

function formatJson(value: unknown) {
  if (value === null || value === undefined) return "{}";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function TaskBadge({
  variant,
  value,
}: {
  variant: "task" | "billing";
  value?: string | null;
}) {
  if (!value) {
    return <span className="tasks-chip tasks-chip--neutral">-</span>;
  }
  const statusClass = `tasks-chip tasks-chip--${value}`;
  return (
    <span className={statusClass}>
      {variant === "task" ? taskStatusText(value) : billingStatusText(value)}
    </span>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="tasks-detail-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default function TasksPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<AsyncTaskListItem[]>([]);
  const [summary, setSummary] = useState<AsyncTaskStats>(EMPTY_STATS);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("all");
  const [queryInput, setQueryInput] = useState("");
  const [modelInput, setModelInput] = useState("");
  const [filters, setFilters] = useState({ query: "", model: "", status: "all" });
  const [reloadKey, setReloadKey] = useState(0);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [detail, setDetail] = useState<AsyncTaskDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");

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
        const data = await listAsyncTasks({
          page,
          size: PAGE_SIZE,
          ...filters,
        });
        setItems(data.items);
        setSummary(data.summary);
        setTotal(data.total);
        if (data.items.length === 0) {
          setDrawerOpen(false);
          setSelectedTaskId("");
          setDetail(null);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "任务加载失败");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [filters, navigate, page, reloadKey]);

  useEffect(() => {
    if (!drawerOpen || !selectedTaskId) {
      return;
    }
    const loadDetail = async () => {
      setDetailLoading(true);
      setDetailError("");
      try {
        const data = await getAsyncTaskDetail(selectedTaskId);
        setDetail(data);
      } catch (err) {
        setDetail(null);
        setDetailError(err instanceof Error ? err.message : "任务详情加载失败");
      } finally {
        setDetailLoading(false);
      }
    };
    void loadDetail();
  }, [drawerOpen, reloadKey, selectedTaskId]);

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / PAGE_SIZE)), [total]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFilters({
      query: queryInput.trim(),
      model: modelInput.trim(),
      status,
    });
    setPage(1);
  }

  function openTaskDetail(taskId: string) {
    setSelectedTaskId(taskId);
    setDrawerOpen(true);
  }

  return (
    <div className="logs-page tasks-page">
      <section className="logs-hero">
        <div className="logs-copy">
          <span className="logs-kicker">Async Tasks</span>
          <h1>任务</h1>
          <p>这里按异步任务展示执行状态、结果可用性和计费阶段，和请求链路、最终账单分开查看。</p>
        </div>
        <AppButton variant="outline" size="md" onClick={() => setReloadKey((current) => current + 1)}>
          刷新
        </AppButton>
      </section>

      <section className="tasks-summary-grid">
        <article className="task-stat-card">
          <span>进行中</span>
          <strong>{summary.active_count}</strong>
          <p>已提交、排队中、处理中</p>
        </article>
        <article className="task-stat-card">
          <span>待结算</span>
          <strong>{summary.pending_billing_count}</strong>
          <p>任务已创建，账单尚未收口</p>
        </article>
        <article className="task-stat-card">
          <span>已完成</span>
          <strong>{summary.completed_count}</strong>
          <p>结果已回写到任务记录</p>
        </article>
        <article className="task-stat-card">
          <span>失败 / 免单</span>
          <strong>{summary.failed_or_waived_count}</strong>
          <p>执行失败、取消或已免单</p>
        </article>
      </section>

      <section className="logs-panel">
        <form className="logs-toolbar" onSubmit={handleSubmit}>
          <div className="logs-toolbar-grid tasks-toolbar-grid">
            <Input
              value={queryInput}
              onChange={(event) => setQueryInput(event.target.value)}
              placeholder="搜索任务ID / 请求ID"
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
                <option value="submitted">已提交</option>
                <option value="queued">排队中</option>
                <option value="processing">处理中</option>
                <option value="completed">已完成</option>
                <option value="failed">失败</option>
                <option value="cancelled">已取消</option>
              </select>
            </div>
          </div>
          <div className="logs-toolbar-actions">
            <AppButton
              variant="outline"
              size="md"
              type="button"
              onClick={() => {
                setQueryInput("");
                setModelInput("");
                setStatus("all");
                setFilters({ query: "", model: "", status: "all" });
                setPage(1);
              }}
            >
              重置
            </AppButton>
            <AppButton variant="primary" size="md" type="submit">
              查询
            </AppButton>
          </div>
        </form>

        {error ? <div className="logs-feedback error">{error}</div> : null}
        {loading ? <div className="logs-feedback">任务加载中...</div> : null}

        {!loading && !error && items.length > 0 ? (
          <>
            <div className="logs-table-wrap">
              <table className="logs-table tasks-table">
                <thead>
                  <tr>
                    <th>任务ID</th>
                    <th>模型</th>
                    <th>类型</th>
                    <th>任务状态</th>
                    <th>计费状态</th>
                    <th>更新时间</th>
                    <th>请求ID</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.task_id} onClick={() => openTaskDetail(item.task_id)}>
                      <td>
                        <div className="logs-request-id">{item.task_id}</div>
                        <div className="tasks-subline">{item.provider_account_short_id || item.provider_code}</div>
                      </td>
                      <td>{item.model}</td>
                      <td>{routeTypeText(item.route_type)}</td>
                      <td><TaskBadge variant="task" value={item.task_status} /></td>
                      <td><TaskBadge variant="billing" value={item.billing_status} /></td>
                      <td>{formatDateTime(item.updated_at)}</td>
                      <td>
                        <div className="logs-request-id">{item.request_id}</div>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="logs-detail-link"
                          onClick={(event) => {
                            event.stopPropagation();
                            openTaskDetail(item.task_id);
                          }}
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
              <span>共 {total} 条任务</span>
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
            <LoaderCircleIcon className="logs-empty-icon" />
            <strong>还没有任务</strong>
            <span>当前账号下暂无异步任务，调用视频或音频等异步模型后会在这里集中展示。</span>
          </div>
        ) : null}
      </section>

      <Drawer
        title={detail?.task_id || selectedTaskId || "任务详情"}
        open={drawerOpen}
        width={620}
        onClose={() => {
          setDrawerOpen(false);
          setSelectedTaskId("");
          setDetail(null);
          setDetailError("");
        }}
        className="tasks-drawer"
      >
        <div className="tasks-drawer-stack">
          {detailError ? <div className="logs-feedback error">{detailError}</div> : null}
          {detailLoading ? <div className="logs-feedback">任务详情加载中...</div> : null}

          {!detailLoading && !detailError && detail ? (
            <>
              <article className="tasks-detail-card">
                <div className="tasks-detail-header">
                  <div>
                    <h2>{detail.model}</h2>
                    <p>{routeTypeText(detail.route_type)} / {detail.route_group}</p>
                  </div>
                  <div className="tasks-detail-badges">
                    <TaskBadge variant="task" value={detail.task_status} />
                    <TaskBadge variant="billing" value={detail.billing_status} />
                  </div>
                </div>
              </article>

              <article className="tasks-detail-card">
                <h3>生命周期</h3>
                <div className="tasks-detail-list">
                  <DetailRow label="创建时间" value={formatDateTime(detail.created_at)} />
                  <DetailRow label="更新时间" value={formatDateTime(detail.updated_at)} />
                  <DetailRow label="完成时间" value={formatDateTime(detail.finished_at)} />
                </div>
              </article>

              <article className="tasks-detail-card">
                <h3>结果</h3>
                {detail.result_urls.length > 0 ? (
                  <div className="tasks-result-links">
                    {detail.result_urls.map((url, index) => (
                      <a key={`${url}-${index}`} href={url} target="_blank" rel="noreferrer" className="tasks-result-link">
                        查看结果 {index + 1}
                      </a>
                    ))}
                  </div>
                ) : (
                  <div className="tasks-detail-empty">当前任务还没有可直接打开的结果链接。</div>
                )}
                <pre className="tasks-code-block">{formatJson(detail.result_payload)}</pre>
              </article>

              <article className="tasks-detail-card">
                <h3>关联信息</h3>
                <div className="tasks-detail-list">
                  <DetailRow label="请求ID" value={detail.request_id} />
                  <DetailRow label="请求路径" value={detail.request_path || "-"} />
                  <DetailRow label="供应商" value={detail.provider_code} />
                  <DetailRow label="执行账号" value={detail.provider_account_short_id || "-"} />
                  <DetailRow label="资源归属" value={ownerTypeText(detail.provider_account_owner_type)} />
                  <DetailRow label="上游任务ID" value={detail.provider_task_id || "-"} />
                  <DetailRow label="关联算力" value={formatNumber(detail.power_amount)} />
                  <DetailRow label="销售金额" value={formatNumber(detail.sale_amount, 8)} />
                </div>
                <div className="tasks-detail-actions">
                  <AppButton
                    variant="outline"
                    size="sm"
                    leftIcon={<ArrowUpRightIcon />}
                    onClick={() => navigate(`/logs/${detail.request_id}`)}
                  >
                    查看请求
                  </AppButton>
                </div>
              </article>

              {detail.error_message ? (
                <article className="tasks-detail-card">
                  <h3>错误信息</h3>
                  <div className="tasks-detail-empty error">{detail.error_message}</div>
                </article>
              ) : null}
            </>
          ) : null}

          {!detailLoading && !detailError && !detail ? (
            <div className="tasks-detail-empty">任务详情不可用。</div>
          ) : null}
        </div>
      </Drawer>
    </div>
  );
}
