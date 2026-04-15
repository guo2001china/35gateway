import "./page.scss";
import { message } from "antd";
import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { getProfile, updateProfile, type UserProfileResponse } from "@/api/platform";
import { useUser } from "@/contexts/UserContext";
import AppButton from "@/shared/ui/button/button";
import { formatDateTime, formatNumberLike } from "@/utils/format";

const IDENTITY_LABELS: Record<string, string> = {
  password_local: "邮箱密码",
  email_otp: "邮箱验证码",
  phone_sms: "手机号验证码",
  google_oauth: "Google",
};

function formatIdentityLabel(provider: string) {
  return IDENTITY_LABELS[provider] ?? provider;
}

export default function SettingsPage() {
  const navigate = useNavigate();
  const { refresh } = useUser();
  const [profile, setProfile] = useState<UserProfileResponse | null>(null);
  const [name, setName] = useState("");
  const [profileLoading, setProfileLoading] = useState(true);
  const [profileSaving, setProfileSaving] = useState(false);

  const loadProfile = async () => {
    setProfileLoading(true);
    try {
      const data = await getProfile();
      setProfile(data);
      setName(data.name);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "账户信息加载失败");
    } finally {
      setProfileLoading(false);
    }
  };

  useEffect(() => {
    const token = localStorage.getItem("session_token");
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    void loadProfile();
  }, [navigate]);

  const handleSaveProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalized = name.trim();
    if (!normalized) {
      message.error("名称不能为空");
      return;
    }
    try {
      setProfileSaving(true);
      const data = await updateProfile({ name: normalized });
      setProfile(data);
      await refresh();
      message.success("账户资料已更新");
    } catch (err) {
      message.error(err instanceof Error ? err.message : "更新账户失败");
    } finally {
      setProfileSaving(false);
    }
  };

  return (
    <div className="settings-page">
      <section className="settings-hero">
        <div className="settings-copy">
          <span className="settings-kicker">Settings</span>
          <h1>设置</h1>
          <p>这里现在只保留账户资料、登录方式、登录邮箱和密码状态；API Keys 和文件素材已经迁到左侧独立页面。</p>
        </div>
        <div className="settings-summary-grid">
          <div className="settings-summary-card">
            <span>当前余额</span>
            <strong>{formatNumberLike(profile?.balance ?? "-", 0)}</strong>
          </div>
          <div className="settings-summary-card">
            <span>账户编号</span>
            <strong>{profile?.user_no ?? "-"}</strong>
          </div>
          <div className="settings-summary-card">
            <span>登录方式</span>
            <strong>
              {profile?.identities.length
                ? Array.from(new Set(profile.identities.map((item) => formatIdentityLabel(item.provider)))).join(" / ")
                : "-"}
            </strong>
          </div>
        </div>
      </section>

      <section className="settings-grid two-col">
        <article className="settings-panel">
          <div className="settings-panel-head">
            <div>
              <h2>基本信息</h2>
              <p>更新名称后，会同步到当前账号和主产品头部信息。</p>
            </div>
          </div>
          {profileLoading ? (
            <div className="settings-feedback">账户信息加载中...</div>
          ) : profile ? (
            <form className="settings-form-grid" onSubmit={handleSaveProfile}>
              <label>
                <span>名称</span>
                <input value={name} onChange={(event) => setName(event.target.value)} placeholder="输入显示名称" />
              </label>
              <div className="settings-static-field">
                <span>邮箱</span>
                <strong>{profile.email ?? "-"}</strong>
              </div>
              <div className="settings-static-field">
                <span>手机号</span>
                <strong>{profile.phone ?? "-"}</strong>
              </div>
              <div className="settings-actions-row">
                <AppButton variant="primary" size="md" type="submit" disabled={profileSaving}>
                  {profileSaving ? "保存中..." : "保存资料"}
                </AppButton>
              </div>
            </form>
          ) : null}
        </article>

        <article className="settings-panel">
          <div className="settings-panel-head">
            <div>
              <h2>登录与安全</h2>
              <p>这里展示当前账号绑定的登录方式、登录邮箱和密码状态。</p>
            </div>
          </div>
          {profile ? (
            <div className="settings-form-grid">
              <div className="settings-static-field">
                <span>登录邮箱</span>
                <strong>{profile.email ?? "-"}</strong>
              </div>
              <div className="settings-static-field">
                <span>密码状态</span>
                <strong>{profile.password_login_enabled ? "已设置" : "未设置"}</strong>
              </div>
              <div className="settings-static-field">
                <span>密码最近更新</span>
                <strong>{profile.password_updated_at ? formatDateTime(profile.password_updated_at) : "-"}</strong>
              </div>
            </div>
          ) : null}
          {profile?.identities.length ? (
            <div className="settings-list">
              {profile.identities.map((item) => (
                <div key={item.provider} className="settings-list-row">
                  <div>
                    <strong>{formatIdentityLabel(item.provider)}</strong>
                    <span>{item.email ?? item.phone ?? "未绑定邮箱或手机号"}</span>
                  </div>
                  <span>{formatDateTime(item.last_login_at)}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="settings-empty-note">当前没有可展示的登录方式信息。</div>
          )}
          <div className="settings-inline-note">当前仅展示登录方式与密码状态；密码修改暂未在设置页单独开放。</div>
        </article>
      </section>
    </div>
  );
}
