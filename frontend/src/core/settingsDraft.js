/**
 * Conversion between the settings returned by the API and the editable form
 * draft, where optional numbers are kept as the text the user typed.
 */

import { formatNumber, parseInteger } from './format.js';

const OPTIONAL_NUMBERS = { max_area: 'Área máxima', min_total: 'Valor mínimo', max_total: 'Valor máximo' };

export function toDraft(settings) {
  return {
    enabled: settings.enabled,
    neighborhoods: [...settings.neighborhoods],
    max_bedrooms: settings.max_bedrooms,
    check_times: [...settings.check_times],
    ...Object.fromEntries(Object.keys(OPTIONAL_NUMBERS).map((key) => [key, formatNumber(settings[key])])),
  };
}

/** Returns `{ value }` ready for the API, or `{ error }` with a message for the user. */
export function toPayload(draft) {
  const value = {
    enabled: draft.enabled,
    neighborhoods: draft.neighborhoods,
    max_bedrooms: draft.max_bedrooms,
    check_times: draft.check_times,
  };
  for (const [key, label] of Object.entries(OPTIONAL_NUMBERS)) {
    const number = parseInteger(draft[key]);
    if (Number.isNaN(number)) return { error: `${label} inválido(a): use só números.` };
    value[key] = number;
  }
  return { value };
}
