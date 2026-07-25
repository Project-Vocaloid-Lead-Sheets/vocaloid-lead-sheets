/**
 * Generate a URL-friendly slug from a song title
 * Rules:
 * - Convert to lowercase
 * - Replace non-URL-safe special characters between words with dashes
 * - Omit apostrophes without inserting dashes
 * - Remove non-URL-safe characters at beginning/end
 * - Replace multiple spaces/dashes with single dash
 * - Trim leading/trailing dashes
 *
 * URL-safe characters for slugs: a-z, 0-9, and hyphens (-)
 */
export function generateSongSlug(title: string): string {
  return (
    title
      .toLowerCase()
      // Remove apostrophes without inserting dashes
      .replace(/['’]/g, '')
      // Replace any non-URL-safe character with dash or empty based on context
      .replace(/[^a-z0-9-]/g, (match, offset, string) => {
        // Check if the non-URL character is between two URL-safe word characters
        const before = offset > 0 ? string[offset - 1] : ''
        const after = offset < string.length - 1 ? string[offset + 1] : ''
        const isBeforeWord = /[a-z0-9]/i.test(before)
        const isAfterWord = /[a-z0-9]/i.test(after)

        // If between two words, replace with dash, otherwise remove
        return isBeforeWord && isAfterWord ? '-' : ''
      })
      // Replace multiple consecutive dashes with single dash
      .replace(/-+/g, '-')
      // Remove leading/trailing dashes
      .replace(/^-+|-+$/g, '')
  )
}
