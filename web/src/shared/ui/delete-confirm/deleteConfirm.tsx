import "./deleteConfirm.scss";
import { XIcon } from "@/shared/ui/icon";
export default function DeleteConfirm({
  isOpen,
  onCancel,
  onOk,
  title,
  content,
}: {
  isOpen: boolean;
  onCancel: () => void;
  onOk: () => void;
  title?: string;
  content?: string;
}) {
  if (!isOpen) {
    return null;
  }
  return (
    <div className="delete-modal-mask">
      <div className="delete-modal">
        <div className="delete-modal-header">
          <div>{title || "确定清空运行记录？"}</div>
          <div className="close-btn" onClick={() => onCancel()}>
            <XIcon className="app-icon" />
          </div>
        </div>
        <div className="delete-modal-content">
          {content ?? "清空将无法找回"}
        </div>
        <div className="delete-modal-footer">
          <div className="delete-modal-cancel" onClick={() => onCancel()}>
            取消
          </div>
          <div className="delete-modal-confirm" onClick={() => onOk()}>
            确认
          </div>
        </div>
      </div>
    </div>
  );
}
