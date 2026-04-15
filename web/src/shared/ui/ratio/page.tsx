import "./page.scss";
import { dynamicStyle } from "@/utils/cardToolUtil";
import { useState, useEffect } from "react";
import { ScanSearchIcon } from "@/shared/ui/icon";
function AppRatio({ optionList, currentValue, label = "label", value = "value", onSelectCall }: { optionList: any[], currentValue: string, label?: string, value?: string, onSelectCall: (value: any) => void }) {
  const [rightList, setRightList] = useState<any[]>([])
  useEffect(() => {
    setRightList(optionList.slice(1))
  },[optionList]);

  const getOptionKey = (item: any, index: number) => {
    const primary = item?.[value];
    if (typeof primary === "string" || typeof primary === "number") {
      return String(primary);
    }
    const secondary = item?.[label];
    if (typeof secondary === "string" || typeof secondary === "number") {
      return `${String(secondary)}-${index}`;
    }
    return `ratio-option-${index}`;
  };

  return (
    <>
      {optionList.length > 5 && (
        <div className="app-ratio-grid">
          <div className="left">
            <div
              className={`app-ratio-option ${currentValue === optionList[0][value] ? 'active' : ''}`}
              onClick={() => onSelectCall(optionList[0][value])}
            >
              {optionList[0][value] !== "auto" && <div className="app-ratio-option__example" style={dynamicStyle(optionList[0][value])}></div>}
              <p className="app-ratio-option__text">
                {optionList[0][value] === "auto" && <ScanSearchIcon className="icon app-icon" />}
                {optionList[0][label]}
              </p>
            </div>
          </div>
          <div className="right" style={{gridTemplateColumns: `repeat(${rightList.length / 2}, 1fr)`}}>
            {rightList.map((item, index) => {
              return (
                <div
                  key={getOptionKey(item, index + 1)}
                  className={`app-ratio-option ${currentValue === item[value] ? 'active' : ''}`}
                  onClick={() => onSelectCall(item[value])}
                >
                  {item[value] !== "auto" && <div className="app-ratio-option__example" style={dynamicStyle(item[value])}></div>}
                  <p className="app-ratio-option__text">
                    {item[value] === "auto" && <ScanSearchIcon className="icon app-icon" />}
                    {item[label]}
                  </p>
                </div>
              )
            })}
          </div>
        </div>
      )}
      {optionList.length <= 5 && (
        <div className="app-ratio-group">
          {optionList.map((item, index) => {
            return (
              <div
                key={getOptionKey(item, index)}
                className={`app-ratio-option ${currentValue === item[value] ? 'active' : ''}`}
                onClick={() => onSelectCall(item[value])}
              >
                {item[value] !== "auto" && <div className="app-ratio-option__example" style={dynamicStyle(item[value])}></div>}
                <p className="app-ratio-option__text">
                  {item[value] === "auto" && <ScanSearchIcon className="icon app-icon" />}
                  {item[label]}
                </p>
              </div>
            )
          })}
        </div>
      )}
    </>
  );
}

export default AppRatio;
