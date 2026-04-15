import "./blocknoteEditor.scss"
import React, { useEffect, useRef, useImperativeHandle, useCallback, useMemo } from "react";
import { MantineProvider } from "@mantine/core";
import "@blocknote/mantine/style.css";
// import "@mantine/core/styles.css";
import "@blocknote/core/fonts/inter.css";
import type { Block } from "@blocknote/core";
import { zh } from "@blocknote/core/locales";
import { useCreateBlockNote } from "@blocknote/react";
import { BlockNoteView } from "@blocknote/mantine";

import { uploadFile as uploadFileUtil } from "@/utils/file";
import { debounceFn } from "@/utils/debounceThrottle";

export type BlockNoteEditorRef = {
  getHTML: () => Promise<string>;
  getMarkdown: () => Promise<string>;
  getBlocks: () => Block[];
};

// 定义初始化数据接口
export interface BlockNoteInitialData {
  eidtorBlocks?: Block[];
  markdown?: string;
}

type BlockNoteEditorProps = {
  initialData?: BlockNoteInitialData;
  editable?: boolean;
  onChange?: (data: BlockNoteInitialData) => void;
};

// 自定义 BlockNoteEditor 组件
// 用于在 React 中使用 BlockNote 编辑器
// 支持初始化 Markdown 内容、可编辑状态和 onChange 回调
export const BlockNoteEditor = React.forwardRef<BlockNoteEditorRef, BlockNoteEditorProps>(({ initialData, editable = true, onChange }, ref) => {
  const lastAppliedMarkdownRef = useRef<string | null>(null);  

  // 使用 useMemo 缓存 options，避免每次 render 都重新创建 editor 实例导致 history 丢失
  const editorOptions = useMemo(() => ({
    dictionary: {
      ...zh,
      placeholders: {
        ...zh.placeholders,
        default: "输入 '/' 呼出命令菜单...",
      },
    },
    uploadFile: async (file: File) => {
      const res = await uploadFileUtil(file);
      return res;
    }
  }), []);

  const editor = useCreateBlockNote(editorOptions);

  useEffect(() => {
    (async () => {
      const { eidtorBlocks, markdown } = initialData || {};

      if (!eidtorBlocks && !markdown) return;
      if (lastAppliedMarkdownRef.current === markdown) return;

      if (Array.isArray(eidtorBlocks) && eidtorBlocks.length > 0 && markdown) {
        const markdownContent = await editor.blocksToMarkdownLossy(eidtorBlocks);
        if (markdownContent !== markdown) {
          const newBlocks = await editor.tryParseMarkdownToBlocks(markdown);
          await editor.replaceBlocks(editor.document, newBlocks);
        } else {
          await editor.replaceBlocks(editor.document, eidtorBlocks);
        }
      } else if (markdown) {
        const markdownBlocks = await editor.tryParseMarkdownToBlocks(markdown);
        editor.replaceBlocks(editor.document, markdownBlocks);
      }
      const markdownContent = await editor.blocksToMarkdownLossy(editor.document);
      const blocksContent = editor.document;
      lastAppliedMarkdownRef.current = markdownContent || "";
      // 触发 onChange 回调 默认返回 markdown 内容和 blocks 内容
      onChange?.({ markdown: markdownContent || "", eidtorBlocks: blocksContent });
    })();
  }, [editor, initialData]);

  // 导出 HTML 和 Markdown 内容
  useImperativeHandle(ref, () => ({
    getHTML: async () => editor.blocksToHTMLLossy(editor.document),
    getMarkdown: async () => editor.blocksToMarkdownLossy(editor.document),
    getBlocks: () => editor.document,
  }), [editor]);

  // 注册 onChange 回调
  useEffect(() => {
    const unsubscribe = editor.onChange(debounceFn(async () => {
      const markdownContent = await editor.blocksToMarkdownLossy(editor.document);
      if (lastAppliedMarkdownRef.current === markdownContent) return;

      lastAppliedMarkdownRef.current = markdownContent;
      // 触发 onChange 回调 默认返回 markdown 内容和 blocks 内容
      onChange?.({ markdown: markdownContent || "", eidtorBlocks: editor.document });
    }));
    return () => {
      // @ts-ignore
      unsubscribe?.();
    };
  }, [editor, onChange]);

  const [nodrag, setNodrag] = React.useState(false);

  return (
    <MantineProvider defaultColorScheme="light">
      <div
        className={`blocknote-wrapper ${nodrag ? 'nodrag cursor-text' : ''} ${editable ? "" : " blocknote-wrapper--readonly"}`}
        onDoubleClick={() => {
          setNodrag(true);
          editable && (editor.isEditable = true);
        }}
        onBlur={() => {
          setNodrag(false);
          editable && (editor.isEditable = false);
        }}
      >
        <BlockNoteView
          sideMenu={false}
          editable={editable}
          editor={editor}          
          theme="light"
        />        
      </div>
    </MantineProvider>
  );
});

export default BlockNoteEditor;
