import { computed } from 'vue'
import { useRoute } from 'vue-router'
import type { Song, Instrument } from '@/types/types'
import { useSongsStore } from '@/stores/songs'
import { getPdfDownloadUrl } from '@/utils/pdfUtils'

export const useSongActions = () => {
  const route = useRoute()
  const songsStore = useSongsStore()

  // Get current song based on route
  const currentSong = computed<Song | null>(() => {
    const songSlug = route.params.songSlug as string
    if (!songSlug) return null
    return songsStore.getSongBySlug(songSlug) || null
  })

  const currentInstrument = computed(() => (route.query.instrument as Instrument) || 'C')

  // Functions for the footer actions
  const printPdf = () => {
    const song = currentSong.value
    if (!song) return

    const pdfPath = song.pdfs[currentInstrument.value] || song.pdfs['C']
    if (pdfPath) {
      const directUrl = getPdfDownloadUrl(pdfPath)
      const printWindow = window.open('', '_blank', 'width=800,height=1000')
      if (printWindow) {
        printWindow.document.write(`
          <html>
            <head>
              <title>Print PDF</title>
              <style>body,html{margin:0;padding:0;height:100%;}</style>
            </head>
            <body style="margin:0;padding:0;">
              <iframe src="${directUrl}" style="width:100vw;height:100vh;border:none;" id="pdfFrame"></iframe>
              <script>
                const iframe = document.getElementById('pdfFrame');
                iframe.onload = function() {
                  setTimeout(() => { window.print(); }, 500);
                };
              <\/script>
            </body>
          </html>
        `)
        printWindow.document.close()
      }
    }
  }

  const watchOnYouTube = () => {
    const song = currentSong.value
    if (!song?.videoLinks?.YouTube) return

    window.open(song.videoLinks.YouTube, '_blank')
  }

  return {
    currentSong,
    currentInstrument,
    printPdf,
    watchOnYouTube,
  }
}
