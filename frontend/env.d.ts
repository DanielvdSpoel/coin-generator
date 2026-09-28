/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the API. Same-origin `/api` in every environment; override only for odd dev setups. */
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
