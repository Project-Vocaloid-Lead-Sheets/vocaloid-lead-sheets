export type Instrument = 'C' | 'Bb' | 'Eb' | 'F' | 'G' | 'Alto' | 'Bass' | 'Vocals'
export const instruments: Instrument[] = ['C', 'Bb', 'Eb', 'F', 'G', 'Alto', 'Bass', 'Vocals']

//TODO: Add support for flexible labels and video links
export interface Song {
  title: string
  producer: string
  singer: string
  pdfs: Partial<Record<Instrument, string>> //OPTIONAL: Make PDF its own type with instrument, source, transcriber, and other sheet-specific metadata
}
