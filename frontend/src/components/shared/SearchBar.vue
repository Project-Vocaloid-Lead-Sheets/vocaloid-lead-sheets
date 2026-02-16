<template>
  <div class="input-group input-group-sm">
    <input type="text" class="form-control" :placeholder="placeholder" v-model="searchQuery" />
    <button class="btn btn-outline-light" type="button" @click="onReset">
      <i class="bi bi-arrow-clockwise"></i>
    </button>
  </div>
</template>

<script setup lang="ts">
interface Props {
  placeholder?: string
}

withDefaults(defineProps<Props>(), {
  placeholder: 'Search by name',
})

const searchQuery = defineModel<string>('searchQuery', { required: true })

const emit = defineEmits<{
  reset: []
}>()

const onReset = () => {
  emit('reset')
}
</script>
