import { createRouter, createWebHistory } from 'vue-router'
import MainView from '../views/MainView.vue'
import HomeView from '@/views/HomeView.vue'
import SheetView from '@/views/SheetView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'main',
      component: MainView,
      children: [
        {
          path: '',
          name: 'home',
          component: HomeView,
        },
        {
          path: '/view/:songSlug',
          name: 'sheetView',
          component: SheetView,
          props: (route) => ({
            songSlug: route.params.songSlug,
          }),
        },
      ],
    },
  ],
})

export default router
