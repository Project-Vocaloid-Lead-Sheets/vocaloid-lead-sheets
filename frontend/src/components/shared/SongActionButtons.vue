<template>
  <div class="btn-group w-100" role="group" aria-label="Song actions">
    <button
      type="button"
      class="btn btn-outline-light btn-sm"
      data-bs-toggle="modal"
      :data-bs-target="downloadModalId"
      :disabled="!currentSong"
      title="Download PDF"
    >
      <i class="bi bi-download"></i>
      <span :class="downloadLabelClass">Download</span>
    </button>
    <button
      type="button"
      class="btn btn-outline-light btn-sm"
      @click="emit('watchOnYouTube')"
      :disabled="!currentSong?.videoLinks?.YouTube"
      title="Watch on YouTube"
    >
      <i class="bi bi-youtube"></i>
      <span :class="youtubeLabelClass">YouTube</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import type { Song } from '@/types/types'

interface Props {
  currentSong: Song | undefined
  downloadModalId: string
  downloadLabelClass?: string
  youtubeLabelClass?: string
}

withDefaults(defineProps<Props>(), {
  downloadLabelClass: 'd-none d-xl-inline ms-1',
  youtubeLabelClass: 'd-none d-xl-inline ms-1',
})

const emit = defineEmits<{
  watchOnYouTube: []
}>()
</script>
