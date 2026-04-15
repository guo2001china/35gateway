import "./empty.scss";
import { PackageOpenIcon } from "@/shared/ui/icon";

interface EmptyDataProps {
  className?: string;
  width?: number;
  tip?: string;
}

export default function EmptyData({ className, width = 122, tip = "暂无数据" }: EmptyDataProps) {

  return (
    <div className={`empty-container ${className || ""}`}>
      <PackageOpenIcon className="empty-icon" style={{ width: `${width}px`, height: `${width}px` }} />
      <div className="empty-tip">{tip}</div>
    </div>
  );
}
