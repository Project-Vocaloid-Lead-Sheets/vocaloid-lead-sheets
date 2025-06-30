import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import type { Song, Instrument } from '@/types/types'
import { instruments } from '@/types/types'

import mockData from '@/data/mockData.json'

// Global reactive state to ensure all components share the same state
const selectedInstrument = ref<Instrument>('C')
const searchQuery = ref<string>('')
const groupBy = ref<'none' | 'singer' | 'producer'>('singer')
const sortBy = ref<'a-z' | 'z-a'>('a-z')
const isFilterModalShowing = ref(false)
const areGroupsCollapsed = ref(false)
const isSidebarCollapsed = ref(true) // Start collapsed to match Bootstrap's default state
const selectedLabels = ref<string[]>([])
const selectedProducers = ref<string[]>([])
const selectedSingers = ref<string[]>([])
const dateRange = ref<{ start: string; end: string }>({ start: '', end: '' })
const songs = ref<Song[]>(mockData)

export const useSongFilters = () => {
  const route = useRoute()
  const router = useRouter()

  watch(selectedInstrument, (value) => {
    router.replace({ query: { ...route.query, instrument: value } })
  })

  const resetSearch = () => {
    searchQuery.value = ''
    selectedLabels.value = []
    selectedProducers.value = []
    selectedSingers.value = []
    dateRange.value = { start: '', end: '' }
  }

  const resetAllFilters = () => {
    resetSearch()
  }

  const toggleFilterModal = () => {
    isFilterModalShowing.value = !isFilterModalShowing.value
  }

  const toggleGroupsCollapsed = () => {
    areGroupsCollapsed.value = !areGroupsCollapsed.value
  }

  const toggleSidebarCollapsed = () => {
    isSidebarCollapsed.value = !isSidebarCollapsed.value
  }

  //TODO: Move fetched songs into shared context with sheet view

  // Computed arrays for filter options
  const availableLabels = computed(() => {
    const labelSet = new Set<string>()
    songs.value.forEach((song) => {
      if (song.labels) {
        song.labels.forEach((label) => labelSet.add(label))
      }
    })
    return Array.from(labelSet).sort()
  })

  const availableProducers = computed(() => {
    const producerSet = new Set<string>()
    songs.value.forEach((song) => {
      producerSet.add(song.producer)
      if (song.additionalProducers) {
        song.additionalProducers.forEach((producer) => producerSet.add(producer))
      }
    })
    return Array.from(producerSet).sort()
  })

  const availableSingers = computed(() => {
    const singerSet = new Set<string>()
    songs.value.forEach((song) => {
      singerSet.add(song.singer)
      if (song.additionalSingers) {
        song.additionalSingers.forEach((singer) => singerSet.add(singer))
      }
    })
    return Array.from(singerSet).sort()
  })

  const filteredSongs = computed(() => {
    const query = searchQuery.value.toLowerCase()

    const result = songs.value.filter((song) => {
      // Basic text search
      const matchesQuery = song.title.toLowerCase().includes(query)

      // Check if song has PDF for selected instrument
      const hasPdf = song.pdfs[selectedInstrument.value]?.trim()

      // Label filtering
      const matchesLabels =
        selectedLabels.value.length === 0 ||
        (song.labels && selectedLabels.value.some((label) => song.labels!.includes(label)))

      // Producer filtering
      const matchesProducers =
        selectedProducers.value.length === 0 ||
        selectedProducers.value.includes(song.producer) ||
        (song.additionalProducers &&
          song.additionalProducers.some((producer) => selectedProducers.value.includes(producer)))

      // Singer filtering
      const matchesSingers =
        selectedSingers.value.length === 0 ||
        selectedSingers.value.includes(song.singer) ||
        (song.additionalSingers &&
          song.additionalSingers.some((singer) => selectedSingers.value.includes(singer)))

      // Date range filtering - convert dates to comparable format
      const songDate = song.releaseDate // "20250102"
      const startDate = dateRange.value.start ? dateRange.value.start.replace(/-/g, '') : '' // "2025-01-02" -> "20250102"
      const endDate = dateRange.value.end ? dateRange.value.end.replace(/-/g, '') : '' // "2025-01-02" -> "20250102"

      const matchesDateRange =
        (!startDate || songDate >= startDate) && (!endDate || songDate <= endDate)

      return (
        matchesQuery &&
        hasPdf &&
        matchesLabels &&
        matchesProducers &&
        matchesSingers &&
        matchesDateRange
      )
    })

    return result
  })

  // Combination function that groups and sorts
  const orderedSongs = computed(() => {
    const direction = sortBy.value === 'a-z' ? 1 : -1
    if (groupBy.value === 'none') {
      const sorted = [...filteredSongs.value].sort(
        (a, b) => direction * a.title.toLowerCase().localeCompare(b.title.toLowerCase()),
      )
      return [{ groupName: 'All Songs', songs: sorted }]
    }

    const groups: Record<string, Song[]> = {}

    for (const song of filteredSongs.value) {
      const key = song[groupBy.value]
      if (!groups[key]) groups[key] = []
      groups[key].push(song)
    }

    return Object.entries(groups)
      .sort(([a], [b]) => direction * a.toLowerCase().localeCompare(b.toLowerCase()))
      .map(([groupName, songs]) => ({
        groupName,
        songs: songs.sort(
          (a, b) => direction * a.title.toLowerCase().localeCompare(b.title.toLowerCase()),
        ),
      }))
  })

  const pickRandomSong = () => {
    const randomIndex = Math.floor(Math.random() * filteredSongs.value.length)
    const slug = filteredSongs.value[randomIndex].title.toLowerCase().replace(/\s+/g, '-')
    router.push({
      name: 'sheetView',
      params: {
        songSlug: slug,
      },
    })
  }

  return {
    instruments,
    selectedInstrument,
    searchQuery,
    groupBy,
    sortBy,
    resetSearch,
    resetAllFilters,
    toggleFilterModal,
    isFilterModalShowing,
    toggleGroupsCollapsed,
    areGroupsCollapsed,
    toggleSidebarCollapsed,
    isSidebarCollapsed,
    orderedSongs,
    pickRandomSong,
    // Advanced filter properties
    selectedLabels,
    selectedProducers,
    selectedSingers,
    dateRange,
    availableLabels,
    availableProducers,
    availableSingers,
  }
}
