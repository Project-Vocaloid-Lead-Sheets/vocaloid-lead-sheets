/**
 * Utility functions for handling PDF URLs, especially Google Drive links
 */

/**
 * Converts a Google Drive sharing URL to an embeddable URL
 * @param url - The Google Drive URL (https://drive.google.com/file/d/FILE_ID/view)
 * @returns The embeddable URL for PDF viewers
 */
export function convertGoogleDriveUrl(url: string): string {
  // Check if it's a Google Drive URL
  const driveMatch = url.match(/https:\/\/drive\.google\.com\/file\/d\/([a-zA-Z0-9_-]+)/)

  if (driveMatch) {
    const fileId = driveMatch[1]
    // Convert to embed URL that works with CORS policies
    return `https://drive.google.com/file/d/${fileId}/preview`
  }

  // If it's not a Google Drive URL, return as-is
  return url
} /**
 * Gets the direct PDF URL for display in PDF viewers
 * @param url - The original PDF URL
 * @returns A URL that can be used directly in PDF embedding components
 */
export function getPdfDisplayUrl(url: string): string {
  if (!url) return ''

  // Convert Google Drive URLs to direct access format
  if (url.includes('drive.google.com')) {
    return convertGoogleDriveUrl(url)
  }

  // For other URLs, return as-is
  return url
}

/**
 * Gets the download URL for a PDF
 * @param url - The original PDF URL
 * @returns A URL that can be used for downloading
 */
export function getPdfDownloadUrl(url: string): string {
  if (!url) return ''

  // For Google Drive URLs, use the download format
  const driveMatch = url.match(/https:\/\/drive\.google\.com\/file\/d\/([a-zA-Z0-9_-]+)/)
  if (driveMatch) {
    const fileId = driveMatch[1]
    return `https://drive.google.com/uc?export=download&id=${fileId}`
  }

  // For other URLs, return as-is
  return url
}

/**
 * Checks if a PDF URL is accessible for embedding
 * @param url - The PDF URL to check
 * @returns Promise<boolean> indicating if the URL is accessible
 */
export async function isPdfUrlAccessible(url: string): Promise<boolean> {
  try {
    const response = await fetch(url, { method: 'HEAD' })
    return response.ok
  } catch (error) {
    console.warn('PDF URL accessibility check failed:', error)
    return false
  }
}
