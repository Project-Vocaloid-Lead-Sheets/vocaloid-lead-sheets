// utils/jsonLoader.ts
import type { Song } from '@/types/types'

import { SONG_MANIFEST } from './songManifest'

// Use Vite's import.meta.glob to dynamically import all JSON files in the data directory (relative to this file)
const songFiles = import.meta.glob('../data/*.json')

/**
 * Load all JSON song files from the data directory
 */
export async function loadAllSongs(): Promise<Song[]> {
  const songs: Song[] = []
  try {
    const songImports = await Promise.allSettled(
      SONG_MANIFEST.map((filename) => {
        // The key in songFiles will be like '../data/filename.json'
        const key = `../data/${filename}`
        const importer = songFiles[key]
        if (importer) {
          return importer()
        } else {
          return Promise.reject(new Error(`No import found for ${filename}`))
        }
      }),
    )
    songImports.forEach((result, index) => {
      if (result.status === 'fulfilled') {
        const song = (result.value as { default: Song }).default
        songs.push(song)
        console.log(`✅ Loaded ${SONG_MANIFEST[index]}`)
      } else {
        console.error(`❌ Failed to load ${SONG_MANIFEST[index]}:`, result.reason)
      }
    })
  } catch (error) {
    console.error('Failed to load songs:', error)
  }
  console.log(`📄 Total JSON files loaded: ${songs.length}/${SONG_MANIFEST.length}`)
  return songs
}

/**
 * Load a specific song by filename
 */
export async function loadSong(filename: string): Promise<Song | null> {
  try {
    // Check if the filename exists in the manifest
    if (!SONG_MANIFEST.includes(filename as any)) {
      console.warn(`Song file not found in manifest: ${filename}`)
      return null
    }
    const key = `../data/${filename}`
    const importer = songFiles[key]
    if (!importer) {
      console.warn(`No import function found for: ${filename}`)
      return null
    }
    const songModule = await importer()
    return (songModule as { default: Song }).default
  } catch (error) {
    console.error(`Failed to load song ${filename}:`, error)
    return null
  }
}

/**
 * Load all available song filenames from the manifest
 * This is automatically updated based on available JSON files
 */
export function getAvailableSongFiles(): string[] {
  return [...SONG_MANIFEST]
}
