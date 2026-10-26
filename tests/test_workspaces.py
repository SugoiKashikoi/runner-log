"""python3 tests/test_workspaces.py (Python Playwright, Chromium)."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright


server = ThreadingHTTPServer(
    ("127.0.0.1", 0),
    partial(SimpleHTTPRequestHandler, directory=str(Path(__file__).resolve().parents[1])),
)
Thread(target=server.serve_forever, daemon=True).start()

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.goto(f"http://127.0.0.1:{server.server_port}", wait_until="domcontentloaded")
    page.wait_for_function("db !== null")
    page.evaluate(
        """async()=>{
        const stock=await db.collection('kits').add({name:'在庫キット',status:'stock',grade:'HG',jan:'11111111'});
        const active=await db.collection('kits').add({name:'進捗キット',status:'building',grade:'MG',next:'塗装'});
        const done=await db.collection('kits').add({name:'完成キット',status:'done',grade:'RG'});
        const idea=await db.collection('kits').add({name:'構想キット',status:'stock',grade:'HG',theme:'砂漠仕様'});
        await db.collection('logs').add({kitId:idea.id,type:'memo',date:'2026-10-26',memo:'候補',idea:'cand'});
        await db.collection('logs').add({kitId:active.id,type:'work',date:'2026-10-26',memo:'組立',minutes:30});
      }"""
    )
    page.wait_for_function("kits.length === 4 && logs.length === 2")
    assert page.locator("#list .kit").count() == 4
    assert "所持 4箱" in page.locator("#workspaceSummary").inner_text()

    page.locator('[data-workspace="progress"]').click()
    assert page.locator("#list .kit").count() == 2
    assert page.locator("#list").get_by_text("進捗キット").count() == 1
    assert page.locator("#list").get_by_text("在庫キット").count() == 0
    assert page.locator("#filters").is_hidden()
    assert page.locator("#stats").is_hidden()
    assert "次：塗装" in page.locator("#list").inner_text()

    page.locator('[data-workspace="ideas"]').click()
    assert page.locator("#list .kit").count() == 1
    assert "砂漠仕様" in page.locator("#list").inner_text()
    assert "アイデア候補 1件" in page.locator("#workspaceSummary").inner_text()
    page.locator("#q").fill("砂漠")
    assert page.locator("#list .kit").count() == 1

    page.reload(wait_until="domcontentloaded")
    page.wait_for_function("db !== null && kits.length === 4")
    assert page.locator('[data-workspace="ideas"]').get_attribute("aria-pressed") == "true"
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.locator("#list .kit").click()
    page.locator("#back").click()
    assert page.locator("#note").is_hidden()
    browser.close()

server.shutdown()
print("PASS: inventory/progress/ideas views, counts, contextual search, persisted workspace, mobile width, clean back")
