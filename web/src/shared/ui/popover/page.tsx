import { Popover } from "antd";
import { useState, ReactNode, MouseEvent } from "react";
import { CheckIcon } from "@/shared/ui/icon";
import "./page.scss";
type AppPopoverProps = {
  children: ReactNode;
  label?: string;
  value?: string;
  currentValue: string;
  optionList: any;
  onSelectCall: (item: any) => void;
};
function AppPopover({ children, optionList, currentValue, label="label", value="value", onSelectCall }: AppPopoverProps) {
  const [open, setOpen] = useState(false);
  const handleOpenChange = (newOpen: boolean) => {
    setOpen(newOpen);
  };
  const selectCallFn = (e: MouseEvent, item: any) => {
    e.stopPropagation();
    setOpen(false);
    onSelectCall(item);
  };
  return (
    <div className="app-popover">
      <Popover
        content={
          <div className="popover-option-list">
            {optionList.map((item: any) => (
              <div className="popover-option-item" onClick={(e) => selectCallFn(e, item)} key={item[value]}>
                <div className="option-item-text">
                  {item[label]}
                </div>
                {(item[value] == currentValue) && (
                  <div className="option-item-icon checked">
                    <CheckIcon />
                  </div>
                )}
              </div>
            ))}
          </div>
        }
        arrow={false}
        openClassName="app-popover"
        trigger="click"
        color="transparent"
        placement="bottom"
        open={open}
        onOpenChange={handleOpenChange}
        overlayClassName="card-popover-overlay"
      >
        <div className="app-popover__trigger">
          {children}
        </div>
      </Popover>
    </div>
  );
}

export default AppPopover;
