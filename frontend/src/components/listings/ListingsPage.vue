<!--
  Listings page: keeps the filters in the URL, reloads the cards when they
  change and whenever the monitor reports a finished check.
-->
<script setup>
import { computed, onBeforeUnmount, watch } from 'vue';
import PageLayout from '../layout/PageLayout.vue';
import ListingsHero from './ListingsHero.vue';
import ListingFilters from './ListingFilters.vue';
import ListingCard from './ListingCard.vue';
import { useMonitor, useRouter, useServices, useToasts } from '../../core/injection.js';
import { filtersFromQuery, filtersToQuery } from '../../config/listingFilters.js';
import { useListings } from '../../stores/useListings.js';

const router = useRouter();
const monitor = useMonitor();
const toasts = useToasts();
const { listings: listingsService } = useServices();
const { cards, neighborhoods, loading, loaded, load, toggleFlag } = useListings(listingsService, toasts);

const filters = computed({
  get: () => filtersFromQuery(router.query.value),
  set: (next) => router.replaceQuery(filtersToQuery(next)),
});

const reload = () => load(filters.value);
watch(filters, reload, { immediate: true });
onBeforeUnmount(monitor.onCheckFinished(reload));

async function toggle(card, flag) {
  const changed = await toggleFlag(card, flag);
  if (!changed) return;
  if (flag === 'favorite' && card.listing.favorite) {
    toasts.success('Favoritado — você será avisado se sair do ar ou mudar de preço.');
  }
  reload();
}
</script>

<template>
  <PageLayout>
    <template #hero>
      <ListingsHero :count="cards.length" />
    </template>

    <ListingFilters v-model="filters" :neighborhoods="neighborhoods" :result-count="cards.length" />

    <div v-if="!loaded" class="card p-10 text-center text-tinta-500 dark:text-tinta-400">Carregando…</div>
    <div v-else-if="!cards.length" class="card relative overflow-hidden p-10 text-center text-tinta-500 dark:text-tinta-400">
      <div class="azulejo pointer-events-none absolute inset-0 text-cobalto-700/[0.06] dark:text-cobalto-300/[0.06]" />
      <p class="display relative text-2xl text-cobalto-700 dark:text-cobalto-200">Nada por aqui</p>
      <p class="relative mt-1">Nenhum apartamento com esses filtros.</p>
    </div>

    <div class="grid auto-rows-fr gap-5 transition-opacity sm:grid-cols-2 lg:grid-cols-3" :class="{ 'opacity-60': loading && loaded }">
      <ListingCard
        v-for="card in cards"
        :key="card.listing.id"
        :card="card"
        @toggle-favorite="toggle($event, 'favorite')"
        @toggle-hidden="toggle($event, 'hidden')"
      />
    </div>
  </PageLayout>
</template>
