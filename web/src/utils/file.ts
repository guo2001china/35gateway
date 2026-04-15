import { message as antMessage, message } from "antd";
import ExcelJS from "exceljs";
import { parseHtmlToFileApi } from "@/api/loadFile";
import { api35Request } from "@/api/api35";
export const loadFile = async (filePath: string): Promise<string> => {
  if (!filePath) return "";
  if (!isLocalAbsolutePath(filePath)) {
    return filePath;
  }

  const token = localStorage.getItem("session_token");
  if (!token) {
    throw new Error("缺少登录态，无法加载本地媒体文件");
  }

  const response = await fetch(`/api/app/media/local?path=${encodeURIComponent(filePath)}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error(`加载本地媒体文件失败: ${response.status}`);
  }

  const blob = await response.blob();
  return URL.createObjectURL(blob);
};

const isLocalAbsolutePath = (value: string) => {
  const normalized = String(value || "").trim();
  if (!normalized) return false;
  if (normalized.startsWith("http://") || normalized.startsWith("https://") || normalized.startsWith("data:") || normalized.startsWith("blob:")) {
    return false;
  }
  if (normalized.startsWith("/")) return true;
  return /^[A-Za-z]:[\\/]/.test(normalized);
};

export const base64ToFile = (dataUrl: string, filename: string): File => {
  const arr = dataUrl.split(",");
  const mime = arr[0].match(/:(.*?);/)?.[1] || "image/png";
  const bstr = atob(arr[1] || "");
  let n = bstr.length;
  const u8arr = new Uint8Array(n);
  while (n--) {
    u8arr[n] = bstr.charCodeAt(n);
  }
  return new File([u8arr], filename, { type: mime });
};

export const getImageDimensions = async (imageUrl: string): Promise<{ width: number; height: number } | null> => {
  return new Promise((resolve, reject) => {
    // 创建一个新的Image对象
    const img = new Image();

    // 设置跨域属性（如果需要）
    img.crossOrigin = 'anonymous';

    // 当图片加载成功时
    img.onload = () => {
      resolve({
        width: img.naturalWidth,
        height: img.naturalHeight
      });
    };

    // 当图片加载失败时
    img.onerror = () => {
      console.error('Failed to load image:', imageUrl);
      resolve(null);
    };

    // 开始加载图片
    img.src = imageUrl;
  });
};
export const openFolder = async (filePath: string) => {
  if (!filePath) {
    antMessage.warning("文件地址不存在");
    return;
  }
  window.open(filePath, "_blank", "noopener,noreferrer");
};

// 将 Univer cellData 格式转换为二维数组
const cellDataTo2DArray = (cellData: any): any[][] => {
  if (!cellData || Object.keys(cellData).length === 0) {
    return [];
  }

  // 找到最大行号和列号
  const rowIndices = Object.keys(cellData).map(k => parseInt(k));
  const maxRow = Math.max(...rowIndices);

  const colIndices: number[] = [];
  Object.values(cellData).forEach((row: any) => {
    Object.keys(row).forEach(k => colIndices.push(parseInt(k)));
  });
  const maxCol = colIndices.length > 0 ? Math.max(...colIndices) : 0;

  // 创建二维数组
  const result: any[][] = Array(maxRow + 1).fill(null).map(() => Array(maxCol + 1).fill(""));

  // 填充数据
  Object.entries(cellData).forEach(([rowKey, row]: any) => {
    const rowNum = parseInt(rowKey);
    Object.entries(row).forEach(([colKey, cell]: any) => {
      const colNum = parseInt(colKey);
      result[rowNum][colNum] = cell?.v ?? "";
    });
  });

  return result;
};

// 检测cellData中是否有图片
const hasImages = (cellData: any): boolean => {
  return Object.values(cellData).some((row: any) =>
    Object.values(row).some((cell: any) => cell?.p?.drawings)
  );
};

const bufferToBase64 = (buffer: ArrayBuffer): string => {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    const chunk = bytes.subarray(i, i + chunkSize);
    binary += String.fromCharCode(...chunk);
  }
  return btoa(binary);
};

const getImageDataFromSource = async (source: string): Promise<{ base64: string; extension: string } | null> => {
  try {
    if (source.startsWith("data:image")) {
      const base64Data = source.split(",")[1];
      const mimeType = source.match(/data:([^;]+)/)?.[1] || "image/png";
      return {
        base64: base64Data,
        extension: mimeType.split("/")[1] || "png",
      };
    }

    const response = await fetch(source);
    if (!response.ok) {
      console.warn(`拉取图片失败：${source}，状态码 ${response.status}`);
      return null;
    }
    const mimeType = response.headers.get("content-type") || "image/png";
    const buffer = await response.arrayBuffer();
    return {
      base64: bufferToBase64(buffer),
      extension: mimeType.split("/")[1] || "png",
    };
  } catch (error) {
    console.error("获取图片数据失败", source, error);
    return null;
  }
};

// 使用 exceljs 导出包含图片的Excel
const exportExcelWithImages = async (
  cellData: any,
  fileName: string,
) => {
  const workbook = new ExcelJS.Workbook();
  const worksheet = workbook.addWorksheet("Sheet1");

  // 填充数据和图片
  for (const [rowKey, rowValue] of Object.entries(cellData) as [string, Record<string, any>][]) {
    const rowNum = parseInt(rowKey);
    const normalizedRow = rowValue || {};
    for (const colKey of Object.keys(normalizedRow)) {
      const cell = normalizedRow[colKey];
      const colNum = parseInt(colKey);
      const cellRef = worksheet.getCell(rowNum + 1, colNum + 1);

      // 设置单元格值
      if (cell?.v !== undefined) {
        cellRef.value = cell.v;
      }

      // 处理图片
      if (cell?.p?.drawings) {
        const drawings = cell.p.drawings;
        for (const [, drawing] of Object.entries(drawings) as any) {
          const source = drawing.source;
          if (!source) continue;
          const imageInfo: any = await getImageDataFromSource(source);
          if (!imageInfo) continue;

          try {
            const imageId = workbook.addImage({
              base64: imageInfo.base64,
              extension: imageInfo.extension,
            });

            const imgWidth = drawing.transform?.width || drawing.docTransform?.size?.width || 64;
            const imgHeight = drawing.transform?.height || drawing.docTransform?.size?.height || 64;

            worksheet.getRow(rowNum + 1).height = Math.max(worksheet.getRow(rowNum + 1).height || 20, imgHeight + 5);
            worksheet.getColumn(colNum + 1).width = Math.max(worksheet.getColumn(colNum + 1).width || 20, (imgWidth + 5) / 7);

            worksheet.addImage(imageId, {
              tl: { col: colNum, row: rowNum },
              ext: { width: imgWidth, height: imgHeight },
            });

          } catch (err) {
            console.error(`Failed to add image to cell [${rowNum}, ${colNum}]:`, err);
          }
        }
      }
    }
  }

  // 自动调整列宽
  worksheet.columns.forEach((col, idx) => {
    col.width = 20;
  });

  // 导出文件
  const buffer = await workbook.xlsx.writeBuffer();
  const blob = new Blob([buffer], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${fileName}.xlsx`;
  link.click();
  URL.revokeObjectURL(url);
  return true;
};

export const exportExcel = async (data: {
  name: string;
  content: string;
}) => {
  try {
    if (!data.content) {
      antMessage.warning("暂无可导出的表格数据");
      return;
    }
    let excelData = JSON.parse(data.content);
    // cellData 格式直接用 exceljs 导出
    if (excelData && typeof excelData === "object" && !Array.isArray(excelData)) {
      const success = await exportExcelWithImages(
        excelData,
        data?.name || "表格导出",
      );
      if (success) {
        antMessage.success("导出成功");
      } else {
        antMessage.error("导出失败，请重试");
      }
    }
  } catch (error: any) {
    console.error("导出失败:", error)
    antMessage.error("导出失败，请重试");
  }
};

// 选择文件
export const selectFile = async (accept?: string[]): Promise<string> => {
  return selectFileWeb(accept);
};

// web端选择文件
export const selectFileWeb = async (accept?: string[]): Promise<string> => {
  return new Promise((resolve, reject) => {
    // 创建input元素
    const input = document.createElement("input");
    input.type = "file";
    // 设置可选参数
    if (accept) {
      input.accept = accept.join(",");
    }
    // 监听文件选择
    input.addEventListener("change", function (e) {
      const files = (e.target as HTMLInputElement).files;
      if (files && files.length > 0) {
        const file = files[0];
        uploadFile(file)
          .then((path: string) => {
            if (path) {
              resolve(path);
            }
          })
          .catch((error: any) => {
            console.error("选择文件失败:", error);
            reject(error);
          });
      } else {
        resolve("");
      }
    });
    // 触发文件选择
    input.click();
  });
}


// 根据文件名转换 contentType（MIME）。浏览器 File.type 已是完整 MIME（如 video/mp4），勿再拼 ext 否则会变成 video/mp4/mp4
const getContentType = (fileName: string, type: string) => {
  if (type && type.includes("/")) return type;
  const ext = (fileName.split(".").pop() || "").toLowerCase();
  return ext ? `${type}/${ext}` : type || "application/octet-stream";
};
export const uploadFile = async (params: File): Promise<string> => {
  const uploadPolicy = await getUploadPolicy(params);
  const formData = new FormData();
  formData.append("key", uploadPolicy.object_key);
  formData.append("policy", uploadPolicy.policy);
  formData.append("OSSAccessKeyId", uploadPolicy.access_key_id);
  formData.append("Signature", uploadPolicy.signature);
  formData.append("success_action_status", uploadPolicy.success_action_status);
  formData.append("Content-Type", uploadPolicy.content_type);
  formData.append("file", params);

  const uploadResp = await fetch(uploadPolicy.upload_url, {
    method: "POST",
    body: formData,
  });

  if (!uploadResp.ok) {
    throw new Error(`上传文件失败: ${uploadResp.status}`);
  }

  const completedFile = await api35Request<Api35FileObject>("/v1/files/complete", {
    method: "POST",
    body: JSON.stringify({
      file_id: uploadPolicy.file_id,
      size: params.size,
      content_type: uploadPolicy.content_type,
      etag: uploadResp.headers.get("etag") || undefined,
    }),
  });

  return completedFile.url || "";
};

type Api35UploadPolicy = {
  file_id: string;
  object_key: string;
  upload_url: string;
  policy: string;
  signature: string;
  access_key_id: string;
  success_action_status: string;
  content_type: string;
};

type Api35FileObject = {
  file_id: string;
  url: string | null;
};

const getUploadPolicy = async (params: { name: string; type: string; size: number }): Promise<Api35UploadPolicy> => {
  const fileName = params.name.split(/[/\\]/).pop() || params.name;
  const contentType = getContentType(params.name, params.type);
  const policy = await api35Request<Omit<Api35UploadPolicy, "content_type">>("/v1/files/upload-policy", {
    method: "POST",
    body: JSON.stringify({
      filename: fileName,
      content_type: contentType,
      size: params.size,
    }),
  });

  return {
    ...policy,
    content_type: contentType,
  };
};

/**
 * 根据文件路径或文件名获取文件类型
 *
 * @param {String} filename - 文件路径或文件名（如：image.jpg 或 https://example.com/image.jpg）
 * @returns {String} - 文件分类类型：'image'|'video'|'audio'|'document'|'file'
 */
export const getCardTypeByFileName = (filename: string) => {
  if (!filename) return "file";

  // 提取扩展名（支持 URL、本地路径、带 query/hash 的远程地址）
  const normalizedFilename = filename
    .split("#")[0]
    .split("?")[0]
    .trim();
  const ext = (normalizedFilename.split(".").pop() || "").toLowerCase();

  const typeMap: { [key: string]: string } = {
    // 图片类型
    jpg: "image_card",
    jpeg: "image_card",
    png: "image_card",
    gif: "image_card",
    bmp: "image_card",
    webp: "image_card",
    svg: "image_card",
    ico: "image_card",
    // 视频类型
    mp4: "video_card",
    avi: "video_card",
    mov: "video_card",
    mkv: "video_card",
    webm: "video_card",
    flv: "video_card",
    wmv: "video_card",
    "3gp": "video_card",
    // 音频类型
    mp3: "audio_card",
    wav: "audio_card",
    aac: "audio_card",
    flac: "audio_card",
    m4a: "audio_card",
    ogg: "audio_card",
    wma: "audio_card",
  };

  return typeMap[ext] || "";
};

export const getFileStreamBlob = async (filePath: string) => {
  try {
    return await fetch(filePath).then((response) => response.blob());
  } catch (error) {
    console.error("加载文件失败:", error);
    return "";
  }
};

// download html to html pdf woord
export const downloadHtmlFile = async (html: string, fileName: string, type = "pdf") => {
  if (!html) {
    message.error('请输入内容');
    return;
  }
  const completeHTML = `<!DOCTYPE html>
    <html lang="zh-CN">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title></title>
        <style>
          body { font-family: Arial, sans-serif; padding: 20px; }
            audio, video { max-width: 100%; margin: 10px 0; }
            table { border-collapse: collapse; margin: 10px 0; }
            td { border: 1px solid #ccc; padding: 8px; }
        </style>
      </head>
    <body>
      ${html}
    </body>
    </html>`;
  // 使用DOMParser解析HTML
  const parser = new DOMParser();
  const doc = parser.parseFromString(completeHTML, 'text/html');
  // 注意：DOMParser 只能解析标准 HTML 标签，若 html 字符串里 video 是自定义组件或带命名空间，querySelectorAll 会匹配不到
  const videos = doc.querySelectorAll('video');
  videos.forEach(video => {
    if (!video.hasAttribute('controls')) {
      video.setAttribute('controls', '');
    }
    video.setAttribute('autoplay', 'true');
    video.setAttribute('muted', 'true');
    video.setAttribute('preload', 'auto');
    if (video.src.includes('https://supra-buddy.oss-cn-beijing.aliyuncs.com/')) {
      video.setAttribute('poster', `${video.src}?x-oss-process=video/snapshot,t_0,f_jpg`);
    }
  });

  const audios = doc.querySelectorAll('audio');
  audios.forEach(audio => {
    if (!audio.hasAttribute('controls')) {
      audio.setAttribute('controls', '');
    }
  });

  // 将修改后的DOM序列化为字符串
  const fixedHTML = new XMLSerializer().serializeToString(doc);
  const data = await parseHtmlToFileApi({
    html: fixedHTML,
    filename: fileName,
    type,
  });
  if (data.success) {
    window.open(data.path, '_blank', 'noopener,noreferrer');
  } else {
    message.error(data.error || '文件转换失败');
  }
};

// 浏览器打开oss文件
export const openOssFile = async (url: string) => {
  if (!url) {
    antMessage.error('文件地址不存在');
    return;
  }
  window.open(url, '_blank', 'noopener,noreferrer');
};
