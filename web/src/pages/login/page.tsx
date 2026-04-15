import React, { useEffect, useState } from 'react';
import { message, Popover } from 'antd';
import { useNavigate } from 'react-router-dom';
import { loginWithEmail, loginWithPassword, sendEmailVerificationCode } from '@/api/loginapi';
import { BRAND_ICON_URL, LOGIN_BRAND_TEXT } from '@/constants/brand';
import { captureAnalyticsEvent, getAnalyticsGrowthContext, identifyAnalyticsUser } from '@/utils/analytics';
import { assetPath } from '@/utils/appBase';
import { MailIcon, UserIcon, WeChatIcon } from '@/shared/ui/icon';
import './page.scss';

const LOGIN_BACKGROUND_VIDEO = assetPath('assets/login-background.mp4');
const LOGIN_COMMUNITY_QR = assetPath('assets/login-community-qr.jpg');

type LoginMode = 'password' | 'email_code';

const Login: React.FC = () => {
  const navigate = useNavigate();
  const [mode, setMode] = useState<LoginMode>('password');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
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

  useEffect(() => {
    if (typeof window === 'undefined' || !window.location.hash) {
      return;
    }

    const params = new URLSearchParams(window.location.hash.replace(/^#/, ''));
    const sessionToken = params.get('session_token');
    const nextPath = params.get('next');
    const authError = params.get('auth_error');

    if (authError) {
      message.error(`登录失败：${authError}`);
    }

    if (sessionToken) {
      localStorage.setItem('session_token', sessionToken);
      captureAnalyticsEvent('login_completed', { auth_method: 'callback' });
      window.dispatchEvent(new Event('user-login'));
      navigate(nextPath && nextPath.startsWith('/') ? nextPath : '/', { replace: true });
    }

    if (sessionToken || authError) {
      window.history.replaceState(null, '', window.location.pathname + window.location.search);
    }
  }, [navigate]);

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

  useEffect(() => {
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

  const handlePasswordLogin = async () => {
    const normalizedEmail = validateEmail();
    if (!normalizedEmail) return;
    if (!password) {
      message.warning('请输入密码');
      return;
    }

    setIsLoading(true);
    try {
      const data = await loginWithPassword(normalizedEmail, password, getAnalyticsGrowthContext());
      localStorage.setItem('session_token', data.session_token ?? '');
      identifyAnalyticsUser(data.user);
      captureAnalyticsEvent('login_completed', {
        auth_method: 'password',
        user_id: data.user.user_id,
        user_no: data.user.user_no,
      });
      window.dispatchEvent(new Event('user-login'));
      message.success('登录成功');
      navigate('/', { replace: true });
    } catch (error) {
      console.error('密码登录失败:', error);
      message.error('登录失败，请检查邮箱和密码');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEmailCodeLogin = async () => {
    const normalizedEmail = validateEmail();
    if (!normalizedEmail) return;
    if (!verificationCode || verificationCode.length !== 6) {
      message.warning('请输入 6 位验证码');
      return;
    }

    setIsLoading(true);
    try {
      const data = await loginWithEmail(normalizedEmail, verificationCode, getAnalyticsGrowthContext());
      localStorage.setItem('session_token', data.session_token ?? '');
      identifyAnalyticsUser(data.user);
      captureAnalyticsEvent('login_completed', {
        auth_method: 'email_code',
        user_id: data.user.user_id,
        user_no: data.user.user_no,
      });
      window.dispatchEvent(new Event('user-login'));
      message.success('登录成功');
      navigate('/', { replace: true });
    } catch (error) {
      console.error('邮箱验证码登录失败:', error);
      message.error('登录失败，请检查验证码是否正确');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === 'password') {
      await handlePasswordLogin();
      return;
    }
    await handleEmailCodeLogin();
  };

  const renderForm = () => (
    <>
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

      {mode === 'password' ? (
        <div className="form-group">
          <div className="input-container">
            <UserIcon aria-hidden="true" className="input-icon" strokeWidth={2} />
            <input
              type="password"
              placeholder="请输入密码"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="phone-input"
              maxLength={128}
              disabled={isLoading}
            />
          </div>
        </div>
      ) : (
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
      )}

      <button
        type="submit"
        className="login-btn"
        disabled={
          isLoading || !email.trim() || (mode === 'password' ? !password : !verificationCode)
        }
      >
        {isLoading ? '登录中...' : '登录'}
      </button>

      <div className="login-method-icons" role="tablist" aria-label="登录方式">
        <button
          type="button"
          className={`login-method-icon ${mode === 'password' ? 'active' : ''}`}
          aria-label="邮箱密码登录"
          title="邮箱密码登录"
          onClick={() => setMode('password')}
        >
          <UserIcon />
        </button>
        <button
          type="button"
          className={`login-method-icon ${mode === 'email_code' ? 'active' : ''}`}
          aria-label="邮箱验证码登录"
          title="邮箱验证码登录"
          onClick={() => setMode('email_code')}
        >
          <MailIcon />
        </button>
      </div>

      <div className="auth-link-row">
        <span className="auth-link-copy">没有账号？</span>
        <button type="button" className="auth-inline-link" onClick={() => navigate('/register')}>
          立即注册
        </button>
      </div>
    </>
  );

  return (
    <div className="login-container">
      {renderCanvasBackground()}
      <main className="login-overlay">
        <section className="login-section">
          <div className="login-content">
            <div className="login-panel-head">
              <h2 className="login-title">开启稳定可靠之旅</h2>
              <p className="login-subtitle">自己的Key和平台混用，供应商可用率透明。</p>
            </div>

            <form className="login-form" onSubmit={handleSubmit}>
              {renderForm()}

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

export default Login;
