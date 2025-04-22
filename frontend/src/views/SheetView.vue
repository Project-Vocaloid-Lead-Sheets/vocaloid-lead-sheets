<script setup lang="ts">
import type { Instrument } from '@/types/types'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import VuePdfEmbed from 'vue-pdf-embed'
import { useRoute } from 'vue-router'

const route = useRoute()
const instrument = computed(() => (route.query.instrument as Instrument) || 'C')
const songSlug = computed(() => route.params.songSlug as string)

import mockData from '@/data/mockData.json'
import type { Song } from '@/types/types'

const songs = ref<Song[]>(mockData)

//TODO: Add alias support with fixed PDF IDs/slugs
const currentSong = computed(() =>
  songs.value.find((song) => song.title.toLowerCase().replace(/\s+/g, '-') === songSlug.value),
)

const pdfSource = computed(() => {
  const pdfs = currentSong.value?.pdfs ?? {}
  return pdfs[instrument.value] || pdfs['C'] //TODO: Add fallback for missing PDFs
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
    <VuePdfEmbed class="pdf-viewer" :height="pdfHeight" :width="pdfWidth" :source="pdfSource" />
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
  max-width: 100vw;
}
</style>
