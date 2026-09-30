import type { Filament, FilamentVersion, FontInfo, Preset, Template } from '@/types/coin'
import { jsonFetcher } from '@/services/utils/Fetcher'

export const getFonts = () => jsonFetcher<FontInfo[]>('/fonts')
export const getFilaments = () => jsonFetcher<Filament[]>('/filaments')
export const getFilamentVersion = () => jsonFetcher<FilamentVersion>('/filaments/version')
export const getPresets = () => jsonFetcher<Preset[]>('/presets')
export const getTemplates = () => jsonFetcher<Template[]>('/templates')
