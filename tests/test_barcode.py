"""python3 tests/test_barcode.py (requires Playwright and Chromium). No real camera."""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
from playwright.sync_api import sync_playwright
server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(Path(__file__).resolve().parents[1])))
Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}'
MOCK = '''
window.calls={media:0,stops:0,resets:0,detects:0,max:0,inflight:0};
window.cameraReady=null;window.readResult=null;window.detectReady=null;
const track={stop(){calls.stops++}};
const fakeStream={getTracks(){return [track]}};
Object.defineProperty(HTMLMediaElement.prototype,'srcObject',{get(){return this._s},set(v){this._s=v}});
HTMLMediaElement.prototype.play=async function(){};
Object.defineProperty(navigator.mediaDevices,'getUserMedia',{value:async()=>{calls.media++;if(window.delayCamera)await new Promise(r=>cameraReady=r);return fakeStream}});
window.BarcodeDetector=class {
 static async getSupportedFormats(){return window.fallback?[]:['ean_13']}
 async detect(){calls.detects++;calls.inflight++;calls.max=Math.max(calls.max,calls.inflight);try{return await new Promise(r=>detectReady=r)}finally{calls.inflight--}}
};
window.ZXing={BrowserMultiFormatReader:class{
 reset(){calls.resets++}
 async decodeFromStream(s,v,cb){if(window.failZX)throw new Error('startup');window.readResult=cb}
}};
'''
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
    def fresh(extra=''):
        context = browser.new_context()
        page = context.new_page()
        page.add_init_script(MOCK + extra)
        page.goto(url, wait_until='domcontentloaded')
        page.wait_for_function('db !== null')
        page.locator('#addKit').click()
        page.locator('summary').filter(has_text='型式・JAN・グレード・スケール').click()
        return page
    page = fresh('window.delayCamera=true;')
    page.locator('#scanKit').click()
    page.wait_for_function('cameraReady !== null')
    page.evaluate('scanJan()')
    assert page.evaluate('calls.media') == 1
    page.locator('#scanCancel').click()
    page.evaluate('cameraReady()')
    page.wait_for_function('calls.stops > 0')
    assert page.locator('#scanCancel').count() == 0
    assert page.evaluate('calls.detects') == 0
    page.context.close()
    page = fresh()
    page.locator('#scanKit').click()
    page.wait_for_function('detectReady !== null')
    page.wait_for_timeout(650)
    assert page.evaluate('calls.max === 1 && calls.detects === 1')
    page.evaluate("detectReady([{rawValue:'4901234567894'},{rawValue:'4901234567894'}])")
    page.locator('#f_jan').wait_for(state='attached')
    assert page.locator('#f_jan').input_value() == '4901234567894'
    assert page.evaluate('kits.length') == 0  # scan creates a draft, not a record
    assert page.locator('#scanCancel').count() == 0
    assert page.evaluate('calls.stops') > 0
    page.context.close()
    page = fresh('window.fallback=true;')
    page.locator('#scanKit').click()
    page.wait_for_function('readResult !== null')
    page.evaluate("readResult({getText:()=> '4901234567894'});readResult({getText:()=> '4901234567894'})")
    page.locator('#f_jan').wait_for(state='attached')
    assert page.evaluate('calls.resets') > 0
    assert page.evaluate('kits.length') == 0
    page.context.close()
    page = fresh('window.fallback=true;window.failZX=true;')
    page.locator('#scanKit').click()
    page.wait_for_function('calls.stops > 0 && activeScan === null')
    assert page.locator('#scanCancel').count() == 0
    assert '使えませんでした' in page.locator('#toast').inner_text()
    page.context.close()
    page = fresh()
    page.locator('#scanKit').click()
    page.wait_for_function('detectReady !== null')
    page.evaluate("window.dispatchEvent(new Event('pagehide'))")
    page.evaluate("detectReady([{rawValue:'4901234567894'}])")
    assert page.evaluate("calls.stops > 0 && activeScan === null && openId === '__new'")
    page.context.close()
    browser.close()
server.shutdown()
print('PASS: cancel during permission, single session/detection, native and ZXing duplicate callbacks, ZXing failure, pagehide and late result')
