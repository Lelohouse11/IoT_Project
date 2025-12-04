const APP_CACHE = 'driver-app-v1'
const ASSETS = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/iot_icon.ico',
]

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(APP_CACHE).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting())
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== APP_CACHE).map((k) => caches.delete(k)))))
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return
  const isApi = request.url.includes('/api/')
  event.respondWith(
    (isApi
      ? fetch(request)
          .then((res) => {
            const clone = res.clone()
            caches.open(APP_CACHE).then((cache) => cache.put(request, clone))
            return res
          })
          .catch(() => caches.match(request))
      : caches.match(request).then((cached) => cached || fetch(request))
    )
  )
})
