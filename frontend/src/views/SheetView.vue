<script setup lang="ts">
import type { Instrument } from '@/types/types'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getPdfDisplayUrl } from '@/utils/pdfUtils'
import { useSongsStore } from '@/stores/songs'
import UnderReviewDialog from '@/components/UnderReviewDialog.vue'
import ExplicitContentDialog from '@/components/ExplicitContentDialog.vue'
import PdfViewer from '@/components/PdfViewer.vue'

const route = useRoute()
const router = useRouter()
const instrument = computed(() => (route.query.instrument as Instrument) || 'C')
const songSlug = computed(() => route.params.songSlug as string)

const songsStore = useSongsStore()

//TODO: Add alias support with fixed PDF IDs/slugs
const currentSong = computed(() => songsStore.getSongBySlug(songSlug.value))

// Review mode dialog handling
const showReviewDialog = ref(false)
const reviewDialogRef = ref<InstanceType<typeof UnderReviewDialog>>()

// Explicit content dialog handling
const showExplicitDialog = ref(false)
const explicitDialogRef = ref<InstanceType<typeof ExplicitContentDialog>>()
// Track all explicit songs that have been acknowledged this session
const acknowledgedExplicitSongs = ref<Set<string>>(new Set())

const checkReviewConfirmation = () => {
  if (route.meta.requiresReviewConfirmation && currentSong.value) {
    showReviewDialog.value = true
    setTimeout(() => {
      reviewDialogRef.value?.show()
    }, 100)
  }
}

const onReviewConfirm = () => {
  songsStore.toggleUnderReviewView()
  showReviewDialog.value = false
  // Clear the meta flag
  route.meta.requiresReviewConfirmation = false
  checkExplicitDialog()
}

const onReviewCancel = () => {
  showReviewDialog.value = false
  router.back()
}

const isExplicitSong = computed(() => {
  return currentSong.value ? songsStore.isExplicitSong(currentSong.value) : false
})

const checkExplicitDialog = () => {
  if (!currentSong.value) return
  if (!isExplicitSong.value) return
  if (instrument.value !== 'Vocals') return
  if (showReviewDialog.value) return

  // Only show if this song hasn't been acknowledged this session
  if (acknowledgedExplicitSongs.value.has(songSlug.value)) return

  showExplicitDialog.value = true
  setTimeout(() => {
    explicitDialogRef.value?.show()
  }, 100)
}

const onExplicitConfirm = () => {
  // Mark this song as acknowledged for the session
  if (currentSong.value) {
    acknowledgedExplicitSongs.value.add(songSlug.value)
  }
  showExplicitDialog.value = false
}

const onExplicitCancel = () => {
  showExplicitDialog.value = false
  router.back()
}

const pdfSource = computed(() => {
  const pdfs = currentSong.value?.pdfs ?? {}
  const originalUrl = pdfs[instrument.value] || pdfs['C'] //TODO: Add fallback for missing PDFs
  return originalUrl ? getPdfDisplayUrl(originalUrl) : ''
})

// Watch for route changes to check for review mode confirmation
watch(
  () => route.meta.requiresReviewConfirmation,
  () => {
    checkReviewConfirmation()
  },
)

watch([songSlug, instrument, currentSong], () => {
  checkExplicitDialog()
})

onMounted(() => {
  checkReviewConfirmation()
  checkExplicitDialog()
})
</script>

<template>
  <div>
    <div class="scroll-container bg-secondary pt-0" :class="{ 'blur-content': showExplicitDialog }">
      <!-- Loading state -->
      <div
        v-if="songsStore.isLoading"
        class="d-flex justify-content-center align-items-center h-100"
      >
        <div class="text-center text-light">
          <div class="spinner-border" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
          <p class="mt-2">Loading songs...</p>
        </div>
      </div>

      <!-- Song not found -->
      <div
        v-else-if="!currentSong && !songsStore.isLoading"
        class="d-flex justify-content-center align-items-center h-100"
      >
        <div class="text-center text-light">
          <h4>Song not found</h4>
          <p>The requested song could not be found.</p>
          <RouterLink to="/" class="btn btn-primary">Go Home</RouterLink>
        </div>
      </div>

      <!-- PDF content (only show when song is found and not loading) -->
      <template v-else-if="currentSong">
        <!-- Use PdfViewer component -->
        <PdfViewer v-if="pdfSource" :source="pdfSource" class="pdf-viewer" />
        <!-- Show message when no PDF is available -->
        <div v-else class="d-flex justify-content-center align-items-center h-100">
          <div class="text-center text-muted">
            <h4>No PDF available</h4>
            <p>The sheet music for this song and instrument is not available.</p>
          </div>
        </div>
      </template>
    </div>

    <!-- Review Confirmation Dialog -->
    <UnderReviewDialog
      v-if="showReviewDialog"
      :song-title="currentSong?.title || ''"
      ref="reviewDialogRef"
      @confirm="onReviewConfirm"
      @cancel="onReviewCancel"
    />

    <!-- Explicit Content Dialog -->
    <ExplicitContentDialog
      v-if="showExplicitDialog"
      :song-title="currentSong?.title || ''"
      ref="explicitDialogRef"
      @confirm="onExplicitConfirm"
      @cancel="onExplicitCancel"
    />
  </div>
</template>

<style>
.scroll-container {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  width: 100%;
  /* Offset the whole scroll container below the fixed navbar so its
     boundingClientRect().top equals the navbar bottom. Use margin-top
     (not padding) so the element's top moves. Also reduce max-height
     so the content fits within the remaining viewport. */
  margin: 0;
  margin-top: var(--navbar-height, 0px);
  height: calc(var(--vh, 1vh) * 100 - var(--navbar-height, 0px));
  overflow-x: hidden;
  overflow-y: auto;
}

/* On small/narrow viewports where the fixed-top navbar is active, make
   the scroll container fixed so its top is exactly the navbar bottom.
   This avoids cumulative margins/padding from other layout elements. */
@media (max-width: 991px) {
  .scroll-container {
    position: fixed;
    top: var(--navbar-height, 0px);
    left: 0;
    right: 0;
    bottom: 0;
    margin: 0;
    max-height: none;
    overflow-x: hidden;
    overflow-y: auto;
    z-index: 1;
  }
}

/* When the fixed-top navbar is visible on small screens, add top padding
   so the navbar does not overlap the PDF viewer. The value is provided
   by --navbar-height (set in main.ts). Fallback to 56px. */
/* removed padding-top here; PdfViewer handles navbar offset */

.pdf-viewer {
  width: 100%;
  height: 100%;
  max-height: 100%;
  overflow: auto;
  display: block;
  margin: 0 auto;
}

/* On mobile, use full width since sidebar is collapsed */
@media (max-width: 991px) {
  .pdf-viewer {
    width: 100vw;
    max-width: 100vw;
    height: 100%;
    max-height: 100%;
    overflow: auto;
  }
}

/* Blur effect for explicit content warning */
.scroll-container.blur-content {
  filter: blur(10px);
  pointer-events: none;
}
</style>
