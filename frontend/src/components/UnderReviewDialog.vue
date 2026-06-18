<template>
  <div
    class="modal fade"
    id="underReviewModal"
    tabindex="-1"
    aria-labelledby="underReviewModalLabel"
    aria-hidden="true"
    ref="modalRef"
  >
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h1 class="modal-title fs-5" id="underReviewModalLabel">Sheet Under Review</h1>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Close"
            @click="onCancel"
          ></button>
        </div>
        <div class="modal-body">
          <p>
            <strong>"{{ songTitle }}"</strong> is marked as "under review" and may not be complete
            or fully accurate.
          </p>
          <p>Would you like to enable Review Mode to view this and other sheets in review?</p>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="onCancel">Go to Home Page</button>
          <button type="button" class="btn btn-primary" @click="onConfirm">
            Enable Review Mode
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface Props {
  songTitle: string
}

defineProps<Props>()

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()

const modalRef = ref<HTMLElement>()
type BootstrapModal = {
  show: () => void
  hide: () => void
}
let modalInstance: BootstrapModal | null = null

onMounted(() => {
  if (modalRef.value) {
    void import('bootstrap').then(({ Modal }) => {
      if (!modalRef.value) return

      modalInstance = new Modal(modalRef.value, {
        backdrop: 'static',
        keyboard: false,
      })
    })
  }
})

const show = () => {
  modalInstance?.show()
}

const hide = () => {
  modalInstance?.hide()
}

const onConfirm = () => {
  emit('confirm')
  hide()
}

const onCancel = () => {
  emit('cancel')
  hide()
}

defineExpose({
  show,
  hide,
})
</script>
