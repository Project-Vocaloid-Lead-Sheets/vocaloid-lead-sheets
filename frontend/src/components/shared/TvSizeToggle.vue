<template>
  <div v-if="hasTvSize" class="btn-group w-100" role="group" aria-label="Version toggle">
    <button
      type="button"
      :class="!useTvSize ? 'btn btn-sm btn-light' : 'btn btn-sm btn-outline-light'"
      @click="useTvSize = false"
    >
      Full
    </button>
    <button
      type="button"
      :class="useTvSize ? 'btn btn-sm btn-light' : 'btn btn-sm btn-outline-light'"
      @click="useTvSize = true"
    >
      TV Size
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Song } from '@/types/types'

interface Props {
  currentSong: Song | null | undefined
}

const props = defineProps<Props>()

const useTvSize = defineModel<boolean>('useTvSize', { required: true })

// Check if current song has any TV size PDFs available
const hasTvSize = computed(() => {
  if (!props.currentSong?.pdfsTvSize) return false
  return Object.keys(props.currentSong.pdfsTvSize).length > 0
})
</script>
