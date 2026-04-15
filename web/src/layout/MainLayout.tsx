import { Outlet } from 'react-router-dom';
import Menu from './menu/page';
import './MainLayout.scss';

/**
 * 主布局组件 - 包含侧边栏菜单和内容区域
 * 用于需要显示菜单的页面
 */
export default function MainLayout() {  
  return (
    <div className="main-layout">
      <Menu />
      <div className="main-content">
        <Outlet />
      </div>    
    </div>
  );
}
