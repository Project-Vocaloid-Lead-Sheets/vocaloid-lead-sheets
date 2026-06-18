import { createApp } from 'vue'
import { createPinia } from 'pinia'
import type { RouterHistory } from 'vue-router'

import App from '@/App.vue'
import { createAppRouter } from '@/router'
import { useSongsStore } from '@/stores/songs'

export function createVocaLeadApp(history?: RouterHistory) {
  const app = createApp(App)
  const pinia = createPinia()
  const router = createAppRouter(history)

  app.use(pinia)
  app.use(router)

  const songsStore = useSongsStore(pinia)

  return {
    app,
    pinia,
    router,
    songsStore,
  }
}
