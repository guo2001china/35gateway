import "./page.scss";
import { Drawer, message } from "antd";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  createApiKey,
  deleteApiKey,
  getSystemDefaultApiKey,
  listApiKeys,
  revealApiKey,
  resetSystemDefaultApiKey,
  updateApiKey,
  type UserApiKeyResponse,
} from "@/api/platform";
import { captureAnalyticsEvent } from "@/utils/analytics";
import AppButton from "@/shared/ui/button/button";
import { CopyIcon, EyeIcon, EyeOffIcon } from "@/shared/ui/icon";
import { formatDateTime } from "@/utils/format";

type KeyEditorMode = "create" | "rename";

export default function ApiKeysPage() {
  const navigate = useNavigate();
  const [keysLoading, setKeysLoading] = useState(false);
  const [keys, setKeys] = useState<UserApiKeyResponse[]>([]);
  const [keyName, setKeyName] = useState("");
  const [latestCreatedKey, setLatestCreatedKey] = useState<{ keyName: string; apiKey: string } | null>(null);
  const [busyKeyId, setBusyKeyId] = useState<number | null>(null);
  const [revealedKey, setRevealedKey] = useState<{ id: number; apiKey: string } | null>(null);
  const [revealingKeyId, setRevealingKeyId] = useState<number | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editorMode, setEditorMode] = useState<KeyEditorMode>("create");
  const [editingKey, setEditingKey] = useState<UserApiKeyResponse | null>(null);

  const visibleKeys = useMemo(
    () =>
      [...keys]
        .filter((item) => item.status !== "deleted")
        .sort((left, right) => {
          const leftRank = left.key_kind === "system_default" ? 0 : 1;
          const rightRank = right.key_kind === "system_default" ? 0 : 1;
          if (leftRank !== rightRank) {
            return leftRank - rightRank;
          }
          return right.id - left.id;
        }),
    [keys],
  );
  const activeKeyCount = useMemo(() => visibleKeys.filter((item) => item.status === "active").length, [visibleKeys]);

  const loadKeys = async () => {
    setKeysLoading(true);
    try {
      const data = await listApiKeys();
      setKeys(data);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "API Keys 加载失败");
    } finally {
      setKeysLoading(false);
    }
  };

  const closeEditor = () => {
    setEditorOpen(false);
    setEditingKey(null);
    setEditorMode("create");
    setKeyName("");
    setLatestCreatedKey(null);
  };

  const openCreateDrawer = () => {
    setEditorMode("create");
    setEditingKey(null);
    setKeyName("");
    setLatestCreatedKey(null);
    setEditorOpen(true);
  };

  const openRenameDrawer = (item: UserApiKeyResponse) => {
    setEditorMode("rename");
    setEditingKey(item);
    setKeyName(item.key_name);
    setLatestCreatedKey(null);
    setEditorOpen(true);
  };

  useEffect(() => {
    const token = localStorage.getItem("session_token");
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    void loadKeys();
  }, [navigate]);

  const handleSubmitKeyEditor = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalized = keyName.trim();
    if (!normalized) {
      message.error("请输入 Key 名称");
      return;
    }
    if (editorMode === "rename" && editingKey && normalized === editingKey.key_name) {
      closeEditor();
      return;
    }
    try {
      if (editorMode === "create") {
        const data = await createApiKey({ key_name: normalized });
        captureAnalyticsEvent("api_key_created", {
          api_key_id: data.id,
          key_kind: data.key_kind,
          key_name_length: normalized.length,
        });
        setKeyName("");
        if (data.api_key) {
          setLatestCreatedKey({ keyName: data.key_name, apiKey: data.api_key });
        }
        await loadKeys();
        message.success("Key 已创建");
        return;
      }
      if (!editingKey) {
        message.error("当前 Key 不存在");
        return;
      }
      setBusyKeyId(editingKey.id);
      await updateApiKey(editingKey.id, { key_name: normalized });
      await loadKeys();
      closeEditor();
      message.success("Key 已更新");
    } catch (err) {
      message.error(err instanceof Error ? err.message : editorMode === "create" ? "创建 Key 失败" : "更新 Key 失败");
    } finally {
      if (editorMode === "rename") {
        setBusyKeyId(null);
      }
    }
  };

  const handleToggleKey = async (item: UserApiKeyResponse) => {
    const nextStatus = item.status === "active" ? "disabled" : "active";
    try {
      setBusyKeyId(item.id);
      await updateApiKey(item.id, { status: nextStatus });
      await loadKeys();
      message.success("Key 状态已更新");
    } catch (err) {
      message.error(err instanceof Error ? err.message : "更新 Key 失败");
    } finally {
      setBusyKeyId(null);
    }
  };

  const handleResetSystemKey = async (item: UserApiKeyResponse) => {
    try {
      setBusyKeyId(item.id);
      const data = await resetSystemDefaultApiKey();
      if (data.api_key) {
        setRevealedKey({ id: item.id, apiKey: data.api_key });
      }
      await loadKeys();
      message.success("系统 Key 已重置");
    } catch (err) {
      message.error(err instanceof Error ? err.message : "系统 Key 操作失败");
    } finally {
      setBusyKeyId(null);
    }
  };

  const handleToggleReveal = async (item: UserApiKeyResponse) => {
    if (revealedKey?.id === item.id) {
      setRevealedKey(null);
      return;
    }
    try {
      setRevealingKeyId(item.id);
      const data = item.key_kind === "system_default" ? await getSystemDefaultApiKey() : await revealApiKey(item.id);
      if (!data.api_key) {
        message.error("完整 Key 暂不可用");
        return;
      }
      setRevealedKey({ id: item.id, apiKey: data.api_key });
    } catch (err) {
      message.error(err instanceof Error ? err.message : "获取完整 Key 失败");
    } finally {
      setRevealingKeyId(null);
    }
  };

  const handleDeleteKey = async (item: UserApiKeyResponse) => {
    const confirmed = window.confirm(`确认删除 Key「${item.key_name}」吗？删除后将不再出现在列表中。`);
    if (!confirmed) {
      return;
    }
    try {
      setBusyKeyId(item.id);
      await deleteApiKey(item.id);
      if (revealedKey?.id === item.id) {
        setRevealedKey(null);
      }
      await loadKeys();
      message.success("Key 已删除");
    } catch (err) {
      message.error(err instanceof Error ? err.message : "删除 Key 失败");
    } finally {
      setBusyKeyId(null);
    }
  };

  const handleCopy = async (value: string, label: string) => {
    try {
      await navigator.clipboard.writeText(value);
      message.success(`${label}已复制`);
    } catch {
      message.error("复制失败");
    }
  };

  return (
    <div className="settings-page">
      <section className="settings-hero">
        <div className="settings-copy">
          <span className="settings-kicker">API Keys</span>
          <h1>API Keys</h1>
          <p>统一管理系统默认 Key 和你的自定义 Key。</p>
        </div>
        <div className="settings-summary-grid">
          <div className="settings-summary-card">
            <span>全部 Keys</span>
            <strong>{keysLoading ? "-" : visibleKeys.length}</strong>
          </div>
          <div className="settings-summary-card">
            <span>活跃 Keys</span>
            <strong>{keysLoading ? "-" : activeKeyCount}</strong>
          </div>
          <div className="settings-summary-card">
            <span>最近创建</span>
            <strong>{latestCreatedKey?.keyName ?? "-"}</strong>
          </div>
        </div>
      </section>

      <section className="settings-stack">
        <article className="settings-panel">
          <div className="settings-panel-head">
            <div>
              <h2>Key 列表</h2>
              <p>系统默认 Key 固定置顶；自定义 Key 支持创建、重命名、启停和删除。</p>
            </div>
            <AppButton variant="primary" size="sm" onClick={openCreateDrawer}>
              创建 Key
            </AppButton>
          </div>
          {keysLoading ? (
            <div className="settings-feedback">Keys 加载中...</div>
          ) : visibleKeys.length ? (
            <div className="settings-table-wrap">
              <table className="settings-table">
                <thead>
                  <tr>
                    <th>名称</th>
                    <th>前缀 / 完整值</th>
                    <th>状态</th>
                    <th>创建时间</th>
                    <th>最近使用</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleKeys.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <div className="api-keys-name-cell">
                          <strong>{item.key_kind === "system_default" ? "系统默认 Key" : item.key_name}</strong>
                          {item.key_kind === "system_default" ? (
                            <span>登录后自动补齐，供浏览器会话和控制台默认使用</span>
                          ) : null}
                        </div>
                      </td>
                      <td>
                        <div className="settings-key-prefix-cell">
                          <div className="settings-key-prefix-row">
                            {revealedKey?.id === item.id ? <code>{revealedKey.apiKey}</code> : <span>{item.key_prefix ?? "-"}</span>}
                            <button
                              type="button"
                              className="settings-key-toggle"
                              aria-label={revealedKey?.id === item.id ? "收起完整 Key" : "查看完整 Key"}
                              title={revealedKey?.id === item.id ? "收起完整 Key" : "查看完整 Key"}
                              onClick={() => void handleToggleReveal(item)}
                              disabled={revealingKeyId === item.id || busyKeyId === item.id}
                            >
                              {revealingKeyId === item.id ? (
                                <span className="settings-key-toggle-text">...</span>
                              ) : revealedKey?.id === item.id ? (
                                <EyeOffIcon />
                              ) : (
                                <EyeIcon />
                              )}
                            </button>
                            {revealedKey?.id === item.id ? (
                              <AppButton
                                variant="link"
                                size="sm"
                                leftIcon={<CopyIcon />}
                                onClick={() => void handleCopy(revealedKey.apiKey, `${item.key_name} Key`)}
                              >
                                复制
                              </AppButton>
                            ) : null}
                          </div>
                        </div>
                      </td>
                      <td><span className={`settings-status settings-status--${item.status}`}>{item.status}</span></td>
                      <td>{formatDateTime(item.created_at)}</td>
                      <td>{formatDateTime(item.last_used_at)}</td>
                      <td>
                        {item.key_kind === "system_default" ? (
                          <div className="settings-actions-row compact">
                            <AppButton variant="link" size="sm" disabled={busyKeyId === item.id} onClick={() => void handleResetSystemKey(item)}>
                              重置
                            </AppButton>
                          </div>
                        ) : (
                          <div className="settings-actions-row compact">
                            <AppButton variant="link" size="sm" disabled={busyKeyId === item.id} onClick={() => openRenameDrawer(item)}>
                              重命名
                            </AppButton>
                            <AppButton variant="link" size="sm" disabled={busyKeyId === item.id} onClick={() => void handleToggleKey(item)}>
                              {item.status === "active" ? "禁用" : "启用"}
                            </AppButton>
                            <AppButton variant="link" size="sm" disabled={busyKeyId === item.id} onClick={() => void handleDeleteKey(item)}>
                              删除
                            </AppButton>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="settings-empty-note">
              还没有创建任何 Key。
              <div className="settings-actions-row compact">
                <AppButton variant="primary" size="sm" onClick={openCreateDrawer}>
                  创建第一个 Key
                </AppButton>
              </div>
            </div>
          )}
        </article>
      </section>

      <Drawer
        title={editorMode === "create" ? "创建新 Key" : "重命名 Key"}
        open={editorOpen}
        onClose={closeEditor}
        className="api-keys-drawer"
        width={420}
      >
        <div className="api-keys-drawer-stack">
          <form className="settings-inline-form api-keys-editor-form" onSubmit={handleSubmitKeyEditor}>
            <input
              value={keyName}
              onChange={(event) => setKeyName(event.target.value)}
              placeholder="例如：本地调试"
              autoFocus
            />
            <AppButton
              variant="primary"
              size="md"
              type="submit"
              disabled={editorMode === "rename" && busyKeyId === editingKey?.id}
            >
              {editorMode === "create" ? "创建 Key" : "保存"}
            </AppButton>
          </form>
          {editorMode === "create" ? (
            <div className="settings-empty-note">完整明文只会在创建当次返回一次，建议按用途分别命名。</div>
          ) : (
            <div className="settings-empty-note">修改名称不会影响已有调用和日志记录。</div>
          )}
          {latestCreatedKey ? (
            <div className="settings-code-card success">
              <div>
                <strong>{latestCreatedKey.keyName}</strong>
                <code>{latestCreatedKey.apiKey}</code>
              </div>
              <div className="settings-actions-row compact">
                <AppButton variant="outline" size="sm" onClick={() => void handleCopy(latestCreatedKey.apiKey, "Key")}>
                  复制
                </AppButton>
                <AppButton variant="link" size="sm" onClick={closeEditor}>
                  我已保存
                </AppButton>
              </div>
            </div>
          ) : null}
        </div>
      </Drawer>
    </div>
  );
}
