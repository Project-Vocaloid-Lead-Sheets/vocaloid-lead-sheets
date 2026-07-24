import { createMemoryHistory } from 'vue-router'
import { renderToString } from 'vue/server-renderer'

import { createVocaLeadApp } from '@/app/createApp'
import type { Song } from '@/types/types'

interface RenderOptions {
  songs?: Song[]
}

export async function render(url: string, options: RenderOptions = {}) {
  const { app, router, songsStore } = createVocaLeadApp(
    createMemoryHistory(import.meta.env.BASE_URL),
  )

  if (Array.isArray(options.songs) && options.songs.length > 0) {
    songsStore.songs = options.songs
  } else {
    await songsStore.loadSongs()
  }

  await router.push(url)
  await router.isReady()

  const appHtml = await renderToString(app)

  return { appHtml }
}
