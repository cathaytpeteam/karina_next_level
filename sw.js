const CACHE_PREFIX="find-pax-";
const APP_VERSION="v1.1";
const CACHE_REV="r16";
const CACHE=CACHE_PREFIX+APP_VERSION+"-"+CACHE_REV;
const ASSETS=[
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./apple-touch-icon.png",
  "./icon-192.png",
  "./icon-512.png",
  "./icon-maskable-192.png",
  "./icon-maskable-512.png",
  "./phone-bottom-icon.png",
  "./scenario-icon-1.png",
  "./scenario-icon-2.png",
  "./scenario-icon-3.png",
  "./scenario-icon-4.png",
  "./libphonenumber-max.js"
];
self.addEventListener("install",e=>e.waitUntil((async()=>{
  const cache=await caches.open(CACHE);
  await cache.addAll(ASSETS);
  await self.skipWaiting();
})()));

self.addEventListener("activate",e=>e.waitUntil(
  caches.keys()
    .then(keys=>Promise.all(keys.filter(k=>k.startsWith(CACHE_PREFIX)&&k!==CACHE).map(k=>caches.delete(k))))
    .then(()=>self.clients.claim())
));

self.addEventListener("fetch",e=>{
  if(e.request.method!=="GET") return;
  e.respondWith(
    fetch(e.request).then(r=>{
      if(r&&(r.ok||r.type==="opaque")){
        const copy=r.clone();
        e.waitUntil(caches.open(CACHE).then(c=>c.put(e.request,copy)).catch(()=>{}));
      }
      return r;
    }).catch(async()=>{
      const cache=await caches.open(CACHE);
      return (await cache.match(e.request,{ignoreSearch:true})) || (e.request.mode==="navigate"?await cache.match("./index.html"):undefined);
    })
  );
});
