<!-- Listings header: count, last check, per-portal status and the "check now" button. -->
<script setup>
import { computed } from 'vue';
import AppIcon from '../ui/AppIcon.vue';
import { useMonitor } from '../../core/injection.js';
import { formatDateTime } from '../../core/format.js';

defineProps({
  count: { type: Number, required: true },
});

const monitor = useMonitor();
const status = monitor.status;
const busy = monitor.busy;
const lastCheck = computed(() =>
  status.value?.last_check_at ? `Última verificação ${formatDateTime(status.value.last_check_at)}` : '',
);
</script>

<template>
  <div class="flex flex-col items-center gap-4 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
    <div>
      <p class="text-sm font-medium uppercase tracking-wider text-white/60">Apartamentos para alugar</p>
      <h1 class="mt-1 text-3xl font-extrabold tracking-tight sm:text-4xl">{{ count }} opções na Pampulha</h1>
      <p class="mt-2 text-sm text-white/70">
        <template v-if="lastCheck">{{ lastCheck }}</template>
        <template v-else-if="status">Nenhuma verificação ainda. Clique em <b>Verificar agora</b> para buscar os anúncios.</template>
      </p>
    </div>
    <button
      type="button"
      :disabled="busy"
      class="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-white px-4 py-3 sm:w-auto sm:py-2.5 text-sm font-semibold text-brand-700 shadow-lg transition hover:bg-brand-50 disabled:opacity-70"
      @click="monitor.checkNow()"
    >
      <AppIcon name="refresh" class="h-4 w-4" :class="{ 'animate-spin': busy }" stroke-width="2.2" />
      {{ busy ? 'Buscando… (1–3 min)' : 'Verificar agora' }}
    </button>
  </div>
  <div v-if="status?.sources.length" class="mt-4 flex flex-wrap justify-center gap-2 sm:justify-start">
    <span
      v-for="source in status.sources"
      :key="source.source"
      :title="source.error || null"
      class="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ring-1"
      :class="source.ok ? 'bg-white/10 text-white/85 ring-white/20' : 'bg-rose-500/25 text-white ring-rose-300/40'"
    >
      <span class="h-1.5 w-1.5 rounded-full" :class="source.ok ? 'bg-emerald-300' : 'bg-rose-300'" />
      {{ source.label }}: {{ source.ok ? source.found : 'erro' }}
    </span>
  </div>
</template>
