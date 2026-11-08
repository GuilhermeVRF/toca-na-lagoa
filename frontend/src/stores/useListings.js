/**
 * State of the listings page: loading cards for a set of filters and toggling
 * favorite/hidden flags with optimistic updates.
 */

import { ref } from 'vue';

export function useListings(listingsService, toasts) {
  const cards = ref([]);
  const neighborhoods = ref([]);
  const loading = ref(false);
  const loaded = ref(false);
  let latestRequest = 0;

  async function load(filters) {
    const request = ++latestRequest;
    loading.value = true;
    try {
      const page = await listingsService.list(filters);
      if (request !== latestRequest) return;
      cards.value = page.cards;
      neighborhoods.value = page.neighborhoods;
      loaded.value = true;
    } catch (error) {
      toasts.error(error.message);
    } finally {
      if (request === latestRequest) loading.value = false;
    }
  }

  async function toggleFlag(card, flag) {
    const listing = card.listing;
    const nextValue = !listing[flag];
    listing[flag] = nextValue;
    try {
      Object.assign(listing, await listingsService.update(listing.id, { [flag]: nextValue }));
      return true;
    } catch (error) {
      listing[flag] = !nextValue;
      toasts.error(error.message);
      return false;
    }
  }

  return { cards, neighborhoods, loading, loaded, load, toggleFlag };
}
