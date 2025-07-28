<script setup lang="ts">
import { computed } from 'vue'
import type { Song, Instrument } from '@/types/types'
import { instruments } from '@/types/types'
import { getPdfDownloadUrl } from '@/utils/pdfUtils'

interface Props {
  song: Song | null
  currentInstrument: Instrument
  id?: string
}

const props = withDefaults(defineProps<Props>(), {
  id: 'downloadModal',
})

// Get available instruments to download
const availableInstruments = computed(() => {
  if (!props.song) return []
  return instruments.filter((instrument) => props.song!.pdfs[instrument])
})

// Download a specific instrument PDF
const downloadInstrument = (instrument: Instrument) => {
  const song = props.song
  if (!song?.pdfs[instrument]) return

  const pdfPath = song.pdfs[instrument]
  const directUrl = getPdfDownloadUrl(pdfPath)
  const link = document.createElement('a')
  link.href = directUrl
  link.download = `${song.title}-${instrument}.pdf`
  link.click()
}

// Download all available PDFs at once (not a ZIP)
const downloadAll = () => {
  const song = props.song
  if (!song) return

  // Stagger downloads slightly to not overwhelm browser
  availableInstruments.value.forEach((instrument) => {
    setTimeout(
      () => {
        downloadInstrument(instrument)
      },
      100 * instruments.indexOf(instrument),
    )
  })
}
</script>

<template>
  <div
    class="modal fade"
    :id="props.id"
    tabindex="-1"
    :aria-labelledby="props.id + 'Label'"
    aria-hidden="true"
  >
    <div class="modal-dialog">
      <div class="modal-content bg-dark text-light">
        <div class="modal-header border-secondary">
          <h5 class="modal-title" :id="props.id + 'Label'">
            Download {{ song?.title || 'Sheet Music' }}
          </h5>
          <button
            type="button"
            class="btn-close btn-close-white"
            data-bs-dismiss="modal"
            aria-label="Close"
          ></button>
        </div>
        <div class="modal-body">
          <div v-if="!song" class="text-center text-muted">No song selected</div>
          <div v-else>
            <p class="mb-3">Choose which version to download:</p>

            <!-- Download All Button (hidden for now) -->
            <!--
            <div class="mb-3">
              <button
                type="button"
                class="btn btn-primary w-100"
                @click="downloadAll"
                :disabled="availableInstruments.length === 0"
              >
                <i class="bi bi-download me-2"></i>
                Download All ({{ availableInstruments.length }} files)
              </button>
            </div>
            -->

            <hr class="border-secondary" />

            <!-- Individual Instrument Downloads -->
            <div class="row g-2">
              <div v-for="instrument in availableInstruments" :key="instrument" class="col-6">
                <button
                  type="button"
                  class="btn btn-outline-light w-100"
                  @click="downloadInstrument(instrument)"
                  :class="{ 'btn-light text-dark': instrument === currentInstrument }"
                >
                  <i class="bi bi-download me-1"></i>
                  {{ instrument }}
                  <span v-if="instrument === currentInstrument" class="badge bg-primary ms-1">
                    Current
                  </span>
                </button>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer border-secondary">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>
