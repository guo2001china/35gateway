import React, { useState, useRef, ChangeEvent, useEffect } from 'react';
import { Input } from 'antd';

const { TextArea } = Input;

// 定义组件的 Props 接口
interface IntelligentTextAreaProps {
  value?: string;
  onChange?: (e: ChangeEvent<HTMLTextAreaElement>) => void;
  [key: string]: any; // 允许传递任意其他属性
}

const IntelligentTextArea = ({ onChange, value, ...restProps }: IntelligentTextAreaProps) => {
  const [innerValue, setInnerValue] = useState(value || '');
  const isComposingRef = useRef(false); // 标记是否在组合输入中

  // 当外部 value 改变时，同步更新 innerValue
  useEffect(() => {
    setInnerValue(value || '');
  }, [value]);

  const handleCompositionStart = () => {
    isComposingRef.current = true;
  };

  const handleCompositionEnd = (e: any) => {
    isComposingRef.current = false;
    // 组合结束时，手动触发一次 onChange
    if (onChange) {
      const syntheticEvent = {
        ...e,
        target: { ...e.target, value: e.target.value },
        currentTarget: { ...e.currentTarget, value: e.target.value }
      };
      onChange(syntheticEvent as unknown as ChangeEvent<HTMLTextAreaElement>);
    }
  };

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setInnerValue(e.target.value);
    // 只有在非组合输入状态下，才调用外部的 onChange
    if (!isComposingRef.current && onChange) {
      onChange(e);
    }
  };

  return (
    <TextArea
      {...restProps}
      value={innerValue}
      onChange={handleChange}
      onCompositionStart={handleCompositionStart}
      onCompositionEnd={handleCompositionEnd}
    />
  );
};

export default IntelligentTextArea;