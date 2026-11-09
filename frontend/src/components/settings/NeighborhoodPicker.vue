<!-- Tag input for neighborhoods with accent-insensitive autocomplete. -->
<script setup>
import { computed, ref } from 'vue';
import AppIcon from '../ui/AppIcon.vue';
import { normalizeText } from '../../core/format.js';

const MAX_SUGGESTIONS = 8;

const props = defineProps({
  suggestions: { type: Array, default: () => [] },
  defaults: { type: Array, default: () => [] },
});
const names = defineModel({ type: Array, required: true });

const query = ref('');
const highlight = ref(0);
const input = ref(null);

const taken = computed(() => new Set(names.value.map(normalizeText)));
const matches = computed(() => {
  const wanted = normalizeText(query.value);
  if (!wanted) return [];
  return props.suggestions
    .filter((name) => !taken.value.has(normalizeText(name)) && normalizeText(name).includes(wanted))
    .slice(0, MAX_SUGGESTIONS);
});
const isDefault = computed(
  () => names.value.length === props.defaults.length && names.value.every((name, index) => name === props.defaults[index]),
);

function addMany(rawNames) {
  const seen = new Set(taken.value);
  const added = [];
  for (const raw of rawNames) {
    const name = raw.replace(/,/g, ' ').trim().replace(/\s+/g, ' ');
    if (name && !seen.has(normalizeText(name))) {
      seen.add(normalizeText(name));
      added.push(name);
    }
  }
  if (added.length) names.value = [...names.value, ...added];
  query.value = '';
  highlight.value = 0;
}

const add = (name) => addMany([name]);
const remove = (index) => { names.value = names.value.filter((_, position) => position !== index); };
const clear = () => {
  names.value = [];
  input.value.focus();
};
const restoreDefaults = () => { names.value = [...props.defaults]; };

function addHighlighted() {
  if (query.value.trim()) add(matches.value[highlight.value] ?? query.value);
}

function addOnComma(event) {
  if (event.key !== ',') return;
  event.preventDefault();
  add(query.value);
}

function removeLast() {
  if (!query.value && names.value.length) remove(names.value.length - 1);
}

function move(step) {
  highlight.value = Math.min(Math.max(highlight.value + step, 0), Math.max(matches.value.length - 1, 0));
}

const paste = (event) => addMany(event.clipboardData.getData('text').split(/[,;\n]/));
</script>

<template>
  <div>
    <div class="mb-1 flex items-baseline justify-between gap-2">
      <span class="text-xs font-semibold text-tinta-500 dark:text-tinta-400">Bairros <span class="font-normal">({{ names.length }})</span></span>
      <span class="flex gap-3 text-xs font-semibold">
        <button v-if="!isDefault" type="button" class="text-cobalto-600 hover:underline dark:text-cobalto-300" @click="restoreDefaults">Restaurar padrão</button>
        <button v-if="names.length" type="button" class="text-tinta-400 hover:text-barro-500" @click="clear">Limpar</button>
      </span>
    </div>
    <div
      class="flex min-h-[42px] cursor-text flex-wrap items-center gap-1.5 rounded-md bg-white p-1.5 ring-1 ring-tinta-200 transition focus-within:ring-2 focus-within:ring-cobalto-600 dark:bg-tinta-800 dark:ring-tinta-700"
      @click="input.focus()"
    >
      <span
        v-for="(name, index) in names"
        :key="name"
        class="inline-flex items-center gap-1 rounded-md bg-cobalto-50 py-1 pl-2.5 pr-1 text-xs font-semibold text-cobalto-700 dark:bg-cobalto-300/15 dark:text-cobalto-300"
      >
        {{ name }}
        <button
          type="button"
          :title="`Remover ${name}`"
          class="grid h-4 w-4 place-items-center rounded text-cobalto-700/60 hover:bg-cobalto-100 hover:text-barro-600 dark:text-cobalto-300/60 dark:hover:bg-cobalto-500/20"
          @click.stop="remove(index)"
        >
          <AppIcon name="close" class="h-3 w-3" stroke-width="3" />
        </button>
      </span>
      <div class="relative min-w-[10rem] flex-1">
        <input
          ref="input"
          v-model="query"
          type="text"
          autocomplete="off"
          role="combobox"
          aria-label="Adicionar bairro"
          :aria-expanded="matches.length > 0"
          placeholder="Digite um bairro e tecle Enter…"
          class="w-full border-0 bg-transparent px-1.5 py-1 text-sm placeholder:text-tinta-400 focus:outline-none focus:ring-0"
          @keydown="addOnComma"
          @keydown.enter.prevent="addHighlighted"
          @keydown.backspace="removeLast"
          @keydown.down.prevent="move(1)"
          @keydown.up.prevent="move(-1)"
          @keydown.esc="query = ''"
          @paste.prevent="paste"
          @input="highlight = 0"
        >
        <ul
          v-if="matches.length"
          role="listbox"
          class="absolute left-0 top-full z-10 mt-2 max-h-56 w-64 overflow-auto rounded-md bg-white p-1 text-sm shadow-lg ring-1 ring-tinta-200 dark:bg-tinta-800 dark:ring-tinta-700"
          @mousedown.prevent
        >
          <li
            v-for="(match, index) in matches"
            :key="match"
            role="option"
            :aria-selected="index === highlight"
            class="cursor-pointer rounded-md px-3 py-1.5"
            :class="{ 'bg-cobalto-50 text-cobalto-700 dark:bg-cobalto-300/15 dark:text-cobalto-300': index === highlight }"
            @click="add(match)"
            @mouseenter="highlight = index"
          >
            {{ match }}
          </li>
        </ul>
      </div>
    </div>
    <p class="mt-1 text-xs text-tinta-400">Enter ou vírgula adiciona · Backspace remove o último · dá para colar uma lista.</p>
  </div>
</template>
