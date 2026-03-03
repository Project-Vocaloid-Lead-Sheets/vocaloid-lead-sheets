<script setup lang="ts">
// Dedicated PDF viewer built using EmbedPDF for Vue. Supports two page spread as well as other useful features. Accepts an absolute path to a pdf file.
import { computed, onUnmounted, ref } from 'vue'
import {
  PDFViewer,
  ScrollStrategy,
  SpreadMode,
  UIPlugin,
  ZoomMode,
  type PluginRegistry,
} from '@embedpdf/vue-pdf-viewer'
import { dispatchOpenDownloadModalEvent } from '@/utils/downloadEvents'

// Flat schema file to fully control the viewer UI
import flatSchema from '../components/embedpdf-flat-schema.json'

interface Props {
  source: string
}

const props = defineProps<Props>()

const VIEWER_SETTINGS_KEY = 'vls-pdf-viewer-settings-v1'

type StoredViewerSettings = {
  spreadMode?: SpreadMode
  scrollStrategy?: ScrollStrategy
}

const readViewerSettings = (): StoredViewerSettings => {
  if (typeof window === 'undefined') return {}

  try {
    const raw = window.localStorage.getItem(VIEWER_SETTINGS_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as StoredViewerSettings
    return parsed ?? {}
  } catch {
    return {}
  }
}

const writeViewerSettings = (partial: StoredViewerSettings) => {
  if (typeof window === 'undefined') return

  try {
    const existing = readViewerSettings()
    const merged = { ...existing, ...partial }
    window.localStorage.setItem(VIEWER_SETTINGS_KEY, JSON.stringify(merged))
  } catch {}
}

const initialSettings = readViewerSettings()

const spreadModePreference = ref<SpreadMode>(initialSettings.spreadMode ?? SpreadMode.None)
const scrollStrategyPreference = ref<ScrollStrategy>(
  initialSettings.scrollStrategy ?? ScrollStrategy.Vertical,
)

const viewerConfig = computed(() => ({
  src: pdfUrl.value,
  spread: { defaultSpreadMode: spreadModePreference.value },
  scroll: { defaultStrategy: scrollStrategyPreference.value },
  zoom: { defaultZoomLevel: ZoomMode.FitPage },
}))

const viewerInstanceKey = computed(() => `pdf-viewer:${pdfUrl.value}`)

const unregisterHandlers: Array<() => void> = []

const pdfUrl = computed(() => {
  if (!props.source) return ''

  const url = props.source

  // Ensure absolute URL for worker fetches. Worker may not resolve root-relative paths.
  if (typeof window !== 'undefined' && url.startsWith('/')) {
    try {
      return window.location.origin + encodeURI(url)
    } catch {
      return url
    }
  }
  return url
})

function handleReady(registry: PluginRegistry) {
  const ui = registry.getPlugin<UIPlugin>('ui')?.provides?.()
  const commands = registry.getPlugin('commands')?.provides?.()
  const spread = registry.getPlugin('spread')?.provides?.()
  const scroll = registry.getPlugin('scroll')?.provides?.()

  if (!commands || !ui) return

  ui.mergeSchema(flatSchema as Partial<any>)

  try {
    commands.unregisterCommand?.('app:download')
    commands.registerCommand?.({
      id: 'app:download',
      label: 'Download',
      icon: 'download',
      action: () => {
        dispatchOpenDownloadModalEvent()
      },
    })
  } catch {}

  unregisterHandlers.splice(0).forEach((unregister) => unregister())

  if (spread?.onSpreadChange) {
    const unregister = spread.onSpreadChange((event: any) => {
      const mode = event?.spreadMode ?? event
      if (mode !== SpreadMode.None && mode !== SpreadMode.Odd && mode !== SpreadMode.Even) return

      spreadModePreference.value = mode
      writeViewerSettings({ spreadMode: mode })
    })
    unregisterHandlers.push(unregister)
  }

  if (scroll?.onStateChange) {
    const unregister = scroll.onStateChange((state: any) => {
      const strategy = state?.strategy
      if (strategy !== ScrollStrategy.Vertical && strategy !== ScrollStrategy.Horizontal) return

      scrollStrategyPreference.value = strategy
      writeViewerSettings({ scrollStrategy: strategy })
    })
    unregisterHandlers.push(unregister)
  }

  // Ensure navbar measurements update after the viewer has rendered.
  try {
    if (typeof window !== 'undefined') {
      // Immediate attempt
      ;(window as any).__updateNavbarHeight?.()
      // Repeat shortly after to handle late layout changes
      setTimeout(() => (window as any).__updateNavbarHeight?.(), 120)
      setTimeout(() => (window as any).__updateNavbarHeight?.(), 400)
    }
  } catch {}
}

onUnmounted(() => {
  unregisterHandlers.splice(0).forEach((unregister) => unregister())
})
</script>

<template>
  <div class="pdf-viewer-root">
    <div class="pdf-viewer-container">
      <div class="pdf-viewer-scroll" v-if="pdfUrl">
        <PDFViewer :key="viewerInstanceKey" @ready="handleReady" :config="viewerConfig" />
      </div>

      <div v-else class="loading-overlay">
        <div class="spinner-border text-light" role="status">
          <span class="visually-hidden">Loading PDF...</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pdf-viewer-root {
  display: flex;
  flex-direction: column;
  /* Fill the parent scroll container; parent is already offset and sized
     according to the navbar height, so the viewer simply fills 100%. */
  height: 100%;
  max-height: 100%;
  min-height: 0;
  min-width: 0;
}

.pdf-viewer-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  height: 100%;
  min-width: 0;
  min-height: 0; /* allow children to shrink/scroll */
  overflow: hidden; /* prevent the viewer from overflowing the screen */
}

.pdf-viewer-scroll {
  flex: 1 1 auto;
  height: 100%;
  min-height: 0; /* critical for child overflow to work in flex */
  overflow: auto; /* PDF content scrolls here if it's too large */
}

/* Ensure the embedded PDF viewer component fills the scroll container
   exactly. Use a deep selector so the component's root element (whatever
   tag it renders) receives 100% height and flex growth. */
.pdf-viewer-scroll ::v-deep(> *) {
  flex: 1 1 auto;
  height: 100% !important;
  min-height: 0 !important;
}

.loading-overlay {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}
</style>
