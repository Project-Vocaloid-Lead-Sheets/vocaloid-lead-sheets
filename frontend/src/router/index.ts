import { createRouter, createWebHistory } from 'vue-router'
import MainView from '../views/MainView.vue'
import HomeView from '@/views/HomeView.vue'
import SheetView from '@/views/SheetView.vue'
import { useSongsStore } from '@/stores/songs'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
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

export default router
