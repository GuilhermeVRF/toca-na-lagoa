<!-- One apartment: photo, prices, details, copies on other portals and price history. -->
<script setup>
import { computed, ref } from 'vue';
import AppIcon from '../ui/AppIcon.vue';
import { useOptions } from '../../core/injection.js';
import { formatBrl, formatDate, formatDayMonth } from '../../core/format.js';

const props = defineProps({
  card: { type: Object, required: true },
});
defineEmits(['toggle-favorite', 'toggle-hidden']);

const { sourceLabel, kindLabel } = useOptions();
const showHistory = ref(false);
const listing = computed(() => props.card.listing);

const priceChanged = computed(() => props.card.previous_total && props.card.previous_total !== listing.value.total);
const priceDropped = computed(() => props.card.previous_total && props.card.previous_total > listing.value.total);
const charges = computed(() =>
  listing.value.source === 'quintoandar'
    ? `cond.+IPTU+taxas ${formatBrl(listing.value.total - listing.value.rent)}`
    : `cond. ${formatBrl(listing.value.condo)} · IPTU ${formatBrl(listing.value.iptu)}`,
);
const bedrooms = computed(() => {
  const count = listing.value.bedrooms;
  return `${count || 'sem'} quarto${count === 1 ? '' : 's'}`;
});
const copiesText = computed(() =>
  props.card.copies.map((copy) => `${sourceLabel(copy.source)} (${formatBrl(copy.total)})`).join(', '),
);
const historyNewestFirst = computed(() => [...props.card.history].reverse());
</script>

<template>
  <article
    class="group relative flex h-full flex-col overflow-hidden rounded-2xl bg-white shadow-sm ring-1 transition hover:shadow-md dark:bg-slate-900"
    :class="[
      listing.favorite ? 'ring-amber-300 dark:ring-amber-500/50' : 'ring-slate-200 dark:ring-slate-800',
      { 'opacity-60': listing.hidden || !listing.active },
    ]"
  >
    <a :href="listing.url" target="_blank" rel="noopener" class="relative block aspect-[3/2] shrink-0 overflow-hidden bg-slate-100 dark:bg-slate-800">
      <img v-if="listing.image_url" :src="listing.image_url" alt="" loading="lazy" referrerpolicy="no-referrer" class="absolute inset-0 h-full w-full object-cover">
      <div class="absolute left-2.5 top-2.5 flex flex-wrap gap-1.5">
        <span v-if="card.is_new" class="rounded-full bg-brand-600 px-2 py-0.5 text-[11px] font-bold text-white shadow">NOVO</span>
        <span v-if="priceDropped" class="rounded-full bg-emerald-500 px-2 py-0.5 text-[11px] font-bold text-white shadow">BAIXOU</span>
        <span v-if="!listing.active" class="rounded-full bg-slate-700 px-2 py-0.5 text-[11px] font-bold text-white shadow">SAIU DO AR · {{ formatDayMonth(listing.last_seen) }}</span>
      </div>
      <span class="absolute bottom-2.5 right-2.5 rounded-full bg-slate-900/75 px-2 py-0.5 text-[11px] font-semibold text-white backdrop-blur">{{ sourceLabel(listing.source) }}</span>
    </a>

    <div class="flex flex-1 flex-col p-4">
      <div class="flex items-start justify-between gap-2">
        <div>
          <p class="text-2xl font-extrabold tracking-tight">{{ formatBrl(listing.total) }}<span class="text-sm font-medium text-slate-400">/mês</span></p>
          <p v-if="priceChanged" class="text-xs text-slate-400">antes <s>{{ formatBrl(card.previous_total) }}</s></p>
        </div>
        <div class="flex gap-1">
          <button
            type="button"
            :aria-pressed="listing.favorite"
            :title="listing.favorite ? 'Remover dos favoritos' : 'Favoritar e acompanhar'"
            class="rounded-lg p-1.5 transition hover:bg-slate-100 dark:hover:bg-slate-800"
            :class="listing.favorite ? 'text-amber-500' : 'text-slate-400'"
            @click="$emit('toggle-favorite', card)"
          >
            <AppIcon name="star" :filled="listing.favorite" class="h-5 w-5" />
          </button>
          <button
            type="button"
            :aria-pressed="listing.hidden"
            :title="listing.hidden ? 'Mostrar de novo' : 'Ocultar (não alerta mais)'"
            class="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-rose-500 dark:hover:bg-slate-800"
            @click="$emit('toggle-hidden', card)"
          >
            <AppIcon :name="listing.hidden ? 'eye' : 'eyeOff'" class="h-5 w-5" />
          </button>
        </div>
      </div>

      <p class="mt-1 text-xs text-slate-500">aluguel {{ formatBrl(listing.rent) }} · {{ charges }}</p>

      <p class="mt-3 truncate font-semibold leading-snug" :title="`${kindLabel(listing.kind)} · ${listing.neighborhood}`">{{ kindLabel(listing.kind) }} · {{ listing.neighborhood }}</p>
      <p class="h-5 truncate text-sm text-slate-500" :title="listing.address">{{ listing.address }}</p>

      <div class="mt-3 flex flex-wrap gap-1.5 text-xs">
        <span v-if="listing.area" class="rounded-md bg-slate-100 px-2 py-1 dark:bg-slate-800">{{ listing.area }} m²</span>
        <span v-if="card.price_per_m2" class="rounded-md bg-slate-100 px-2 py-1 dark:bg-slate-800">R$ {{ Math.round(card.price_per_m2) }}/m²</span>
        <span class="rounded-md bg-slate-100 px-2 py-1 dark:bg-slate-800">{{ bedrooms }}</span>
        <span v-if="listing.furnished" class="rounded-md bg-brand-50 px-2 py-1 font-medium text-brand-700 dark:bg-brand-500/15 dark:text-brand-400">mobiliado</span>
      </div>

      <div class="mt-auto pt-4 text-xs text-slate-500">
        <p class="mb-1 h-4 truncate" :title="copiesText">
          <template v-if="card.copies.length">Também anunciado em:</template>
          <template v-for="(copy, index) in card.copies" :key="copy.url">
            <a :href="copy.url" target="_blank" rel="noopener" class="font-medium text-brand-600 hover:underline dark:text-brand-400">{{ sourceLabel(copy.source) }} ({{ formatBrl(copy.total) }})</a>{{ index < card.copies.length - 1 ? ', ' : '' }}
          </template>
        </p>
        <div class="flex items-center justify-between gap-2">
          <span>visto desde {{ formatDayMonth(listing.first_seen) }}</span>
          <button
            v-if="card.history.length > 1"
            type="button"
            :aria-expanded="showHistory"
            class="font-medium text-brand-600 hover:underline dark:text-brand-400"
            @click="showHistory = !showHistory"
          >
            histórico de preço
          </button>
        </div>
        <div
          v-if="showHistory"
          class="absolute inset-x-3 bottom-11 max-h-48 overflow-auto rounded-xl bg-white p-3 shadow-lg ring-1 ring-slate-200 dark:bg-slate-800 dark:ring-slate-700"
        >
          <p class="mb-1 font-semibold text-slate-600 dark:text-slate-300">Histórico de preço</p>
          <ul class="space-y-0.5">
            <li v-for="point in historyNewestFirst" :key="point.observed_at" class="flex justify-between">
              <span>{{ formatDate(point.observed_at) }}</span><span class="font-medium">{{ formatBrl(point.total) }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </article>
</template>
