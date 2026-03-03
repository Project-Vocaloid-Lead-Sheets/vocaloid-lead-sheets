export const OPEN_DOWNLOAD_MODAL_EVENT = 'vls:open-download-modal'

export const dispatchOpenDownloadModalEvent = () => {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent(OPEN_DOWNLOAD_MODAL_EVENT))
}
