import { describe, expect, it, vi } from 'vitest';
import { ApiError, HttpClient } from '../src/core/httpClient.js';
import { ListingsService } from '../src/services/listingsService.js';
import { filtersFromQuery } from '../src/config/listingFilters.js';

const jsonResponse = (status, body) => ({ ok: status < 400, status, json: async () => body });

describe('HttpClient', () => {
  it('sends JSON and returns the parsed body', async () => {
    const fetch = vi.fn().mockResolvedValue(jsonResponse(200, { ok: true }));
    const result = await new HttpClient(fetch).put('/api/settings', { enabled: true });
    expect(result).toEqual({ ok: true });
    expect(fetch).toHaveBeenCalledWith('/api/settings', expect.objectContaining({ method: 'PUT', body: '{"enabled":true}' }));
  });

  it('raises the API detail as an ApiError', async () => {
    const fetch = vi.fn().mockResolvedValue(jsonResponse(422, { detail: 'O valor mínimo é maior que o máximo' }));
    const request = new HttpClient(fetch).put('/api/settings', {});
    await expect(request).rejects.toThrow(new ApiError('O valor mínimo é maior que o máximo', 422));
  });

  it('notifies the app when the session is no longer valid', async () => {
    const fetch = vi.fn().mockResolvedValue(jsonResponse(401, { detail: 'Faça login para continuar' }));
    const onUnauthorized = vi.fn();
    await expect(new HttpClient(fetch, { onUnauthorized }).get('/api/status')).rejects.toThrow('Faça login');
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

    it('reports a network failure in Portuguese', async () => {
    const fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));
    await expect(new HttpClient(fetch).get('/api/status')).rejects.toThrow('Sem conexão');
  });
});

describe('ListingsService', () => {
  it('sends only the active filters as query parameters', async () => {
    const http = { get: vi.fn().mockResolvedValue({ cards: [] }) };
    await new ListingsService(http).list(filtersFromQuery({ favorites: '1' }));
    expect(http.get).toHaveBeenCalledWith('/api/listings', { sort: 'total', order: 'asc', favorites: '1' });
  });
});
