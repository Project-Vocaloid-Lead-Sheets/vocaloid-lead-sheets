import type { LocationQueryRaw } from 'vue-router'
import type { Instrument } from '@/types/types'

/**
 * Normalize TV size query parameter from route.query
 * Returns: string (if valid), null (if explicitly null), or undefined (if missing/invalid)
 */
export const normalizeTvSizeQuery = (rawTvSize: unknown): string | null | undefined => {
  if (typeof rawTvSize === 'string') return rawTvSize
  if (rawTvSize === null) return null
  if (Array.isArray(rawTvSize) && typeof rawTvSize[0] === 'string') return rawTvSize[0]
  return undefined
}

/**
 * Normalize transposition/instrument query parameter from route.query
 * Returns: valid Instrument, or null if missing/invalid
 */
export const normalizeTranspositionQuery = (
  rawTransposition: unknown,
  validInstruments: Instrument[],
): Instrument | null => {
  if (typeof rawTransposition === 'string' && validInstruments.includes(rawTransposition as any)) {
    return rawTransposition as Instrument
  }
  return null
}

/**
 * Build a clean query object with only non-default parameters
 * Default: transposition='C', tv_size=undefined
 */
export const buildCleanQuery = (
  transposition: Instrument | null | undefined,
  tvSize: string | null | undefined,
): LocationQueryRaw => {
  const query: LocationQueryRaw = {}

  // Only include transposition if it's not the default 'C'
  if (transposition && transposition !== 'C') {
    query.transposition = transposition
  }

  // Only include tv_size if it's defined (including null for explicit removal)
  if (tvSize !== undefined) {
    query.tv_size = tvSize
  }

  return query
}

/**
 * Check if two query param sets are semantically equivalent
 * Since buildCleanQuery only includes non-default params, we compare by:
 * - Any transposition in current must match expected's transposition
 * - Any tv_size in current must match expected's tv_size
 * - No unexpected keys should be in current
 */
export const areQueriesEquivalent = (
  current: Record<string, any>,
  expected: LocationQueryRaw,
): boolean => {
  // Check transposition - can be string, array, or missing
  const currentTranspositionStr =
    typeof current.transposition === 'string'
      ? current.transposition
      : Array.isArray(current.transposition) && typeof current.transposition[0] === 'string'
        ? current.transposition[0]
        : undefined

  const expectedTranspositionStr =
    typeof expected.transposition === 'string' ? expected.transposition : undefined

  if (currentTranspositionStr !== expectedTranspositionStr) return false

  // Check tv_size - can be string, null, array, or missing
  const currentTvSizeValue = normalizeTvSizeQuery(current.tv_size)
  const expectedTvSizeValue = expected.tv_size

  if (currentTvSizeValue !== expectedTvSizeValue) return false

  // Check for unexpected keys
  const unexpectedKeys = Object.keys(current).filter(
    (key) => key !== 'transposition' && key !== 'tv_size',
  )
  if (unexpectedKeys.length > 0) return false

  return true
}
