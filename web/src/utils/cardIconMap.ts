import { createElement, type ComponentType } from "react";
import {
  AudioLinesIcon,
  BoxesIcon,
  ClapperboardIcon,
  FileTextIcon,
  ImageIcon,
  type AppIconProps,
} from "@/shared/ui/icon";

export const CardIconMap: Record<string, ComponentType<AppIconProps>> = {
  text_card: FileTextIcon,
  image_card: ImageIcon,
  video_card: ClapperboardIcon,
  audio_card: AudioLinesIcon,
  group_card: BoxesIcon,
};

export const renderCardIcon = (
  cardType: string,
  className?: string,
  props?: AppIconProps
) => {
  const Icon = CardIconMap[cardType] || FileTextIcon;
  return createElement(Icon, { className, ...props });
};

export const CardTextMap = {
    text_card: '文本', // 文本卡片
    image_card: "图片", // 图片卡片
    video_card: "视频", // 视频卡片
    audio_card: "配音", // 配音卡片
    group_card: "分组", // 分组卡片
};
