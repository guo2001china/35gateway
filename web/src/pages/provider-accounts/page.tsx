import "./page.scss";
import { Drawer, message } from "antd";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import {
  createProviderAccount,
  deleteProviderAccount,
  listProviderAccountProviders,
  listProviderAccounts,
  syncProviderAccountBalance,
  updateProviderAccount,
  verifyProviderAccount,
  type ProviderAccountProviderOptionResponse,
  type ProviderAccountResponse,
} from "@/api/platform";
import AppButton from "@/shared/ui/button/button";
import { CircleAlertIcon, CircleCheckIcon, PlusIcon } from "@/shared/ui/icon";
import { formatCurrency, formatDateTime } from "@/utils/format";

type DrawerMode = "create" | "edit";

type FormState = {
  provider_code: string;
  display_name: string;
  base_url_override: string;
  status: string;
  priority: string;
  notes: string;
  credential_payload: Record<string, string>;
};

const DEFAULT_FORM: FormState = {
  provider_code: "",
  display_name: "",
  base_url_override: "",
  status: "active",
  priority: "100",
  notes: "",
  credential_payload: {},
};

function formatBalance(account: ProviderAccountResponse) {
  if (account.balance_status === "ok" && account.balance_amount) {
    return formatCurrency(account.balance_amount, account.balance_currency || "USD");
  }
  if (account.balance_status === "failed") {
    return "异常";
  }
  return "不支持";
}

function formatVerificationLabel(status: string) {
  switch (status) {
    case "verified":
      return "验证成功";
    case "failed":
      return "验证失败";
    default:
      return "待验证";
  }
}

function formatStatusLabel(status: string) {
  switch (status) {
    case "active":
      return "启用中";
    case "disabled":
      return "已停用";
    case "deleted":
      return "已删除";
    default:
      return status;
  }
}

function formatProviderAccountError(error: unknown, fallback: string) {
  const detail = error instanceof Error ? error.message.trim() : "";
  if (!detail) {
    return fallback;
  }
  if (detail === "provider_code_required") return "请选择供应商";
  if (detail === "provider_code_not_supported") return "当前供应商暂不支持账号接入";
  if (detail === "provider_account_display_name_required") return "请输入名称/备注";
  if (detail === "provider_account_api_key_required") return "请输入 API Key";
  if (detail === "provider_account_credentials_incomplete") return "请补全当前供应商所需凭证";
  if (detail === "provider_account_not_found") return "账号不存在，请刷新后重试";
  if (detail === "provider_account_balance_not_supported") return "当前供应商暂不支持余额同步";
  if (detail === "provider_account_verify_not_supported") return "当前供应商暂不支持测试连接";
  if (detail.startsWith("provider_account_verify_failed:")) return `测试连接失败：${detail.replace("provider_account_verify_failed:", "").trim()}`;
  if (detail.startsWith("provider_account_balance_sync_failed:")) {
    return `余额同步失败：${detail.replace("provider_account_balance_sync_failed:", "").trim()}`;
  }
  return detail;
}

function buildNextForm(
  account: ProviderAccountResponse | null,
  providers: ProviderAccountProviderOptionResponse[],
): FormState {
  if (!account) {
    return {
      ...DEFAULT_FORM,
      provider_code: providers[0]?.provider_code ?? "",
    };
  }
  return {
    provider_code: account.provider_code,
    display_name: account.display_name,
    base_url_override: account.base_url_override ?? "",
    status: account.status,
    priority: String(account.priority),
    notes: account.notes ?? "",
    credential_payload: {},
  };
}

export default function ProviderAccountsPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [providerOptions, setProviderOptions] = useState<ProviderAccountProviderOptionResponse[]>([]);
  const [accounts, setAccounts] = useState<ProviderAccountResponse[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerMode, setDrawerMode] = useState<DrawerMode>("create");
  const [editingAccount, setEditingAccount] = useState<ProviderAccountResponse | null>(null);
  const [formState, setFormState] = useState<FormState>(DEFAULT_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [busyAccountId, setBusyAccountId] = useState<number | null>(null);

  const activeCount = useMemo(() => accounts.filter((item) => item.status === "active").length, [accounts]);
  const verifiedCount = useMemo(
    () => accounts.filter((item) => item.verification_status === "verified").length,
    [accounts],
  );
  const supportedBalanceCount = useMemo(
    () => accounts.filter((item) => item.supports_balance_sync).length,
    [accounts],
  );

  const currentProviderOption = useMemo(
    () => providerOptions.find((item) => item.provider_code === formState.provider_code) ?? null,
    [formState.provider_code, providerOptions],
  );

  const loadPage = async () => {
    setLoading(true);
    try {
      const [providersData, accountsData] = await Promise.all([listProviderAccountProviders(), listProviderAccounts()]);
      setProviderOptions(providersData);
      setAccounts(accountsData);
      setFormState((previous) => ({
        ...previous,
        provider_code: previous.provider_code || providersData[0]?.provider_code || "",
      }));
    } catch (err) {
      message.error(formatProviderAccountError(err, "供应商账号加载失败"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const token = localStorage.getItem("session_token");
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    void loadPage();
  }, [navigate]);

  const openCreateDrawer = () => {
    setDrawerMode("create");
    setEditingAccount(null);
    setFormState(buildNextForm(null, providerOptions));
    setDrawerOpen(true);
  };

  const openEditDrawer = (account: ProviderAccountResponse) => {
    setDrawerMode("edit");
    setEditingAccount(account);
    setFormState(buildNextForm(account, providerOptions));
    setDrawerOpen(true);
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    setEditingAccount(null);
    setDrawerMode("create");
    setFormState(buildNextForm(null, providerOptions));
  };

  const handleCredentialChange = (fieldName: string, value: string) => {
    setFormState((previous) => ({
      ...previous,
      credential_payload: {
        ...previous.credential_payload,
        [fieldName]: value,
      },
    }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const providerCode = formState.provider_code.trim();
    const displayName = formState.display_name.trim();
    if (!providerCode) {
      message.error("请选择供应商");
      return;
    }
    if (!displayName) {
      message.error("请输入名称/备注");
      return;
    }

    const credentialPayload = Object.fromEntries(
      Object.entries(formState.credential_payload).filter(([, value]) => value.trim()),
    );

    try {
      setSubmitting(true);
      if (drawerMode === "create") {
        await createProviderAccount({
          provider_code: providerCode,
          display_name: displayName,
          base_url_override: formState.base_url_override.trim() || null,
          credential_payload: credentialPayload,
          status: formState.status,
          priority: Number(formState.priority) || 100,
          notes: formState.notes.trim() || null,
        });
        message.success("供应商账号已添加");
      } else if (editingAccount) {
        const payload: {
          display_name?: string;
          base_url_override?: string | null;
          credential_payload?: Record<string, string>;
          status?: string;
          priority?: number;
          notes?: string | null;
        } = {
          display_name: displayName,
          base_url_override: formState.base_url_override.trim() || null,
          status: formState.status,
          priority: Number(formState.priority) || editingAccount.priority,
          notes: formState.notes.trim() || null,
        };
        if (Object.keys(credentialPayload).length) {
          payload.credential_payload = credentialPayload;
        }
        await updateProviderAccount(editingAccount.id, payload);
        message.success("供应商账号已更新");
      }
      closeDrawer();
      await loadPage();
    } catch (err) {
      message.error(formatProviderAccountError(err, drawerMode === "create" ? "创建账号失败" : "更新账号失败"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleStatus = async (account: ProviderAccountResponse) => {
    const nextStatus = account.status === "active" ? "disabled" : "active";
    try {
      setBusyAccountId(account.id);
      await updateProviderAccount(account.id, { status: nextStatus });
      await loadPage();
      message.success("账号状态已更新");
    } catch (err) {
      message.error(formatProviderAccountError(err, "更新账号状态失败"));
    } finally {
      setBusyAccountId(null);
    }
  };

  const handleDelete = async (account: ProviderAccountResponse) => {
    if (!window.confirm(`确认删除供应商账号「${account.display_name}」吗？`)) {
      return;
    }
    try {
      setBusyAccountId(account.id);
      await deleteProviderAccount(account.id);
      await loadPage();
      message.success("账号已删除");
    } catch (err) {
      message.error(formatProviderAccountError(err, "删除账号失败"));
    } finally {
      setBusyAccountId(null);
    }
  };

  const handleVerify = async (account: ProviderAccountResponse) => {
    try {
      setBusyAccountId(account.id);
      await verifyProviderAccount(account.id);
      await loadPage();
      message.success("测试连接成功");
    } catch (err) {
      await loadPage();
      message.error(formatProviderAccountError(err, "测试连接失败"));
    } finally {
      setBusyAccountId(null);
    }
  };

  const handleSyncBalance = async (account: ProviderAccountResponse) => {
    try {
      setBusyAccountId(account.id);
      await syncProviderAccountBalance(account.id);
      await loadPage();
      message.success("余额已同步");
    } catch (err) {
      await loadPage();
      message.error(formatProviderAccountError(err, "同步余额失败"));
    } finally {
      setBusyAccountId(null);
    }
  };

  return (
    <div className="settings-page provider-accounts-page">
      <section className="settings-hero">
        <div className="settings-copy">
          <span className="settings-kicker">Provider Accounts</span>
          <h1>供应商账号</h1>
          <p>连接你的供应商账号，系统会按顺序优先尝试你的账号。</p>
        </div>
        <div className="settings-summary-grid">
          <div className="settings-summary-card">
            <span>全部账号</span>
            <strong>{loading ? "-" : accounts.length}</strong>
          </div>
          <div className="settings-summary-card">
            <span>启用中</span>
            <strong>{loading ? "-" : activeCount}</strong>
          </div>
          <div className="settings-summary-card">
            <span>验证成功</span>
            <strong>{loading ? "-" : verifiedCount}</strong>
          </div>
          <div className="settings-summary-card">
            <span>支持余额</span>
            <strong>{loading ? "-" : supportedBalanceCount}</strong>
          </div>
        </div>
      </section>

      <section className="settings-stack">
        <article className="settings-panel">
          <div className="settings-panel-head">
            <div>
              <h2>账号列表</h2>
              <p>平台会按顺序优先尝试你的账号；账号不可用时默认自动回退到平台资源。</p>
            </div>
            <div className="provider-accounts-toolbar">
              <AppButton variant="primary" size="sm" leftIcon={<PlusIcon />} onClick={openCreateDrawer}>
                添加账号
              </AppButton>
            </div>
          </div>

          {loading ? (
            <div className="settings-feedback">供应商账号加载中...</div>
          ) : accounts.length ? (
            <div className="settings-table-wrap">
              <table className="settings-table provider-accounts-table">
                <thead>
                  <tr>
                    <th>短ID</th>
                    <th>供应商 / 名称</th>
                    <th>状态</th>
                    <th>余额</th>
                    <th>顺序</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {accounts.map((account) => (
                    <tr key={account.id}>
                      <td>
                        <div className="provider-accounts-short-id">
                          <strong>{account.short_id}</strong>
                          <span>{account.provider_code}</span>
                        </div>
                      </td>
                      <td>
                        <div className="provider-accounts-name-cell">
                          <strong>{account.display_name}</strong>
                          <span>{account.provider_name}</span>
                          <div className="provider-accounts-meta">
                            <span className={`provider-accounts-badge ${account.verification_status}`}>
                              {account.verification_status === "verified" ? <CircleCheckIcon /> : <CircleAlertIcon />}
                              {formatVerificationLabel(account.verification_status)}
                            </span>
                          </div>
                          {account.last_verification_error ? (
                            <div className="provider-accounts-meta">
                              <span>最近错误：{account.last_verification_error}</span>
                            </div>
                          ) : null}
                        </div>
                      </td>
                      <td>
                        <span className={`provider-accounts-badge ${account.status}`}>
                          {formatStatusLabel(account.status)}
                        </span>
                      </td>
                      <td>
                        <div className="provider-accounts-balance">
                          <strong>{formatBalance(account)}</strong>
                          <span>
                            {account.balance_updated_at ? `更新于 ${formatDateTime(account.balance_updated_at)}` : "-"}
                          </span>
                        </div>
                      </td>
                      <td>{account.priority}</td>
                      <td>
                        <div className="provider-accounts-actions">
                          <AppButton
                            variant="link"
                            size="sm"
                            disabled={busyAccountId === account.id}
                            onClick={() => void handleVerify(account)}
                          >
                            测试连接
                          </AppButton>
                          {account.supports_balance_sync ? (
                            <AppButton
                              variant="link"
                              size="sm"
                              disabled={busyAccountId === account.id}
                              onClick={() => void handleSyncBalance(account)}
                            >
                              同步余额
                            </AppButton>
                          ) : null}
                          <AppButton variant="link" size="sm" onClick={() => openEditDrawer(account)}>
                            编辑
                          </AppButton>
                          <AppButton
                            variant="link"
                            size="sm"
                            disabled={busyAccountId === account.id}
                            onClick={() => void handleToggleStatus(account)}
                          >
                            {account.status === "active" ? "停用" : "启用"}
                          </AppButton>
                          <AppButton
                            variant="link"
                            size="sm"
                            disabled={busyAccountId === account.id}
                            onClick={() => void handleDelete(account)}
                          >
                            删除
                          </AppButton>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="settings-feedback">当前还没有供应商账号，先添加一套你的上游账号。</div>
          )}
        </article>
      </section>

      <Drawer
        className="provider-accounts-drawer"
        title={drawerMode === "create" ? "添加供应商账号" : "编辑供应商账号"}
        width={520}
        open={drawerOpen}
        onClose={closeDrawer}
      >
        <form className="settings-stack provider-accounts-drawer-stack" onSubmit={handleSubmit}>
          <div className="settings-form-grid">
            <label className="settings-static-field">
              <span>供应商</span>
              <select
                value={formState.provider_code}
                onChange={(event) =>
                  setFormState((previous) => ({ ...previous, provider_code: event.target.value, credential_payload: {} }))
                }
                disabled={drawerMode === "edit"}
              >
                {providerOptions.map((item) => (
                  <option key={item.provider_code} value={item.provider_code}>
                    {item.provider_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="settings-static-field">
              <span>状态</span>
              <select
                value={formState.status}
                onChange={(event) => setFormState((previous) => ({ ...previous, status: event.target.value }))}
              >
                <option value="active">启用中</option>
                <option value="disabled">已停用</option>
              </select>
            </label>
            <label className="settings-static-field">
              <span>名称/备注</span>
              <input
                value={formState.display_name}
                onChange={(event) => setFormState((previous) => ({ ...previous, display_name: event.target.value }))}
                placeholder="例如：我的 Veo 账号"
              />
            </label>
            <label className="settings-static-field">
              <span>顺序</span>
              <input
                type="number"
                min={0}
                value={formState.priority}
                onChange={(event) => setFormState((previous) => ({ ...previous, priority: event.target.value }))}
              />
            </label>
            <label className="settings-static-field settings-form-grid-full">
              <span>Base URL（可选）</span>
              <input
                value={formState.base_url_override}
                onChange={(event) =>
                  setFormState((previous) => ({ ...previous, base_url_override: event.target.value }))
                }
                placeholder="留空则使用平台默认地址"
              />
            </label>
            {currentProviderOption?.auth_fields.map((field) => (
              <label key={field.field_name} className="settings-static-field settings-form-grid-full">
                <span>
                  {field.label}
                  {field.required ? " *" : ""}
                </span>
                <input
                  type={field.secret ? "password" : "text"}
                  value={formState.credential_payload[field.field_name] ?? ""}
                  onChange={(event) => handleCredentialChange(field.field_name, event.target.value)}
                  placeholder={drawerMode === "edit" ? "留空则保持当前凭证不变" : `请输入${field.label}`}
                  autoComplete="off"
                />
              </label>
            ))}
            <label className="settings-static-field settings-form-grid-full">
              <span>备注</span>
              <textarea
                value={formState.notes}
                onChange={(event) => setFormState((previous) => ({ ...previous, notes: event.target.value }))}
                placeholder="可选：记录 project / account / endpoint 等信息"
                rows={4}
              />
            </label>
          </div>
          <div className="provider-accounts-drawer-actions">
            <AppButton type="button" variant="outline" size="sm" onClick={closeDrawer}>
              取消
            </AppButton>
            <AppButton type="submit" variant="primary" size="sm" disabled={submitting}>
              {submitting ? "保存中..." : drawerMode === "create" ? "保存账号" : "保存修改"}
            </AppButton>
          </div>
        </form>
      </Drawer>
    </div>
  );
}
