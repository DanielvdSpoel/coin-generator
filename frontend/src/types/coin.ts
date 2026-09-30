/**
 * The design as the app holds it: the generated `CoinConfig` with every field present.
 *
 * The OpenAPI schema marks fields with defaults as optional, which is right on the
 * wire but wrong for the store, where a loaded design always has every field. A
 * complete config is assignable to the wire type, so services pass it through.
 */
import type { components } from '@/types/api'

export type Schemas = components['schemas']

type Complete<T> = T extends unknown[]
  ? { [K in keyof T]: Complete<T[K]> }
  : T extends object
    ? { [K in keyof T]-?: Complete<Exclude<T[K], undefined>> }
    : T

export type WireCoinConfig = Schemas['CoinConfig']
export type ColorRef = Schemas['ColorRef']
type CompleteConfig = Complete<WireCoinConfig>
type CompleteFace = CompleteConfig['faces']['front']
/** A colour is either/or, so it keeps the wire shape rather than being completed. */
export type FaceConfig = Omit<CompleteFace, 'inlay'> & { inlay: ColorRef }
export type CoinConfig = Omit<CompleteConfig, 'colors' | 'faces'> & {
  colors: { relief: ColorRef }
  faces: { front: FaceConfig; back: FaceConfig }
}
export type TextConfig = FaceConfig['top_text']
export type FontRef = CoinConfig['font']
export type CustomFont = Schemas['CustomFont']
export type IconPlacement = Exclude<FaceConfig['icon'], null>
export type IconGeometry = IconPlacement['geometry']
export type IconPolygon = IconGeometry['polygons'][number]
export type Point = IconPolygon['exterior'][number]
export type FaceName = 'front' | 'back'
export type TextSlot = 'top_text' | 'bottom_text'

export type Filament = Schemas['FilamentDTO']
export type FontInfo = Schemas['FontDTO']
export type Preset = Schemas['PresetDTO']
export type Template = Schemas['TemplateDTO']
export type Warning = Schemas['WarningDTO']
export type ValidateResponse = Schemas['ValidateResponse']
export type ExportFormat = Schemas['ExportBody']['format']

export const FACES: readonly FaceName[] = ['front', 'back']
export const TEXT_SLOTS: readonly TextSlot[] = ['top_text', 'bottom_text']

/** Design units across the coin (decision D13). */
export const DESIGN_DIAMETER = 320
export const MAX_TEXT_LENGTH = 40
