import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current directory
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [tailwindcss(), react()],
    
    // Server configuration
    server: {
      host: true, // Listen on all addresses (important for Docker)
      port: parseInt(env.VITE_PORT) || 5173, // Use env variable or default
      strictPort: true, // Exit if port is already in use
      allowedHosts: [
        '.ngrok-free.app', // Allows any subdomain of ngrok-free.app
        'localhost',
        '127.0.0.1'
      ],
      
      // Watch options for Docker
      watch: {
        usePolling: env.VITE_USE_POLLING === 'true', // Enable for Docker on Windows/WSL
        interval: parseInt(env.VITE_POLLING_INTERVAL) || 100 // Polling interval
      }
    },
    
    // Preview configuration (for production build preview)
    preview: {
      host: true,
      port: parseInt(env.VITE_PREVIEW_PORT) || 4173,
      allowedHosts: [
        '.ngrok-free.app',
        'localhost',
        '127.0.0.1'
      ]
    },
    
    // Build configuration
    build: {
      outDir: 'dist',
      sourcemap: mode === 'development', // Enable sourcemaps only in development
      minify: mode === 'production' ? 'esbuild' : false,
      
      // Chunking optimization
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ['react', 'react-dom'],
            router: ['react-router-dom'],
            ui: ['@headlessui/react', '@heroicons/react'],
            utils: ['axios', 'lodash', 'date-fns']
          },
          chunkFileNames: 'assets/js/[name]-[hash].js',
          entryFileNames: 'assets/js/[name]-[hash].js',
          assetFileNames: (assetInfo) => {
            const extType = assetInfo.name.split('.')[1];
            if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(extType)) {
              return 'assets/images/[name]-[hash][extname]';
            }
            if (/css/i.test(extType)) {
              return 'assets/css/[name]-[hash][extname]';
            }
            return 'assets/[name]-[hash][extname]';
          }
        }
      },
      
      // Optimize dependencies
      optimizeDeps: {
        include: ['react', 'react-dom', 'react-router-dom']
      }
    },
    
    // Environment variables
    define: {
      __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
      __BUILD_TIME__: JSON.stringify(new Date().toISOString())
    },
    
    // CSS configuration
    css: {
      devSourcemap: mode === 'development',
      modules: {
        localsConvention: 'camelCase'
      }
    },
    
    // Resolve configuration
    resolve: {
      alias: {
        '@': '/src',
        '@components': '/src/components',
        '@pages': '/src/pages',
        '@utils': '/src/utils',
        '@hooks': '/src/hooks',
        '@assets': '/src/assets'
      }
    }
  }
})