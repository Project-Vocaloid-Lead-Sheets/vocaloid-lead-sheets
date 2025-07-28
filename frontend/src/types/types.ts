export type Instrument = 'C' | 'Bb' | 'Eb' | 'F' | 'G' | 'Vocals' | 'Alto' | 'Bass' | 'Percussion'
export const instruments: Instrument[] = [
  'C',
  'Bb',
  'Eb',
  'F',
  'G',
  'Vocals',
  'Alto',
  'Bass',
  'Percussion',
]

export interface Song {
  title: string // "World is Mine"
  alternativeNames?: string[] // "ワールドイズマイン"
  producer: string // "ryo"
  additionalProducers?: string[]
  singer: string // "Hatsune Miku"
  additionalVoices?: string[]
  releaseDate: string // "20070831"
  labels?: string[] // "Project Sekai, Project Diva"
  transcriber?: string // Transcriber name
  videoLinks?: Partial<Record<string, string>> // { "YouTube" : "youtube.com/..."}
  pdfs: Partial<Record<Instrument, string>> // Maps instrument/key to PDF URL
}
