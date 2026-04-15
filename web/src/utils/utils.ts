
// 判断两个矩形是否重叠
export const isRectanglesOverlap = (
  rect1: { x: number; y: number; width: number; height: number },
  rect2: { x: number; y: number; width: number; height: number }
): boolean => {
  return !(
    rect1.x + rect1.width < rect2.x ||  // rect1 在 rect2 左边
    rect2.x + rect2.width < rect1.x ||  // rect2 在 rect1 左边
    rect1.y + rect1.height < rect2.y || // rect1 在 rect2 上方
    rect2.y + rect2.height < rect1.y    // rect2 在 rect1 下方
  );
};
export const cardSizeMap = (type?: string):{width: number, height: number} => {
  let res:{width: number, height: number} = {
    width: 360,
    height: 260
  }
  switch (type) {
    case 'text_card':
    case 'audio_card':
      res.height = 164;
      break
    default:
      break
  }
  return res;
};
