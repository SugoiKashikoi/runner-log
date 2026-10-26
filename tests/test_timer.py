"""python3 tests/test_timer.py (Python Playwright, Chromium)."""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
from playwright.sync_api import sync_playwright
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(Path(__file__).resolve().parents[1])))
Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':390,'height':844})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{server.server_port}',wait_until='domcontentloaded')
    page.wait_for_function('db !== null')
    page.clock.install()
    page.locator('#addKit').click()
    page.locator('#timerToggle').click()
    assert page.evaluate('kits.length === 0 && readWorkTimer().active === null')
    page.locator('#f_name').fill('タイマー検証')
    page.locator('#save').click()
    page.wait_for_function('kits.length === 1')
    page.locator('#timerToggle').click()
    assert page.evaluate('readWorkTimer().active.kitId === kits[0].id')
    page.locator('#back').click()
    page.clock.fast_forward(125000)
    page.reload(wait_until='domcontentloaded')
    page.wait_for_function('db !== null && kits.length === 1')
    page.locator('#list .kit').click()
    assert '計測中' in page.locator('#timerStatus').inner_text()
    page.locator('#timerToggle').click()
    assert page.locator('#r_min').input_value() == '3'
    assert page.evaluate('readWorkTimer().active === null')
    page.locator('#r_min').fill('7')
    page.reload(wait_until='domcontentloaded')
    page.wait_for_function('db !== null && kits.length === 1')
    page.locator('#list .kit').click()
    assert page.locator('#r_min').input_value() == '7'
    page.locator('#r_text').fill('右腕の作業')
    page.locator('#addRec').click()
    page.wait_for_function("logs.length === 1 && !Object.hasOwn(readWorkTimer().pending,kits[0].id)")
    assert page.evaluate("logs[0].type === 'work' && logs[0].minutes === 7 && !Object.hasOwn(readWorkTimer().pending,kits[0].id)")
    page.locator('#timerToggle').click()
    page.clock.fast_forward(20000)
    page.locator('#timerToggle').click()
    assert page.locator('#r_min').input_value() == '1'
    page.locator('#r_min').fill('')
    page.evaluate("()=>{window.realSet=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k===TIMER_KEY)throw new Error('quota');return realSet.call(this,k,v)}}")
    page.locator('#timerToggle').click()
    assert page.evaluate('readWorkTimer().active === null')
    assert '保存できません' in page.locator('#toast').inner_text()
    assert not errors,errors
    browser.close()
server.shutdown()
print('PASS: no ghost kit, close/reload elapsed time, rounded minutes, stopped/manual minutes persist, log saves minutes, storage failure')
