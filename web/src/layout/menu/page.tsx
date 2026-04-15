import "./page.scss";
import React, { useState, useRef, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { APP_NAME, BRAND_ICON_URL } from "@/constants/brand";
import { logout } from "@/api/loginapi";
import { useUser } from "@/contexts/UserContext";
import { Modal } from "antd";
import ResizableBoxComponent, { ResizableBoxHandle } from "@/shared/ui/resizable/resizable-box";
import AppButton from "@/shared/ui/button/button";
import EditProfile from "../edit-profile/editProfile";
import {
  BoxesIcon,
  EllipsisIcon,
  HistoryIcon,
  HouseIcon,
  LoaderCircleIcon,
  LockIcon,
  LogOutIcon,
  MapIcon,
  SettingsIcon,
} from "@/shared/ui/icon";

export default function Menu() {
  const brandIcon = BRAND_ICON_URL;
  const brandDisplayText = APP_NAME;
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const location = useLocation();
  const { userInfo } = useUser();
  const [editProfileOpen, setEditProfileOpen] = useState(false);

  // 切换下拉菜单显示状态
  const toggleDropdown = (e: React.MouseEvent) => {
    e.stopPropagation(); // 防止事件冒泡导致立即关闭
    setIsDropdownOpen(!isDropdownOpen);
  };

  const handleLogout = async (e: React.MouseEvent) => {
    e.stopPropagation(); // 阻止事件冒泡
    setIsDropdownOpen(false); // 关闭下拉菜单
    try {
      await logout()
    } catch (error) {
      console.error('退出登录失败:', error);
    }
    // 清除单个项目
    localStorage.removeItem('session_token');
    // 触发登出事件
    window.dispatchEvent(new Event('user-logout'));
    // 使用react-router导航到登录页
    navigate('/login');
  };

  // 格式化手机号，隐藏中间四位
  const formatPhoneNumber = (phone: string): string => {
    if (!phone || phone.length !== 11) return phone || '';
    return `${phone.substring(0, 3)}****${phone.substring(7)}`;
  };

  // 点击外部区域关闭下拉菜单
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  // 工作流列表状态，初始为空数组
  const handleCollapse = () => {
    setIsCollapsed(prev => {
      const next = !prev;
      const targetWidth = next ? 60 : Math.max(216, menuContainerWidth);
      menuResizableRef.current?.updateSize({ width: targetWidth });
      setMenuContainerWidth(targetWidth);
      return next;
    });
  };

  // 展示默认头像
  const [showDefaultAvatar, setShowDefaultAvatar] = useState(true);
  useEffect(() => {
    setShowDefaultAvatar(!userInfo?.avatar)
  }, [userInfo?.avatar]);

  // resize 菜单逻辑
  const [menuContainerWidth, setMenuContainerWidth] = useState(216);
  // const [menuContainerHeight, setMenuContainerHeight] = useState(window.innerHeight);
  const menuResizableRef = useRef<ResizableBoxHandle | null>(null);

  useEffect(() => {
    if (menuContainerWidth < 155) {
      setIsCollapsed(true)
    } else {
      setIsCollapsed(false)
    }
  }, [menuContainerWidth])

  // 监听窗口变化
  useEffect(() => {
    const handleResize = () => {
      menuResizableRef.current?.updateSize({ height: window.innerHeight });
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  // 用户信息区域的激活状态
  const [isUserInfoActive, setIsUserInfoActive] = useState(false);
  const isHomeActive = location.pathname === "/" || location.pathname === "/home";
  const isApiKeysActive = location.pathname === "/api-keys";
  const isProviderAccountsActive = location.pathname === "/provider-accounts";
  const isModelPricingActive = location.pathname === "/model-pricing";
  const isTasksActive = location.pathname === "/tasks";
  const isLogsActive = location.pathname === "/logs" || location.pathname.startsWith("/logs/");
  const isSettingsActive = location.pathname === "/settings";

  return (
    <ResizableBoxComponent
      ref={menuResizableRef}
      axis="x"
      minWidth={60}
      maxWidth={280}
      initialHeight={window.innerHeight}
      maxHeight={window.innerHeight}
      initialWidth={216}
      className="menu-resizable-box"
      onResize={({ width, height }) => {
        setMenuContainerWidth(width);
      }}
    >
      <div className={`menu-container ${isCollapsed ? 'collapsed' : ''}`} style={{ width: menuContainerWidth }}>
        {/* <div className="collapse-container" onClick={handleCollapse}>
          <img className="collapse-icon" src={iconMenu} alt="collapse" />
        </div> */}
        <div className="menu-content">
          <div className="menu-brand" onClick={() => navigate('/')}>
            <img className="menu-brand-icon" src={brandIcon} alt="35m.ai" />
            {!isCollapsed && <span className="menu-brand-text">{brandDisplayText}</span>}
          </div>
          <div className="menu-nav">
            <button
              type="button"
              className={`menu-nav-item ${isHomeActive ? "active" : ""}`}
              onClick={() => navigate("/")}
            >
              <HouseIcon className="app-icon" />
              {!isCollapsed && <span>首页</span>}
            </button>
            <button
              type="button"
              className={`menu-nav-item ${isTasksActive ? "active" : ""}`}
              onClick={() => navigate("/tasks")}
            >
              <LoaderCircleIcon className="app-icon" />
              {!isCollapsed && <span>任务</span>}
            </button>
            <button
              type="button"
              className={`menu-nav-item ${isLogsActive ? "active" : ""}`}
              onClick={() => navigate("/logs")}
            >
              <HistoryIcon className="app-icon" />
              {!isCollapsed && <span>请求</span>}
            </button>
          </div>
          <div className="menu-secondary">
            <button
              type="button"
              className={`menu-nav-item ${isModelPricingActive ? "active" : ""}`}
              onClick={() => navigate("/model-pricing")}
            >
              <BoxesIcon className="app-icon" />
              {!isCollapsed && <span>价格</span>}
            </button>
            <button
              type="button"
              className={`menu-nav-item ${isApiKeysActive ? "active" : ""}`}
              onClick={() => navigate("/api-keys")}
            >
              <LockIcon className="app-icon" />
              {!isCollapsed && <span>Keys</span>}
            </button>
            <button
              type="button"
              className={`menu-nav-item ${isProviderAccountsActive ? "active" : ""}`}
              onClick={() => navigate("/provider-accounts")}
            >
              <MapIcon className="app-icon" />
              {!isCollapsed && <span>供应商</span>}
            </button>
            <button
              type="button"
              className={`menu-nav-item ${isSettingsActive ? "active" : ""}`}
              onClick={() => navigate('/settings')}
            >
              <SettingsIcon className="app-icon" />
              {!isCollapsed && <span>设置</span>}
            </button>
          </div>
          <div
            className={`user-info ${isUserInfoActive ? 'active-state' : ''}`}
            onMouseDown={() => setIsUserInfoActive(true)}
            onMouseUp={() => setIsUserInfoActive(false)}
            onMouseLeave={() => setIsUserInfoActive(false)}
          >
            {!showDefaultAvatar ? (
              <img
                className="user-avatar"
                src={userInfo?.avatar}
                alt="头像"
                onError={() => {
                  setShowDefaultAvatar(true)
                }}
              />
            ) : (
              <div key="user-avatar" className="user-avatar">{userInfo?.name?.charAt(0) || '用户'}</div>
            )}

            <p className="user-name ellipsis">
              {userInfo?.name || userInfo?.phone}
            </p>
            <div className={`more-container ${isDropdownOpen ? 'open' : ''}`} onMouseDown={(e) => e.stopPropagation()} onClick={(e) => e.stopPropagation()} ref={dropdownRef}>
              <AppButton
                onClick={(e) => {
                  toggleDropdown(e);
                }}
                className="delete-btn hidden-bg"
                variant="default"
                size="sm"
                leftIcon={<EllipsisIcon className="app-icon icon-more" />}>
              </AppButton>
              <div className="pop-container" onMouseDown={(e) => e.stopPropagation()} onClick={(e) => e.stopPropagation()}>
                <div className="pop-list">
                  {userInfo?.phone && (
                    <div className="phone-item">
                      <p className="phone-item-title">{formatPhoneNumber(userInfo.phone)}<br /><span>KD {userInfo?.balance.toString() || '0'}</span>
                      </p>
                    </div>
                  )}
                  {/* <div onClick={() => setEditProfileOpen(true)} className="pop-item">
                    <div className="flex items-center gap-[8px]">
                      <UserIcon className="app-icon" />
                      <p className="pop-item-title">个人信息</p>
                    </div>
                    <span />
                  </div>
                  <div className="pop-item-hr"></div> */}
                  <div className="pop-item" onClick={handleLogout}>
                    <div className="flex items-center gap-[8px]">
                      <LogOutIcon className="app-icon" />
                      <p className="pop-item-title">退出登录</p>
                    </div>
                    <span />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      {/* 个人信息弹窗 */}
      {editProfileOpen && (
        <Modal
          // destroyOnHidden={true}
          title=""
          open={editProfileOpen}
          width={415}
          centered={true}
          footer={null}
          onCancel={() => setEditProfileOpen(false)}
          rootClassName="app-modal-root"
        >
          <EditProfile />
        </Modal>
      )}
    </ResizableBoxComponent>
  );
}
