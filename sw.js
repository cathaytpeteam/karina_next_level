const CACHE_PREFIX="find-pax-";
const APP_VERSION="v1.1";
const CACHE_REV="R1";
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

// Android cold start: Static Routing lets Chrome answer launch requests straight
// from Cache Storage without first booting this worker. Only the exact ASSETS
// URLs (no query string) are routed; anything else, and every browser without
// the API (iOS Safari, older Chrome), keeps using the fetch handler below.
// A routed request that is missing from the cache falls back to the network.
const HAS_STATIC_ROUTES=typeof InstallEvent!=="undefined"&&"addRoutes" in InstallEvent.prototype;
function staticRoutes(){
  const scope=new URL(self.registration.scope);
  return ASSETS.map(a=>({
    condition:{urlPattern:new URLPattern({
      protocol:scope.protocol.replace(":",""),
      hostname:scope.hostname,
      port:scope.port,
      pathname:new URL(a,scope).pathname,
      search:""
    })},
    source:"cache"
  }));
}

self.addEventListener("install",e=>{
  let routes=Promise.resolve();
  if(HAS_STATIC_ROUTES){
    try{ routes=Promise.resolve(e.addRoutes(staticRoutes())).catch(()=>{}); }catch(err){}
  }
  e.waitUntil((async()=>{
    await routes;
    const cache=await caches.open(CACHE);
    await cache.addAll(ASSETS);
    await self.skipWaiting();
  })());
});

self.addEventListener("activate",e=>e.waitUntil(
  caches.keys()
    .then(keys=>Promise.all(keys.filter(k=>k.startsWith(CACHE_PREFIX)&&k!==CACHE).map(k=>caches.delete(k))))
    .then(()=>self.clients.claim())
    // install's addAll may have been served from the HTTP cache; revalidate once
    // so a statically routed launch never keeps a stale copy (304s are cheap).
    .then(()=>{ if(HAS_STATIC_ROUTES) startRefresh(); })
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

// Background refresh for statically routed assets. Routed launch requests never
// reach the fetch handler, so the page asks for this refresh from the phone-input
// idle window (a few seconds after first paint) instead of during startup.
// Without Static Routing the fetch handler already refreshes, so this is a no-op.
let refreshing=null;
async function refreshAssets(){
  const cache=await caches.open(CACHE);
  for(const a of ASSETS){
    const url=new URL(a,self.registration.scope).toString();
    try{
      const r=await fetch(url,{cache:"no-cache"});
      if(!r||!r.ok||r.redirected) continue;
      const old=await cache.match(url);
      const tag=r.headers.get("etag"), oldTag=old&&old.headers.get("etag");
      if(tag&&oldTag&&tag===oldTag) continue; // unchanged: skip the disk write
      await cache.put(url,r).catch(()=>{});
    }catch(err){}
  }
  try{ await self.registration.update(); }catch(err){}
}
function startRefresh(){
  if(!refreshing) refreshing=refreshAssets().finally(()=>{refreshing=null;});
  return refreshing;
}
self.addEventListener("message",e=>{
  if(!HAS_STATIC_ROUTES||!e.data||e.data.type!=="refresh") return;
  e.waitUntil(startRefresh());
});
