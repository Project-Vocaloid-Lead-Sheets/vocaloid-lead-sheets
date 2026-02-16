import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'
import type { Song } from '@/types/types'
import { loadAllSongs } from '@/utils/jsonLoader'
import { generateSongSlug } from '@/utils/slugUtils'
import { readUserSettings, writeUserSettings, SETTINGS_KEY } from '@/utils/userSettings'

// Ensure songs store installs storage listener only once per page
let _songsStorageListenerInstalled = false

export const useSongsStore = defineStore('songs', () => {
  // State
  const songs = ref<Song[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const underReviewViewEnabled = ref(false)

  // Initialize underReview flag from centralized storage
  const _stored = readUserSettings()
  if (_stored && typeof _stored.underReviewViewEnabled === 'boolean') {
    underReviewViewEnabled.value = _stored.underReviewViewEnabled as boolean
  }

  // Persist underReviewViewEnabled whenever it changes (handles v-model direct updates)
  watch(underReviewViewEnabled, (val) => {
    writeUserSettings({ underReviewViewEnabled: val })
  })

  // Cross-tab sync for underReviewViewEnabled
  if (typeof window !== 'undefined' && !_songsStorageListenerInstalled) {
    window.addEventListener('storage', (e) => {
      if (e.key !== SETTINGS_KEY) return
      const s = readUserSettings()
      if (!s) return
      if (typeof s.underReviewViewEnabled === 'boolean') {
        underReviewViewEnabled.value = s.underReviewViewEnabled
      }
    })
    _songsStorageListenerInstalled = true
  }

  // Getters
  const availableSongs = computed(() => {
    if (underReviewViewEnabled.value) {
      return songs.value // Show all songs
    }
    return songs.value.filter((song) => !song.status || song.status.toLowerCase() === 'completed')
  })

  const songCount = computed(() => availableSongs.value.length)

  const allProducers = computed(() => {
    const producers = new Set<string>()
    availableSongs.value.forEach((song) => {
      if (song.producer) producers.add(song.producer)
    })
    return Array.from(producers).sort()
  })

  const allSingers = computed(() => {
    const singers = new Set<string>()
    availableSongs.value.forEach((song) => {
      if (song.singer) singers.add(song.singer)
    })
    return Array.from(singers).sort()
  })

  const allLabels = computed(() => {
    const labels = new Set<string>()
    availableSongs.value.forEach((song) => {
      song.labels?.forEach((label) => labels.add(label))
    })
    return Array.from(labels).sort()
  })

  // Actions
  const toggleUnderReviewView = () => {
    underReviewViewEnabled.value = !underReviewViewEnabled.value
    writeUserSettings({ underReviewViewEnabled: underReviewViewEnabled.value })
  }

  const isUnderReviewSong = (song: Song) => {
    return song.status && song.status.toLowerCase() === 'under review'
  }

  const isExplicitSong = (song: Song) => {
    return song.labels?.some((label) => label.toLowerCase() === 'explicit') ?? false
  }

  const loadSongs = async () => {
    if (isLoading.value) return

    isLoading.value = true
    error.value = null

    try {
      // Load from JSON files
      const jsonSongs = await loadAllSongs()
      songs.value = jsonSongs
    } catch (err) {
      console.error('Failed to load songs:', err)
      error.value = err instanceof Error ? err.message : 'Failed to load songs'
      songs.value = []
    } finally {
      isLoading.value = false
    }
  }

  const getSongBySlug = (slug: string): Song | undefined => {
    return songs.value.find((song) => generateSongSlug(song.title) === slug)
  }

  const refreshSongs = async () => {
    songs.value = []
    await loadSongs()
  }

  return {
    // State
    songs,
    availableSongs,
    isLoading,
    error,
    underReviewViewEnabled,

    // Getters
    songCount,
    allProducers,
    allSingers,
    allLabels,

    // Actions
    loadSongs,
    getSongBySlug,
    refreshSongs,
    toggleUnderReviewView,
    isUnderReviewSong,
    isExplicitSong,
  }
})
