const CACHE_PREFIX="find-pax-";
const APP_VERSION="v1.1";
const CACHE_REV="r35";
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

function cacheKey(req){
  if(req.mode==="navigate") return new Request(new URL("./index.html",self.registration.scope));
  const u=new URL(req.url);
  u.search="";
  u.hash="";
  return new Request(u.toString(),{method:"GET"});
}

self.addEventListener("fetch",e=>{
  const req=e.request;
  if(req.method!=="GET") return;
  const url=new URL(req.url);
  if(url.origin!==self.location.origin) return;

  const key=cacheKey(req);
  const network=fetch(req).then(async r=>{
    const canCache=r&&(r.ok||r.type==="opaque")&&!(req.mode==="navigate"&&r.redirected);
    if(canCache){
      const cache=await caches.open(CACHE);
      await cache.put(key,r.clone()).catch(()=>{});
    }
    return r;
  });

  // Keep the network refresh alive, but never make a cached launch wait for it.
  e.waitUntil(network.then(()=>{}).catch(()=>{}));
  e.respondWith((async()=>{
    const cache=await caches.open(CACHE);
    const cached=await cache.match(key);
    if(cached) return cached;
    return network;
  })());
});
