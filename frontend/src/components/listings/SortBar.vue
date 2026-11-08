<!-- Sort options (scrollable on small screens) and the ascending/descending switch. -->
<script setup>
import AppIcon from '../ui/AppIcon.vue';
import { useOptions } from '../../core/injection.js';
import { defaultOrder } from '../../config/listingFilters.js';

const filters = defineModel({ type: Object, required: true });
const { options } = useOptions();

const setSort = (sort) => { filters.value = { ...filters.value, sort, order: defaultOrder(sort) }; };
const flipOrder = () => { filters.value = { ...filters.value, order: filters.value.order === 'asc' ? 'desc' : 'asc' }; };
</script>

<template>
  <div class="flex items-center gap-2 sm:gap-3">
    <span class="hidden shrink-0 text-xs font-semibold uppercase tracking-wider text-slate-400 sm:inline">Ordenar</span>
    <div
      class="no-scrollbar -my-1 flex min-w-0 flex-1 gap-1.5 overflow-x-auto py-1 [mask-image:linear-gradient(to_right,black_85%,transparent)] sm:[mask-image:none]"
      role="radiogroup"
      aria-label="Ordenar por"
    >
      <button
        v-for="(label, key) in options.sort_labels"
        :key="key"
        type="button"
        role="radio"
        :aria-checked="filters.sort === key"
        class="chip shrink-0"
        :class="{ 'chip--solid': filters.sort === key }"
        @click="setSort(key)"
      >
        {{ label }}
      </button>
      <span class="w-6 shrink-0 sm:hidden" aria-hidden="true" />
    </div>
    <button
      type="button"
      :title="filters.order === 'asc' ? 'Menor primeiro — toque para inverter' : 'Maior primeiro — toque para inverter'"
      :aria-label="filters.order === 'asc' ? 'Menor primeiro' : 'Maior primeiro'"
      class="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-full bg-slate-100 px-2.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-200 sm:px-3 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
      @click="flipOrder"
    >
      <AppIcon name="arrowDown" class="h-4 w-4 transition" :class="{ 'rotate-180': filters.order === 'desc' }" stroke-width="2" />
      <span class="hidden sm:inline">{{ filters.order === 'asc' ? 'Menor primeiro' : 'Maior primeiro' }}</span>
    </button>
  </div>
</template>
