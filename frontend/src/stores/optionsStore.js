/** Labels and suggestions loaded once and shared by the pages. */

import { ref } from 'vue';

const EMPTY_OPTIONS = {
  source_labels: {},
  kind_labels: {},
  sort_labels: {},
  default_neighborhoods: [],
  neighborhood_suggestions: [],
};

export function createOptionsStore(optionsService, toasts) {
  const options = ref(EMPTY_OPTIONS);

  async function load() {
    try {
      options.value = await optionsService.get();
    } catch (error) {
      toasts.error(error.message);
    }
  }

  const sourceLabel = (source) => options.value.source_labels[source] ?? source;
  const kindLabel = (kind) => options.value.kind_labels[kind] ?? 'Apartamento';

  return { options, load, sourceLabel, kindLabel };
}
