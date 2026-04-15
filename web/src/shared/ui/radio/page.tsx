import { createElement } from "react";
import "./page.scss";
function AppRadio({optionList, currentValue, label="label", value="value", onSelectCall}: {optionList: any[], currentValue: string, label?:string, value?:string, onSelectCall: (value:any)=>void}) {
  const getOptionKey = (item: any, index: number) => {
    const primary = item?.[value];
    if (typeof primary === "string" || typeof primary === "number") {
      return String(primary);
    }
    const secondary = item?.[label];
    if (typeof secondary === "string" || typeof secondary === "number") {
      return `${String(secondary)}-${index}`;
    }
    return `radio-option-${index}`;
  };

  return (
    <div className="app-radio-group">
      {optionList.map((item, index) => {
        return (
          <div 
            key={getOptionKey(item, index)}
            className={`app-radio-option ${currentValue === item[value]? 'active': ''}`}
            onClick={()=>onSelectCall(item[value])}
          >
            {item.icon ? createElement(item.icon, { className: "icon app-icon" }) : null}
            {item[label]}
          </div>
        )
      })}
    </div>
  );
}

export default AppRadio;
