<script setup lang="ts">
import type { Instrument } from '@/types/types'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import VuePdfEmbed from 'vue-pdf-embed'
import { useRoute } from 'vue-router'
import { getPdfDisplayUrl } from '@/utils/pdfUtils'
import { useSongsStore } from '@/stores/songs'

const route = useRoute()
const instrument = computed(() => (route.query.instrument as Instrument) || 'C')
const songSlug = computed(() => route.params.songSlug as string)

const songsStore = useSongsStore()

//TODO: Add alias support with fixed PDF IDs/slugs
const currentSong = computed(() =>
  songsStore.songs.find((song) => song.title.toLowerCase().replace(/\s+/g, '-') === songSlug.value),
)

const pdfSource = computed(() => {
  const pdfs = currentSong.value?.pdfs ?? {}
  const originalUrl = pdfs[instrument.value] || pdfs['C'] //TODO: Add fallback for missing PDFs
  return originalUrl ? getPdfDisplayUrl(originalUrl) : ''
})

const isGoogleDrive = computed(() => {
  return pdfSource.value.includes('drive.google.com')
})

const NAVBAR_HEIGHT = 56
const pdfHeight = ref<number | undefined>(undefined)
const pdfWidth = ref<number | undefined>(undefined)

// Constrain size by width if portrait and height if landscape
const updatePdfSize = () => {
  const width = window.innerWidth
  const height = window.innerHeight
  const isMobile = width < 768
  const isLandscape = width > height

  if (isLandscape) {
    pdfHeight.value = height
    pdfWidth.value = undefined
  } else {
    pdfHeight.value = undefined
    pdfWidth.value = width
  }

  if (isMobile && pdfHeight.value !== undefined) {
    pdfHeight.value -= NAVBAR_HEIGHT
  }
}

onMounted(() => {
  updatePdfSize()
  window.addEventListener('resize', updatePdfSize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updatePdfSize)
})
</script>

<template>
  <div class="scroll-container bg-secondary pt-5 pt-lg-0">
    <!-- Use iframe for Google Drive PDFs -->
    <iframe
      v-if="isGoogleDrive && pdfSource"
      :src="pdfSource"
      class="pdf-viewer"
      :height="pdfHeight"
      :width="pdfWidth"
      frameborder="0"
      allowfullscreen
    />
    <!-- Use VuePdfEmbed for regular PDFs -->
    <VuePdfEmbed
      v-else-if="pdfSource"
      class="pdf-viewer"
      :height="pdfHeight"
      :width="pdfWidth"
      :source="pdfSource"
    />
    <!-- Show message when no PDF is available -->
    <div v-else class="d-flex justify-content-center align-items-center h-100">
      <div class="text-center text-muted">
        <h4>No PDF available</h4>
        <p>The sheet music for this song and instrument is not available.</p>
      </div>
    </div>
  </div>
</template>

<style>
.scroll-container {
  display: flex;
  justify-content: center;
  width: 100%;
  max-height: 100vh;
  overflow-x: hidden;
  overflow-y: auto;
  margin: 0;
  padding: 0;
}

.pdf-viewer {
  object-fit: contain;
  max-width: calc(100vw - 300px); /* Account for sidebar width */
  max-height: 100vh;
}

/* On mobile, use full width since sidebar is collapsed */
@media (max-width: 991px) {
  .pdf-viewer {
    max-width: 100vw;
  }
}
</style>
