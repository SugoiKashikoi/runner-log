"""python3 tests/test_storage.py (Python Playwright, Chromium)."""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
from playwright.sync_api import sync_playwright
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(Path(__file__).resolve().parents[1])))
Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=browser.new_page()
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{server.server_port}',wait_until='domcontentloaded')
    page.wait_for_function('db !== null')
    page.locator('#addKit').click()
    page.locator('#f_name').fill('保存アダプター確認')
    page.locator('summary').filter(has_text='型式・JAN・グレード').click()
    page.locator('#f_jan').fill('4901234567894')
    page.locator('#save').click()
    page.wait_for_function('kits.length === 1')
    page.evaluate('''async()=>{
      const c=document.createElement('canvas');c.width=c.height=1;
      const b=await new Promise(r=>c.toBlob(r));const r=await assets.upload(b,{original:true});
      await db.collection('kits').doc(kits[0].id).update({photos:[r.id]});
      if(!(await assets.read(r.id)).size||!assets.url(r.id))throw Error('photo API');
    }''')
    page.reload(wait_until='domcontentloaded')
    page.wait_for_function('db !== null && kits.length === 1')
    assert page.evaluate("kits[0].jan === '4901234567894' && !!imgUrl(kits[0].photos[0])")
    # A completely different in-memory adapter: UI must not depend on IndexedDB.
    page.evaluate('''async()=>{
      const cols={};
      const collection=name=>cols[name]||(cols[name]=(()=>{
        let rows=[],listeners=[];const emit=()=>listeners.forEach(f=>f({docs:rows.map(r=>({id:r.id,data:()=>({...r})}))}));
        return {onSnapshot(f){listeners.push(f);emit()},async add(row){const r={...row,id:crypto.randomUUID()};rows.push(r);emit();return {id:r.id}},doc(id){return {async update(value){Object.assign(rows.find(r=>r.id===id),value);emit()},async delete(){rows=rows.filter(r=>r.id!==id);emit()}}}};
      })());
      const blobs=new Map();
      const images={url:id=>blobs.has(id)?'data:image/png;base64,':'' ,read:async id=>blobs.get(id),async upload(b){const id=crypto.randomUUID();blobs.set(id,b);return {id}},async delete(id){blobs.delete(id)},async clear(){blobs.clear()}};
      closeNote();await connectStorage({db:{collection},assets:images});
      Object.defineProperty(window,'indexedDB',{get(){throw Error('UI accessed IndexedDB')}});
      window.importPhotoCount=()=>blobs.size;
    }''')
    page.locator('#addKit').click()
    page.locator('#f_name').fill('差し替え先')
    page.locator('#save').click()
    page.wait_for_function('kits.length === 1')
    page.locator('#r_text').fill('差し替えた保存先の記録')
    page.locator('#addRec').click()
    page.wait_for_function('logs.length === 1')
    page.locator('#back').click()
    page.locator('#openSettings').click()
    page.locator('#bkCopy').click()
    page.wait_for_function("document.querySelector('#bkText').value.includes('差し替え先')")
    page.locator('#bkRestore').click()
    page.locator('#bkRestore').click()
    page.wait_for_function('kits.length === 2 && logs.length === 2')
    assert not errors,errors
    browser.close()
server.shutdown()
print('PASS: IndexedDB kit/photo reload, db/assets API, alternate adapter UI save/log/export/import without IndexedDB')
