<template>
  <div
    class="modal fade"
    id="explicitContentModal"
    tabindex="-1"
    aria-labelledby="explicitContentModalLabel"
    aria-hidden="true"
    ref="modalRef"
  >
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h1 class="modal-title fs-5" id="explicitContentModalLabel">Explicit Content</h1>
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
            <strong>"{{ songTitle }}"</strong> is labeled Explicit. The vocals sheet includes adult
            language.
          </p>
          <p>Do you want to continue viewing the vocals sheet?</p>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="onCancel">Go Back</button>
          <button type="button" class="btn btn-primary" @click="onConfirm">Continue</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

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

const addBackdropClass = () => {
  // Use setTimeout to ensure backdrop element exists
  setTimeout(() => {
    const backdrop = document.querySelector('.modal-backdrop')
    if (backdrop) {
      backdrop.classList.add('explicit-backdrop')
    }
  }, 10)
}

const removeBackdropClass = () => {
  const backdrop = document.querySelector('.modal-backdrop.explicit-backdrop')
  if (backdrop) {
    backdrop.classList.remove('explicit-backdrop')
  }
}

onMounted(() => {
  if (modalRef.value) {
    void import('bootstrap').then(({ Modal }) => {
      if (!modalRef.value) return

      modalInstance = new Modal(modalRef.value, {
        backdrop: 'static',
        keyboard: false,
      })

      modalRef.value.addEventListener('shown.bs.modal', addBackdropClass)
      modalRef.value.addEventListener('hidden.bs.modal', removeBackdropClass)
    })
  }
})

onBeforeUnmount(() => {
  if (modalRef.value) {
    modalRef.value.removeEventListener('shown.bs.modal', addBackdropClass)
    modalRef.value.removeEventListener('hidden.bs.modal', removeBackdropClass)
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

<style>
.modal-backdrop.explicit-backdrop {
  background-color: rgba(10, 10, 10, 0.8) !important;
}
</style>
