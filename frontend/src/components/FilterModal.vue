<script setup lang="ts">
import { ref, computed, useId } from 'vue'
import { useSongFilters } from '@/scripts/useSongFilters'
import DualRangeSlider from '@/components/shared/DualRangeSlider.vue'
import TagFilter from '@/components/shared/TagFilter.vue'
import { describeKey, filterMusicalKeys, getKeyQueryOption } from '@/utils/musicalKeys'
import { difficultyCriteria } from '@/types/types'
import type { DifficultyCriterion, DifficultyRanges } from '@/types/types'
import {
  cloneDifficultyRanges,
  createDifficultyRanges,
  difficultyLabels,
  difficultyDescriptions,
} from '@/utils/songMetadata'

// Keep Bootstrap's dotted event name intact instead of treating it as Vue modifiers.
const modalShowEvent = 'show.bs.modal'
const difficultyDescriptionId = useId()

const {
  // Selected by user in filter modal
  selectedLabels,
  selectedProducers,
  selectedSingers,
  includedKeys,
  excludedKeys,
  difficultyRanges,
  difficultySectionExpanded,
  keySectionExpanded,
  availableKeys,
  difficultyBounds,
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
const tempIncludedKeys = ref<string[]>([])
const tempExcludedKeys = ref<string[]>([])
const tempDifficultyRanges = ref<DifficultyRanges>(createDifficultyRanges())

const onDifficultyToggle = (event: Event) => {
  difficultySectionExpanded.value = (event.target as HTMLDetailsElement).open
}

const onKeyToggle = (event: Event) => {
  keySectionExpanded.value = (event.target as HTMLDetailsElement).open
}

const updateIncludedKeys = (keys: string[]) => {
  tempIncludedKeys.value = keys
  tempExcludedKeys.value = tempExcludedKeys.value.filter((key) => !keys.includes(key))
}

const updateExcludedKeys = (keys: string[]) => {
  tempExcludedKeys.value = keys
  tempIncludedKeys.value = tempIncludedKeys.value.filter((key) => !keys.includes(key))
}

const setDifficultyRange = (
  criterion: DifficultyCriterion,
  range: { min: number; max: number },
) => {
  const bounds = difficultyBounds.value[criterion]
  tempDifficultyRanges.value[criterion] = {
    min: range.min <= bounds.min ? null : range.min,
    max: range.max >= bounds.max ? null : range.max,
  }
}
const tempDateRange = ref<{ start: string; end: string }>({ start: '', end: '' })
const tempLengthRange = ref<{ min: number | null; max: number | null }>({ min: null, max: null })
const tempLengthFilterSource = ref<'full' | 'tv' | 'either'>('full')

// Initialize modal with current filter values
const initializeTempFilters = () => {
  tempSelectedLabels.value = [...selectedLabels.value]
  tempSelectedProducers.value = [...selectedProducers.value]
  tempSelectedSingers.value = [...selectedSingers.value]
  tempIncludedKeys.value = [...includedKeys.value]
  tempExcludedKeys.value = [...excludedKeys.value]
  tempDifficultyRanges.value = cloneDifficultyRanges(difficultyRanges.value)
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
  includedKeys.value = [...tempIncludedKeys.value]
  excludedKeys.value = [...tempExcludedKeys.value]
  difficultyRanges.value = cloneDifficultyRanges(tempDifficultyRanges.value)
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

const clearAllFilters = () => {
  tempSelectedLabels.value = []
  tempSelectedProducers.value = []
  tempSelectedSingers.value = []
  tempIncludedKeys.value = []
  tempExcludedKeys.value = []
  tempDifficultyRanges.value = createDifficultyRanges()
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
</script>

<template>
  <div class="modal fade" tabindex="-1" @[modalShowEvent]="initializeTempFilters">
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
          <div class="mb-4">
            <TagFilter
              v-model="tempSelectedSingers"
              :options="availableSingers"
              label="Singers"
              badge-class="filter-tag--singers"
            />
          </div>
          <div class="mb-4">
            <TagFilter
              v-model="tempSelectedProducers"
              :options="availableProducers"
              label="Producers"
              badge-class="filter-tag--producers"
            />
          </div>
          <div class="mb-4">
            <TagFilter
              v-model="tempSelectedLabels"
              :options="availableLabels"
              label="Labels"
              badge-class="filter-tag--labels"
            />
          </div>

          <details class="mb-4" :open="keySectionExpanded" @toggle="onKeyToggle">
            <summary class="fw-bold mb-2"><i class="bi bi-music-note-list me-2"></i>Key</summary>
            <p class="small text-muted">
              Include: Only songs with these keys will be shown.<br />
              Exclude: Songs with these keys will be hidden.<br />
              Exclusion takes priority, so if a song changes to an excluded key, it will be hidden.
            </p>
            <div class="mb-3">
              <TagFilter
                :model-value="tempIncludedKeys"
                :options="availableKeys"
                label="Include keys"
                badge-class="filter-tag--included-keys"
                placeholder='"C major", "1 flat", "<2 sharps/flats"'
                :filter-options="filterMusicalKeys"
                :query-option="getKeyQueryOption"
                :describe-option="describeKey"
                @update:model-value="updateIncludedKeys"
              />
            </div>
            <TagFilter
              :model-value="tempExcludedKeys"
              :options="availableKeys"
              label="Exclude keys"
              placeholder='"G# minor", ">=5 flats"'
              badge-class="filter-tag--excluded-keys"
              :filter-options="filterMusicalKeys"
              :query-option="getKeyQueryOption"
              :describe-option="describeKey"
              @update:model-value="updateExcludedKeys"
            />
          </details>

          <details class="mb-3" :open="difficultySectionExpanded" @toggle="onDifficultyToggle">
            <summary class="fw-bold mb-1">
              <i class="bi bi-speedometer2 me-2"></i>Difficulty
            </summary>
            <div class="row gx-3 gy-2">
              <fieldset
                v-for="criterion in difficultyCriteria"
                :key="criterion"
                class="col-12"
                :class="{ 'col-md-6': criterion !== 'overall' }"
              >
                <legend class="form-label fs-6 mb-0 d-flex justify-content-between gap-2">
                  <span>{{ difficultyLabels[criterion] }}</span>
                  <span class="small text-muted text-nowrap">
                    {{ tempDifficultyRanges[criterion].min ?? difficultyBounds[criterion].min }} to
                    {{ tempDifficultyRanges[criterion].max ?? difficultyBounds[criterion].max }}
                  </span>
                </legend>
                <DualRangeSlider
                  :label="`${difficultyLabels[criterion].toLowerCase()} difficulty`"
                  :aria-describedby="`${difficultyDescriptionId}-${criterion}`"
                  :min="difficultyBounds[criterion].min"
                  :max="difficultyBounds[criterion].max"
                  :model-value="{
                    min: tempDifficultyRanges[criterion].min ?? difficultyBounds[criterion].min,
                    max: tempDifficultyRanges[criterion].max ?? difficultyBounds[criterion].max,
                  }"
                  @update:model-value="setDifficultyRange(criterion, $event)"
                />
                <p
                  :id="`${difficultyDescriptionId}-${criterion}`"
                  class="small text-muted lh-sm mb-0"
                >
                  {{ difficultyDescriptions[criterion] }}
                </p>
              </fieldset>
            </div>
          </details>

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
            <DualRangeSlider
              class="mb-3"
              label="length"
              :min="sliderMin"
              :max="sliderMax"
              :model-value="{ min: resolvedMinLength, max: resolvedMaxLength }"
              @update:model-value="setTempLengthRange($event.min, $event.max)"
            />
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
:deep(.filter-tag) {
  color: #fff;
  --bs-btn-close-filter: invert(1) grayscale(100%) brightness(200%);
}

:deep(.filter-tag--singers) {
  background-color: #0dcaf0;
  color: #000;
  --bs-btn-close-filter: none;
}

:deep(.filter-tag--producers) {
  background-color: #ffc107;
  color: #000;
  --bs-btn-close-filter: none;
}

:deep(.filter-tag--labels) {
  background-color: #e27aa0;
  color: #000;
  --bs-btn-close-filter: none;
}

:deep(.filter-tag--included-keys) {
  background-color: #0d6efd;
}

:deep(.filter-tag--excluded-keys) {
  background-color: #dc3545;
}
</style>
