<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, useId } from 'vue'

const props = defineProps<{
  modelValue: string[]
  options: string[]
  label: string
  placeholder?: string
  badgeClass: string
  filterOptions?: (query: string, options: string[]) => string[]
  describeOption?: (option: string) => string
  queryOption?: (query: string, options: string[]) => string | null
}>()

const emit = defineEmits<{ 'update:modelValue': [value: string[]] }>()
const id = useId()
const root = ref<HTMLElement | null>(null)
const input = ref<HTMLInputElement | null>(null)
const query = ref('')
const isOpen = ref(false)
const highlightedIndex = ref(0)
const matchingOptions = computed(() =>
  props.filterOptions
    ? props.filterOptions(query.value, props.options)
    : props.options.filter((option) => option.toLowerCase().includes(query.value.toLowerCase())),
)
const querySelection = computed(() => props.queryOption?.(query.value, props.options) ?? null)
const dropdownOptions = computed(() =>
  querySelection.value
    ? [
        querySelection.value,
        ...matchingOptions.value.filter((option) => option !== querySelection.value),
      ]
    : matchingOptions.value,
)

const toggleOption = (option: string) => {
  const next = props.modelValue.includes(option)
    ? props.modelValue.filter((value) => value !== option)
    : [...props.modelValue, option]
  emit('update:modelValue', next)
  isOpen.value = true
}

const removeOption = (option: string) =>
  emit(
    'update:modelValue',
    props.modelValue.filter((value) => value !== option),
  )

const onQueryInput = () => {
  highlightedIndex.value = 0
  isOpen.value = true
}

const onKeydown = (event: KeyboardEvent) => {
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    const last = Math.max(0, dropdownOptions.value.length - 1)
    highlightedIndex.value = !isOpen.value
      ? 0
      : Math.max(0, Math.min(last, highlightedIndex.value + (event.key === 'ArrowDown' ? 1 : -1)))
    isOpen.value = true
  } else if (event.key === 'Enter') {
    event.preventDefault()
    const option = dropdownOptions.value[highlightedIndex.value]
    if (isOpen.value && option) toggleOption(option)
  }
}

const closeDropdown = () => {
  isOpen.value = false
}
const onOutsidePointer = (event: PointerEvent) => {
  if (event.target instanceof Node && !root.value?.contains(event.target)) closeDropdown()
}
const onFocusOut = (event: FocusEvent) => {
  if (!(event.relatedTarget instanceof Node) || !root.value?.contains(event.relatedTarget))
    closeDropdown()
}
const onEscape = (event: KeyboardEvent) => {
  if (!isOpen.value) return
  event.preventDefault()
  event.stopPropagation()
  closeDropdown()
  input.value?.focus()
  // Focusing the input opens its suggestions, so close them again afterward.
  closeDropdown()
}
onMounted(() => document.addEventListener('pointerdown', onOutsidePointer))
onUnmounted(() => document.removeEventListener('pointerdown', onOutsidePointer))
</script>

<template>
  <div ref="root" @focusout="onFocusOut" @keydown.esc="onEscape">
    <label :for="`${id}-input`" class="form-label fw-bold">{{ label }}</label>
    <div v-if="modelValue.length" class="d-flex flex-wrap gap-1 mb-2">
      <span
        v-for="option in modelValue"
        :key="option"
        class="badge filter-tag d-inline-flex align-items-center"
        :class="badgeClass"
      >
        {{ option }}
        <button
          type="button"
          class="btn-close ms-1"
          :aria-label="`Remove ${option} from ${label}`"
          @click="removeOption(option)"
        ></button>
      </span>
    </div>
    <div class="position-relative">
      <input
        :id="`${id}-input`"
        ref="input"
        v-model="query"
        type="text"
        class="form-control"
        autocomplete="off"
        :placeholder="placeholder ?? `Search ${label.toLowerCase()}...`"
        :aria-expanded="isOpen"
        :aria-controls="`${id}-options`"
        @focus="isOpen = true"
        @click="isOpen = true"
        @input="onQueryInput"
        @keydown="onKeydown"
      />
      <div
        v-if="isOpen"
        :id="`${id}-options`"
        class="dropdown-menu show w-100 tag-filter-options"
        role="group"
        :aria-label="`${label} options`"
      >
        <label
          v-for="(option, index) in dropdownOptions"
          :key="option"
          class="dropdown-item d-flex align-items-center gap-2 mb-0"
          :class="{
            'bg-body-secondary': index === highlightedIndex,
            'border-bottom fw-semibold': option === querySelection,
          }"
          @mouseenter="highlightedIndex = index"
          @mousedown.prevent
        >
          <input
            type="checkbox"
            class="form-check-input flex-shrink-0 mt-0"
            :checked="modelValue.includes(option)"
            @change="toggleOption(option)"
          />
          <span class="flex-grow-1">{{ option }}</span>
          <small v-if="describeOption" class="text-body-secondary">{{
            describeOption(option)
          }}</small>
        </label>
        <div v-if="!dropdownOptions.length" class="px-3 py-2 small text-body-secondary">
          No matching options.
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tag-filter-options {
  max-height: 16rem;
  overflow-y: auto;
}

.tag-filter-options .dropdown-item {
  cursor: pointer;
  white-space: normal;
}

.badge .btn-close {
  font-size: 0.65em;
}
</style>
