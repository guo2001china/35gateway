import React, { useState } from 'react';
import { message, Popover } from 'antd';
import { useNavigate } from 'react-router-dom';
import { registerWithPassword, sendEmailVerificationCode } from '@/api/loginapi';
import { BRAND_ICON_URL, LOGIN_BRAND_TEXT } from '@/constants/brand';
import { captureAnalyticsEvent, getAnalyticsGrowthContext, identifyAnalyticsUser } from '@/utils/analytics';
import { assetPath } from '@/utils/appBase';
import { LockIcon, MailIcon, WeChatIcon } from '@/shared/ui/icon';
import '../login/page.scss';
import './page.scss';

const LOGIN_BACKGROUND_VIDEO = assetPath('assets/login-background.mp4');
const LOGIN_COMMUNITY_QR = assetPath('assets/login-community-qr.jpg');

const Register: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [isCountingDown, setIsCountingDown] = useState(false);
  const normalizeEmail = () => email.trim().toLowerCase();

  const validateEmail = () => {
    const normalized = normalizeEmail();
    const emailRegex = /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}$/i;
    if (!emailRegex.test(normalized)) {
      message.warning('请输入正确的邮箱地址');
      return null;
    }
    return normalized;
  };

  const renderHeader = () => (
    <header className="header">
      <div className="brand-head">
        <img src={BRAND_ICON_URL} alt="35m.ai" className="brand-icon" />
        <div className="brand-copy">
          <strong className="brand-name">{LOGIN_BRAND_TEXT}</strong>
        </div>
      </div>
    </header>
  );

  const renderCanvasBackground = () => (
    <div className="login-background" aria-hidden="true">
      <video
        className="login-background-video"
        src={LOGIN_BACKGROUND_VIDEO}
        autoPlay
        muted
        loop
        playsInline
      />
      <div className="login-background-overlay" />
      {renderHeader()}
    </div>
  );

  const handleSendVerificationCode = async () => {
    const normalizedEmail = validateEmail();
    if (!normalizedEmail) return;

    setIsCountingDown(true);
    setCountdown(60);
    try {
      const response = await sendEmailVerificationCode(normalizedEmail);
      if (response.debug_code) {
        message.success(`邮箱验证码已发送，测试码 ${response.debug_code}`);
      } else {
        message.success('邮箱验证码已发送');
      }
    } catch (error) {
      message.error('发送验证码失败，请稍后重试');
      setIsCountingDown(false);
      setCountdown(0);
    }
  };

  React.useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    if (isCountingDown && countdown > 0) {
      timer = setTimeout(() => {
        setCountdown(countdown - 1);
      }, 1000);
    } else if (countdown === 0) {
      setIsCountingDown(false);
    }
    return () => {
      if (timer !== undefined) clearTimeout(timer);
    };
  }, [countdown, isCountingDown]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const normalizedEmail = validateEmail();
    if (!normalizedEmail) return;
    if (!verificationCode || verificationCode.length !== 6) {
      message.warning('请输入 6 位验证码');
      return;
    }
    if (password.length < 8) {
      message.warning('密码至少需要 8 位');
      return;
    }
    if (password !== confirmPassword) {
      message.warning('两次输入的密码不一致');
      return;
    }

    setIsLoading(true);
    try {
      const data = await registerWithPassword(
        normalizedEmail,
        verificationCode,
        password,
        getAnalyticsGrowthContext(),
      );
      localStorage.setItem('session_token', data.session_token ?? '');
      identifyAnalyticsUser(data.user);
      captureAnalyticsEvent('signup_completed', {
        auth_method: 'password',
        user_id: data.user.user_id,
        user_no: data.user.user_no,
      });
      window.dispatchEvent(new Event('user-login'));
      message.success('注册成功');
      navigate('/', { replace: true });
    } catch (error) {
      console.error('注册失败:', error);
      message.error('注册失败，请检查验证码和密码后重试');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-container">
      {renderCanvasBackground()}
      <main className="login-overlay">
        <section className="login-section">
          <div className="login-content">
            <div className="login-panel-head">
              <h2 className="login-title">创建账号</h2>
              <p className="login-subtitle">先完成邮箱验证，再设置你的登录密码。</p>
            </div>

            <form className="login-form" onSubmit={handleSubmit}>
              <div className="form-group">
                <div className="input-container">
                  <MailIcon aria-hidden="true" className="input-icon" strokeWidth={2} />
                  <input
                    type="email"
                    placeholder="请输入邮箱"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="phone-input"
                    maxLength={200}
                    disabled={isLoading}
                  />
                </div>
              </div>

              <div className="form-group">
                <div className="verification-code-container">
                  <input
                    type="text"
                    placeholder="请输入 6 位验证码"
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value)}
                    className="verification-input"
                    maxLength={6}
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    className={`verify-btn ${isCountingDown ? 'counting-down' : ''}`}
                    onClick={handleSendVerificationCode}
                    disabled={isLoading || isCountingDown || !email.trim()}
                  >
                    {isCountingDown ? `已发送 ${countdown}s` : '发送邮箱验证码'}
                  </button>
                </div>
              </div>

              <div className="form-group">
                <div className="input-container">
                  <LockIcon aria-hidden="true" className="input-icon" strokeWidth={2} />
                  <input
                    type="password"
                    placeholder="请设置密码"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="phone-input"
                    maxLength={128}
                    disabled={isLoading}
                  />
                </div>
              </div>

              <div className="form-group">
                <div className="input-container">
                  <LockIcon aria-hidden="true" className="input-icon" strokeWidth={2} />
                  <input
                    type="password"
                    placeholder="请再次输入密码"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="phone-input"
                    maxLength={128}
                    disabled={isLoading}
                  />
                </div>
              </div>

              <button
                type="submit"
                className="login-btn"
                disabled={isLoading || !email.trim() || !verificationCode || !password || !confirmPassword}
              >
                {isLoading ? '注册中...' : '注册'}
              </button>

              <div className="auth-link-row">
                <span className="auth-link-copy">已有账号？</span>
                <button type="button" className="auth-inline-link" onClick={() => navigate('/login')}>
                  去登录
                </button>
              </div>

              <div className="community-entry-wrap">
                <Popover
                  trigger="click"
                  placement="bottom"
                  rootClassName="card-popover-overlay login-community-popover-overlay"
                  content={(
                    <div className="login-community-popover">
                      <img src={LOGIN_COMMUNITY_QR} alt="35m.ai 社群二维码" className="login-community-qr" />
                    </div>
                  )}
                >
                  <button type="button" className="community-entry">
                    <WeChatIcon className="community-entry-icon" />
                    <span>加社群领取免费算力</span>
                  </button>
                </Popover>
              </div>
            </form>
          </div>
        </section>
      </main>
    </div>
  );
};

export default Register;
