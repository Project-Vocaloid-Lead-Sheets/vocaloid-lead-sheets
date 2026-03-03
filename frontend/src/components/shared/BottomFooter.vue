<template>
  <div class="bottom-footer">
    <div
      v-if="hasTop"
      class="bottom-footer-section"
      :class="{ 'bottom-footer-section--shadowed': hasTop }"
    >
      <slot name="top" />
    </div>

    <div v-if="hasTop && hasBottom" class="bottom-footer-divider" />

    <div
      v-if="hasBottom"
      class="bottom-footer-section"
      :class="{ 'bottom-footer-section--shadowed': !hasTop }"
    >
      <slot name="bottom" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    showTop?: boolean
    showBottom?: boolean
  }>(),
  {
    showTop: false,
    showBottom: true,
  },
)

const hasTop = computed(() => props.showTop)
const hasBottom = computed(() => props.showBottom)
</script>

<style scoped>
.bottom-footer {
  --bottom-footer-x-padding: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.45);
  margin-left: -1rem;
  margin-right: -1rem;
  padding-left: var(--bottom-footer-x-padding);
  padding-right: var(--bottom-footer-x-padding);
}

.bottom-footer-section {
  padding-top: 0.75rem;
  padding-bottom: 0.75rem;
}

.bottom-footer-section--shadowed {
  position: relative;
}

.bottom-footer-section--shadowed::before {
  content: '';
  position: absolute;
  left: calc(-1 * var(--bottom-footer-x-padding));
  right: calc(-1 * var(--bottom-footer-x-padding));
  top: -10px;
  height: 10px;
  pointer-events: none;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.28), rgba(0, 0, 0, 0));
}

.bottom-footer-divider {
  border-top: 1px solid rgba(255, 255, 255, 0.25);
}
</style>
