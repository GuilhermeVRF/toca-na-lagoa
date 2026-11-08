/**
 * Composition root: builds the HTTP client, services and stores once, wires
 * them together and provides them to the component tree. Nothing else
 * constructs dependencies.
 */

import { createApp, markRaw, watch } from 'vue';
import './styles/main.css';
import App from './App.vue';
import { createAuthGuard, LOGIN_PATH } from './core/authGuard.js';
import { HttpClient } from './core/httpClient.js';
import { AUTH, MONITOR, OPTIONS, ROUTER, SERVICES, TOASTS } from './core/injection.js';
import { AuthService } from './services/authService.js';
import { ListingsService } from './services/listingsService.js';
import { MonitorService } from './services/monitorService.js';
import { OptionsService } from './services/optionsService.js';
import { SettingsService } from './services/settingsService.js';
import { TelegramService } from './services/telegramService.js';
import { createAuthStore } from './stores/authStore.js';
import { createMonitorStore } from './stores/monitorStore.js';
import { createOptionsStore } from './stores/optionsStore.js';
import { createRouter } from './stores/router.js';
import { createToastStore } from './stores/toastStore.js';
import LoginPage from './components/auth/LoginPage.vue';
import ListingsPage from './components/listings/ListingsPage.vue';
import SettingsPage from './components/settings/SettingsPage.vue';

const http = new HttpClient(window.fetch.bind(window), { onUnauthorized: () => auth.sessionExpired() });
const services = {
  auth: new AuthService(http),
  listings: new ListingsService(http),
  settings: new SettingsService(http),
  telegram: new TelegramService(http),
  monitor: new MonitorService(http),
  options: new OptionsService(http),
};

const toasts = createToastStore();
const auth = createAuthStore(services.auth);
const router = createRouter([
  { path: '/', label: 'Apartamentos', component: markRaw(ListingsPage), nav: true },
  { path: '/settings', label: 'Configurações', component: markRaw(SettingsPage), nav: true },
  { path: LOGIN_PATH, label: 'Entrar', component: markRaw(LoginPage), nav: false },
]);
const monitor = createMonitorStore(services.monitor, toasts);
const options = createOptionsStore(services.options, toasts);

router.setGuard(createAuthGuard(auth));
watch([auth.checked, auth.authenticated], () => router.revalidate());
auth.on('signedIn', () => {
  options.load();
  monitor.startPolling();
});
auth.on('signedOut', () => monitor.stopPolling());
auth.check();

createApp(App)
  .provide(SERVICES, services)
  .provide(TOASTS, toasts)
  .provide(AUTH, auth)
  .provide(ROUTER, router)
  .provide(MONITOR, monitor)
  .provide(OPTIONS, options)
  .mount('#app');
