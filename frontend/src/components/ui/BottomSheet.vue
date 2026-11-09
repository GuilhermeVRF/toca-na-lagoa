<!-- Panel that slides up from the bottom of the screen (mobile), closing on backdrop click or Escape. -->
<script setup>
import { onBeforeUnmount, watch } from 'vue';
import AppIcon from './AppIcon.vue';

defineProps({
  title: { type: String, required: true },
});
const open = defineModel('open', { type: Boolean, required: true });

const close = () => { open.value = false; };
const closeOnEscape = (event) => {
  if (event.key === 'Escape') close();
};

watch(open, (isOpen) => {
  document.body.style.overflow = isOpen ? 'hidden' : '';
  if (isOpen) document.addEventListener('keydown', closeOnEscape);
  else document.removeEventListener('keydown', closeOnEscape);
});

onBeforeUnmount(() => {
  document.body.style.overflow = '';
  document.removeEventListener('keydown', closeOnEscape);
});
</script>

<template>
  <Teleport to="body">
    <Transition name="sheet-backdrop">
      <div v-if="open" class="fixed inset-0 z-40 bg-tinta-950/50 backdrop-blur-sm" @click="close" />
    </Transition>
    <Transition name="sheet">
      <section
        v-if="open"
        role="dialog"
        aria-modal="true"
        :aria-label="title"
        class="fixed inset-x-0 bottom-0 z-50 flex max-h-[85vh] flex-col rounded-t-[18px] bg-white shadow-2xl dark:bg-tinta-900"
      >
        <div class="mx-auto mt-2.5 h-1.5 w-10 shrink-0 rounded-full bg-tinta-200 dark:bg-tinta-700" />
        <header class="flex shrink-0 items-center justify-between px-5 pb-2 pt-3">
          <h2 class="display text-xl">{{ title }}</h2>
          <button type="button" title="Fechar" class="rounded-md p-1.5 text-tinta-400 hover:bg-tinta-100 dark:hover:bg-tinta-800" @click="close">
            <AppIcon name="close" class="h-5 w-5" stroke-width="2.2" />
          </button>
        </header>
        <div class="flex-1 overflow-y-auto px-5 pb-4">
          <slot />
        </div>
        <footer v-if="$slots.footer" class="shrink-0 border-t border-tinta-100 px-5 pb-[max(1rem,env(safe-area-inset-bottom))] pt-3 dark:border-tinta-800">
          <slot name="footer" />
        </footer>
      </section>
    </Transition>
  </Teleport>
</template>
