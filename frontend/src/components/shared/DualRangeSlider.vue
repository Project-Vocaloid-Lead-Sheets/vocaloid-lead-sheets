<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: { min: number; max: number }
    min: number
    max: number
    step?: number
    label: string
  }>(),
  { step: 1 },
)

const emit = defineEmits<{
  'update:modelValue': [value: { min: number; max: number }]
}>()

const clamp = (value: number) => Math.min(Math.max(value, props.min), props.max)
const lowerValue = computed(() => clamp(props.modelValue.min))
const upperValue = computed(() => Math.max(lowerValue.value, clamp(props.modelValue.max)))
const thumbPosition = (value: number) =>
  props.max > props.min ? ((value - props.min) / (props.max - props.min)) * 100 : 0
const fillStyle = computed(() => ({
  left: `${thumbPosition(lowerValue.value)}%`,
  width: `${thumbPosition(upperValue.value) - thumbPosition(lowerValue.value)}%`,
}))

const onLowerInput = (event: Event) => {
  const value = Number((event.target as HTMLInputElement).value)
  emit('update:modelValue', {
    min: Math.min(clamp(value), upperValue.value),
    max: upperValue.value,
  })
}

const onUpperInput = (event: Event) => {
  const value = Number((event.target as HTMLInputElement).value)
  emit('update:modelValue', {
    min: lowerValue.value,
    max: Math.max(clamp(value), lowerValue.value),
  })
}
</script>

<template>
  <div class="dual-range" role="group" :aria-label="label">
    <div class="dual-range__track"></div>
    <div class="dual-range__fill" :style="fillStyle"></div>
    <input
      type="range"
      class="dual-range__input"
      :style="{ zIndex: lowerValue === max ? 2 : undefined }"
      :min="min"
      :max="max"
      :step="step"
      :value="lowerValue"
      :disabled="min >= max"
      :aria-label="`Minimum ${label}`"
      @input="onLowerInput"
    />
    <input
      type="range"
      class="dual-range__input"
      :min="min"
      :max="max"
      :step="step"
      :value="upperValue"
      :disabled="min >= max"
      :aria-label="`Maximum ${label}`"
      @input="onUpperInput"
    />
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

.dual-range__input:focus-visible::-webkit-slider-thumb {
  outline: 2px solid var(--bs-primary);
  outline-offset: 2px;
}

.dual-range__input:focus-visible::-moz-range-thumb {
  outline: 2px solid var(--bs-primary);
  outline-offset: 2px;
}
</style>
