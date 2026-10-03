"""Service Worker scenarios (--sw) served over a GitHub-Pages-like local server."""
import vb_core
globals().update({k: v for k, v in vars(vb_core).items() if not k.startswith("__")})


import hashlib, http.server, io, os, shutil, tempfile, threading

class _SwServer:
    PRE = b'try{delete InstallEvent.prototype.addRoutes;}catch(e){}\n'
    def __init__(self, port, root, noroutes):
        self.port, self.root, self.noroutes = port, root, noroutes
        self.hits, self.fail404, self.httpd = [], set(), None
    def start(self):
        srv = self
        class H(http.server.SimpleHTTPRequestHandler):
            def __init__(h, *a, **k): super().__init__(*a, directory=srv.root, **k)
            def log_message(h, *a): pass
            def send_head(h):
                p = h.path.split("?")[0]
                srv.hits.append(p)
                if p in srv.fail404:
                    h.send_response(404); h.send_header("Content-Length", "0"); h.end_headers(); return io.BytesIO(b"")
                path = h.translate_path(h.path)
                if os.path.isdir(path): path = os.path.join(path, "index.html")
                if not os.path.isfile(path): return super().send_head()
                data = open(path, "rb").read()
                if srv.noroutes and p.endswith("/sw.js"): data = _SwServer.PRE + data
                tag = '"%s"' % hashlib.md5(data).hexdigest()
                if h.headers.get("If-None-Match") == tag:
                    h.send_response(304); h.send_header("ETag", tag); h.send_header("Cache-Control", "max-age=600"); h.end_headers(); return None
                h.send_response(200); h.send_header("Content-Type", h.guess_type(path)); h.send_header("Content-Length", str(len(data)))
                h.send_header("ETag", tag); h.send_header("Cache-Control", "max-age=600"); h.end_headers()
                return io.BytesIO(data)
        http.server.ThreadingHTTPServer.allow_reuse_address = True
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", self.port), H)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
    def stop(self):
        if self.httpd:
            self.httpd.shutdown(); self.httpd.server_close(); self.httpd = None
    @property
    def url(self): return f"http://localhost:{self.port}/"

def _copy_build(src, dst):
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git", ".github", "__pycache__"))

_SW_IDLE_JS = "navigator.serviceWorker.getRegistration().then(r=>!!r&&!r.installing&&!r.waiting)"

async def _sw_quiet(pg, srv, start, limit, need_sw=True, quiet=0.4, floor=0.0):
    """Wait until the Service Worker has finished this launch's work, at most limit ms.
    Done means: the browser's update check for sw.js reached the server (Chrome sends it about
    a second after load, so an update is not missed), no request for quiet s, no worker
    installing or waiting, and at least floor s since start. Offline there is no update
    check, so only the time conditions apply. Never waits longer than the old fixed limit."""
    loop = asyncio.get_running_loop(); end = loop.time() + limit / 1000
    seen, last = len(srv.hits), loop.time()
    while loop.time() < end:
        now = loop.time()
        if len(srv.hits) != seen: seen, last = len(srv.hits), now
        online = srv.httpd is not None
        sw_checked = not (online and need_sw) or any(h.endswith("/sw.js") for h in srv.hits[start:])
        if sw_checked and now - last >= quiet and now - (end - limit / 1000) >= floor:
            try:
                if await pg.evaluate(_SW_IDLE_JS): return
            except Exception:
                return
        await asyncio.sleep(0.05)

async def _sw_launch(ctx, srv, settle=3000):
    n = len(srv.hits); pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    try: await pg.goto(srv.url)
    except Exception as e: errs.append("goto: " + str(e)[:80])
    await pg.wait_for_timeout(500)
    early = len(srv.hits) - n if srv.httpd else 0
    # settle is the upper limit; short settles (300 ms) only read the cache and skip the update check.
    # Offline the failed background refresh (phone-input window, ~0.6 s after load) must have run: floor 0.8 s.
    await _sw_quiet(pg, srv, n, settle, need_sw=settle > 1000, floor=0 if srv.httpd else min(0.8, settle / 1000))
    return pg, early, errs

async def _sw_flow(pg):
    await pg.fill("#phoneInput", PHONE); await pg.wait_for_timeout(150)
    for sel in ("#cta", "#goMiss", "#missJoin"):
        await pg.click(sel); await pg.wait_for_timeout(200)
    await pg.fill("#mFlight", "451"); await pg.wait_for_timeout(150); await pg.click("#cta"); await pg.wait_for_timeout(200)
    await pg.fill("#mSec", "123"); await pg.wait_for_timeout(150); await pg.click("#cta"); await pg.wait_for_timeout(300)
    return await pg.eval_on_selector("#msg", "e=>e.value")

_CACHE_JS = """async()=>{const o={};for(const k of await caches.keys()){const c=await caches.open(k);o[k]=(await c.keys()).length;}return o}"""
async def _cached_text(pg, path):
    return await pg.evaluate("async p=>{const r=await caches.match(new URL(p,location).href);return r?await r.text():null}", path)
async def _has(pg, marker):
    return await pg.evaluate("m=>new XMLSerializer().serializeToString(document).includes(m)", marker)
async def _expire_http_cache(ctx):
    pg = await ctx.new_page(); cdp = await ctx.new_cdp_session(pg)
    await cdp.send("Network.enable"); await cdp.send("Network.clearBrowserCache"); await pg.close()
async def _until(ctx, srv, marker, maxn=4, expire=False):
    if expire: await _expire_http_cache(ctx)
    for i in range(1, maxn + 1):
        pg, _, _ = await _sw_launch(ctx, srv); ok = await _has(pg, marker); await pg.close()
        if ok: return i
    return None

async def _until_app_version(ctx, srv, version, maxn=4, expire=False):
    """Wait for the installed page to render the current build's home label."""
    if expire: await _expire_http_cache(ctx)
    for i in range(1, maxn + 1):
        pg, _, _ = await _sw_launch(ctx, srv)
        try:
            label = await pg.locator(".appVersion").inner_text(timeout=5000)
        except Exception:
            label = ""
        finally:
            await pg.close()
        if label.strip() == version:
            return i
    return None

def _app_version(root):
    html = Path(root, "index.html").read_text(encoding="utf-8")
    m = re.search(r'<span\b[^>]*class="[^"]*\bappVersion\b[^"]*"[^>]*>([^<]+)</span>', html)
    return m.group(1).strip() if m else ""

def _join_en(root):
    """Current S1 Join English message, read from the build's copy.js."""
    src = Path(root, "copy.js").read_text(encoding="utf-8")
    m = re.search(r'"s1\.join\.en":\s*("(?:[^"\\]|\\.)*")', src)
    return json.loads(m.group(1)) if m else ""

async def _sw_mode(p, tag, noroutes, port, previous, tmp):
    T = f"[SW {tag}] "
    exp = " after HTTP cache expiry" if noroutes else ""
    root = os.path.join(tmp, tag.replace(" ", "_")); _copy_build(R, root)
    srv = _SwServer(port, root, noroutes); srv.start()
    b = await launch_chromium(p)
    ctx = await b.new_context(viewport={"width": 390, "height": 800}, is_mobile=True, has_touch=True)
    # 1 first visit
    pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    await pg.goto(srv.url, wait_until="domcontentloaded")
    ck(T + "1 first visit: SW not registered during first paint", not await pg.evaluate("navigator.serviceWorker.getRegistration().then(r=>!!r)"))
    loop = asyncio.get_running_loop(); end = loop.time() + 4
    while loop.time() < end and not await pg.evaluate("navigator.serviceWorker.getRegistration().then(r=>!!(r&&r.active&&r.active.state==='activated'))"):
        await asyncio.sleep(0.05)
    await _sw_quiet(pg, srv, 0, max(0, (end - loop.time()) * 1000), need_sw=False)
    ck(T + "1 first visit: SW registered and active in the phone-input idle window", await pg.evaluate("navigator.serviceWorker.getRegistration().then(r=>!!(r&&r.active))"))
    cs = await pg.evaluate(_CACHE_JS)
    ck(T + f"1 first visit: one cache with all {N_ASSETS} assets", len(cs) == 1 and list(cs.values()) == [N_ASSETS], str(cs))
    ck(T + "1 first visit: no JavaScript errors", not errs, "; ".join(errs[:3])); await pg.close()
    # 2 controlled launch
    if noroutes: await _expire_http_cache(ctx)
    n0 = len(srv.hits)
    pg, early, errs = await _sw_launch(ctx, srv)
    ck(T + "2 launch: page controlled by the SW", await pg.evaluate("!!navigator.serviceWorker.controller"))
    # Slow company network: no network request during launch in either mode;
    # every cached file is revalidated afterwards, in parallel, inside the phone-input window.
    ck(T + "2 launch: zero network requests during launch", early == 0, f"{early} requests")
    assets = {"/" + a[2:] for a in re.findall(r'"(\./[^"]*)"', open(os.path.join(root, "sw.js"), encoding="utf-8").read().split("const ASSETS=[")[1].split("];")[0])}
    seen = set(srv.hits[n0:])
    ck(T + "2 launch: every cached file revalidated in the phone-input window", assets <= seen, str(sorted(assets - seen)))
    msg = await _sw_flow(pg)
    ck(T + "2 launch: S1 Join flow reaches preview with current copy", "451/123" in msg and _join_en(R) in msg, msg[:80])
    ck(T + "2 launch: no JavaScript errors", not errs, "; ".join(errs[:3])); await pg.close()
    # 3 offline
    srv.stop()
    pg, _, errs = await _sw_launch(ctx, srv)
    ck(T + "3 offline: app opens with the phone library loaded", await pg.evaluate("!!window.libphonenumber"))
    ck(T + "3 offline: every image renders", await pg.evaluate("[...document.images].every(i=>i.complete&&i.naturalWidth>0)"))
    msg = await _sw_flow(pg)
    ck(T + "3 offline: full flow reaches preview", _join_en(R) in msg and "451/123" in msg)
    ck(T + "3 offline: failed background refresh raises no JavaScript errors", not errs, "; ".join(errs[:3]))
    ck(T + "3 offline: cache intact", sum((await pg.evaluate(_CACHE_JS)).values()) == N_ASSETS); await pg.close()
    srv.start()
    # 4 update: index.html only
    open(os.path.join(root, "index.html"), "a").write("\n<!-- UPD-A -->\n")
    n = await _until(ctx, srv, "UPD-A", expire=noroutes)
    ck(T + "4 update (index.html only): new version on 2nd launch" + exp, n is not None and n <= 2, f"launch {n}")
    pg, _, _ = await _sw_launch(ctx, srv, settle=300)
    idx = await _cached_text(pg, "./index.html"); root_ = await _cached_text(pg, "./")
    if noroutes: ck(T + "4 update: ./index.html cache entry refreshed", idx and "UPD-A" in idx)
    else: ck(T + "4 update: ./ and ./index.html cache entries both refreshed", idx and root_ and "UPD-A" in idx and "UPD-A" in root_)
    await pg.close()
    # 5 update: sw.js + index.html, with a new CACHE_REV as every release has, while an older copy of the
    # app stays open (a second tab, or the PWA left in the background): skipWaiting must still let the
    # new SW take over, and activate must delete the old cache.
    keeper, _, _ = await _sw_launch(ctx, srv)
    sw_path = os.path.join(root, "sw.js"); src = open(sw_path, encoding="utf-8").read()
    src_b = re.sub(r'const CACHE_REV="([^"]*)";', r'const CACHE_REV="\1-UPD-B";', src, count=1)
    ck(T + "5 update: test build moves CACHE_REV", src_b != src)
    open(sw_path, "w", encoding="utf-8").write(src_b + '\nself.addEventListener("message",e=>{if(e.data==="ver")e.source.postMessage("UPD-B");});\n')
    open(os.path.join(root, "index.html"), "a").write("\n<!-- UPD-B -->\n")
    n = await _until(ctx, srv, "UPD-B", expire=noroutes)
    ck(T + "5 update (sw.js + index.html): new version by 3rd launch" + exp, n is not None and n <= 3, f"launch {n}")
    pg, early, _ = await _sw_launch(ctx, srv)
    ver = await pg.evaluate("""()=>new Promise(res=>{const c=navigator.serviceWorker.controller;if(!c)return res(null);
      navigator.serviceWorker.addEventListener("message",e=>res(e.data),{once:true});c.postMessage("ver");setTimeout(()=>res("timeout"),2000)})""")
    ck(T + "5 update: new SW controls the page while an older page stays open", ver == "UPD-B", str(ver))
    cs = await pg.evaluate(_CACHE_JS)
    ck(T + "5 update: old cache removed, only the new CACHE_REV cache left", len(cs) == 1 and next(iter(cs)).endswith("-UPD-B"), str(sorted(cs)))
    if not noroutes: ck(T + "5 update: launch still makes zero network requests", early == 0, f"{early}")
    await pg.close(); await keeper.close()
    # 6 broken deploy
    srv.fail404 = {"/scenario-icon-4.png"}
    open(os.path.join(root, "index.html"), "a").write("\n<!-- UPD-C -->\n")
    await _until(ctx, srv, "UPD-C", expire=noroutes)
    pg, _, _ = await _sw_launch(ctx, srv)
    st = await pg.evaluate("async()=>{const r=await caches.match(new URL('./scenario-icon-4.png',location).href);return r?r.status:null}")
    ck(T + "6 deploy with a 404 file: cached good copy is kept", st == 200, str(st)); await pg.close()
    srv.fail404 = set()
    # 7 cache miss
    pg, _, _ = await _sw_launch(ctx, srv, settle=300)
    await pg.evaluate("async()=>{for(const k of await caches.keys()){const c=await caches.open(k);await c.delete(new URL('./libphonenumber-mobile.js',location).href);}}")
    await pg.close()
    # Without Static Routing the fetch handler answers the miss and must store the copy at once, before the
    # background refresh (phone-input window) could restore it. A routed miss goes to the network directly,
    # so with Static Routing only the refresh writes it back (checked below).
    n0 = len(srv.hits); pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    await pg.goto(srv.url)
    early_put = refreshed = False
    for _ in range(60):  # up to 3 s
        cached = (await _cached_text(pg, "./libphonenumber-mobile.js")) is not None
        refreshed = any(h not in ("/libphonenumber-mobile.js", "/sw.js") for h in srv.hits[n0:])
        if cached or refreshed:
            early_put = cached and not refreshed; break
        await pg.wait_for_timeout(50)
    if noroutes: ck(T + "7 cache miss: fetch handler stores the network copy before the background refresh", early_put,
                    "refresh ran first" if refreshed else "never stored")
    await _sw_quiet(pg, srv, n0, 3000)
    ck(T + "7 cache miss: asset fetched from network, app works", await pg.evaluate("!!window.libphonenumber") and not errs, "; ".join(errs[:3]))
    for _ in range(30):  # up to 1.5 s for the write-back
        if (await _cached_text(pg, "./libphonenumber-mobile.js")) is not None: break
        await pg.wait_for_timeout(50)
    ck(T + "7 cache miss: asset written back to cache", (await _cached_text(pg, "./libphonenumber-mobile.js")) is not None)
    await pg.close(); await ctx.close()
    # 8 upgrade from a previous build
    if previous:
        up = os.path.join(tmp, tag.replace(" ", "_") + "_up"); _copy_build(previous, up); srv.stop(); srv.root = up; srv.start()
        ctx = await b.new_context(viewport={"width": 390, "height": 800}, is_mobile=True, has_touch=True)
        for _ in range(2):
            pg, _, _ = await _sw_launch(ctx, srv, settle=2500); await pg.close()
        for f in os.listdir(R):
            if (R / f).is_file(): shutil.copy(R / f, os.path.join(up, f))
        current_version = _app_version(R)
        ck(T + "8 upgrade: current build has a homepage version label", bool(current_version), current_version)
        n = await _until_app_version(ctx, srv, current_version, expire=noroutes)
        ck(T + "8 upgrade from previous build: new version by 3rd launch" + exp, n is not None and n <= 3, f"launch {n}")
        pg, early, errs = await _sw_launch(ctx, srv)
        if not noroutes: ck(T + "8 upgrade: launch makes zero network requests", early == 0, f"{early}")
        msg = await _sw_flow(pg)
        ck(T + "8 upgrade: current copy in effect", _join_en(R) in msg and "451/123" in msg)
        ck(T + "8 upgrade: no JavaScript errors", not errs, "; ".join(errs[:3])); await pg.close()
        srv.stop()
        pg, _, _ = await _sw_launch(ctx, srv, settle=2500)
        ck(T + "8 upgrade: offline flow works", _join_en(R) in await _sw_flow(pg)); await pg.close()
    srv.stop(); await b.close()

async def sw_suite(previous):
    """Both modes, each with its own server, port, build copy and browser. With --jobs 2/3 they run at the
    same time (each mode's steps stay in order, since every step builds on the one before); --jobs 1 runs
    them one after the other. verify_release.py runs them with --jobs 2 unless --jobs is given.
    Each mode prints its lines together when it ends."""
    from playwright.async_api import async_playwright
    modes = [("static-routing", False, 8931), ("no-static-routing", True, 8932)]
    with tempfile.TemporaryDirectory() as tmp:
        async with async_playwright() as p:
            async def one(tag, noroutes, port):
                buf = []
                vb_core._OUT.set(buf)
                try:
                    await _sw_mode(p, tag, noroutes, port, previous, tmp)
                finally:
                    if buf:
                        print("\n".join(buf), flush=True)
            if workers() > 1:
                done = await asyncio.gather(*(one(*m) for m in modes), return_exceptions=True)
                for e in done:
                    if isinstance(e, BaseException):
                        raise e
            else:
                for m in modes:
                    await one(*m)
    if not previous:
        print("SKIP [SW] 8 upgrade from a previous build (run with --previous DIR to include)")
