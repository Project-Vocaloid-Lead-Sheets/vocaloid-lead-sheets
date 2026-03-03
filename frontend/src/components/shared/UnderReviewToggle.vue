<template>
  <div class="form-check form-switch">
    <input
      class="form-check-input"
      type="checkbox"
      role="switch"
      :id="toggleId"
      v-model="underReviewViewEnabled"
    />
    <label class="form-check-label text-light small" :for="toggleId">
      Show sheets currently under review
    </label>
  </div>
</template>

<script setup lang="ts">
interface Props {
  toggleId: string
}

defineProps<Props>()

const underReviewViewEnabled = defineModel<boolean>('underReviewViewEnabled', { required: true })
</script>

<style scoped>
.form-switch .form-check-input {
  background-color: #6c757d;
  border-color: #6c757d;
}

.form-check {
  margin-bottom: 0;
}

.form-check-label {
  white-space: nowrap;
}

.form-switch .form-check-input:checked {
  background-color: #0d6efd;
  border-color: #0d6efd;
}

.form-switch .form-check-input:focus {
  box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
}
</style>
