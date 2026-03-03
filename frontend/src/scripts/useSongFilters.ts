import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import type { Song, Instrument } from '@/types/types'
import { instruments } from '@/types/types'
import { useSongsStore } from '@/stores/songs'
import { generateSongSlug } from '@/utils/slugUtils'
import { readUserSettings, writeUserSettings, SETTINGS_KEY } from '@/utils/userSettings'

// Ensure storage listener installed only once per page
let _settingsStorageListenerInstalled = false
let _groupCollapseListenerInstalled = false

// Global reactive state to ensure all components share the same state
const selectedInstrument = ref<Instrument>('C')
const searchQuery = ref<string>('')
const groupBy = ref<'none' | 'singer' | 'producer'>('none')
type SortField = 'title' | 'bpm' | 'date' | 'length' | 'tv-length'
type SortOrder = 'asc' | 'desc'

// sortBy format: '<field>-<order>' where field is 'title' | 'bpm' | 'date' | 'length' | 'tv-length' and order is 'asc' | 'desc'
const sortBy = ref<
  | 'title-asc'
  | 'title-desc'
  | 'bpm-asc'
  | 'bpm-desc'
  | 'date-asc'
  | 'date-desc'
  | 'length-asc'
  | 'length-desc'
  | 'tv-length-asc'
  | 'tv-length-desc'
>('title-asc')
const isFilterModalShowing = ref(false)
const areGroupsCollapsed = ref(false)
const isSidebarCollapsed = ref(true) // Start collapsed to match Bootstrap's default state
const selectedLabels = ref<string[]>([])
const selectedProducers = ref<string[]>([])
const selectedSingers = ref<string[]>([])
const dateRange = ref<{ start: string; end: string }>({ start: '', end: '' })
const lengthRange = ref<{ min: number | null; max: number | null }>({ min: null, max: null })
const useTvSize = ref<boolean>(false)

// Initialize from storage if available
const _initialSettings = readUserSettings()
if (_initialSettings) {
  if (_initialSettings.selectedInstrument)
    selectedInstrument.value = _initialSettings.selectedInstrument as any
  if (_initialSettings.sortBy) sortBy.value = _initialSettings.sortBy as any
  if (_initialSettings.groupBy) groupBy.value = _initialSettings.groupBy as any
  if (_initialSettings.selectedLabels) selectedLabels.value = [..._initialSettings.selectedLabels]
  if (_initialSettings.selectedProducers)
    selectedProducers.value = [..._initialSettings.selectedProducers]
  if (_initialSettings.selectedSingers)
    selectedSingers.value = [..._initialSettings.selectedSingers]
  if (_initialSettings.dateRange) dateRange.value = { ..._initialSettings.dateRange }
  if (_initialSettings.lengthRange) lengthRange.value = { ..._initialSettings.lengthRange }
  if (typeof _initialSettings.useTvSize === 'boolean') useTvSize.value = _initialSettings.useTvSize
}

export const useSongFilters = () => {
  const route = useRoute()
  const router = useRouter()
  const songsStore = useSongsStore()

  // Use availableSongs from store instead of all songs
  const songs = computed(() => songsStore.availableSongs)

  const parseLengthToSeconds = (lengthValue?: string): number | null => {
    if (!lengthValue) return null
    const trimmed = lengthValue.trim()
    if (!trimmed) return null

    const parts = trimmed.split(':')
    if (parts.length !== 2) return null

    const minutes = Number.parseInt(parts[0], 10)
    const seconds = Number.parseInt(parts[1], 10)

    if (
      Number.isNaN(minutes) ||
      Number.isNaN(seconds) ||
      minutes < 0 ||
      seconds < 0 ||
      seconds > 59
    ) {
      return null
    }

    return minutes * 60 + seconds
  }

  const formatSecondsAsLength = (totalSeconds: number): string => {
    const safeValue = Math.max(0, Math.floor(totalSeconds))
    const minutes = Math.floor(safeValue / 60)
    const seconds = safeValue % 60
    return `${minutes}:${String(seconds).padStart(2, '0')}`
  }

  const getEffectiveSongLengthSeconds = (song: Song): number | null => {
    const fullLength = parseLengthToSeconds(song.length)
    const tvLength = parseLengthToSeconds(song.tvSizeLength)
    if (useTvSize.value && tvLength !== null) return tvLength
    return fullLength
  }

  const sortFields = new Set<SortField>(['title', 'bpm', 'date', 'length', 'tv-length'])
  const sortOrders = new Set<SortOrder>(['asc', 'desc'])

  const parseSortBy = (value: string): { field: SortField; order: SortOrder } => {
    const lastDashIndex = value.lastIndexOf('-')
    if (lastDashIndex === -1) {
      return { field: 'title', order: 'asc' }
    }

    const fieldCandidate = value.slice(0, lastDashIndex) as SortField
    const orderCandidate = value.slice(lastDashIndex + 1) as SortOrder

    if (!sortFields.has(fieldCandidate) || !sortOrders.has(orderCandidate)) {
      return { field: 'title', order: 'asc' }
    }

    return { field: fieldCandidate, order: orderCandidate }
  }

  const effectiveLengthBounds = computed(() => {
    const lengths = songs.value
      .map((song) => getEffectiveSongLengthSeconds(song))
      .filter((value): value is number => value !== null)

    if (lengths.length === 0) {
      return { min: 0, max: 0 }
    }

    return {
      min: Math.min(...lengths),
      max: Math.max(...lengths),
    }
  })

  watch(selectedInstrument, (value) => {
    router.replace({ query: { ...route.query, instrument: value } })
    // persist instrument choice
    writeUserSettings({ selectedInstrument: value })
  })

  const resetSearch = () => {
    searchQuery.value = ''
    selectedLabels.value = []
    selectedProducers.value = []
    selectedSingers.value = []
    dateRange.value = { start: '', end: '' }
    lengthRange.value = { min: null, max: null }
  }

  const resetAllFilters = () => {
    resetSearch()
  }

  const toggleFilterModal = () => {
    isFilterModalShowing.value = !isFilterModalShowing.value
  }

  const syncGroupsCollapsedFromDom = () => {
    if (typeof document === 'undefined') return

    const groupElements = Array.from(document.querySelectorAll<HTMLElement>('.song.collapse'))
    if (groupElements.length === 0) {
      areGroupsCollapsed.value = false
      return
    }

    const allExpanded = groupElements.every((element) => element.classList.contains('show'))
    areGroupsCollapsed.value = !allExpanded
  }

  const setAllGroupsExpanded = (expand: boolean) => {
    if (typeof document === 'undefined') return

    const groupElements = Array.from(document.querySelectorAll<HTMLElement>('.song.collapse'))
    if (groupElements.length === 0) {
      areGroupsCollapsed.value = !expand
      return
    }

    const bootstrapApi = (window as any).bootstrap

    groupElements.forEach((element) => {
      const isExpanded = element.classList.contains('show')
      if (isExpanded === expand) return

      if (bootstrapApi?.Collapse?.getOrCreateInstance) {
        const collapse = bootstrapApi.Collapse.getOrCreateInstance(element, { toggle: false })
        if (expand) {
          collapse.show()
        } else {
          collapse.hide()
        }
        return
      }

      element.classList.toggle('show', expand)
    })

    areGroupsCollapsed.value = !expand
  }

  const toggleGroupsCollapsed = () => {
    syncGroupsCollapsedFromDom()
    const shouldExpandAll = areGroupsCollapsed.value
    setAllGroupsExpanded(shouldExpandAll)
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
      if (song.additionalVoices) {
        song.additionalVoices.forEach((singer) => singerSet.add(singer))
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
        (song.additionalVoices &&
          song.additionalVoices.some((singer) => selectedSingers.value.includes(singer)))

      // Date range filtering - convert dates to comparable format
      const songDate = song.releaseDate // "20250102"
      const startDate = dateRange.value.start ? dateRange.value.start.replace(/-/g, '') : '' // "2025-01-02" -> "20250102"
      const endDate = dateRange.value.end ? dateRange.value.end.replace(/-/g, '') : '' // "2025-01-02" -> "20250102"

      const matchesDateRange =
        (!startDate || songDate >= startDate) && (!endDate || songDate <= endDate)

      const effectiveLength = getEffectiveSongLengthSeconds(song)
      const hasLengthFilter = lengthRange.value.min !== null || lengthRange.value.max !== null
      const minLength = lengthRange.value.min ?? Number.NEGATIVE_INFINITY
      const maxLength = lengthRange.value.max ?? Number.POSITIVE_INFINITY
      const matchesLengthRange =
        !hasLengthFilter ||
        (effectiveLength !== null && effectiveLength >= minLength && effectiveLength <= maxLength)

      return (
        matchesQuery &&
        hasPdf &&
        matchesLabels &&
        matchesProducers &&
        matchesSingers &&
        matchesDateRange &&
        matchesLengthRange
      )
    })

    return result
  })

  // Combination function that groups and sorts
  const orderedSongs = computed(() => {
    const { field, order } = parseSortBy(sortBy.value)
    const dir = order === 'asc' ? 1 : -1

    const comparator = (a: Song, b: Song) => {
      if (field === 'title') {
        return dir * a.title.toLowerCase().localeCompare(b.title.toLowerCase())
      }

      if (field === 'bpm') {
        return dir * (a.bpm - b.bpm)
      }

      if (field === 'length') {
        const aLength = getEffectiveSongLengthSeconds(a)
        const bLength = getEffectiveSongLengthSeconds(b)
        return dir * ((aLength ?? Number.MAX_SAFE_INTEGER) - (bLength ?? Number.MAX_SAFE_INTEGER))
      }

      if (field === 'tv-length') {
        const aLength = parseLengthToSeconds(a.tvSizeLength)
        const bLength = parseLengthToSeconds(b.tvSizeLength)
        return dir * ((aLength ?? Number.MAX_SAFE_INTEGER) - (bLength ?? Number.MAX_SAFE_INTEGER))
      }

      // field === 'date'
      // releaseDate is stored as YYYYMMDD (string). Compare as strings to preserve chronological order.
      const aDate = a.releaseDate || ''
      const bDate = b.releaseDate || ''
      return dir * aDate.localeCompare(bDate)
    }

    if (groupBy.value === 'none') {
      const sorted = [...filteredSongs.value].sort(comparator)
      return [{ groupName: 'All Songs', songs: sorted }]
    }

    const groups: Record<string, Song[]> = {}

    for (const song of filteredSongs.value) {
      const key = (song as any)[groupBy.value]
      if (!groups[key]) groups[key] = []
      groups[key].push(song)
    }

    return Object.entries(groups)
      .sort(([a], [b]) => dir * a.toLowerCase().localeCompare(b.toLowerCase()))
      .map(([groupName, songsList]) => ({
        groupName,
        songs: songsList.sort(comparator),
      }))
  })

  const pickRandomSong = () => {
    const randomIndex = Math.floor(Math.random() * filteredSongs.value.length)
    const slug = generateSongSlug(filteredSongs.value[randomIndex].title)
    router.push({
      name: 'sheetView',
      params: {
        songSlug: slug,
      },
    })
  }

  // Persist relevant settings whenever they change
  watch(
    [
      selectedInstrument,
      sortBy,
      groupBy,
      selectedLabels,
      selectedProducers,
      selectedSingers,
      dateRange,
      lengthRange,
      useTvSize,
    ],
    () => {
      writeUserSettings({
        selectedInstrument: selectedInstrument.value,
        sortBy: sortBy.value,
        groupBy: groupBy.value,
        selectedLabels: selectedLabels.value,
        selectedProducers: selectedProducers.value,
        selectedSingers: selectedSingers.value,
        dateRange: dateRange.value,
        lengthRange: lengthRange.value,
        useTvSize: useTvSize.value,
      })
    },
    { deep: true },
  )

  // Cross-tab sync: update reactive refs if settings change in another tab/window
  if (typeof window !== 'undefined' && !_settingsStorageListenerInstalled) {
    window.addEventListener('storage', (e) => {
      if (e.key !== SETTINGS_KEY) return
      const s = readUserSettings()
      if (!s) return
      if (s.selectedInstrument) selectedInstrument.value = s.selectedInstrument as any
      if (s.sortBy) sortBy.value = s.sortBy as any
      if (s.groupBy) groupBy.value = s.groupBy as any
      if (s.selectedLabels) selectedLabels.value = [...s.selectedLabels]
      if (s.selectedProducers) selectedProducers.value = [...s.selectedProducers]
      if (s.selectedSingers) selectedSingers.value = [...s.selectedSingers]
      if (s.dateRange) dateRange.value = { ...s.dateRange }
      if (s.lengthRange) lengthRange.value = { ...s.lengthRange }
      if (typeof s.useTvSize === 'boolean') useTvSize.value = s.useTvSize
    })
    _settingsStorageListenerInstalled = true
  }

  if (typeof window !== 'undefined' && !_groupCollapseListenerInstalled) {
    const onCollapseStateChanged = (event: Event) => {
      const target = event.target as HTMLElement | null
      if (!target?.classList?.contains('song') || !target.classList.contains('collapse')) return
      syncGroupsCollapsedFromDom()
    }

    document.addEventListener('shown.bs.collapse', onCollapseStateChanged as EventListener)
    document.addEventListener('hidden.bs.collapse', onCollapseStateChanged as EventListener)

    queueMicrotask(() => {
      syncGroupsCollapsedFromDom()
    })

    _groupCollapseListenerInstalled = true
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
    lengthRange,
    availableLabels,
    availableProducers,
    availableSingers,
    effectiveLengthBounds,
    formatSecondsAsLength,
    useTvSize,
  }
}
