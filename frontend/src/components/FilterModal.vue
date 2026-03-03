<script setup lang="ts">
import { ref, computed } from 'vue'
import { useSongFilters } from '@/scripts/useSongFilters'

const {
  // Selected by user in filter modal
  selectedLabels,
  selectedProducers,
  selectedSingers,
  dateRange,
  lengthRange,
  lengthFilterSource,
  // Calculated from all song metadata
  availableLabels,
  availableProducers,
  availableSingers,
  getLengthBoundsForSource,
  formatSecondsAsLength,
} = useSongFilters()

// Staged filter state for tracking user editing in-modal
const tempSelectedLabels = ref<string[]>([])
const tempSelectedProducers = ref<string[]>([])
const tempSelectedSingers = ref<string[]>([])
const tempDateRange = ref<{ start: string; end: string }>({ start: '', end: '' })
const tempLengthRange = ref<{ min: number | null; max: number | null }>({ min: null, max: null })
const tempLengthFilterSource = ref<'full' | 'tv' | 'either'>('full')

// Initialize modal with current filter values
const initializeTempFilters = () => {
  tempSelectedLabels.value = [...selectedLabels.value]
  tempSelectedProducers.value = [...selectedProducers.value]
  tempSelectedSingers.value = [...selectedSingers.value]
  tempDateRange.value = { ...dateRange.value }
  tempLengthFilterSource.value = lengthFilterSource.value
  tempLengthRange.value = { ...lengthRange.value }
  syncLengthInputsFromTempRange()
}

// Apply staged filters to actual filter state
const applyFilters = () => {
  selectedLabels.value = [...tempSelectedLabels.value]
  selectedProducers.value = [...tempSelectedProducers.value]
  selectedSingers.value = [...tempSelectedSingers.value]
  dateRange.value = { ...tempDateRange.value }
  lengthFilterSource.value = tempLengthFilterSource.value

  const minBound = sliderMin.value
  const maxBound = sliderMax.value
  const selectedMin = tempLengthRange.value.min
  const selectedMax = tempLengthRange.value.max

  const isFullRange =
    selectedMin !== null &&
    selectedMax !== null &&
    selectedMin <= minBound &&
    selectedMax >= maxBound

  lengthRange.value = isFullRange ? { min: null, max: null } : { ...tempLengthRange.value }
}

// Input field refs and states
const labelInput = ref('')
const producerInput = ref('')
const singerInput = ref('')
const showLabelDropdown = ref(false)
const showProducerDropdown = ref(false)
const showSingerDropdown = ref(false)

// Add computed properties for all fields to suggest autocompletes based on input so far
const filteredLabels = computed(() => {
  return availableLabels.value.filter(
    (label) =>
      label.toLowerCase().includes(labelInput.value.toLowerCase()) &&
      !tempSelectedLabels.value.includes(label),
  )
})

const filteredProducers = computed(() => {
  return availableProducers.value.filter(
    (producer) =>
      producer.toLowerCase().includes(producerInput.value.toLowerCase()) &&
      !tempSelectedProducers.value.includes(producer),
  )
})

const filteredSingers = computed(() => {
  return availableSingers.value.filter(
    (singer) =>
      singer.toLowerCase().includes(singerInput.value.toLowerCase()) &&
      !tempSelectedSingers.value.includes(singer),
  )
})

// Stage filter tags by adding them from the input fields
const addLabel = (label: string) => {
  if (!tempSelectedLabels.value.includes(label)) {
    tempSelectedLabels.value.push(label)
  }
  labelInput.value = ''
  showLabelDropdown.value = true
}

const addProducer = (producer: string) => {
  if (!tempSelectedProducers.value.includes(producer)) {
    tempSelectedProducers.value.push(producer)
  }
  producerInput.value = ''
  showProducerDropdown.value = true
}

const addSinger = (singer: string) => {
  if (!tempSelectedSingers.value.includes(singer)) {
    tempSelectedSingers.value.push(singer)
  }
  singerInput.value = ''
  showSingerDropdown.value = true
}

// Remove tags
const removeLabel = (label: string) => {
  const index = tempSelectedLabels.value.indexOf(label)
  if (index > -1) {
    tempSelectedLabels.value.splice(index, 1)
  }
}

const removeProducer = (producer: string) => {
  const index = tempSelectedProducers.value.indexOf(producer)
  if (index > -1) {
    tempSelectedProducers.value.splice(index, 1)
  }
}

const removeSinger = (singer: string) => {
  const index = tempSelectedSingers.value.indexOf(singer)
  if (index > -1) {
    tempSelectedSingers.value.splice(index, 1)
  }
}

// Keyboard navigation handlers
const highlightedLabelIndex = ref(-1)
const highlightedProducerIndex = ref(-1)
const highlightedSingerIndex = ref(-1)

const handleLabelKeydown = (event: KeyboardEvent) => {
  if (!showLabelDropdown.value || filteredLabels.value.length === 0) return

  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      highlightedLabelIndex.value = Math.min(
        highlightedLabelIndex.value + 1,
        filteredLabels.value.length - 1,
      )
      break
    case 'ArrowUp':
      event.preventDefault()
      highlightedLabelIndex.value = Math.max(highlightedLabelIndex.value - 1, -1)
      break
    case 'Enter':
      event.preventDefault()
      if (highlightedLabelIndex.value >= 0) {
        addLabel(filteredLabels.value[highlightedLabelIndex.value])
        highlightedLabelIndex.value = -1
      }
      break
    case 'Escape':
      showLabelDropdown.value = false
      highlightedLabelIndex.value = -1
      break
  }
}

const handleProducerKeydown = (event: KeyboardEvent) => {
  if (!showProducerDropdown.value || filteredProducers.value.length === 0) return

  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      highlightedProducerIndex.value = Math.min(
        highlightedProducerIndex.value + 1,
        filteredProducers.value.length - 1,
      )
      break
    case 'ArrowUp':
      event.preventDefault()
      highlightedProducerIndex.value = Math.max(highlightedProducerIndex.value - 1, -1)
      break
    case 'Enter':
      event.preventDefault()
      if (highlightedProducerIndex.value >= 0) {
        addProducer(filteredProducers.value[highlightedProducerIndex.value])
        highlightedProducerIndex.value = -1
      }
      break
    case 'Escape':
      showProducerDropdown.value = false
      highlightedProducerIndex.value = -1
      break
  }
}

const handleSingerKeydown = (event: KeyboardEvent) => {
  if (!showSingerDropdown.value || filteredSingers.value.length === 0) return

  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      highlightedSingerIndex.value = Math.min(
        highlightedSingerIndex.value + 1,
        filteredSingers.value.length - 1,
      )
      break
    case 'ArrowUp':
      event.preventDefault()
      highlightedSingerIndex.value = Math.max(highlightedSingerIndex.value - 1, -1)
      break
    case 'Enter':
      event.preventDefault()
      if (highlightedSingerIndex.value >= 0) {
        addSinger(filteredSingers.value[highlightedSingerIndex.value])
        highlightedSingerIndex.value = -1
      }
      break
    case 'Escape':
      showSingerDropdown.value = false
      highlightedSingerIndex.value = -1
      break
  }
}

// Reset highlighted indices when input changes
const resetHighlightedIndices = () => {
  highlightedLabelIndex.value = -1
  highlightedProducerIndex.value = -1
  highlightedSingerIndex.value = -1
}

const clearAllFilters = () => {
  tempSelectedLabels.value = []
  tempSelectedProducers.value = []
  tempSelectedSingers.value = []
  tempDateRange.value = { start: '', end: '' }
  tempLengthFilterSource.value = 'full'
  tempLengthRange.value = { min: sliderMin.value, max: sliderMax.value }
  syncLengthInputsFromTempRange()
}

const sliderBounds = computed(() => getLengthBoundsForSource(tempLengthFilterSource.value))
const sliderMin = computed(() => sliderBounds.value.min)
const sliderMax = computed(() => sliderBounds.value.max)
const lengthMinInput = ref('')
const lengthMaxInput = ref('')

const resolvedMinLength = computed(() => tempLengthRange.value.min ?? sliderMin.value)
const resolvedMaxLength = computed(() => tempLengthRange.value.max ?? sliderMax.value)

const clampLengthValue = (value: number) =>
  Math.min(Math.max(value, sliderMin.value), sliderMax.value)

const updateLengthInputs = (minSeconds: number, maxSeconds: number) => {
  lengthMinInput.value = formatSecondsAsLength(minSeconds)
  lengthMaxInput.value = formatSecondsAsLength(maxSeconds)
}

const setTempLengthRange = (minSeconds: number, maxSeconds: number) => {
  const clampedMin = clampLengthValue(minSeconds)
  const clampedMax = clampLengthValue(maxSeconds)
  const normalizedMin = Math.min(clampedMin, clampedMax)
  const normalizedMax = Math.max(clampedMin, clampedMax)

  tempLengthRange.value = { min: normalizedMin, max: normalizedMax }
  updateLengthInputs(normalizedMin, normalizedMax)
}

const parseLengthTextInput = (value: string): number | null => {
  const match = value.trim().match(/^(\d+):(\d{1,2})$/)
  if (!match) return null

  const minutes = Number(match[1])
  const seconds = Number(match[2])

  if (Number.isNaN(minutes) || Number.isNaN(seconds) || seconds >= 60) {
    return null
  }

  return minutes * 60 + seconds
}

const syncLengthInputsFromTempRange = () => {
  const minSeconds = tempLengthRange.value.min ?? sliderMin.value
  const maxSeconds = tempLengthRange.value.max ?? sliderMax.value
  updateLengthInputs(minSeconds, maxSeconds)
}

const displayMinLength = computed(() => {
  const value = resolvedMinLength.value
  return formatSecondsAsLength(value)
})

const displayMaxLength = computed(() => {
  const value = resolvedMaxLength.value
  return formatSecondsAsLength(value)
})

const minThumbPosition = computed(() => {
  const range = sliderMax.value - sliderMin.value
  if (range <= 0) return 0
  return ((resolvedMinLength.value - sliderMin.value) / range) * 100
})

const maxThumbPosition = computed(() => {
  const range = sliderMax.value - sliderMin.value
  if (range <= 0) return 100
  return ((resolvedMaxLength.value - sliderMin.value) / range) * 100
})

const onMinLengthSliderInput = (event: Event) => {
  const nextValue = Number((event.target as HTMLInputElement).value)
  setTempLengthRange(Math.min(nextValue, resolvedMaxLength.value), resolvedMaxLength.value)
}

const onMaxLengthSliderInput = (event: Event) => {
  const nextValue = Number((event.target as HTMLInputElement).value)
  setTempLengthRange(resolvedMinLength.value, Math.max(nextValue, resolvedMinLength.value))
}

const onMinLengthTextCommit = () => {
  const parsedSeconds = parseLengthTextInput(lengthMinInput.value)
  if (parsedSeconds === null) {
    lengthMinInput.value = formatSecondsAsLength(resolvedMinLength.value)
    return
  }

  const clampedMin = clampLengthValue(parsedSeconds)
  setTempLengthRange(Math.min(clampedMin, resolvedMaxLength.value), resolvedMaxLength.value)
}

const onMaxLengthTextCommit = () => {
  const parsedSeconds = parseLengthTextInput(lengthMaxInput.value)
  if (parsedSeconds === null) {
    lengthMaxInput.value = formatSecondsAsLength(resolvedMaxLength.value)
    return
  }

  const clampedMax = clampLengthValue(parsedSeconds)
  setTempLengthRange(resolvedMinLength.value, Math.max(clampedMax, resolvedMinLength.value))
}

const onLengthSourceChange = () => {
  tempLengthRange.value = { min: sliderMin.value, max: sliderMax.value }
  syncLengthInputsFromTempRange()
}

// Initialize temp filters when component mounts
initializeTempFilters()

// Helper functions for blur events
const hideLabelDropdown = () => {
  setTimeout(() => {
    showLabelDropdown.value = false
    highlightedLabelIndex.value = -1
  }, 200)
}

const hideProducerDropdown = () => {
  setTimeout(() => {
    showProducerDropdown.value = false
    highlightedProducerIndex.value = -1
  }, 200)
}

const hideSingerDropdown = () => {
  setTimeout(() => {
    showSingerDropdown.value = false
    highlightedSingerIndex.value = -1
  }, 200)
}
</script>

<template>
  <div class="modal fade" tabindex="-1" @shown.bs.modal="initializeTempFilters">
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <!-- Filter Modal Header -->
        <div class="modal-header">
          <h5 class="modal-title fs-5">Advanced Filter</h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Close"
          ></button>
        </div>
        <!-- Filter Modal Body -->
        <div class="modal-body">
          <!-- Singers Section -->
          <div class="mb-4">
            <h6 class="fw-bold mb-2"><i class="bi bi-mic-fill me-2"></i>Singers</h6>
            <!-- Selected Singers -->
            <div v-if="tempSelectedSingers.length > 0" class="mb-2">
              <span
                v-for="singer in tempSelectedSingers"
                :key="singer"
                class="badge bg-info me-1 mb-1"
              >
                {{ singer }}
                <button
                  type="button"
                  class="btn-close btn-close-white ms-1"
                  style="font-size: 0.65em"
                  @click="removeSinger(singer)"
                ></button>
              </span>
            </div>
            <!-- Input Field -->
            <div class="position-relative">
              <input
                type="text"
                class="form-control"
                placeholder="Type to search or add singers..."
                v-model="singerInput"
                @keydown="handleSingerKeydown"
                @input="resetHighlightedIndices"
                @focus="showSingerDropdown = true"
                @blur="hideSingerDropdown"
              />
              <!-- Dropdown -->
              <div
                v-if="showSingerDropdown && filteredSingers.length > 0"
                class="dropdown-menu show position-absolute w-100"
                style="top: 100%; z-index: 1000"
              >
                <button
                  v-for="(singer, index) in filteredSingers"
                  :key="singer"
                  type="button"
                  class="dropdown-item"
                  :class="{ active: index === highlightedSingerIndex }"
                  @click="addSinger(singer)"
                >
                  {{ singer }}
                </button>
              </div>
            </div>
          </div>

          <!-- Producers Section -->
          <div class="mb-4">
            <h6 class="fw-bold mb-2"><i class="bi bi-person-fill me-2"></i>Producers</h6>
            <!-- Selected Producers -->
            <div v-if="tempSelectedProducers.length > 0" class="mb-2">
              <span
                v-for="producer in tempSelectedProducers"
                :key="producer"
                class="badge bg-warning text-dark me-1 mb-1"
              >
                {{ producer }}
                <button
                  type="button"
                  class="btn-close ms-1"
                  style="font-size: 0.65em"
                  @click="removeProducer(producer)"
                ></button>
              </span>
            </div>
            <!-- Input Field -->
            <div class="position-relative">
              <input
                type="text"
                class="form-control"
                placeholder="Type to search or add producers..."
                v-model="producerInput"
                @keydown="handleProducerKeydown"
                @input="resetHighlightedIndices"
                @focus="showProducerDropdown = true"
                @blur="hideProducerDropdown"
              />
              <!-- Dropdown -->
              <div
                v-if="showProducerDropdown && filteredProducers.length > 0"
                class="dropdown-menu show position-absolute w-100"
                style="top: 100%; z-index: 1000"
              >
                <button
                  v-for="(producer, index) in filteredProducers"
                  :key="producer"
                  type="button"
                  class="dropdown-item"
                  :class="{ active: index === highlightedProducerIndex }"
                  @click="addProducer(producer)"
                >
                  {{ producer }}
                </button>
              </div>
            </div>
          </div>

          <!-- Labels Section -->
          <div class="mb-4">
            <h6 class="fw-bold mb-2"><i class="bi bi-tags me-2"></i>Labels</h6>
            <!-- Selected Labels -->
            <div v-if="tempSelectedLabels.length > 0" class="mb-2">
              <span
                v-for="label in tempSelectedLabels"
                :key="label"
                class="badge me-1 mb-1"
                style="background-color: #e91e63; color: white"
              >
                {{ label }}
                <button
                  type="button"
                  class="btn-close btn-close-white ms-1"
                  style="font-size: 0.65em"
                  @click="removeLabel(label)"
                ></button>
              </span>
            </div>
            <!-- Input Field -->
            <div class="position-relative">
              <input
                type="text"
                class="form-control"
                placeholder="Type to search or add labels..."
                v-model="labelInput"
                @keydown="handleLabelKeydown"
                @input="resetHighlightedIndices"
                @focus="showLabelDropdown = true"
                @blur="hideLabelDropdown"
              />
              <!-- Dropdown -->
              <div
                v-if="showLabelDropdown && filteredLabels.length > 0"
                class="dropdown-menu show position-absolute w-100"
                style="top: 100%; z-index: 1000"
              >
                <button
                  v-for="(label, index) in filteredLabels"
                  :key="label"
                  type="button"
                  class="dropdown-item"
                  :class="{ active: index === highlightedLabelIndex }"
                  @click="addLabel(label)"
                >
                  {{ label }}
                </button>
              </div>
            </div>
          </div>

          <!-- Date Range Section -->
          <div class="mb-4">
            <h6 class="fw-bold mb-2">
              <i class="bi bi-calendar-range me-2"></i>Release Date Range
            </h6>
            <div class="row">
              <div class="col-md-6">
                <label for="startDate" class="form-label">From</label>
                <input
                  id="startDate"
                  type="date"
                  class="form-control"
                  v-model="tempDateRange.start"
                />
              </div>
              <div class="col-md-6">
                <label for="endDate" class="form-label">To</label>
                <input id="endDate" type="date" class="form-control" v-model="tempDateRange.end" />
              </div>
            </div>
          </div>

          <!-- Length Range Section -->
          <div class="mb-4" v-if="sliderMax > 0">
            <h6 class="fw-bold mb-2"><i class="bi bi-clock me-2"></i>Length Range</h6>
            <div class="mb-3">
              <label class="form-label small mb-1">Length Source</label>
              <div class="btn-group btn-group-sm w-100" role="group" aria-label="Length source">
                <input
                  id="lengthSourceEither"
                  type="radio"
                  class="btn-check"
                  name="lengthSource"
                  value="either"
                  v-model="tempLengthFilterSource"
                  @change="onLengthSourceChange"
                />
                <label class="btn btn-outline-secondary" for="lengthSourceEither">Either</label>

                <input
                  id="lengthSourceFull"
                  type="radio"
                  class="btn-check"
                  name="lengthSource"
                  value="full"
                  v-model="tempLengthFilterSource"
                  @change="onLengthSourceChange"
                />
                <label class="btn btn-outline-secondary" for="lengthSourceFull">Full Version</label>

                <input
                  id="lengthSourceTv"
                  type="radio"
                  class="btn-check"
                  name="lengthSource"
                  value="tv"
                  v-model="tempLengthFilterSource"
                  @change="onLengthSourceChange"
                />
                <label class="btn btn-outline-secondary" for="lengthSourceTv">TV Size</label>
              </div>
            </div>
            <div class="small text-muted mb-2">
              {{ displayMinLength }} to {{ displayMaxLength }}
            </div>
            <div class="dual-range mb-3">
              <div class="dual-range__track"></div>
              <div
                class="dual-range__fill"
                :style="{
                  left: `${minThumbPosition}%`,
                  width: `${Math.max(maxThumbPosition - minThumbPosition, 0)}%`,
                }"
              ></div>
              <input
                type="range"
                class="dual-range__input"
                :min="sliderMin"
                :max="sliderMax"
                :value="resolvedMinLength"
                @input="onMinLengthSliderInput"
                aria-label="Minimum length"
              />
              <input
                type="range"
                class="dual-range__input"
                :min="sliderMin"
                :max="sliderMax"
                :value="resolvedMaxLength"
                @input="onMaxLengthSliderInput"
                aria-label="Maximum length"
              />
            </div>
            <div class="row g-2">
              <div class="col-6">
                <label class="form-label small mb-1">Min (mm:ss)</label>
                <input
                  type="text"
                  class="form-control form-control-sm font-monospace"
                  v-model="lengthMinInput"
                  placeholder="0:00"
                  @blur="onMinLengthTextCommit"
                  @keydown.enter.prevent="onMinLengthTextCommit"
                />
              </div>
              <div class="col-6">
                <label class="form-label small mb-1">Max (mm:ss)</label>
                <input
                  type="text"
                  class="form-control form-control-sm font-monospace"
                  v-model="lengthMaxInput"
                  placeholder="0:00"
                  @blur="onMaxLengthTextCommit"
                  @keydown.enter.prevent="onMaxLengthTextCommit"
                />
              </div>
            </div>
          </div>
        </div>
        <!-- Filter Modal Footer -->
        <div class="modal-footer">
          <button type="button" class="btn btn-danger me-auto" @click="clearAllFilters">
            <i class="bi bi-x-circle me-1"></i>Clear All
          </button>
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
            <i class="bi bi-x-lg me-1"></i>Cancel
          </button>
          <button
            type="button"
            class="btn btn-primary"
            @click="applyFilters"
            data-bs-dismiss="modal"
          >
            <i class="bi bi-funnel me-1"></i>Apply Filters
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dual-range {
  position: relative;
  height: 2rem;
  display: flex;
  align-items: center;
}

.dual-range__track,
.dual-range__fill {
  position: absolute;
  height: 0.35rem;
  border-radius: 999px;
}

.dual-range__track {
  width: 100%;
  background: var(--bs-border-color);
}

.dual-range__fill {
  background: var(--bs-primary);
}

.dual-range__input {
  position: absolute;
  width: 100%;
  margin: 0;
  background: transparent;
  pointer-events: none;
  -webkit-appearance: none;
  appearance: none;
}

.dual-range__input::-webkit-slider-runnable-track {
  height: 0.35rem;
  background: transparent;
}

.dual-range__input::-webkit-slider-thumb {
  width: 1rem;
  height: 1rem;
  margin-top: -0.325rem;
  border: 0;
  border-radius: 50%;
  background: var(--bs-primary);
  pointer-events: auto;
  -webkit-appearance: none;
}

.dual-range__input::-moz-range-track {
  height: 0.35rem;
  background: transparent;
}

.dual-range__input::-moz-range-thumb {
  width: 1rem;
  height: 1rem;
  border: 0;
  border-radius: 50%;
  background: var(--bs-primary);
  pointer-events: auto;
}
</style>
