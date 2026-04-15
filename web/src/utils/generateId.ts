import { nanoid, customAlphabet } from 'nanoid';

/**
 * 生成唯一 ID (使用 nanoid)
 * @param {number} size - ID 长度，默认为 21
 * @returns {string} 返回一个唯一的 ID 字符串
 * @example
 * const id = generateId(); // "V1StGXR8_Z5jdHi6B-myT"
 * const shortId = generateId(10); // "V1StGXR8_Z"
 */
export function generateId(size?: number): string {
  return nanoid(size);
}

/**
 * 生成数字 ID (仅包含数字)
 * @param {number} size - ID 长度，默认为 10
 * @returns {string} 返回一个仅包含数字的 ID 字符串
 * @example
 * const id = generateNumericId(); // "1234567890"
 */
export function generateNumericId(size: number = 10): string {
  const numericNanoid = customAlphabet('0123456789', size);
  return numericNanoid();
}

/**
 * 生成可读 ID (仅包含字母和数字，不包含易混淆字符)
 * @param {number} size - ID 长度，默认为 16
 * @returns {string} 返回一个易读的 ID 字符串
 * @example
 * const id = generateReadableId(); // "A3B7K9M2P4Q8T6Y1"
 */
export function generateReadableId(size: number = 16): string {
  // 移除了容易混淆的字符: 0, O, I, l, 1
  const readableNanoid = customAlphabet('23456789ABCDEFGHJKLMNPQRSTUVWXYZ', size);
  return readableNanoid();
}

/**
 * 生成 UUID v4 格式的 ID (兼容旧代码)
 * @returns {string} 返回一个 UUID v4 格式的字符串
 * @example
 * const id = generateUUID(); // "550e8400-e29b-41d4-a716-446655440000"
 */
export function generateUUID(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }

  // 降级方案
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
