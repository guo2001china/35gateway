import React from "react";
import { LoaderCircleIcon } from "@/shared/ui/icon";
import "./index.scss";

interface LoadingProps {
  tip?: string;
  size?: "small" | "medium" | "large";
  overlay?: boolean; // 是否覆盖整个父容器
}

const Loading: React.FC<LoadingProps> = ({ tip = "加载中...", size = "medium", overlay = false }) => {
  return (
    <div className={`loading-overlay ${size} ${overlay ? 'full-overlay' : ''}`}>
      <div className="loading-content">
        <LoaderCircleIcon className="icon-spin app-icon" />
        <p>{tip}</p>
      </div>
    </div>
  );
};

export default Loading;
