<!--
  Login page. Only asks for the password: there is a single user. After a
  successful login the router guard sends the user back to where they were.
-->
<script setup>
import { onMounted, ref } from 'vue';
import AppIcon from '../ui/AppIcon.vue';
import BrandMark from '../ui/BrandMark.vue';
import { useAuth } from '../../core/injection.js';
import { useTheme } from '../../stores/useTheme.js';

const auth = useAuth();
const { isDark, toggle: toggleTheme } = useTheme();
const password = ref('');
const showPassword = ref(false);
const error = ref('');
const submitting = ref(false);
const input = ref(null);

onMounted(() => input.value.focus());

async function submit() {
  if (!password.value) {
    error.value = 'Digite a senha.';
    return;
  }
  submitting.value = true;
  error.value = '';
  try {
    await auth.login(password.value);
  } catch (loginError) {
    error.value = loginError.message;
    password.value = '';
    input.value.focus();
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="relative flex min-h-screen items-center justify-center overflow-hidden bg-cobalto-700 px-4 py-12 dark:bg-cobalto-900">
    <div class="azulejo pointer-events-none absolute inset-0 text-white/[0.09] dark:text-cobalto-300/[0.08]" />

    <button
      type="button"
      title="Alternar tema"
      class="absolute right-4 top-4 rounded-md p-2 text-white/80 ring-1 ring-white/15 hover:bg-white/10 hover:text-white"
      @click="toggleTheme"
    >
      <AppIcon :name="isDark ? 'sun' : 'moon'" class="h-5 w-5" />
    </button>

    <main class="relative w-full max-w-sm">
      <div class="mb-8 text-center text-white">
        <BrandMark class="mx-auto mb-4 h-14 w-14" />
        <h1 class="display text-4xl">Toca na Lagoa</h1>
        <p class="overline mt-2 text-white/65">Aluguel · Pampulha, BH</p>
      </div>

      <form class="card p-6 shadow-xl shadow-cobalto-950/30" novalidate @submit.prevent="submit">
        <h2 class="display text-xl">Entrar</h2>
        <p class="mb-5 text-sm text-tinta-500 dark:text-tinta-400">Digite a senha para ver os apartamentos.</p>

        <label for="password" class="label">Senha</label>
        <div class="relative">
          <span class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-tinta-400">
            <AppIcon name="lock" class="h-4 w-4" />
          </span>
          <input
            id="password"
            ref="input"
            v-model="password"
            :type="showPassword ? 'text' : 'password'"
            name="password"
            autocomplete="current-password"
            :aria-invalid="Boolean(error)"
            aria-describedby="password-error"
            class="field !pl-9 !pr-10"
            :class="{ '!ring-2 !ring-barro-400 dark:!ring-barro-500/60': error }"
            @input="error = ''"
          >
          <button
            type="button"
            :title="showPassword ? 'Esconder senha' : 'Mostrar senha'"
            :aria-pressed="showPassword"
            class="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-tinta-400 hover:bg-tinta-100 hover:text-tinta-600 dark:hover:bg-tinta-700"
            @click="showPassword = !showPassword"
          >
            <AppIcon :name="showPassword ? 'eyeOff' : 'eye'" class="h-4 w-4" />
          </button>
        </div>
        <p id="password-error" class="mt-1.5 min-h-[1.25rem] text-xs font-medium text-barro-600 dark:text-barro-400" role="alert">{{ error }}</p>

        <button type="submit" class="btn-primary mt-2 w-full justify-center" :disabled="submitting">
          <AppIcon v-if="submitting" name="refresh" class="h-4 w-4 animate-spin" stroke-width="2.2" />
          {{ submitting ? 'Entrando…' : 'Entrar' }}
        </button>
      </form>

      <p class="mt-6 text-center text-xs text-white/65">A sessão fica salva neste navegador por 30 dias.</p>
    </main>
  </div>
</template>
