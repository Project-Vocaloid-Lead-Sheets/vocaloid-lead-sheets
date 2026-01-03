<script setup lang="ts">
import { computed, onMounted, onUnmounted, nextTick, h } from 'vue'
import { Tooltip } from 'bootstrap'
import { useSongsStore } from '@/stores/songs'
import { generateSongSlug } from '@/utils/slugUtils'

const songsStore = useSongsStore()
const MAX_RECENT = 20

const formatSyncedDate = (syncedAt?: string) => {
  if (!syncedAt) return ''
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  }).format(new Date(syncedAt))
}

// Get most recent songs sorted by sync timestamp
const recentSongs = computed(() => {
  const includeUnderReview = songsStore.underReviewViewEnabled

  const pool = includeUnderReview
    ? songsStore.songs
    : songsStore.songs.filter((song) => !song.status || song.status.toLowerCase() === 'completed')

  return pool
    .filter((song) => song.syncedAt)
    .map((song) => ({ ...song, _syncedTs: new Date(song.syncedAt as string).getTime() }))
    .sort((a, b) => b._syncedTs - a._syncedTs)
    .slice(0, MAX_RECENT)
})

onMounted(async () => {
  // Wait for DOM to be fully rendered
  await nextTick()

  // Initialize all tooltips on the page
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((el) => {
    new Tooltip(el as HTMLElement)
  })

  // Refresh navbar height in case assets (like the banner) shift layout after load
  const updateNavbarHeight = (window as any).__updateNavbarHeight as (() => void) | undefined
  if (typeof updateNavbarHeight === 'function') {
    updateNavbarHeight()
    // Re-run shortly after load to catch late asset sizing
    const timeoutId = window.setTimeout(() => updateNavbarHeight(), 150)
    window.addEventListener('load', updateNavbarHeight)

    onUnmounted(() => {
      window.clearTimeout(timeoutId)
      window.removeEventListener('load', updateNavbarHeight)
    })
  }
})
</script>

<template>
  <div class="home-page d-flex flex-column">
    <!-- Banner Section -->
    <div class="banner">
      <img src="/public/logo.png" alt="VocaLeads Logo" class="banner-logo" />
      <div class="title-text">
        <h1>Project VocaLead Sheets</h1>
      </div>
    </div>

    <!-- Body Section -->
    <div class="main-body flex-grow-1 d-flex">
      <!-- Left Content Area -->
      <div class="left-content">
        <!-- About Section -->
        <div class="about">
          <h4>Overview</h4>
          <p>
            Lead sheets of music written for vocal synthesizer software, provided for musicians to
            jam or learn.
          </p>
          <p>
            This is similar to / inspired by
            <a href="https://www.vgleadsheets.com/">VGLeadSheets.com</a>, but it is a separate
            project from VGLS, organized by a different community.
          </p>
          <p>
            If you would like to get in contact for questions, contributions, or anything else,
            please reach out to
            <a href="mailto:vocaloidleadsheets@googlegroups.com"
              >vocaloidleadsheets@googlegroups.com</a
            >.
          </p>
        </div>

        <!-- How-To Section -->
        <div class="features">
          <h4>Site navigation</h4>
          <ul>
            <li>Search, filter, sort and switch parts from the navbar menu</li>
            <li>Open the advanced filter to filter by additional criteria</li>
            <li>Quick navigate with random song and collapse category buttons</li>
            <li>Download, view original or toggle review-mode from the bottom of the nav bar</li>
            <li>Toggle spreads and scroll directions from the PDF viewer</li>
          </ul>
        </div>
        <!-- Footer Disclaimer -->
        <div class="footer-disclaimer">
          <small>
            All lead sheets are licensed under Creative Commons by their respective transcribers and
            are provided for educational and personal use only. All transcriptions were created from
            scratch by listening and analyzing the music and inputting notes into notation software.
            We will gladly take down any music if asked by their respective owners. Please respect
            the copyright and intellectual property rights of the original composers and producers.
          </small>
        </div>
      </div>

      <!-- Right Sidebar -->
      <div class="right-sidebar">
        <div class="recent-songs-box">
          <h5>Recent Activity</h5>
          <ul class="song-list">
            <li v-for="song in recentSongs" :key="song.title" class="song-item">
              <div class="song-row">
                <div class="song-main">
                  <RouterLink
                    :to="{ name: 'sheetView', params: { songSlug: generateSongSlug(song.title) } }"
                  >
                    {{ song.title }}
                  </RouterLink>
                  <span
                    v-if="song.status && song.status.toLowerCase() === 'under review'"
                    class="badge-under-review"
                  >
                    (under review)
                  </span>
                </div>
                <span class="synced-date" v-if="song.syncedAt">{{
                  formatSyncedDate(song.syncedAt)
                }}</span>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-page {
  display: flex;
  flex-direction: column;
  margin-top: var(--navbar-height, 0px);
  height: calc(var(--vh, 1vh) * 100 - var(--navbar-height, 0px));
  overflow: hidden;
}

@media (max-width: 991px) {
  .home-page {
    position: static;
    margin-top: var(--navbar-height, 0px);
    height: auto;
    min-height: calc(var(--vh, 1vh) * 100 - var(--navbar-height, 0px));
    overflow: visible;
  }
}

.main-body {
  min-height: 0;
  overflow: auto;
}

.banner {
  background: linear-gradient(180deg, #39fcff 0%, transparent 33%, transparent 100%);
  padding: 2rem 1rem 1rem;
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.banner-logo {
  width: 20vw;
  min-width: 128px;
  max-width: 240px;
  height: auto;
  margin-inline: 1rem;
}

.left-content {
  flex: 2;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.title-text h1 {
  font-size: clamp(2rem, 5vw, 3rem);
  color: #333;
}

.left-content p {
  font-size: clamp(1rem, 2.5vw, 1.2rem);
  line-height: 1.6;
  margin-bottom: 1rem;
  color: #555;
}

.footer-disclaimer {
  margin-top: auto;
  padding-top: 1.5rem;
  border-top: 1px solid #ddd;
  color: #999;
}

.right-sidebar {
  flex: 1;
  padding: 2rem 1rem;
  display: flex;
  justify-content: center;
  align-items: stretch;
}

.recent-songs-box {
  background: #fcfcfc;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.5rem;
  width: 100%;
  max-width: 360px;
  display: flex;
  flex-direction: column;
}

.recent-songs-box h5 {
  margin-bottom: 1rem;
  color: #333;
  font-weight: 600;
}

.song-list {
  list-style: none;
  padding: 0;
  margin: 0;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 0.5rem;
  scrollbar-gutter: stable;
}

.song-list li {
  margin-bottom: 0.75rem;
}

.song-list a {
  text-decoration: none;
  transition: color 0.2s;
}

.song-list a:hover {
  text-decoration: underline;
}

.song-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.song-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}

.song-main {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.15rem;
}

.badge-under-review {
  color: #a15b00;
  font-size: 0.9rem;
}

.synced-date {
  color: #666;
  font-size: 0.9rem;
  white-space: nowrap;
}

@media (max-width: 767px) {
  .main-body {
    flex-direction: column;
    overflow: visible;
  }

  .right-sidebar {
    padding: 0 1.5rem 1.5rem;
    align-items: stretch;
  }

  .recent-songs-box {
    max-width: none;
  }
}

.min-vh-100 {
  min-height: 100vh;
}
</style>
