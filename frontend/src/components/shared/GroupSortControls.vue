<template>
  <div class="d-flex gap-2 align-items-center">
    <div class="input-group">
      <span class="input-group-text"><i class="bi bi-folder small"></i></span>
      <select :id="groupSelectId" class="form-select form-select-sm" v-model="groupBy">
        <option value="none">None</option>
        <option value="singer">Singer</option>
        <option value="producer">Producer</option>
      </select>
    </div>
    <div class="input-group">
      <span class="input-group-text"><i class="bi bi-sort-alpha-down small"></i></span>
      <select :id="sortSelectId" class="form-select form-select-sm" v-model="sortBy">
        <option value="title-asc">Title: A → Z</option>
        <option value="title-desc">Title: Z → A</option>
        <option value="bpm-asc">BPM: Low → High</option>
        <option value="bpm-desc">BPM: High → Low</option>
        <option value="date-asc">Release Date: Old → New</option>
        <option value="date-desc">Release Date: New → Old</option>
      </select>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  groupSelectId?: string
  sortSelectId?: string
}

withDefaults(defineProps<Props>(), {
  groupSelectId: 'group-select',
  sortSelectId: 'sort-select',
})

const groupBy = defineModel<string>('groupBy', { required: true })
const sortBy = defineModel<string>('sortBy', { required: true })
</script>
