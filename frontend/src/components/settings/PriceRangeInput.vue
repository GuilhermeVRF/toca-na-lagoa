<!-- "de … até …" pair of money inputs; values stay as typed text until the form saves. -->
<script setup>
defineProps({
  legend: { type: String, required: true },
});

const min = defineModel('min', { type: String, required: true });
const max = defineModel('max', { type: String, required: true });
</script>

<template>
  <fieldset>
    <legend class="label">{{ legend }}</legend>
    <div class="flex items-center gap-2">
      <label class="relative flex-1">
        <span class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-xs font-semibold text-slate-400">de</span>
        <input v-model="min" inputmode="numeric" placeholder="ex.: 1.200" aria-label="Valor total mínimo" class="field !pl-9">
      </label>
      <span class="text-slate-300 dark:text-slate-600">—</span>
      <label class="relative flex-1">
        <span class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-xs font-semibold text-slate-400">até</span>
        <input v-model="max" inputmode="numeric" placeholder="ex.: 2.500" aria-label="Valor total máximo" class="field !pl-11">
      </label>
    </div>
  </fieldset>
</template>
