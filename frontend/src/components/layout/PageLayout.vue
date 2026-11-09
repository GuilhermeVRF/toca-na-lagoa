<!-- Page frame: cobalt tiled header with navigation and a hero slot, closed by the marquee curve, then the content. -->
<script setup>
import AppIcon from '../ui/AppIcon.vue';
import BrandMark from '../ui/BrandMark.vue';
import RouterLink from '../ui/RouterLink.vue';
import { useAuth, useRouter } from '../../core/injection.js';
import { useTheme } from '../../stores/useTheme.js';

const { routes } = useRouter();
const navRoutes = routes.filter((route) => route.nav);
const { passwordRequired, logout } = useAuth();
const { isDark, toggle: toggleTheme } = useTheme();
</script>

<template>
  <div class="min-h-full">
    <header class="relative overflow-hidden bg-cobalto-700 pb-16 text-white sm:pb-20 dark:bg-cobalto-900">
      <div class="azulejo pointer-events-none absolute inset-0 text-white/[0.09] dark:text-cobalto-300/[0.08]" />
      <nav class="relative mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 pb-2 pt-4 sm:px-6 sm:py-5">
        <RouterLink to="/" class="flex min-w-0 items-center gap-3">
          <BrandMark class="h-10 w-10 shrink-0" />
          <span class="min-w-0">
            <span class="display block truncate text-xl leading-tight">Toca na Lagoa</span>
            <span class="overline hidden text-white/65 sm:block">Aluguel · Pampulha, BH</span>
          </span>
        </RouterLink>

        <div class="order-3 grid w-full grid-cols-2 gap-1 rounded-md bg-cobalto-900/40 p-1 ring-1 ring-white/15 sm:order-2 sm:ml-auto sm:flex sm:w-auto dark:bg-white/5">
          <RouterLink
            v-for="route in navRoutes"
            :key="route.path"
            :to="route.path"
            class="whitespace-nowrap rounded px-3 py-2 text-center text-sm font-semibold transition sm:py-1.5"
            active-class="bg-white text-cobalto-800 dark:bg-tinta-100"
            inactive-class="text-white/75 hover:bg-white/10 hover:text-white"
          >
            <span class="sm:hidden">{{ route.shortLabel ?? route.label }}</span>
            <span class="hidden sm:inline">{{ route.label }}</span>
          </RouterLink>
        </div>

        <div class="order-2 flex items-center gap-1 sm:order-3">
          <button type="button" title="Alternar tema" class="rounded-md p-2 text-white/75 hover:bg-white/10 hover:text-white" @click="toggleTheme">
            <AppIcon :name="isDark ? 'sun' : 'moon'" class="h-5 w-5" />
          </button>
          <button v-if="passwordRequired" type="button" title="Sair" class="rounded-md p-2 text-white/75 hover:bg-white/10 hover:text-white" @click="logout">
            <AppIcon name="logout" class="h-5 w-5" />
          </button>
        </div>
      </nav>
      <div class="relative mx-auto max-w-6xl px-4 pt-6 text-center sm:px-6 sm:pt-8 sm:text-left">
        <slot name="hero" />
      </div>
      <!-- The curve of the Pampulha marquee closes the header into the page. -->
      <svg class="absolute inset-x-0 -bottom-px h-8 w-full text-tinta-50 sm:h-12 dark:text-tinta-950" viewBox="0 0 1200 48" preserveAspectRatio="none" aria-hidden="true">
        <path d="M0 48C240 4 480 0 700 22s380 30 500 2V48Z" fill="currentColor" />
      </svg>
    </header>
    <main class="relative mx-auto max-w-6xl px-3 pb-16 pt-2 sm:px-6">
      <slot />
    </main>
  </div>
</template>
