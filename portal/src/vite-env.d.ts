/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ADMIN_PASSWORD?: string;
  readonly VITE_TELEGRAM_BOT_TOKEN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
