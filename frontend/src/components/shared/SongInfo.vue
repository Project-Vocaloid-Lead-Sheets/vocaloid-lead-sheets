<template>
  <div class="d-inline-flex align-items-center">
    <button
      type="button"
      class="btn btn-link p-0 text-reset song-metadata-btn"
      title="Show song metadata"
      aria-label="Show song metadata"
      @click="openSongMetadata"
    >
      <i class="bi bi-info-circle"></i>
    </button>

    <div
      v-if="isMetadataModalOpen"
      class="modal fade show d-block"
      tabindex="-1"
      role="dialog"
      aria-modal="true"
      @click.self="closeSongMetadata"
    >
      <div class="modal-dialog modal-lg modal-dialog-scrollable" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Song Info</h5>
            <button
              type="button"
              class="btn-close"
              aria-label="Close"
              @click="closeSongMetadata"
            ></button>
          </div>
          <div class="modal-body">
            <div class="song-metadata-grid">
              <div v-for="field in metadataFields" :key="field.key" class="song-metadata-row">
                <div class="song-metadata-label">{{ field.label }}</div>
                <div class="song-metadata-value">
                  <template v-if="field.lines.length > 1">
                    <div v-for="(line, index) in field.lines" :key="`${field.key}-${index}`">
                      <a
                        v-if="line.href"
                        :href="line.href"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {{ line.text }}
                      </a>
                      <template v-else>{{ line.text }}</template>
                    </div>
                  </template>
                  <template v-else>
                    <a
                      v-if="field.lines[0]?.href"
                      :href="field.lines[0].href"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {{ field.lines[0].text }}
                    </a>
                    <template v-else>{{ field.lines[0]?.text }}</template>
                  </template>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="closeSongMetadata">
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="isMetadataModalOpen" class="modal-backdrop fade show"></div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Song } from '@/types/types'

type MetadataField = {
  key: string
  label: string
  lines: MetadataLine[]
}

type MetadataLine = {
  text: string
  href?: string
}

const props = defineProps<{
  song: Song
}>()

const isMetadataModalOpen = ref(false)

const formatMetadataLabel = (key: string) => {
  if (key === 'bpm') return 'BPM'
  if (key === 'tvSizeLength') return 'TV Size Length'
  if (key === 'updatedAt') return 'Last Updated'
  if (key.toLowerCase() === 'youtube') return 'YouTube'

  return key
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

const isHttpLink = (value: string) => /^https?:\/\//i.test(value)

const emptyLine = (): MetadataLine[] => [{ text: '—' }]

const formatReleaseDate = (value: string) => {
  if (!/^\d{8}$/.test(value)) return value
  const year = value.slice(0, 4)
  const month = value.slice(4, 6)
  const day = value.slice(6, 8)
  return `${year}-${month}-${day}`
}

const formatIsoDateOnly = (value: string) => {
  const match = value.match(/^(\d{4}-\d{2}-\d{2})/)
  return match ? match[1] : value
}

const formatStatus = (value: string) =>
  value
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())

const normalizeMetadataValue = (key: string, value: unknown): MetadataLine[] => {
  if (value === null) return emptyLine()

  if (typeof value === 'string') {
    const trimmedValue = value.trim()
    if (!trimmedValue) return emptyLine()
    if (key === 'releaseDate') return [{ text: formatReleaseDate(trimmedValue) }]
    if (key === 'updatedAt') return [{ text: formatIsoDateOnly(trimmedValue) }]
    if (key === 'status') return [{ text: formatStatus(trimmedValue) }]
    if (isHttpLink(trimmedValue)) return [{ text: trimmedValue, href: trimmedValue }]
    return [{ text: trimmedValue }]
  }

  if (typeof value === 'number' || typeof value === 'boolean') {
    return [{ text: String(value) }]
  }

  if (Array.isArray(value)) {
    const lines = value
      .map((entry) => String(entry).trim())
      .filter((entry) => entry.length > 0)
      .map((entry) => ({ text: entry, href: isHttpLink(entry) ? entry : undefined }))
    return lines.length > 0 ? lines : emptyLine()
  }

  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
      .filter(
        ([, entryValue]) =>
          entryValue !== undefined && entryValue !== null && String(entryValue).trim() !== '',
      )
      .map(([entryKey, entryValue]) => {
        const entryText = String(entryValue).trim()
        return {
          text: isHttpLink(entryText) ? formatMetadataLabel(entryKey) : `${entryKey}: ${entryText}`,
          href: isHttpLink(entryText) ? entryText : undefined,
        }
      })

    return entries.length > 0 ? entries : emptyLine()
  }

  return emptyLine()
}

const metadataFields = computed<MetadataField[]>(() => {
  const excludedKeys = new Set(['pdfs', 'pdfsTvSize', 'pdfChecksums', 'links', 'syncedAt'])
  const preferredOrder = [
    'title',
    'alternativeNames',
    'producer',
    'additionalProducers',
    'singer',
    'additionalVoices',
    'releaseDate',
    'length',
    'tvSizeLength',
    'bpm',
    'labels',
    'transcriber',
    'videoLinks',
    'status',
    'updatedAt',
  ]

  const sanitizedEntries = Object.entries(props.song)
    .filter(([key, value]) => !excludedKeys.has(key) && value !== undefined)
    .sort(([a], [b]) => {
      const aIndex = preferredOrder.indexOf(a)
      const bIndex = preferredOrder.indexOf(b)
      if (aIndex === -1 && bIndex === -1) return a.localeCompare(b)
      if (aIndex === -1) return 1
      if (bIndex === -1) return -1
      return aIndex - bIndex
    })

  return sanitizedEntries.map(([key, value]) => ({
    key,
    label: formatMetadataLabel(key),
    lines: normalizeMetadataValue(key, value),
  }))
})

const openSongMetadata = () => {
  isMetadataModalOpen.value = true
}

const closeSongMetadata = () => {
  isMetadataModalOpen.value = false
}
</script>

<style scoped>
.song-metadata-btn {
  line-height: 1;
}

.song-metadata-grid {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.song-metadata-row {
  display: grid;
  grid-template-columns: 170px 1fr;
  gap: 0.75rem;
  align-items: start;
  padding: 0.5rem 0.25rem;
  border-bottom: 1px solid var(--bs-border-color-translucent);
}

.song-metadata-row:last-child {
  border-bottom: 0;
}

.song-metadata-label {
  font-weight: 600;
  color: var(--bs-secondary-color);
}

.song-metadata-value {
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 576px) {
  .song-metadata-row {
    grid-template-columns: 1fr;
    gap: 0.25rem;
  }
}
</style>
