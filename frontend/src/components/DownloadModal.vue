<script setup lang="ts">
import { computed, ref } from 'vue'
import { Modal } from 'bootstrap'
import JSZip from 'jszip'
import type { Song, Instrument } from '@/types/types'
import { instruments } from '@/types/types'
import { getPdfDownloadUrl } from '@/utils/pdfUtils'

interface Props {
  song: Song | null
  currentInstrument: Instrument
  useTvSize?: boolean
  id?: string
}

const props = withDefaults(defineProps<Props>(), {
  useTvSize: false,
  id: 'downloadModal',
})

const modalElement = ref<HTMLElement | null>(null)
const isDownloadingAll = ref(false)

const hasTvSizeForSong = computed(() => {
  const tvSizePdfs = props.song?.pdfsTvSize
  if (!tvSizePdfs) return false
  return Object.values(tvSizePdfs).some((pdfUrl) => Boolean(pdfUrl?.trim()))
})

const isTvSizeDownload = computed(() => props.useTvSize && hasTvSizeForSong.value)

const selectedPdfs = computed(() => {
  const song = props.song
  if (!song) return {}

  if (isTvSizeDownload.value && song.pdfsTvSize) {
    return song.pdfsTvSize
  }

  return song.pdfs
})

const modalTitle = computed(() => {
  const baseTitle = props.song?.title || 'Sheet Music'
  return isTvSizeDownload.value ? `${baseTitle} (TV Size)` : baseTitle
})

const downloadVariantSuffix = computed(() => (isTvSizeDownload.value ? '-tv-size' : ''))

const availableInstruments = computed(() => {
  const pdfs = selectedPdfs.value
  return instruments.filter((instrument) => Boolean(pdfs[instrument]))
})

const resolvePdfPath = (instrument: Instrument) => {
  const pdfs = selectedPdfs.value
  return pdfs[instrument] || pdfs['C']
}

const downloadInstrument = (instrument: Instrument) => {
  const song = props.song
  if (!song) return

  const pdfPath = resolvePdfPath(instrument)
  if (!pdfPath) return

  const directUrl = getPdfDownloadUrl(pdfPath, { tvSize: isTvSizeDownload.value })
  const link = document.createElement('a')
  link.href = directUrl
  link.download = `${song.title}-${instrument}${downloadVariantSuffix.value}.pdf`
  link.click()
}

const downloadAll = () => {
  const song = props.song
  if (!song || isDownloadingAll.value) return

  const sanitizeFilename = (value: string) => value.replace(/[\\/:*?"<>|]/g, '').trim() || 'song'

  isDownloadingAll.value = true
  ;(async () => {
    try {
      const zip = new JSZip()
      const safeTitle = sanitizeFilename(song.title)

      for (const instrument of availableInstruments.value) {
        const pdfPath = resolvePdfPath(instrument)
        if (!pdfPath) continue

        const directUrl = getPdfDownloadUrl(pdfPath, { tvSize: isTvSizeDownload.value })
        const response = await fetch(directUrl)
        if (!response.ok) {
          throw new Error(`Failed to fetch ${pdfPath}`)
        }

        const bytes = await response.arrayBuffer()
        zip.file(`${safeTitle}-${instrument}${downloadVariantSuffix.value}.pdf`, bytes)
      }

      const blob = await zip.generateAsync({ type: 'blob' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `${safeTitle}${downloadVariantSuffix.value}-all-keys.zip`
      link.click()
      URL.revokeObjectURL(link.href)
    } catch (error) {
      console.error('Download All ZIP failed:', error)
    } finally {
      isDownloadingAll.value = false
    }
  })()
}

const hideModal = () => {
  if (!modalElement.value) return
  const instance = Modal.getOrCreateInstance(modalElement.value)
  instance.hide()
}

const startDownloadFlow = async () => {
  if (!props.song) return

  if (!modalElement.value) return
  const instance = Modal.getOrCreateInstance(modalElement.value)
  instance.show()
}

defineExpose({
  startDownloadFlow,
})
</script>

<template>
  <div
    ref="modalElement"
    class="modal fade"
    :id="props.id"
    tabindex="-1"
    :aria-labelledby="props.id + 'Label'"
    aria-hidden="true"
  >
    <div class="modal-dialog">
      <div class="modal-content bg-dark text-light">
        <div class="modal-header border-secondary">
          <h5 class="modal-title" :id="props.id + 'Label'">Download {{ modalTitle }}</h5>
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
            <p class="mb-3">Choose which key to download:</p>

            <div class="mb-3">
              <button
                type="button"
                class="btn btn-primary w-100"
                @click="downloadAll"
                :disabled="availableInstruments.length === 0 || isDownloadingAll"
              >
                <span
                  v-if="isDownloadingAll"
                  class="spinner-border spinner-border-sm me-2"
                  role="status"
                  aria-hidden="true"
                ></span>
                <i v-else class="bi bi-download me-2"></i>
                {{
                  isDownloadingAll
                    ? 'Preparing ZIP...'
                    : `Download All (${availableInstruments.length} files)`
                }}
              </button>
            </div>

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
