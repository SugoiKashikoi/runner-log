"""python3 tests/test_disclosures.py (Python Playwright, Chromium)."""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
from playwright.sync_api import sync_playwright
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(Path(__file__).resolve().parents[1])))
Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
    page.goto(f'http://127.0.0.1:{server.server_port}',wait_until='domcontentloaded')
    page.wait_for_function('db !== null')
    page.evaluate("db.collection('kits').add({name:'検証用',status:'stock',grade:'RG',model:'TEST',jan:'4901234567894',want:'塗装',recipe:'レシピ',review:'感想',refs:'資料'})")
    page.locator('#list .kit').click()
    assert page.locator('#f_name').is_visible()
    assert page.locator('#f_status').is_visible()
    assert page.locator('#f_next').is_visible()
    assert page.locator('#r_text').is_visible()
    for field in ['f_model','f_jan','f_gradeSel','f_want','f_recipe','f_review']:
        assert not page.locator('#'+field).is_visible(),field
    summary=page.locator('summary').filter(has_text='型式・JAN・グレード・スケール')
    assert summary.bounding_box()['height']>=44
    summary.click()
    page.locator('#f_model').fill('CHANGED')
    summary.click()
    page.locator('#save').click()
    page.wait_for_function("kits[0].model === 'CHANGED'")
    assert page.evaluate("kits[0].recipe==='レシピ' && kits[0].review==='感想' && kits[0].want==='塗装' && kits[0].jan==='4901234567894'")
    page.reload(wait_until='domcontentloaded')
    page.wait_for_function('db !== null && kits.length === 1')
    page.locator('#list .kit').click()
    assert not page.locator('#f_model').is_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    browser.close()
server.shutdown()
print('PASS: mobile viewport, closed populated fields, 44px disclosure, save preserves closed fields, closed after reload, no horizontal overflow')
