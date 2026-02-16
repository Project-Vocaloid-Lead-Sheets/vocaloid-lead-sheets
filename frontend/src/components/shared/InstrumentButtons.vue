<template>
  <div class="btn-group flex-wrap" :class="wrapperClass" role="group">
    <button
      v-for="instrument in instruments"
      :key="instrument"
      type="button"
      :class="
        instrument === selectedInstrument ? 'btn btn-sm btn-light' : 'btn btn-sm btn-outline-light'
      "
      @click="selectedInstrument = instrument"
    >
      {{ instrument }}
    </button>
  </div>
</template>

<script setup lang="ts">
import type { Instrument } from '@/types/types'

interface Props {
  instruments: Instrument[]
  selectedInstrument: Instrument
  wrapperClass?: string
}

defineProps<Props>()

const selectedInstrument = defineModel<Instrument>('selectedInstrument', { required: true })
</script>
