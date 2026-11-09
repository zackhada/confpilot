/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Dash0 ingest-only browser token. Monitoring is off when this or the endpoint is unset. */
  readonly VITE_DASH0_RUM_TOKEN?: string
  /** Dash0 OTLP over HTTP endpoint for browser telemetry. */
  readonly VITE_DASH0_RUM_ENDPOINT?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
