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
  pdfs: Partial<Record<Instrument, string>> // Maps instrument/key to PDF URL
  status?: string // "completed" or "under review"
  syncedAt?: string // ISO 8601 timestamp of when song was last synced/added
}
