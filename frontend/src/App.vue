<!-- Root component: waits for the session check, then renders the current page and the toasts. -->
<script setup>
import ToastStack from './components/ui/ToastStack.vue';
import { useAuth, useRouter } from './core/injection.js';

const { current } = useRouter();
const { checked } = useAuth();
</script>

<template>
  <div v-if="!checked" class="grid min-h-screen place-items-center text-sm text-slate-400">Carregando…</div>
  <component :is="current.component" v-else :key="current.path" />
  <ToastStack />
</template>
