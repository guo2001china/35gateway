import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const BRAND_ENV = {
  VITE_APP_TITLE: '35m.ai | 你的私有算力中心',
  VITE_FAVICON: '/assets/favicon-32.png',
  VITE_SITE_URL: 'https://35m.ai',
  VITE_APP_DESCRIPTION: '35m.ai 是统一模型控制台，把模型调用、请求日志、账单、充值和设置放进同一处。',
  VITE_APP_KEYWORDS: '35m.ai,AI模型,控制台,API,请求日志,账单,图片生成,视频生成,配音,统一接入',
  VITE_OG_IMAGE: 'https://35m.ai/assets/logo-35m-icon.png',
  VITE_WELCOME_TITLE: '模型控制台',
} as const;

// https://vitejs.dev/config/
// @ts-ignore
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const mergedEnv = { ...BRAND_ENV, ...env };
  const appBase = (mergedEnv.VITE_APP_BASE || '').trim() || (mode === 'development' ? '/' : '/console/');

  return {
    base: appBase,
    define: {
      'import.meta.env.VITE_APP_TITLE': JSON.stringify(mergedEnv.VITE_APP_TITLE),
      'import.meta.env.VITE_FAVICON': JSON.stringify(`${appBase}assets/favicon-32.png`),
      'import.meta.env.VITE_SITE_URL': JSON.stringify(mergedEnv.VITE_SITE_URL),
      'import.meta.env.VITE_APP_DESCRIPTION': JSON.stringify(mergedEnv.VITE_APP_DESCRIPTION),
      'import.meta.env.VITE_APP_KEYWORDS': JSON.stringify(mergedEnv.VITE_APP_KEYWORDS),
      'import.meta.env.VITE_OG_IMAGE': JSON.stringify(mergedEnv.VITE_OG_IMAGE),
      'import.meta.env.VITE_WELCOME_TITLE': JSON.stringify(mergedEnv.VITE_WELCOME_TITLE),       
    },
    plugins: [
      {
        name: 'inject-branding-html',
        transformIndexHtml(html) {
          return html
            .replace(/%VITE_APP_TITLE%/g, mergedEnv.VITE_APP_TITLE)
            .replace(/%VITE_FAVICON%/g, `${appBase}assets/favicon-32.png`)
            .replace(/%VITE_SITE_URL%/g, mergedEnv.VITE_SITE_URL)
            .replace(/%VITE_APP_DESCRIPTION%/g, mergedEnv.VITE_APP_DESCRIPTION)
            .replace(/%VITE_APP_KEYWORDS%/g, mergedEnv.VITE_APP_KEYWORDS)
            .replace(/%VITE_OG_IMAGE%/g, mergedEnv.VITE_OG_IMAGE);
        },
      },
      react(),
    ],
    root: '.',
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    css: {
      preprocessorOptions: {
        scss: {
          api: 'modern-compiler',
        },
      },
    },
    server:
      {
      host: '127.0.0.1',
      port: 5185,
      strictPort: true,
      proxy: {
        '/auth': {
          target: 'http://127.0.0.1:8025',
          changeOrigin: true,
        },
        '/docs': {
          target: 'http://127.0.0.1:8025',
          changeOrigin: true,
        },
        '/me': {
          target: 'http://127.0.0.1:8025',
          changeOrigin: true,
        },
        '/openapi.json': {
          target: 'http://127.0.0.1:8025',
          changeOrigin: true,
        },
        '/site-static': {
          target: 'http://127.0.0.1:8025',
          changeOrigin: true,
        },
        '/v1': {
          target: 'http://127.0.0.1:8025',
          changeOrigin: true,
        },
        '/ws': {
          target: 'ws://127.0.0.1:8025',
          ws: true,
        },
      },      
    },
    build: {
      // Keep build artifacts inside frontend/dist so backend can mount that folder directly
      outDir: 'dist',
      emptyOutDir: true,
      chunkSizeWarningLimit: 1500,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules')) {
              if (id.includes('@blocknote') || id.includes('@mantine')) return 'lib-blocknote';
              if (id.includes('remotion') || id.includes('@remotion')) return 'lib-remotion';
              if (id.includes('exceljs')) return 'lib-exceljs';
              if (id.includes('mermaid')) return 'lib-mermaid';
              if (id.includes('react-markdown') || 
                  id.includes('rehype') || 
                  id.includes('remark') ||
                  id.includes('katex')) {
                return 'lib-markdown';
              }
              return 'vendor';
            }
          }
        }
      }
    },
  }
})
