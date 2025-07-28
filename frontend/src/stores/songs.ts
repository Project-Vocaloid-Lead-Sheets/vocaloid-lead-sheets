import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { Song } from '@/types/types'
import { loadAllSongs } from '@/utils/jsonLoader'

export const useSongsStore = defineStore('songs', () => {
  // State
  const songs = ref<Song[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const songCount = computed(() => songs.value.length)

  const allProducers = computed(() => {
    const producers = new Set<string>()
    songs.value.forEach((song) => {
      if (song.producer) producers.add(song.producer)
    })
    return Array.from(producers).sort()
  })

  const allSingers = computed(() => {
    const singers = new Set<string>()
    songs.value.forEach((song) => {
      if (song.singer) singers.add(song.singer)
    })
    return Array.from(singers).sort()
  })

  const allLabels = computed(() => {
    const labels = new Set<string>()
    songs.value.forEach((song) => {
      song.labels?.forEach((label) => labels.add(label))
    })
    return Array.from(labels).sort()
  })

  // Actions
  const loadSongs = async () => {
    if (isLoading.value) return

    isLoading.value = true
    error.value = null

    try {
      // Load from JSON files
      const jsonSongs = await loadAllSongs()
      songs.value = jsonSongs
      console.log(`Loaded ${jsonSongs.length} songs from JSON files`)
    } catch (err) {
      console.error('Failed to load songs:', err)
      error.value = err instanceof Error ? err.message : 'Failed to load songs'
      songs.value = []
    } finally {
      isLoading.value = false
    }
  }

  const getSongBySlug = (slug: string): Song | undefined => {
    return songs.value.find((song) => song.title.toLowerCase().replace(/[^a-z0-9]+/g, '-') === slug)
  }

  const refreshSongs = async () => {
    songs.value = []
    await loadSongs()
  }

  return {
    // State
    songs,
    isLoading,
    error,

    // Getters
    songCount,
    allProducers,
    allSingers,
    allLabels,

    // Actions
    loadSongs,
    getSongBySlug,
    refreshSongs,
  }
})
