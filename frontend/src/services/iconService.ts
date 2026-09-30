import { jsonFetcher } from '@/services/utils/Fetcher'
import type { IconGeometry, Schemas } from '@/types/coin'

type WireTraceResponse = Schemas['TraceResponse']
type CompleteTrace = NonNullable<NonNullable<IconGeometry['source']>['trace']>
/** The server's answer with the geometry completed the way the store holds it. */
export type TraceResponse = Omit<WireTraceResponse, 'geometry'> & { geometry: IconGeometry }
/**
 * The trace knobs as the dialog holds them. `drop_thin_rings` is being added
 * to the backend schema; until the generated type carries it, it lives here.
 */
export type TraceOptions = Schemas['TraceOptions'] & {
  drop_thin_rings?: boolean
  embed_source?: boolean
}

export const DEFAULT_TRACE_OPTIONS: Required<TraceOptions> = {
  threshold: 128,
  simplify: 0.4,
  drop_largest: false,
  inner_disc: null,
  min_area: 0,
  invert: false,
  drop_thin_rings: true,
  embed_source: false,
}

/** Fill the wire type's optional fields so the geometry matches the store's complete shape. */
export function completeGeometry(wire: WireTraceResponse['geometry']): IconGeometry {
  const src = wire.source
  return {
    polygons: wire.polygons.map((p) => ({ exterior: p.exterior, holes: p.holes ?? [] })),
    source: src
      ? {
          filename: src.filename ?? null,
          sha256: src.sha256 ?? null,
          data_url: src.data_url ?? null,
          trace: src.trace
            ? ({
                ...src.trace,
                inner_disc: src.trace.inner_disc ?? null,
                // Tolerates a schema with or without `drop_thin_rings` (default true).
                drop_thin_rings:
                  (src.trace as { drop_thin_rings?: boolean }).drop_thin_rings ?? true,
              } as CompleteTrace)
            : null,
        }
      : null,
  }
}

/** Trace an image (PNG, JPEG or SVG) into icon geometry. Rejects with `ApiError`. */
export async function traceIcon(
  file: File,
  options: TraceOptions,
  signal?: AbortSignal,
): Promise<TraceResponse> {
  const body = new FormData()
  body.append('file', file, file.name)
  body.append('options', JSON.stringify(options))
  const res = await jsonFetcher<WireTraceResponse>('/icons/trace', { method: 'POST', body, signal })
  return { ...res, geometry: completeGeometry(res.geometry) }
}
