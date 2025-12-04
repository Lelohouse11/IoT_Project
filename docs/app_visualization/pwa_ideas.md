# Issue 17 — Progressive Web Application

## GPS
- PWA’s have the benefits of websites and integrated apps, so it shouldn’t be a problem to get the location on a phone.
- **iOS limitations:**
  - iOS does not allow tracking location in the background.
  - Access to GPS is more restricted and not as easy as on Android.
  - iOS might be trickier.


## Push Notifications
### Android
- Should not be a problem.
- Full support, background pushes are possible.

### iOS
- Web pushes for PWA’s are possible.
- Not working in Safari, only in the installed PWA.
- No notification badges or other advanced features.


## Offline Caching
- Offline functionality is handled via a **Service Worker** in PWA’s.
- Additionally, you can use the **Cache API**.
- Local data can be saved and last received sensor values can be displayed.
- **iOS limitations:**
  - Safari iOS limits memory.
  - IndexedDB on iOS is weaker (but still enough for our use case).


## Installable on iOS and Android
- **Android:** Yes.
- **iOS:** No App Store installation, no system-Bluetooth, restricted permissions.


## Possible Problems
- iOS doesn’t support Bluetooth for web applications.
- Sync:
  - Android: possible (but not fully).
  - iOS: not possible.
- → Real-time data in the background might be a challenge or not possible.
- WebSockets / MQTT should work without a problem.

---

# Which Framework to Use?

## SvelteKit
- Very fast (good for live data).
- Quick and easy setup for PWA and Service Workers.
- Server-Side Rendering + API endpoints included.
- Good for maps (Leaflet, MapLibre).
- Not much overhead.
- Not as many libraries and tutorials as React.

## React
- Biggest ecosystem (lots of libraries and tutorials).
- Workbox for PWA.
- Predefined components for maps, charts, UI…
- Quite heavy and not as fast in performance as others.

## Vue
- Medium performance and ecosystem.
- Good PWA support.
- Still fast enough for most IoT use cases.

## Angular PWA
- Probably too heavy for IoT-based projects.
- Slow startup times.
- Very complex.

---
# Final thoughts:
- Should Choose Between SvelteKit and React
- Svelte: best performance but might be a bit harder to get working.
- React: slightly less performance but easier to get working.

---

# Setup Guides

## Setting up SvelteKit:
https://dev.to/braide/building-progressive-web-applications-using-sveltekit-58gj

## Setting up React:
https://create-react-app.dev/docs/making-a-progressive-web-app/  
https://dev.to/yukaty/pwa-quick-guide-make-your-react-app-installable-2kai

https://github.com/GoogleChrome/workbox
