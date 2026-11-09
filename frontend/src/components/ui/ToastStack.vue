<!-- Renders the toast store in the bottom corner. -->
<script setup>
import AppIcon from './AppIcon.vue';
import { useToasts } from '../../core/injection.js';

const toasts = useToasts();
</script>

<template>
  <div class="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex flex-col items-center gap-2 px-4 sm:inset-x-auto sm:right-4 sm:items-end" aria-live="polite">
    <TransitionGroup name="toast">
      <div
        v-for="toast in toasts.items"
        :key="toast.id"
        class="pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-md bg-white px-4 py-3 text-sm shadow-lg ring-1 dark:bg-tinta-900"
        :class="toast.kind === 'error' ? 'ring-barro-200 dark:ring-barro-500/30' : 'ring-cobalto-100 dark:ring-tinta-800'"
      >
        <span
          class="grid h-7 w-7 shrink-0 place-items-center rounded-full"
          :class="toast.kind === 'error'
            ? 'bg-barro-50 text-barro-600 dark:bg-barro-500/15 dark:text-barro-400'
            : 'bg-cobalto-50 text-cobalto-600 dark:bg-cobalto-300/15 dark:text-cobalto-300'"
        >
          <AppIcon :name="toast.kind === 'error' ? 'alert' : 'check'" class="h-4 w-4" stroke-width="2.2" />
        </span>
        <span class="flex-1 pt-1">{{ toast.text }}</span>
        <button type="button" class="pt-1 text-tinta-400 hover:text-tinta-600" title="Fechar" @click="toasts.dismiss(toast.id)">
          <AppIcon name="close" class="h-4 w-4" stroke-width="2.2" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>
