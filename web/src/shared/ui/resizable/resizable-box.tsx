import { forwardRef, useEffect, useImperativeHandle, useState } from "react";
import { ResizableBox, ResizeCallbackData } from "react-resizable"; 
import "./resizable-box.scss";
type Axis = "x" | "y" | "both";
interface Props {
  children: React.ReactNode;
  axis?: Axis;
  minWidth?: number;
  minHeight?: number;
  maxWidth?: number;
  maxHeight?: number;
  initialWidth?: number;
  initialHeight?: number;
  className?: string;
  style?: React.CSSProperties;
  onResize?: (size: { width: number; height: number }) => void;
};
export type ResizableBoxHandle = {
  updateSize: (next: Partial<{ width: number; height: number }>) => void;
};
const ResizableBoxComponent = forwardRef<ResizableBoxHandle, Props>(function ResizableBoxComponent({
  children,
  axis = "both",
  minWidth = 80,
  minHeight = 80,
  maxWidth = Number.MAX_SAFE_INTEGER,
  maxHeight = Number.MAX_SAFE_INTEGER,
  initialWidth,
  initialHeight,
  className,
  style,
  onResize,
}, ref) {
  const [size, setSize] = useState<{ width: number; height: number }>(() => ({
    width: initialWidth ?? 300,
    height: initialHeight ?? 200,
  }));
  // 将 setSize 暴露给下游，通过 ref 转发
  useImperativeHandle(ref, () => ({
    updateSize: (next: Partial<{ width: number; height: number }>) =>
      setSize((curr) => ({
        width: next.width ?? curr.width,
        height: next.height ?? curr.height,
      })),
  }));
  const [resizing, setResizing] = useState(false);
  useEffect(() => {
    if (onResize) onResize(size);
  }, [size, onResize]);
  const resizeHandles =
    axis === "x" ? (["e"] as Array<"e">) : axis === "y" ? (["s"] as Array<"s">) : (["se"] as Array<"se">);
  const minConstraintsNow: [number, number] =
    axis === "x"
      ? [minWidth, size.height]
      : axis === "y"
      ? [size.width, minHeight]
      : [minWidth, minHeight];
  const maxConstraintsNow: [number, number] =
    axis === "x"
      ? [maxWidth, size.height]
      : axis === "y"
      ? [size.width, maxHeight]
      : [maxWidth, maxHeight];
  return (
    <ResizableBox
      width={size.width}
      height={size.height}
      axis={axis}
      minConstraints={minConstraintsNow}
      maxConstraints={maxConstraintsNow}
      resizeHandles={resizeHandles as any}
      className={`react-resizable ${className || ""} ${resizing ? "resizing" : ""}`}
      onResizeStart={() => setResizing(true)}
      onResizeStop={() => setResizing(false)}
      onResize={(_: React.SyntheticEvent, data: ResizeCallbackData) => {
        setSize({ width: data.size.width, height: data.size.height });
      }}
      style={style}
    >
      <div className="resizable-box-content">{children}</div>
    </ResizableBox>
  );
});
export default ResizableBoxComponent;
