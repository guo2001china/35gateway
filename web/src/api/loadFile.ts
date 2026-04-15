import { request } from './http';

export interface LoadFileData {
  success: boolean;
  path: string;
  filename: string;
  base64: string;
  error: string | null;
}

export type LoadFileRequest = {
  html: string;
  filename: string;
  type: string | 'pdf' | 'html' | 'word';
}

export async function parseHtmlToFileApi(data: LoadFileRequest) {
  return request.post<LoadFileData>('/api/bridge/parse_html_to_file', data);
}