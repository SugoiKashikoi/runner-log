"""python3 tests/test_drafts.py (Python Playwright, Chromium)."""
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

    page.locator("#addKit").click()
    page.locator("#f_name").fill("新規下書き")
    page.locator("#f_next").fill("右腕から")
    page.locator("#r_text").fill("記録の下書き")
    page.locator("#r_type").select_option("work")
    page.locator("#r_min").fill("25")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_function("db !== null")
    assert page.evaluate("kits.length === 0")

    page.locator("#addKit").click()
    assert page.locator("#f_name").input_value() == "新規下書き"
    assert page.locator("#f_next").input_value() == "右腕から"
    assert page.locator("#r_text").input_value() == "記録の下書き"
    assert page.locator("#r_min").input_value() == "25"
    page.locator("#save").click()
    page.wait_for_function("kits.length === 1")
    page.locator("#back").click()
    page.reload(wait_until="domcontentloaded")
    page.wait_for_function("db !== null && kits.length === 1")
    page.locator("#list .kit").click()
    assert page.locator("#r_text").input_value() == "記録の下書き"
    assert page.locator("#r_min").input_value() == "25"

    page.locator("#r_text").fill("保存失敗でも残る")
    page.evaluate(
        """()=>{
        window.originalDB=db;
        db={collection:name=>{
          const collection=originalDB.collection(name);
          return name==='logs'?{...collection,add:async()=>{throw Error('quota')}}:collection;
        }};
      }"""
    )
    page.locator("#addRec").click()
    page.wait_for_function("recordSaving === false")
    page.evaluate("db=originalDB")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_function("db !== null && kits.length === 1")
    page.locator("#list .kit").click()
    assert page.locator("#r_text").input_value() == "保存失敗でも残る"
    page.locator("#addRec").click()
    page.wait_for_function("logs.length === 1")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_function("db !== null && kits.length === 1")
    page.locator("#list .kit").click()
    assert page.locator("#r_text").input_value() == ""
    assert page.evaluate("!localStorage.getItem(RECORD_DRAFT_KEY(kits[0].id))")
    browser.close()

server.shutdown()
print("PASS: new-kit draft, record draft migration/reload, failed-save retention, successful-save cleanup")
