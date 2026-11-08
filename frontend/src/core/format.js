/** Formatting and parsing of the values shown in the UI (pt-BR). */

const BRL = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 });

export function formatBrl(value) {
  return value === null || value === undefined ? '—' : `R$ ${BRL.format(value)}`;
}

export function formatNumber(value) {
  return value === null || value === undefined ? '' : BRL.format(value);
}

/** Naive ISO timestamps from the API are already in local time; read their parts directly. */
function dateParts(iso) {
  const [date, time = ''] = iso.split('T');
  const [year, month, day] = date.split('-');
  return { year, month, day, time: time.slice(0, 5) };
}

export function formatDayMonth(iso) {
  const { day, month } = dateParts(iso);
  return `${day}/${month}`;
}

export function formatDate(iso) {
  const { day, month, year } = dateParts(iso);
  return `${day}/${month}/${year}`;
}

export function formatDateTime(iso) {
  const { day, month, time } = dateParts(iso);
  return `${day}/${month} às ${time}`;
}

/**
 * Parse "2.500", "R$ 2500" or "" into an integer (null when blank).
 * Returns NaN for anything else so callers can report it.
 */
export function parseInteger(text) {
  const digits = String(text ?? '').replace(/R\$|\.|\s/g, '');
  if (!digits) return null;
  return /^\d+$/.test(digits) ? Number(digits) : Number.NaN;
}

export function normalizeText(text) {
  return text.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().trim().replace(/\s+/g, ' ');
}
