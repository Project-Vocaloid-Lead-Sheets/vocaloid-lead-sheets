import { createMemoryHistory } from 'vue-router'
import { renderToString } from 'vue/server-renderer'

import { createVocaLeadApp } from '@/app/createApp'

export async function render(url: string) {
  const { app, router, songsStore } = createVocaLeadApp(
    createMemoryHistory(import.meta.env.BASE_URL),
  )

  await router.push(url)
  await router.isReady()
  await songsStore.loadSongs()

  const appHtml = await renderToString(app)

  return { appHtml }
}
