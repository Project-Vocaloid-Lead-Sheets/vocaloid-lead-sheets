import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import type { Song, Instrument } from '@/types/types'
import { instruments } from '@/types/types'

import mockData from '@/data/mockData.json'

export const useSongFilters = () => {
  const route = useRoute()
  const router = useRouter()

  const selectedInstrument = ref<Instrument>('C')
  const searchQuery = ref<string>('')

  const groupBy = ref<'none' | 'singer' | 'producer'>('singer')
  const sortBy = ref<'a-z' | 'z-a'>('a-z')

  const isFilterModalShowing = ref(false)
  const areGroupsCollapsed = ref(false)

  watch(selectedInstrument, (value) => {
    router.replace({ query: { ...route.query, instrument: value } })
  })

  const resetSearch = () => {
    searchQuery.value = ''
  }

  //TODO: Not implemented
  const toggleFilterModal = () => {
    isFilterModalShowing.value = !isFilterModalShowing.value
  }

  const toggleGroupsCollapsed = () => {
    areGroupsCollapsed.value = !areGroupsCollapsed.value
  }

  //TODO: Move fetched songs into shared context with sheet view
  const songs = ref<Song[]>(mockData)

  const filteredSongs = computed(() => {
    const query = searchQuery.value.toLowerCase()
    return songs.value.filter((song) => {
      return song.title.toLowerCase().includes(query) && song.pdfs[selectedInstrument.value]?.trim()
    })
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
    toggleFilterModal,
    toggleGroupsCollapsed,
    areGroupsCollapsed,
    orderedSongs,
    pickRandomSong,
  }
}
