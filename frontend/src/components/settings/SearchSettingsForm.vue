<!-- Search criteria and schedule. Edits a local draft and saves it as a whole. -->
<script setup>
import { reactive, ref, watch } from 'vue';
import ToggleSwitch from '../ui/ToggleSwitch.vue';
import NeighborhoodPicker from './NeighborhoodPicker.vue';
import PriceRangeInput from './PriceRangeInput.vue';
import CheckTimesEditor from './CheckTimesEditor.vue';
import FavoritesSummary from './FavoritesSummary.vue';
import { useOptions, useServices, useToasts } from '../../core/injection.js';
import { toDraft, toPayload } from '../../core/settingsDraft.js';

const props = defineProps({
  settings: { type: Object, required: true },
});
const emit = defineEmits(['saved']);

const { settings: settingsService } = useServices();
const { options } = useOptions();
const toasts = useToasts();
const draft = reactive({});
const saving = ref(false);

watch(() => props.settings, (settings) => Object.assign(draft, toDraft(settings)), { immediate: true });

async function save() {
  const payload = toPayload(draft);
  if (payload.error) {
    toasts.error(payload.error);
    return;
  }
  saving.value = true;
  try {
    emit('saved', await settingsService.save(payload.value));
    toasts.success('Configurações salvas. A nova busca vale a partir da próxima verificação.');
  } catch (error) {
    toasts.error(error.message);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <section class="card p-6">
    <h2 class="text-base font-bold">Busca e alertas</h2>
    <p class="mb-5 text-sm text-slate-500">Critérios aplicados a todos os sites.</p>
    <form class="space-y-5" @submit.prevent="save">
      <ToggleSwitch v-model="draft.enabled" title="Monitor ligado" description="Desligue para pausar todas as verificações automáticas." />

      <NeighborhoodPicker v-model="draft.neighborhoods" :suggestions="options.neighborhood_suggestions" :defaults="options.default_neighborhoods" />

      <div class="grid gap-4 sm:grid-cols-2">
        <label class="block">
          <span class="label">Máximo de quartos</span>
          <input v-model.number="draft.max_bedrooms" type="number" min="0" max="5" class="field">
        </label>
        <label class="block">
          <span class="label">Área máxima (m², vazio = sem limite)</span>
          <input v-model="draft.max_area" inputmode="numeric" class="field">
        </label>
      </div>

      <PriceRangeInput v-model:min="draft.min_total" v-model:max="draft.max_total" legend="Faixa de preço (R$ total/mês, vazio = sem limite)" />

      <FavoritesSummary />

      <CheckTimesEditor v-model="draft.check_times" />

      <p class="rounded-xl bg-brand-50 px-4 py-3 text-xs leading-relaxed text-brand-700 dark:bg-brand-500/10 dark:text-brand-400">
        A busca guarda só os anúncios que batem com bairros, quartos, área e faixa de preço (valor total = aluguel + condomínio + IPTU).
        A primeira verificação apenas preenche a lista; a partir da segunda, você recebe os apartamentos <b>novos</b> e as <b>novidades dos favoritos</b>.
      </p>

      <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? 'Salvando…' : 'Salvar configurações' }}</button>
    </form>
  </section>
</template>
