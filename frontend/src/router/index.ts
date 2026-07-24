import { createMemoryHistory, createRouter, createWebHistory, type RouterHistory } from 'vue-router'
import MainView from '../views/MainView.vue'
import HomeView from '@/views/HomeView.vue'
import SheetView from '@/views/SheetView.vue'
import { useSongsStore } from '@/stores/songs'
import { instruments } from '@/types/types'
import type { LocationQueryRaw } from 'vue-router'
import {
  normalizeTranspositionQuery,
  normalizeTvSizeQuery,
  buildCleanQuery,
  areQueriesEquivalent,
} from '@/utils/queryNormalization'

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

  if (to.path.endsWith('/')) {
    return {
      ...to,
      path: to.path.replace(/\/+$/, ''),
      replace: true,
    }
  }

  // Keep only valid query keys and sanitize the rest
  const rawTransposition = to.query.transposition
  const validTransposition = normalizeTranspositionQuery(rawTransposition, instruments)

  const rawLegacyInstrument = to.query.instrument
  const validLegacyInstrument = normalizeTranspositionQuery(rawLegacyInstrument, instruments)

  const resolvedTransposition = validTransposition ?? validLegacyInstrument
  const normalizedTvSize = normalizeTvSizeQuery(to.query.tv_size)
  const nextQuery = buildCleanQuery(resolvedTransposition, normalizedTvSize)

  const isQueryClean = areQueriesEquivalent(to.query, nextQuery)
  if (isQueryClean) return true

  return {
    ...to,
    query: nextQuery,
  }
})

export default router
