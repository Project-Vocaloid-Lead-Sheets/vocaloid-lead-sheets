import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { useSongsStore } from '@/stores/songs'

import '@/scss/styles.scss'
import * as bootstrap from 'bootstrap' // Import JS for bootstrap, even if unused here
import 'bootstrap-icons/font/bootstrap-icons.css'

const GA_MEASUREMENT_ID = 'G-DWH4PQ3JPP'

declare global {
  interface Window {
    gtag?: (...args: any[]) => void
  }
}

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Example title: World Is Mine Lead Sheets - ryo ft. Hatsune Miku | Project VocaLead Sheets
function buildSongTabTitle(song: any) {
  const title = song.title || ''

  let producerPart = song.producer || ''
  if (song.additionalProducers && song.additionalProducers.length > 0) {
    producerPart += ` + ${song.additionalProducers.join(' + ')}`
  }

  let singerPart = song.singer || ''
  if (song.additionalVoices && song.additionalVoices.length > 0) {
    singerPart += ` + ${song.additionalVoices.join(' + ')}`
  }

  const artistPart = `${producerPart} ft. ${singerPart}`
  return `${title} Lead Sheets - ${artistPart} | Project VocaLead Sheets`
}

router.afterEach((to) => {
  // Update tab title based on song metadata
  if (to.name === 'sheetView' && typeof to.params.songSlug === 'string') {
    const songsStore = useSongsStore()
    const song = songsStore.getSongBySlug(to.params.songSlug as string)

    if (song) {
      document.title = buildSongTabTitle(song)
    }
  } else {
    // Default title (home page)
    document.title = 'Project VocaLead Sheets | Vocaloid Lead Sheets & Sheet Music'
  }

  const gtag = window.gtag
  if (typeof gtag !== 'function') return

  gtag('config', GA_MEASUREMENT_ID, {
    page_path: to.fullPath,
    page_location: window.location.href,
    page_title: document.title,
  })

  if (to.name === 'sheetView' && typeof to.params.songSlug === 'string') {
    const instrument =
      typeof to.query.transposition === 'string' ? to.query.transposition : 'unknown'

    gtag('event', 'view_sheet', {
      song_slug: to.params.songSlug,
      instrument,
    })
  }
})

// Initialize songs store
const songsStore = useSongsStore()
songsStore.loadSongs()

// Handle redirect from 404.html for GitHub Pages SPA routing
const urlParams = new URLSearchParams(window.location.search)
const redirectPath = urlParams.get('redirect')
if (redirectPath) {
  router.replace(decodeURIComponent(redirectPath))
}

// Set a mobile-friendly CSS "--vh" variable so 100% heights account for
// dynamic browser chrome (address bar) on mobile devices.
function setVh() {
  try {
    document.documentElement.style.setProperty('--vh', `${window.innerHeight * 0.01}px`)
  } catch {}
}

setVh()
window.addEventListener('resize', setVh)
window.addEventListener('orientationchange', setVh)

// Compute navbar height measured from the viewport top.
// We measure boundingClientRect().bottom for header elements so the
// remainder of the viewport (bottom) can be used for the PDF scroller.
function updateNavbarHeight() {
  try {
    const nav = document.querySelector('.navbar') as HTMLElement | null

    let maxBottom = 0

    if (nav) {
      try {
        const r = nav.getBoundingClientRect()
        if (!isNaN(r.bottom)) maxBottom = Math.max(maxBottom, Math.ceil(r.bottom))
      } catch {}
    }

    // If no explicit navbar found, try to detect a fixed/sticky element at top
    if (maxBottom === 0) {
      try {
        const els = Array.from(document.querySelectorAll<HTMLElement>('*'))
        for (const el of els) {
          try {
            const cs = window.getComputedStyle(el)
            if (
              (cs.position === 'fixed' || cs.position === 'sticky') &&
              el.getBoundingClientRect().top <= 0
            ) {
              const r = el.getBoundingClientRect()
              if (!isNaN(r.bottom)) {
                maxBottom = Math.max(maxBottom, Math.ceil(r.bottom))
                break
              }
            }
          } catch {}
        }
      } catch {}
    }

    document.documentElement.style.setProperty('--navbar-height', `${maxBottom}px`)
  } catch {}
}

// Observe header and related elements to keep --navbar-height accurate
function observeHeaderAndContent() {
  try {
    const nav = document.querySelector('.navbar') as HTMLElement | null
    const off = document.getElementById('offcanvasNavbar') as HTMLElement | null

    updateNavbarHeight()

    if (typeof ResizeObserver !== 'undefined') {
      try {
        const ro = new ResizeObserver(() => updateNavbarHeight())
        if (nav) ro.observe(nav)
        if (off) ro.observe(off)
      } catch {}
    }

    if (off) {
      off.addEventListener('show.bs.offcanvas', () => setTimeout(updateNavbarHeight, 50))
      off.addEventListener('shown.bs.offcanvas', updateNavbarHeight)
      off.addEventListener('hide.bs.offcanvas', () => setTimeout(updateNavbarHeight, 50))
      off.addEventListener('hidden.bs.offcanvas', updateNavbarHeight)
    }

    window.addEventListener('resize', updateNavbarHeight)
    window.addEventListener('orientationchange', updateNavbarHeight)
    window.addEventListener(
      'scroll',
      () => {
        try {
          setTimeout(updateNavbarHeight, 20)
        } catch {}
      },
      { passive: true },
    )
  } catch {}
}

observeHeaderAndContent()

// If the navbar is rendered after this script runs (Vue mounts later), watch
// the document for nodes being added and attach observers when .navbar appears.
try {
  const mo = new MutationObserver((mutations, observer) => {
    try {
      for (const m of mutations) {
        if (m.addedNodes && m.addedNodes.length) {
          for (const node of Array.from(m.addedNodes)) {
            const el = node as HTMLElement
            if (!el) continue
            if (el.classList && el.classList.contains && el.classList.contains('navbar')) {
              // navbar added - re-run observers and measurement
              try {
                observeHeaderAndContent()
                updateNavbarHeight()
              } catch {}
              observer.disconnect()
              return
            }
            if (el.id === 'offcanvasNavbar') {
              try {
                observeHeaderAndContent()
                updateNavbarHeight()
              } catch {}
              observer.disconnect()
              return
            }
          }
        }
      }
    } catch {}
  })
  mo.observe(document.documentElement || document.body, { childList: true, subtree: true })
} catch {}

// Expose the measurement function so other components can trigger it when
// they've finished rendering (helps ensure accurate layout on mobile).
try {
  ;(window as any).__updateNavbarHeight = updateNavbarHeight
} catch {}

app.mount('#app')
