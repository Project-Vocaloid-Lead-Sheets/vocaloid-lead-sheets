export type StoredSettings = {
  version: number
  sortBy?: string
  groupBy?: string
  selectedLabels?: string[]
  selectedProducers?: string[]
  selectedSingers?: string[]
  dateRange?: { start: string; end: string }
  lengthRange?: { min: number | null; max: number | null }
  lengthFilterSource?: 'full' | 'tv' | 'either'
  underReviewViewEnabled?: boolean
  selectedInstrument?: string
  useTvSize?: boolean
}

export const SETTINGS_KEY = 'project_vls_user_settings'
export const SCHEMA_VERSION = 2

export function readUserSettings(): StoredSettings | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = localStorage.getItem(SETTINGS_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as StoredSettings
    if (!parsed || parsed.version !== SCHEMA_VERSION) {
      // Schema changed or invalid -> reset
      localStorage.removeItem(SETTINGS_KEY)
      return null
    }
    return parsed
  } catch (err) {
    // If parse fails, clear the key and return null
    try {
      localStorage.removeItem(SETTINGS_KEY)
    } catch {}
    return null
  }
}

export function writeUserSettings(partial: Partial<StoredSettings>): void {
  if (typeof window === 'undefined') return
  try {
    const existing = readUserSettings() || { version: SCHEMA_VERSION }
    const merged = { ...existing, ...partial, version: SCHEMA_VERSION }
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(merged))
  } catch (err) {
    // ignore write errors (e.g., quota)
    // Logging is helpful but avoid throwing

    console.warn('Failed to write user settings to localStorage', err)
  }
}
