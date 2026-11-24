// Each pair shares a key signature; negative counts are flats and positive counts are sharps.
const keyPairs = [
  ['Cb major', 'Ab minor'],
  ['Gb major', 'Eb minor'],
  ['Db major', 'Bb minor'],
  ['Ab major', 'F minor'],
  ['Eb major', 'C minor'],
  ['Bb major', 'G minor'],
  ['F major', 'D minor'],
  ['C major', 'A minor'],
  ['G major', 'E minor'],
  ['D major', 'B minor'],
  ['A major', 'F# minor'],
  ['E major', 'C# minor'],
  ['B major', 'G# minor'],
  ['F# major', 'D# minor'],
  ['C# major', 'A# minor'],
] as const

export const musicalKeys = keyPairs.flatMap((pair, index) =>
  pair.map((name) => ({ name, accidentals: index - 7 })),
)
export const allMusicalKeys: string[] = musicalKeys.map((key) => key.name).sort()
const signatures = new Map<string, number>(musicalKeys.map((key) => [key.name, key.accidentals]))

export function describeKey(key: string): string {
  const count = signatures.get(key)
  if (count === undefined)
    return isMusicalKeyQuery(key) ? `${filterMusicalKeys(key).length} matching keys` : ''
  if (count === 0) return '0 sharps/flats'
  return `${Math.abs(count)} ${count < 0 ? 'flat' : 'sharp'}${Math.abs(count) === 1 ? '' : 's'}`
}

const numberWords = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven']
const normalize = (value: string) =>
  value.toLowerCase().replace(/♭/g, 'b').replace(/♯/g, '#').trim()

function normalizeQueryTerm(input: string): string {
  return normalize(input)
    .replace(/≤/g, '<=')
    .replace(/≥/g, '>=')
    .replace(/^(fewer than|less than)\s+/, '<')
    .replace(/^(at most|up to)\s+/, '<=')
    .replace(/^more than\s+/, '>')
    .replace(/^at least\s+/, '>=')
    .replace(/\b(zero|one|two|three|four|five|six|seven)\b/g, (word) =>
      String(numberWords.indexOf(word)),
    )
    .replace(/^no\s+/, '0 ')
}

type AccidentalQuery = { operator: string; limit: number; kind: 'flats' | 'sharps' | 'both' }

function parseAccidentalQuery(input: string): AccidentalQuery | null {
  const match = normalizeQueryTerm(input).match(/^(<=|>=|<|>|=)?\s*(\d+)\s*(.*)$/)
  if (!match) return null
  const [, operator = '', rawLimit, rawKind] = match
  const limit = Number(rawLimit)
  if (!Number.isSafeInteger(limit)) return null
  const suffix = rawKind.replace(/\s*\/\s*/g, '/')
  let kind: AccidentalQuery['kind']
  if (!suffix) kind = 'both'
  else if (
    suffix.includes('/') &&
    ['sharps/flats', 'flats/sharps', 'sharp/flat', 'flat/sharp'].some((name) =>
      name.startsWith(suffix),
    )
  )
    kind = 'both'
  else if ('sharps'.startsWith(suffix)) kind = 'sharps'
  else if ('flats'.startsWith(suffix)) kind = 'flats'
  else if (['symbols', 'accidentals'].some((name) => name.startsWith(suffix))) kind = 'both'
  else return null
  return { operator, limit, kind }
}

function matchesKeyQuery(key: string, input: string): boolean {
  const term = normalizeQueryTerm(input)
  const query = parseAccidentalQuery(input)
  const count = signatures.get(key)
  if (query) {
    if (count === undefined) return false
    const { operator, limit, kind } = query
    // "<2 flats" means zero or one flat, rather than sharp signatures.
    if (kind === 'flats' && count > 0) return false
    if (kind === 'sharps' && count < 0) return false
    const actual = Math.abs(count)
    switch (operator) {
      case '<':
        return actual < limit
      case '<=':
        return actual <= limit
      case '>':
        return actual > limit
      case '>=':
        return actual >= limit
      default:
        return actual === limit
    }
  }
  if (/^flats?$/.test(term)) return count !== undefined && count < 0
  if (/^sharps?$/.test(term)) return count !== undefined && count > 0
  return normalize(key).includes(term)
}

const queryTerms = (query: string): string[] =>
  query
    .split(/[,;]|\bor\b/i)
    .map((term) => term.trim())
    .filter(Boolean)

/** Complete count expressions so suggestions and selected tags always have a full name. */
export function completeKeyQuery(query: string): string | null {
  const terms = queryTerms(query)
  if (!terms.length) return null
  const completed: string[] = []
  for (const term of terms) {
    const parsed = parseAccidentalQuery(term)
    if (parsed) {
      const { operator, limit, kind } = parsed
      const name = kind === 'both' ? 'sharps/flats' : limit === 1 ? kind.slice(0, -1) : kind
      completed.push(`${operator}${limit} ${name}`)
    } else {
      const normalized = normalizeQueryTerm(term)
      if (!/^(flats?|sharps?|major|minor)$/.test(normalized)) return null
      completed.push(normalized)
    }
  }
  return completed.join(', ')
}

/** Recognize expressions separately from individual key names and ordinary search text. */
export const isMusicalKeyQuery = (query: string): boolean => completeKeyQuery(query) !== null

export function filterMusicalKeys(query: string, keys: string[] = allMusicalKeys): string[] {
  const terms = queryTerms(query)
  if (!terms.length) return [...keys]
  return keys.filter((key) => terms.some((term) => matchesKeyQuery(key, term)))
}

export function getKeyQueryOption(query: string, keys: string[]): string | null {
  const completed = completeKeyQuery(query)
  return completed && filterMusicalKeys(completed, keys).length ? completed : null
}

export const normalizeKeySelections = (selections: string[]): string[] => [
  ...new Set(selections.map((selection) => completeKeyQuery(selection) ?? selection)),
]

export function expandKeySelections(selections: string[]): string[] {
  return [
    ...new Set(
      selections.flatMap((selection) =>
        isMusicalKeyQuery(selection) ? filterMusicalKeys(selection) : [selection],
      ),
    ),
  ]
}
