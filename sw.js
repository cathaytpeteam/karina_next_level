const CACHE_PREFIX="find-pax-";
const CACHE="find-pax-release-20260921-paging-fix";
const ASSETS=["./","./index.html","./manifest.webmanifest","./apple-touch-icon.png","./icon-192.png","./icon-512.png","./icon-maskable-192.png","./icon-maskable-512.png","./phone-bottom-icon.png","./disrupted-pax-icon-v2.png","./scenario-icon-1.png","./scenario-icon-2.png","./scenario-icon-3.png","./scenario-icon-4.png"];

self.addEventListener("install",e=>e.waitUntil(
  caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting())
));

self.addEventListener("activate",e=>e.waitUntil(
  caches.keys()
    .then(keys=>Promise.all(keys.filter(k=>k.startsWith(CACHE_PREFIX)&&k!==CACHE).map(k=>caches.delete(k))))
    .then(()=>self.clients.claim())
));

self.addEventListener("fetch",e=>{
  if(e.request.method!=="GET") return;
  e.respondWith(
    fetch(e.request).then(r=>{
      if(r&&r.ok&&r.status===200&&r.type==="basic"){
        const copy=r.clone();
        e.waitUntil(caches.open(CACHE).then(c=>c.put(e.request,copy)).catch(()=>{}));
      }
      return r;
    }).catch(async()=>{
      const cache=await caches.open(CACHE);
      return (await cache.match(e.request)) || (await cache.match("./index.html"));
    })
  );
});
