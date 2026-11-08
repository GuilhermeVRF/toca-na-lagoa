<!--
  Sorting and filtering. On desktop every control is inline; on small screens
  only sorting stays visible and the filters move to a bottom sheet, with the
  active ones shown as removable chips.
-->
<script setup>
import { computed, ref } from 'vue';
import AppIcon from '../ui/AppIcon.vue';
import BottomSheet from '../ui/BottomSheet.vue';
import SortBar from './SortBar.vue';
import FilterControls from './FilterControls.vue';
import ActiveFilterChips from './ActiveFilterChips.vue';
import { useOptions } from '../../core/injection.js';
import { SELECT_FILTERS, TOGGLE_FILTERS, clearedFilters, countActiveFilters } from '../../config/listingFilters.js';

const props = defineProps({
  neighborhoods: { type: Array, required: true },
  resultCount: { type: Number, required: true },
});
const filters = defineModel({ type: Object, required: true });

const { options } = useOptions();
const sheetOpen = ref(false);

const selects = computed(() =>
  SELECT_FILTERS.map((filter) => ({
    ...filter,
    choices: filter.options({ neighborhoods: props.neighborhoods, options: options.value }),
  })),
);
const activeCount = computed(() => countActiveFilters(filters.value));
const activeItems = computed(() => [
  ...selects.value
    .filter(({ key }) => filters.value[key])
    .map(({ key, choices }) => ({
      key,
      label: choices.find(([value]) => value === filters.value[key])?.[1] ?? filters.value[key],
      cleared: '',
    })),
  ...TOGGLE_FILTERS.filter(({ key }) => filters.value[key]).map(({ key, label }) => ({ key, label, cleared: false })),
]);

const remove = (key) => {
  const item = activeItems.value.find((active) => active.key === key);
  filters.value = { ...filters.value, [key]: item.cleared };
};
const clear = () => { filters.value = clearedFilters(filters.value); };
</script>

<template>
  <div class="card mb-6 overflow-hidden">
    <div class="border-b border-slate-100 px-4 py-3 dark:border-slate-800">
      <SortBar v-model="filters" />
    </div>

    <div class="hidden items-center gap-2 px-4 py-3 sm:flex">
      <FilterControls v-model="filters" :selects="selects" layout="inline" class="flex-1" />
      <button
        v-if="activeCount"
        type="button"
        class="inline-flex shrink-0 items-center gap-1.5 self-start rounded-full px-3 py-1.5 text-xs font-semibold text-slate-500 transition hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-500/10"
        @click="clear"
      >
        <span class="grid h-4 min-w-4 place-items-center rounded-full bg-brand-600 px-1 text-[10px] text-white">{{ activeCount }}</span>
        Limpar
        <AppIcon name="close" class="h-3.5 w-3.5" stroke-width="2.4" />
      </button>
    </div>

    <div class="flex items-center gap-2 px-4 py-3 sm:hidden">
      <button
        type="button"
        class="inline-flex h-9 shrink-0 items-center gap-2 rounded-full bg-slate-100 px-3.5 text-sm font-semibold text-slate-700 transition active:scale-95 dark:bg-slate-800 dark:text-slate-200"
        :aria-expanded="sheetOpen"
        @click="sheetOpen = true"
      >
        <AppIcon name="sliders" class="h-4 w-4" stroke-width="2" />
        Filtros
        <span v-if="activeCount" class="grid h-5 min-w-5 place-items-center rounded-full bg-brand-600 px-1 text-[11px] text-white">{{ activeCount }}</span>
      </button>
      <ActiveFilterChips :items="activeItems" class="min-w-0 flex-1" @remove="remove" />
      <span v-if="!activeCount" class="truncate text-xs text-slate-400">Bairro, tipo, site, favoritos…</span>
    </div>
  </div>

  <BottomSheet v-model:open="sheetOpen" title="Filtros">
    <FilterControls v-model="filters" :selects="selects" layout="stacked" />
    <template #footer>
      <div class="flex gap-2">
        <button type="button" class="btn-secondary flex-1 justify-center" :disabled="!activeCount" @click="clear">Limpar</button>
        <button type="button" class="btn-primary flex-[2] justify-center" @click="sheetOpen = false">
          Ver {{ resultCount }} {{ resultCount === 1 ? 'apartamento' : 'apartamentos' }}
        </button>
      </div>
    </template>
  </BottomSheet>
</template>
