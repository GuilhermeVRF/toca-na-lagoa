<!-- Step-by-step Telegram bot setup: save token, detect chat, send a test. -->
<script setup>
import { computed, ref, watch } from 'vue';
import { useServices, useToasts } from '../../core/injection.js';

const props = defineProps({
  settings: { type: Object, required: true },
});
const emit = defineEmits(['saved']);

const { telegram } = useServices();
const toasts = useToasts();
const botToken = ref('');
const chatId = ref('');
const pending = ref('');

watch(() => props.settings.telegram_chat_id, (value) => { chatId.value = value; }, { immediate: true });

const steps = computed(() => [
  { key: 'bot', done: false },
  { key: 'token', done: props.settings.telegram_token_set },
  { key: 'chat', done: Boolean(props.settings.telegram_chat_id) },
  { key: 'test', done: false },
]);

async function run(action, task, successMessage) {
  pending.value = action;
  try {
    const result = await task();
    if (result?.telegram_chat_id !== undefined) emit('saved', result);
    toasts.success(typeof successMessage === 'function' ? successMessage(result) : successMessage);
  } catch (error) {
    toasts.error(error.message);
  } finally {
    pending.value = '';
  }
}

const save = () =>
  run('save', async () => {
    const result = await telegram.save({ botToken: botToken.value, chatId: chatId.value });
    botToken.value = '';
    return result;
  }, 'Telegram salvo');
const detect = () => run('detect', () => telegram.detectChat(), (result) => `Chat detectado: ${result.telegram_chat_id}`);
const sendTest = () => run('test', () => telegram.sendTest(), (result) => result.message);
</script>

<template>
  <section class="card p-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h2 class="display text-xl">Telegram</h2>
        <p class="mb-5 text-sm text-tinta-500 dark:text-tinta-400">Alertas de apartamento novo direto no celular.</p>
      </div>
      <span v-if="settings.telegram_configured" class="rounded bg-folha-100 px-3 py-1 text-xs font-semibold text-folha-700 dark:bg-folha-500/15 dark:text-folha-400">Conectado</span>
      <span v-else class="rounded bg-tinta-100 px-3 py-1 text-xs font-semibold text-tinta-500 dark:text-tinta-400 dark:bg-tinta-800">Não conectado</span>
    </div>

    <ol class="mb-5 space-y-3 text-sm">
      <li v-for="(step, index) in steps" :key="step.key" class="flex gap-3">
        <span
          class="grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-bold"
          :class="step.done ? 'bg-folha-500 text-white' : 'bg-cobalto-50 text-cobalto-700 dark:bg-cobalto-300/15 dark:text-cobalto-300'"
        >{{ index + 1 }}</span>
        <span class="pt-0.5 text-tinta-600 dark:text-tinta-300">
          <template v-if="step.key === 'bot'">
            No Telegram, abra o
            <a class="font-semibold text-cobalto-600 underline dark:text-cobalto-300" href="https://t.me/BotFather" target="_blank" rel="noopener">@BotFather</a>,
            envie <code>/newbot</code> e siga as instruções.
          </template>
          <template v-else-if="step.key === 'token'">Copie o <b>token</b> que ele devolver e cole abaixo. Salve.</template>
          <template v-else-if="step.key === 'chat'">Abra o seu bot novo e envie <code>/start</code>. Depois clique em <b>Detectar chat</b>.</template>
          <template v-else>Clique em <b>Enviar teste</b> para confirmar.</template>
        </span>
      </li>
    </ol>

    <form class="space-y-4" @submit.prevent="save">
      <label class="block">
        <span class="label">Token do bot</span>
        <input
          v-model="botToken"
          type="password"
          autocomplete="off"
          class="field"
          :placeholder="settings.telegram_token_set ? '•••••••• (salvo — deixe em branco para manter)' : '123456789:AA…'"
        >
      </label>
      <label class="block">
        <span class="label">Chat ID</span>
        <input v-model="chatId" placeholder="preenchido pelo Detectar chat" class="field">
      </label>
      <div class="flex flex-wrap gap-2">
        <button type="submit" class="btn-primary" :disabled="Boolean(pending)">{{ pending === 'save' ? 'Salvando…' : 'Salvar' }}</button>
        <button type="button" class="btn-secondary" :disabled="Boolean(pending) || !settings.telegram_token_set" @click="detect">
          {{ pending === 'detect' ? 'Detectando…' : 'Detectar chat' }}
        </button>
        <button type="button" class="btn-secondary" :disabled="Boolean(pending) || !settings.telegram_configured" @click="sendTest">
          {{ pending === 'test' ? 'Enviando…' : 'Enviar teste' }}
        </button>
      </div>
    </form>
  </section>
</template>
