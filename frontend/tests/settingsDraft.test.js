import { describe, expect, it } from 'vitest';
import { toDraft, toPayload } from '../src/core/settingsDraft.js';

const SETTINGS = {
  enabled: true,
  neighborhoods: ['Castelo'],
  max_bedrooms: 1,
  check_times: ['08:00'],
  max_area: 70,
  min_total: null,
  max_total: 2500,
};

describe('settings draft', () => {
  it('shows optional numbers as formatted text', () => {
    expect(toDraft(SETTINGS)).toMatchObject({ max_total: '2.500', min_total: '' });
  });

  it('turns the draft back into the API payload', () => {
    expect(toPayload(toDraft(SETTINGS)).value).toEqual(SETTINGS);
  });

  it('reports a field typed with letters', () => {
    expect(toPayload({ ...toDraft(SETTINGS), min_total: '1k' }).error).toMatch('Valor mínimo');
  });
});
