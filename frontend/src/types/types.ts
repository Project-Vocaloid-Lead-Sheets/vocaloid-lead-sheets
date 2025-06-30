export type Instrument = 'C' | 'Bb' | 'Eb' | 'F' | 'G' | 'Alto' | 'Bass' | 'Vocals'
export const instruments: Instrument[] = ['C', 'Bb', 'Eb', 'F', 'G', 'Alto', 'Bass', 'Vocals']

//TODO: Add support for flexible labels and video links
export interface Song {
  title: string // "World is Mine"
  additionalTitles?: string[] // "ワールドイズマイン"
  producer: string // "ryo"
  additionalProducers?: string[]

  singer: string // "Hatsune Miku"

  additionalSingers?: string[]

  releaseDate: string // "20070831"
  labels?: string[] // "Project Sekai, Project Diva"
  videoLinks?: Partial<Record<string, string>> // { "YouTube" : "youtube.com/..."}
  pdfs: Partial<Record<Instrument, string>> //OPTIONAL: Make PDF its own type with instrument, source, transcriber, and other sheet-specific metadata
}
