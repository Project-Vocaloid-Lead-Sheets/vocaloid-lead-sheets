export type Instrument = 'C' | 'Bb' | 'Eb' | 'F' | 'G' | 'Vocals' | 'Alto' | 'Bass'
export const instruments: Instrument[] = ['C', 'Bb', 'Eb', 'F', 'G', 'Vocals', 'Alto', 'Bass']

export interface Song {
  title: string // "World is Mine"
  alternativeNames?: string[] // "ワールドイズマイン"
  producer: string // "ryo"
  additionalProducers?: string[]
  singer: string // "Hatsune Miku"
  additionalVoices?: string[]
  releaseDate: string // "20070831"
  bpm: number // 140
  labels?: string[] // "Project Sekai, Project Diva"
  transcriber?: string // Transcriber name
  videoLinks?: Partial<Record<string, string>> // { "YouTube" : "youtube.com/..."}
  links?: Partial<Record<Instrument, string>> // Direct Google Drive links (reference only)
  pdfChecksums?: Partial<Record<Instrument, string>> // Drive md5 checksums for change detection
  pdfs: Partial<Record<Instrument, string>> // Maps instrument/key to PDF URL
  status?: string // "completed" or "under review"
  syncedAt?: string // ISO 8601 timestamp when sync script last processed this song
  updatedAt?: string // ISO 8601 timestamp when content/status last changed (for recent activity)
}
