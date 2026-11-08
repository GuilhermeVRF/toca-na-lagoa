<!-- How the favorites are doing, with a shortcut to see them. -->
<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import AppIcon from '../ui/AppIcon.vue';
import RouterLink from '../ui/RouterLink.vue';
import { useMonitor, useServices } from '../../core/injection.js';

const { listings } = useServices();
const monitor = useMonitor();
const summary = ref(null);

async function load() {
  summary.value = await listings.favoritesSummary().catch(() => summary.value);
}

onMounted(load);
onBeforeUnmount(monitor.onCheckFinished(load));
</script>

<template>
  <div class="rounded-xl bg-amber-50 px-4 py-3 ring-1 ring-amber-200/70 dark:bg-amber-500/10 dark:ring-amber-500/20">
    <div class="flex items-center justify-between gap-3">
      <span class="flex items-center gap-2 text-sm font-semibold text-amber-800 dark:text-amber-300">
        <AppIcon name="star" filled class="h-4 w-4" />
        Acompanhamento de favoritos
      </span>
      <RouterLink to="/?favorites=1" class="text-xs font-semibold text-amber-700 hover:underline dark:text-amber-400">Ver favoritos →</RouterLink>
    </div>
    <p class="mt-1 text-xs leading-relaxed text-amber-800/80 dark:text-amber-300/80">
      <template v-if="summary && (summary.available || summary.gone)">
        {{ summary.available }} disponível(is)<template v-if="summary.gone"> · <b>{{ summary.gone }} saiu(saíram) do ar</b></template>.
      </template>
      <template v-else-if="summary">Nenhum favorito ainda — marque a ⭐ nos anúncios.</template>
      Você recebe um alerta quando um favorito <b>sai do ar</b> (provavelmente alugado), <b>volta</b> a ser anunciado ou
      <b>muda de preço</b> — mesmo que saia da faixa de preço.
    </p>
  </div>
</template>
