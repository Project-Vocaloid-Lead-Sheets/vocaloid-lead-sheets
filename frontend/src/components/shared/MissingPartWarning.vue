<template>
  <button
    ref="trigger"
    type="button"
    class="btn btn-link text-warning missing-part-warning"
    :aria-label="message"
    @click="trigger?.focus()"
    @keydown.esc="trigger?.blur()"
  >
    <i class="bi bi-exclamation-triangle" aria-hidden="true"></i>
  </button>
</template>

<script setup lang="ts">
import { onMounted, ref, shallowRef, watchEffect } from 'vue'
import type { Popover } from 'bootstrap'

const props = defineProps<{ message: string }>()
const trigger = ref<HTMLButtonElement | null>(null)
const PopoverConstructor = shallowRef<typeof Popover | null>(null)

onMounted(async () => {
  const bootstrap = await import('bootstrap')
  PopoverConstructor.value = bootstrap.Popover
})

watchEffect((onCleanup) => {
  if (!trigger.value || !PopoverConstructor.value) return

  const popover = new PopoverConstructor.value(trigger.value, {
    content: props.message,
    trigger: 'hover focus',
    placement: 'top',
    container: 'body',
  })

  onCleanup(() => popover.dispose())
})
</script>

<style scoped>
.missing-part-warning {
  padding: 0.5rem;
  margin: -0.5rem;
  line-height: 1;
}
</style>
