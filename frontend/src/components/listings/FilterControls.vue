<!--
  The filter inputs themselves. "inline" renders compact pills (desktop bar);
  "stacked" renders labeled, full-width controls (mobile sheet).
-->
<script setup>
import AppIcon from '../ui/AppIcon.vue';
import { TOGGLE_FILTERS } from '../../config/listingFilters.js';

defineProps({
  selects: { type: Array, required: true },
  layout: { type: String, default: 'inline', validator: (value) => ['inline', 'stacked'].includes(value) },
});
const filters = defineModel({ type: Object, required: true });

const update = (changes) => { filters.value = { ...filters.value, ...changes }; };
</script>

<template>
  <div v-if="layout === 'inline'" class="flex flex-wrap items-center gap-2">
    <label v-for="select in selects" :key="select.key" class="pill-select" :class="{ 'pill-select--active': filters[select.key] }">
      <AppIcon :name="select.icon" class="h-4 w-4 shrink-0" />
      <select
        :aria-label="select.label"
        :value="filters[select.key]"
        class="cursor-pointer appearance-none border-0 bg-transparent py-0 pl-0 pr-5 text-sm font-medium focus:outline-none focus:ring-0"
        @change="update({ [select.key]: $event.target.value })"
      >
        <option value="">{{ select.label }}: todos</option>
        <option v-for="[value, label] in select.choices" :key="value" :value="value">{{ label }}</option>
      </select>
      <AppIcon name="chevronDown" class="pointer-events-none -ml-5 h-3.5 w-3.5 shrink-0 opacity-60" stroke-width="2.4" />
    </label>

    <span class="mx-1 h-6 w-px bg-tinta-200 dark:bg-tinta-700" />

    <button
      v-for="toggle in TOGGLE_FILTERS"
      :key="toggle.key"
      type="button"
      :aria-pressed="filters[toggle.key]"
      class="chip gap-1.5"
      :class="{ 'chip--active': filters[toggle.key] }"
      @click="update({ [toggle.key]: !filters[toggle.key] })"
    >
      <AppIcon :name="toggle.icon" class="h-3.5 w-3.5" stroke-width="2" />
      {{ toggle.label }}
    </button>
  </div>

  <div v-else class="space-y-5">
    <label v-for="select in selects" :key="select.key" class="block">
      <span class="label">{{ select.label }}</span>
      <span class="relative block">
        <AppIcon :name="select.icon" class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-tinta-400" />
        <select
          :value="filters[select.key]"
          class="field cursor-pointer appearance-none !pl-9 !pr-9"
          @change="update({ [select.key]: $event.target.value })"
        >
          <option value="">Todos</option>
          <option v-for="[value, label] in select.choices" :key="value" :value="value">{{ label }}</option>
        </select>
        <AppIcon name="chevronDown" class="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-tinta-400" stroke-width="2.4" />
      </span>
    </label>

    <div>
      <span class="label">Mostrar</span>
      <div class="grid grid-cols-2 gap-2">
        <button
          v-for="toggle in TOGGLE_FILTERS"
          :key="toggle.key"
          type="button"
          :aria-pressed="filters[toggle.key]"
          class="flex h-11 items-center gap-2 rounded-md px-3 text-sm font-semibold ring-1 transition"
          :class="filters[toggle.key]
            ? 'bg-cobalto-50 text-cobalto-700 ring-cobalto-300 dark:bg-cobalto-300/15 dark:text-cobalto-300 dark:ring-cobalto-500/40'
            : 'bg-white text-tinta-600 ring-tinta-200 dark:bg-tinta-800 dark:text-tinta-300 dark:ring-tinta-700'"
          @click="update({ [toggle.key]: !filters[toggle.key] })"
        >
          <AppIcon :name="toggle.icon" class="h-4 w-4 shrink-0" stroke-width="2" />
          {{ toggle.label }}
        </button>
      </div>
    </div>
  </div>
</template>
