import { create } from 'zustand'
import { Node } from "@xyflow/react";
type CopyCardDataType = Record<string, any> | null;

const useCopyStore = create<{ 
  copyCardData: CopyCardDataType;
  setCopyCardData: (data: CopyCardDataType) => void;
  clearCopyCardData: () => void;
  selectedNodes: Node[];
  setSelectedNodes: (data: Node[]) => void;
}>((set) => ({
  copyCardData: null,
  setCopyCardData: (data) => set(() => ({ copyCardData: data })),
  clearCopyCardData: () => set(() => ({ copyCardData: null })),
  selectedNodes: [],
  setSelectedNodes: (data) => set(() => ({ selectedNodes: data })),  
}))

export { useCopyStore }
