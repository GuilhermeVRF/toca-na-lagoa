/** Listings endpoints. */

import { filtersToQuery } from '../config/listingFilters.js';

export class ListingsService {
  constructor(http) {
    this.http = http;
  }

  list(filters) {
    return this.http.get('/api/listings', filtersToQuery(filters));
  }

  update(listingId, changes) {
    return this.http.patch(`/api/listings/${listingId}`, changes);
  }

  favoritesSummary() {
    return this.http.get('/api/favorites/summary');
  }
}
