import { computed } from 'vue'
import { useRoute } from 'vue-router'
import type { Song, Instrument } from '@/types/types'
import { useSongsStore } from '@/stores/songs'

export const useSongActions = () => {
  const route = useRoute()
  const songsStore = useSongsStore()

  // Get current song based on route
  const currentSong = computed<Song | null>(() => {
    const songSlug = route.params.songSlug as string
    if (!songSlug) return null
    return songsStore.getSongBySlug(songSlug) || null
  })

  const currentInstrument = computed(() => (route.query.instrument as Instrument) || 'C')

  // Functions for the footer actions
  const watchOnYouTube = () => {
    const song = currentSong.value
    if (!song?.videoLinks?.YouTube) return

    window.open(song.videoLinks.YouTube, '_blank')
  }

  return {
    currentSong,
    currentInstrument,
    watchOnYouTube,
  }
}
