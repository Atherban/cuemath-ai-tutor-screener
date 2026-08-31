/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the FastAPI backend for HTTP calls. */
  readonly VITE_API_BASE_URL?: string;
  /** Base URL of the FastAPI backend for WebSocket calls. */
  readonly VITE_WS_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}