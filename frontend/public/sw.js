// Cache only the application shell. Never cache authenticated API responses.
const CACHE='hillwatch-shell-v1';
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(c=>c.addAll(['/']))));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))));
self.addEventListener('fetch',event=>{const url=new URL(event.request.url);if(event.request.method!=='GET'||url.origin!==location.origin||url.pathname.startsWith('/api'))return;event.respondWith(fetch(event.request).then(r=>{if(r.ok&&['document','script','style','font'].includes(event.request.destination)){const copy=r.clone();caches.open(CACHE).then(c=>c.put(event.request,copy))}return r}).catch(()=>caches.match(event.request).then(r=>r||new Response('Offline resource unavailable',{status:503}))));});
