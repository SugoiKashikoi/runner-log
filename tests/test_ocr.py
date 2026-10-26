"""python3 tests/test_ocr.py (Python Playwright, Chromium; real offline OCR)."""
from pathlib import Path
from time import monotonic
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(Path(__file__).resolve().parents[1])))
Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':390,'height':844})
    # Deliberately block all remote resources, including existing Google Fonts.
    context.route('**/*',lambda r:r.continue_() if urlparse(r.request.url).hostname in ('127.0.0.1',None) or r.request.url.startswith(('data:','blob:')) else r.abort())
    page=context.new_page()
    requests=[]
    context.on('request',lambda r:requests.append(r.url))
    page.goto(f'http://127.0.0.1:{server.server_port}',wait_until='domcontentloaded')
    page.wait_for_function('db !== null')
    candidates=page.evaluate("boxCandidates('HG 1/144\\nRX-78-2\\nガンダム\\nBANDAI')")
    assert candidates['model']=='RX-78-2' and candidates['grade']=='HG' and candidates['name']=='ガンダム',candidates
    page.locator('#addKit').click()
    page.locator('#f_name').fill('変更しない名前')
    requests.clear()
    page.locator('#boxOCR').click()
    # Canvas-generated synthetic box label; no personal photo or test fixture download.
    image=page.evaluate("""()=>{const c=document.createElement('canvas');c.width=1200;c.height=500;const x=c.getContext('2d');x.fillStyle='white';x.fillRect(0,0,c.width,c.height);x.fillStyle='black';x.font='bold 90px Arial';x.fillText('HG',60,130);x.fillText('RX-78-2',60,260);x.fillText('GUNDAM',60,390);return c.toDataURL('image/png').split(',')[1]}""")
    import base64
    page.locator('#ocrFile').set_input_files({'name':'synthetic.png','mimeType':'image/png','buffer':base64.b64decode(image)})
    page.locator('#ocrResult').wait_for(state='visible',timeout=90000)
    assert page.locator('#ocr_model').input_value()=='RX-78-2',page.locator('#ocrRaw').input_value()
    assert page.locator('#ocr_grade').input_value()=='HG'
    assert not page.locator('#ocrUse_name').is_checked()
    page.locator('#ocrUse_model').check()
    page.locator('#ocr_model').fill('RX-78-2-EDIT')
    page.locator('#ocrApply').click()
    assert page.locator('#f_name').input_value()=='変更しない名前'
    assert page.locator('#f_model').input_value()=='RX-78-2-EDIT'
    assert page.evaluate('kits.length === 0')
    deadline=monotonic()+5
    while page.workers and monotonic()<deadline:page.wait_for_timeout(50)
    assert len(page.workers)==0
    page.locator('#boxOCR').click()
    page.locator('#ocrFile').set_input_files({'name':'bad.png','mimeType':'image/png','buffer':b'not an image'})
    page.wait_for_function("document.querySelector('#ocrProgress').textContent.includes('読み取れませんでした')")
    page.locator('#ocrClose').click()
    assert page.locator('#f_model').input_value()=='RX-78-2-EDIT'
    page.locator('#boxOCR').click()
    page.locator('#ocrFile').set_input_files({'name':'synthetic.png','mimeType':'image/png','buffer':base64.b64decode(image)})
    page.locator('#ocrClose').click()
    page.wait_for_function('ocrSession === null')
    deadline=monotonic()+5
    while page.workers and monotonic()<deadline:page.wait_for_timeout(50)
    assert len(page.workers)==0
    assert page.locator('#f_name').input_value()=='変更しない名前'
    assert not [u for u in requests if urlparse(u).hostname not in ('127.0.0.1',None) and not u.startswith(('data:','blob:'))], requests
    browser.close()
server.shutdown()
print('PASS: real Japanese+English engine offline, synthetic label recognition, editable/selective candidates, invalid image and cancel preserve input, workers terminated')
