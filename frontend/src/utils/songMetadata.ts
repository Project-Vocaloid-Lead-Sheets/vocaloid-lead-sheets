import { difficultyCriteria } from '@/types/types'
import type { DifficultyCriterion, DifficultyRanges, NumericRange, Song } from '@/types/types'
import { expandKeySelections } from '@/utils/musicalKeys'

export const difficultyLabels: Record<DifficultyCriterion, string> = {
  melodic: 'Melodic',
  harmonic: 'Harmonic',
  chord: 'Chords',
  form: 'Form',
  overall: 'Overall',
}

export const difficultyDescriptions: Record<DifficultyCriterion, string> = {
  melodic: 'Motion, leaps, accidentals, rhythmic complexity, speed',
  harmonic: 'Complexity of transitions between chords, modulations',
  chord: 'Presence of non-triadic extensions',
  form: 'Structure, irregular phrase lengths, repeats and jumps',
  overall: 'Overall performance difficulty (not necessarily the mean of the above criteria)',
}

export const createDifficultyRanges = (): DifficultyRanges => ({
  melodic: { min: null, max: null },
  harmonic: { min: null, max: null },
  chord: { min: null, max: null },
  form: { min: null, max: null },
  overall: { min: null, max: null },
})

export const cloneDifficultyRanges = (ranges: DifficultyRanges): DifficultyRanges =>
  Object.fromEntries(
    difficultyCriteria.map((criterion) => [criterion, { ...ranges[criterion] }]),
  ) as DifficultyRanges

export const isRangeActive = (range: NumericRange): boolean =>
  range.min !== null || range.max !== null

export const isDifficultyRating = (value: unknown): value is number =>
  typeof value === 'number' && Number.isSafeInteger(value) && value >= 1

export function matchesSongMetadata(
  song: Song,
  includedKeys: string[],
  excludedKeys: string[],
  ranges: DifficultyRanges,
): boolean {
  const keys = song.key ?? []
  if (includedKeys.length && !expandKeySelections(includedKeys).some((key) => keys.includes(key)))
    return false
  // Exclusion wins when a song modulates between included and excluded keys.
  if (expandKeySelections(excludedKeys).some((key) => keys.includes(key))) return false

  return difficultyCriteria.every((criterion) => {
    const range = ranges[criterion]
    if (!isRangeActive(range)) return true
    const rating = song.difficulties?.[criterion]
    return (
      isDifficultyRating(rating) &&
      (range.min === null || rating >= range.min) &&
      (range.max === null || rating <= range.max)
    )
  })
}
