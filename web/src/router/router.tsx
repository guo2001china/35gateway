import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import MainLayout from '../layout/MainLayout';
import Login from '../pages/login/page';
import Register from '../pages/register/page';
import HomePage from '../pages/home/page';
import ApiKeysPage from '../pages/api-keys/page';
import ProviderAccountsPage from '../pages/provider-accounts/page';
import ModelPricingPage from '../pages/model-pricing/page';
import TasksPage from '../pages/tasks/page';
import LogsPage from '../pages/logs/page';
import LogDetailPage from '../pages/logs/detail/page';
import SettingsPage from '../pages/settings/page';
import { UserProvider } from '../contexts/UserContext';
import NProgress from 'nprogress';

const RouteProgress: React.FC = () => {
  const location = useLocation();
  React.useEffect(() => {
    NProgress.start();
    const t = setTimeout(() => NProgress.done(), 300);
    return () => clearTimeout(t);
  }, [location]);
  return null;
};

/**
 * 路由配置：
 * - /login: 登录页（独立布局，无菜单）
 * - /register: 注册页（独立布局，无菜单）
 * - /: 主应用（包含菜单的嵌套路由）
 *   - /api-keys: API Keys
 *   - /settings: 设置中心
 *   - /logs: 用户请求日志
 */
type AppRouterProps = {
  basename?: string;
};

const AppRouter: React.FC<AppRouterProps> = ({ basename }) => {
  return (
    <Router basename={basename}>
      <RouteProgress />
      <UserProvider>
        <Routes>
          {/* 登录页 - 独立布局 */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          {/* 主应用 - 使用 MainLayout（包含侧边栏菜单） */}
          <Route path="/" element={<MainLayout />}>
            <Route index element={<HomePage />} />
            <Route path="home" element={<HomePage />} />
            <Route path="api-keys" element={<ApiKeysPage />} />
            <Route path="provider-accounts" element={<ProviderAccountsPage />} />
            <Route path="model-pricing" element={<ModelPricingPage />} />
            <Route path="tasks" element={<TasksPage />} />
            <Route path="logs" element={<LogsPage />} />
            <Route path="logs/:requestId" element={<LogDetailPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
          {/* 404 - 重定向到首页 */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </UserProvider>
    </Router>
  );
};

export default AppRouter;
