import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'

// 정적 파일 서빙을 위한 플러그인
function serveResultsPlugin() {
  return {
    name: 'serve-results',
    configureServer(server: any) {
      server.middlewares.use((req: any, res: any, next: any) => {
        if (req.url?.startsWith('/results/')) {
          const filePath = path.join(__dirname, '..', req.url);
          if (fs.existsSync(filePath)) {
            res.setHeader('Content-Type', 'application/json');
            fs.createReadStream(filePath).pipe(res);
            return;
          }
        }
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), serveResultsPlugin()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  base: './',
  publicDir: 'public',
  build: {
    outDir: '../dist',
    emptyOutDir: true,
  },
  server: {
    fs: {
      // Allow serving files from parent directory (for results folder)
      allow: ['..'],
    },
  },
})
