export const getLabelByValue = (value: any, list: any) => {
  const matchedLabel = list.find((item:any) => item.value === value)?.label || "";
  return matchedLabel;
}

export const dynamicStyle = (ratio: string) => {
  let res = {
    width: "16px",
    height: "16px"
  };
  const ratioArr: any = ratio.split(":");
  if (ratioArr.length === 2) {
    if (Number(ratioArr[0]) > Number(ratioArr[1])) {
      res = {
        width: "16px",
        height: `${16 / ratioArr[0] * ratioArr[1]}px`
      }
    } else {
      res = {
        height: "16px",
        width: `${16 / ratioArr[1] * ratioArr[0]}px`
      }
    }
  }
  return res;
}
