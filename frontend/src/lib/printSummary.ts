/**
 * Filament slots for the export summary. Same rule as the backend's 3MF writer:
 * slot 1 is the body, each further distinct colour gets the next slot, so the
 * summary names the filament the slicer will show for each number.
 */
import type { CoinConfig, CoinStats, ColorRef, PrintMaterial } from '@/types/coin'

export interface FilamentSlot {
  slot: number
  hex: string
  materials: PrintMaterial[]
  grams: number
}

export function filamentSlots(stats: CoinStats): FilamentSlot[] {
  const slots: FilamentSlot[] = []
  for (const m of stats.materials) {
    const hex = m.color.toLowerCase()
    const slot = slots.find((s) => s.hex === hex)
    if (slot) {
      slot.materials.push(m.material)
      slot.grams += m.grams
    } else {
      slots.push({ slot: slots.length + 1, hex, materials: [m.material], grams: m.grams })
    }
  }
  return slots
}

export function colorRefFor(config: CoinConfig, material: PrintMaterial): ColorRef {
  if (material === 'enamel_front') return config.faces.front.inlay
  if (material === 'enamel_back') return config.faces.back.inlay
  return config.colors.relief
}

/** "0.7" not "0.70", "3.2" not "3.2000000001". */
export function mm(value: number): string {
  return String(Math.round(value * 100) / 100)
}
