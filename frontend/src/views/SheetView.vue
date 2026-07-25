<script setup lang="ts">
import type { Instrument } from '@/types/types'
import { computed, defineAsyncComponent, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import { getPdfDisplayUrl } from '@/utils/pdfUtils'
import { useSongsStore } from '@/stores/songs'
import { useSongFilters } from '@/scripts/useSongFilters'
import UnderReviewDialog from '@/components/UnderReviewDialog.vue'
import ExplicitContentDialog from '@/components/ExplicitContentDialog.vue'

const isClient = ref(!import.meta.env.SSR)
const PdfViewer = import.meta.env.SSR
  ? null
  : defineAsyncComponent(() => import('@/components/PdfViewer.vue'))

const route = useRoute()
const router = useRouter()
const instrument = computed(() => {
  const transposition = route.query.transposition
  return typeof transposition === 'string' ? (transposition as Instrument) : 'C'
})
const songSlug = computed(() => route.params.songSlug as string)

const songsStore = useSongsStore()
const { useTvSize } = useSongFilters()

//TODO: Add alias support with fixed PDF IDs/slugs
const currentSong = computed(() => songsStore.getSongBySlug(songSlug.value))

const hasTvSizeForCurrentSong = computed(() => {
  const tvSizePdfs = currentSong.value?.pdfsTvSize
  if (!tvSizePdfs) return false
  return Object.values(tvSizePdfs).some((pdfUrl) => Boolean(pdfUrl?.trim()))
})

const isTvSizeQueryEnabled = (value: unknown) => {
  if (Array.isArray(value)) return isTvSizeQueryEnabled(value[0])
  if (value === null) return true
  if (typeof value !== 'string') return false
  const normalized = value.trim().toLowerCase()
  return normalized === '' || normalized === '1' || normalized === 'true'
}

const syncTvSizeQueryParam = (enabled: boolean) => {
  const nextQuery: LocationQueryRaw = {}
  const currentTransposition =
    typeof route.query.transposition === 'string' ? route.query.transposition : null

  if (currentTransposition && currentTransposition !== 'C') {
    nextQuery.transposition = currentTransposition
  }

  if (enabled) {
    nextQuery.tv_size = null
  } else if (typeof route.query.tv_size === 'string') {
    nextQuery.tv_size = route.query.tv_size
  }

  router.replace({ query: nextQuery })
}

// Review mode dialog handling
const showReviewDialog = ref(false)
const reviewDialogRef = ref<InstanceType<typeof UnderReviewDialog>>()

// Explicit content dialog handling
const showExplicitDialog = ref(false)
const explicitDialogRef = ref<InstanceType<typeof ExplicitContentDialog>>()
// Track all explicit songs that have been acknowledged this session
const acknowledgedExplicitSongs = ref<Set<string>>(new Set())
const previousInAppPath = ref<string | null>(null)

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
  router.push('/')
}

const isSameOriginRoute = (target: string | null | undefined) => {
  if (!target) return false
  if (target.startsWith('/')) return true

  try {
    return new URL(target).origin === window.location.origin
  } catch {
    return false
  }
}

const shouldUseBrowserBackWithinSite = () => {
  const state = window.history.state as { back?: string | null } | null
  if (isSameOriginRoute(state?.back)) return true

  return isSameOriginRoute(document.referrer)
}

const isExplicitSong = computed(() => {
  return currentSong.value ? songsStore.isExplicitSong(currentSong.value) : false
})

const requiresExplicitAcknowledgement = computed(() => {
  if (!currentSong.value) return false
  if (!isExplicitSong.value) return false
  if (instrument.value !== 'Vocals') return false
  return !acknowledgedExplicitSongs.value.has(songSlug.value)
})

const shouldBlurContent = computed(() => {
  return showExplicitDialog.value || requiresExplicitAcknowledgement.value
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

  if (previousInAppPath.value) {
    router.push(previousInAppPath.value)
    return
  }

  if (shouldUseBrowserBackWithinSite()) {
    router.back()
    return
  }

  router.push('/')
}

const pdfSource = computed(() => {
  // First, try TV size if enabled
  if (useTvSize.value && currentSong.value?.pdfsTvSize) {
    const tvSizePdfs = currentSong.value.pdfsTvSize
    const tvSizeUrl = tvSizePdfs[instrument.value] || tvSizePdfs['C']
    if (tvSizeUrl) return getPdfDisplayUrl(tvSizeUrl)
  }

  // Fall back to regular PDFs
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

watch(
  () => route.fullPath,
  (newPath, oldPath) => {
    if (oldPath && oldPath !== newPath) {
      previousInAppPath.value = oldPath
    }
  },
)

watch(
  () => route.query.tv_size,
  () => {
    const queryEnabled = isTvSizeQueryEnabled(route.query.tv_size)
    const shouldUseTvSize = queryEnabled && hasTvSizeForCurrentSong.value

    if (useTvSize.value !== shouldUseTvSize) {
      useTvSize.value = shouldUseTvSize
    }

    if (queryEnabled && !hasTvSizeForCurrentSong.value) {
      syncTvSizeQueryParam(false)
    }
  },
  { immediate: true },
)

watch(
  [useTvSize, hasTvSizeForCurrentSong],
  () => {
    if (useTvSize.value && !hasTvSizeForCurrentSong.value) {
      useTvSize.value = false
      return
    }

    const queryEnabled = isTvSizeQueryEnabled(route.query.tv_size)
    if (useTvSize.value !== queryEnabled) {
      syncTvSizeQueryParam(useTvSize.value)
    }
  },
  { immediate: true },
)

onMounted(() => {
  isClient.value = true
  checkReviewConfirmation()
  checkExplicitDialog()
})
</script>

<template>
  <div>
    <div class="scroll-container bg-secondary pt-0" :class="{ 'blur-content': shouldBlurContent }">
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
        <component
          :is="PdfViewer"
          v-if="isClient && PdfViewer && pdfSource"
          :source="pdfSource"
          class="pdf-viewer"
        />
        <!-- Show message when no PDF is available -->
        <div v-else-if="!pdfSource" class="d-flex justify-content-center align-items-center h-100">
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
