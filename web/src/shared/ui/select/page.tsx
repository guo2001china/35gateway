import { Popover } from "antd";
import { useState, MouseEvent } from "react";
import { CheckIcon, ChevronDownIcon } from "@/shared/ui/icon";
import "./page.scss";
type AppSelectProps = {
  label?: string;
  value?: string;
  currentValue: string;
  optionList: any;
  onSelectCall: (item: any) => void;
  classNames?: string;
  popoverClassName?: string;
  placeholder?: string;
  emptyText?: string;
  disabled?: boolean;
  triggerTestId?: string;
};
function AppSelect({
  optionList,
  currentValue,
  label = "label",
  value = "value",
  onSelectCall,
  classNames = '',
  popoverClassName = '',
  placeholder = "请选择",
  emptyText = "暂无选项",
  disabled = false,
  triggerTestId,
}: AppSelectProps) {
  const [open, setOpen] = useState(false);
  const handleOpenChange = (newOpen: boolean) => {
    if (disabled) {
      setOpen(false);
      return;
    }
    setOpen(newOpen);
  };
  const selectCallFn = (e: MouseEvent, value: any) => {
    e.stopPropagation();
    setOpen(false);
    onSelectCall(value);
  };
  const getCurrentLabel = () => {
    return optionList.find((item: any) => item[value] === currentValue)?.[label];
  }

  return (
    <div className={`app-select ${classNames} ${disabled ? 'is-disabled' : ''}`}>
      <Popover
        content={
          <div className={`popover-option-list ${popoverClassName}`}>
            {optionList.length > 0 ? (
              optionList.map((item: any) => (
                <div className="popover-option-item" onClick={(e) => selectCallFn(e, item[value])} key={item[value]}>
                  <div className="option-item-text">
                    {item[label]}
                  </div>
                  {(item[value] == currentValue) && (
                    <div className="option-item-icon checked">
                      <CheckIcon />
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="popover-option-item is-empty">
                <div className="option-item-text">{emptyText}</div>
              </div>
            )}
          </div>
        }
        arrow={false}
        openClassName="app-popover"
        trigger="click"
        color="transparent"
        placement="bottomRight"
        open={open}
        onOpenChange={handleOpenChange}
        overlayClassName="card-popover-overlay"
      >
        <div className="app-select__trigger" data-testid={triggerTestId}>
          <div className={`app-select__value ${getCurrentLabel() ? 'active' : ''}`}>{getCurrentLabel() || placeholder}</div>
          <ChevronDownIcon className="select-chevron" />
        </div>
      </Popover>
    </div>
  );
}

export default AppSelect;
