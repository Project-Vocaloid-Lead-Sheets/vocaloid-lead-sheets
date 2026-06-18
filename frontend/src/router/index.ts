import { createMemoryHistory, createRouter, createWebHistory, type RouterHistory } from 'vue-router'
import MainView from '../views/MainView.vue'
import HomeView from '@/views/HomeView.vue'
import SheetView from '@/views/SheetView.vue'
import { useSongsStore } from '@/stores/songs'
import { instruments } from '@/types/types'
import type { LocationQueryRaw } from 'vue-router'

export function createAppRouter(
  history: RouterHistory = createWebHistory(import.meta.env.BASE_URL),
) {
  return createRouter({
    history,
    routes: [
      {
        path: '/',
        name: 'main',
        component: MainView,
        children: [
          {
            path: '',
            name: 'home',
            component: HomeView,
          },
          {
            path: '/view/:songSlug',
            name: 'sheetView',
            component: SheetView,
            props: (route) => ({
              songSlug: route.params.songSlug,
            }),
            beforeEnter: async (to, from, next) => {
              const songsStore = useSongsStore()
              const songSlug = to.params.songSlug as string

              // Ensure songs are loaded before proceeding
              if (songsStore.songs.length === 0 && !songsStore.isLoading) {
                await songsStore.loadSongs()
              }

              // Wait for loading to complete if it's in progress
              while (songsStore.isLoading) {
                await new Promise((resolve) => setTimeout(resolve, 50))
              }

              // Find the song by slug
              const song = songsStore.getSongBySlug(songSlug)

              if (!song) {
                next({ name: 'home' })
                return
              }

              // Check if song is under review and user didn't come from our app
              const isUnderReview = songsStore.isUnderReviewSong(song)
              const cameFromOurApp = from.name !== undefined // If from.name is undefined, they came directly via URL

              if (isUnderReview && !songsStore.underReviewViewEnabled && !cameFromOurApp) {
                // Store the intended route for after confirmation
                to.meta.requiresReviewConfirmation = true
                to.meta.songData = song
              }

              next()
            },
          },
        ],
      },
    ],
  })
}

const router = createAppRouter(
  typeof window === 'undefined'
    ? createMemoryHistory(import.meta.env.BASE_URL)
    : createWebHistory(import.meta.env.BASE_URL),
)

router.beforeEach((to) => {
  if (to.name !== 'sheetView') return true

  // Keep only valid query keys and sanitize the rest
  const nextQuery: LocationQueryRaw = {}

  const rawTransposition = to.query.transposition
  const validTransposition =
    typeof rawTransposition === 'string' && instruments.includes(rawTransposition as any)
      ? rawTransposition
      : null

  const rawLegacyInstrument = to.query.instrument
  const validLegacyInstrument =
    typeof rawLegacyInstrument === 'string' && instruments.includes(rawLegacyInstrument as any)
      ? rawLegacyInstrument
      : null

  nextQuery.transposition = validTransposition ?? validLegacyInstrument ?? 'C'

  const rawTvSize = to.query.tv_size
  if (typeof rawTvSize === 'string') {
    nextQuery.tv_size = rawTvSize
  } else if (rawTvSize === null) {
    nextQuery.tv_size = null
  } else if (Array.isArray(rawTvSize) && typeof rawTvSize[0] === 'string') {
    nextQuery.tv_size = rawTvSize[0]
  }

  const hasQueryDifference =
    nextQuery.transposition !== to.query.transposition ||
    nextQuery.tv_size !== to.query.tv_size ||
    Object.keys(to.query).some((key) => key !== 'transposition' && key !== 'tv_size')

  if (!hasQueryDifference) return true

  return {
    ...to,
    query: nextQuery,
  }
})

export default router
