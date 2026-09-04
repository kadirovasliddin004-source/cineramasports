"""Прокликивает каждую вкладку каждого раздела и ловит любые ошибки JS."""
from playwright.sync_api import sync_playwright
import pathlib, json, re, http.server, socketserver, threading, functools, sys, mock

root = str(pathlib.Path(".").resolve())
Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=root)
srv = socketserver.TCPServer(("127.0.0.1", 8250), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
CORS = {"Access-Control-Allow-Origin":"*", "content-type":"application/json"}

fails = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width":1280,"height":900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route(re.compile(r"thesportsdb\.com"),
             lambda r: r.fulfill(status=200, headers=CORS, body=json.dumps(mock.handle(r.request.url))))
    pg.goto("http://127.0.0.1:8250/index.html"); pg.wait_for_timeout(2200)

    def check(label, expect_sel=None):
        pg.wait_for_timeout(1400)
        if errs:
            fails.append(f"{label}: JS-ошибка {errs[-1][:90]}"); print(f"  ✗ {label}: {errs[-1][:90]}"); errs.clear(); return
        if expect_sel and not pg.query_selector(expect_sel):
            fails.append(f"{label}: нет {expect_sel}"); print(f"  ✗ {label}: не отрисовалось {expect_sel}"); return
        n = pg.eval_on_selector_all('.match, .event, tbody tr','e=>e.length')
        print(f"  ✓ {label} (строк: {n})")

    for lang in ["ru", "uz"]:
        print(f"\n=== язык {lang.upper()} ===")
        pg.click(f'[data-lang="{lang}"]'); pg.wait_for_timeout(1200)
        for sport, views in [("football", ["results","schedule","round","cal","table","players"]),
                             ("ufc", ["results","schedule"]),
                             ("f1", ["results","schedule"])]:
            pg.click(f'[data-sport="{sport}"]'); pg.wait_for_timeout(1500)
            for v in views:
                pg.click(f'[data-view="{v}"]')
                sel = {"round": ".roundnav-title", "cal": ".cal-grid",
                       "table": "table", "players": ".ptabs"}.get(v)
                check(f"{sport}/{v}", sel)

    print("\n=== интерактив ===")
    pg.click('[data-sport="football"]'); pg.wait_for_timeout(1200)
    pg.click('[data-view="round"]'); pg.wait_for_timeout(1800)
    before = pg.inner_text('.roundnav-title')
    pg.click('[data-round="next"]'); pg.wait_for_timeout(1600)
    after = pg.inner_text('.roundnav-title')
    print(f"  {'✓' if before != after else '✗'} стрелка тура: {before} -> {after}")
    if before == after: fails.append("стрелка тура не работает")

    pg.click('[data-view="cal"]'); pg.wait_for_timeout(2000)
    m1 = pg.inner_text('.cal-title')
    pg.click('[data-month="next"]'); pg.wait_for_timeout(1500)
    m2 = pg.inner_text('.cal-title')
    print(f"  {'✓' if m1 != m2 else '✗'} листание месяца: {m1} -> {m2}")
    if m1 == m2: fails.append("листание месяца не работает")

    pg.click('[data-month="prev"]'); pg.wait_for_timeout(1500)
    dots = pg.eval_on_selector_all('.cal-cell.has-games','e=>e.map(x=>x.textContent.trim())')
    print(f"  {'✓' if dots else '✗'} дни с матчами: {dots}")
    if not dots: fails.append("нет точек в календаре")
    else:
        pg.click('.cal-cell.has-games'); pg.wait_for_timeout(1800)
        n = pg.eval_on_selector_all('.match','e=>e.length')
        print(f"  {'✓' if n else '✗'} клик по числу: {n} матчей")
        if not n: fails.append("клик по числу ничего не даёт")

    pg.click('[data-view="players"]'); pg.wait_for_timeout(1600)
    pg.click('[data-pk="assists"]'); pg.wait_for_timeout(1500)
    print(f"  {'✓' if pg.query_selector('.ptable') else '✗'} переключение на ассистентов")
    pg.screenshot(path="h_final.png")
    b.close()
srv.shutdown()

print("\n" + ("ВСЁ ПРОШЛО" if not fails else f"ПРОВАЛОВ: {len(fails)}"))
for f in fails: print("  -", f)
sys.exit(1 if fails else 0)
