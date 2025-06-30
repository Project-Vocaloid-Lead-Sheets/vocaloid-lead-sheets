import { computed } from 'vue'
import { useRoute } from 'vue-router'
import type { Song, Instrument } from '@/types/types'
import mockData from '@/data/mockData.json'

export const useSongActions = () => {
  const route = useRoute()
  const songs = mockData as Song[]

  // Get current song based on route
  const currentSong = computed<Song | null>(() => {
    const songSlug = route.params.songSlug as string
    if (!songSlug) return null
    return songs.find((song) => song.title.toLowerCase().replace(/\s+/g, '-') === songSlug) || null
  })

  const currentInstrument = computed(() => (route.query.instrument as Instrument) || 'C')

  // Functions for the footer actions
  const printPdf = () => {
    const song = currentSong.value
    if (!song) return

    const pdfPath = song.pdfs[currentInstrument.value] || song.pdfs['C']
    if (pdfPath) {
      window.open(pdfPath, '_blank')?.print()
    }
  }

  const watchOnYouTube = () => {
    const song = currentSong.value
    if (!song?.videoLinks?.YouTube) return

    window.open(song.videoLinks.YouTube, '_blank')
  }

  return {
    currentSong,
    currentInstrument,
    printPdf,
    watchOnYouTube,
  }
}
