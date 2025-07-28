import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { useSongsStore } from '@/stores/songs'

import '@/scss/styles.scss'
import * as bootstrap from 'bootstrap' // Import JS for bootstrap, even if unused here
import 'bootstrap-icons/font/bootstrap-icons.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Initialize songs store
const songsStore = useSongsStore()
songsStore.loadSongs()

// Handle redirect from 404.html for GitHub Pages SPA routing
const urlParams = new URLSearchParams(window.location.search)
const redirectPath = urlParams.get('redirect')
if (redirectPath) {
  router.replace(decodeURIComponent(redirectPath))
}

app.mount('#app')
