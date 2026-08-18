/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DESIGN_PREVIEW?: string;
  readonly VITE_SHOW_LEGACY_LINK?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
