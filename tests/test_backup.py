"""python3 tests/test_backup.py (requires Python Playwright and Chromium)."""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
from playwright.sync_api import sync_playwright
server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(Path(__file__).resolve().parents[1])))
Thread(target=server.serve_forever, daemon=True).start()
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
    page = browser.new_page()
    errors=[]
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{server.server_port}', wait_until='domcontentloaded')
    page.wait_for_function('db !== null')
    page.evaluate('''async()=>{
      const c=document.createElement('canvas');c.width=c.height=1;
      const blob=await new Promise(r=>c.toBlob(r));const photo=await assets.upload(blob);
      const k={name:'検証用',model:'RX-TEST',jan:'4901234567894',grade:'HG',status:'stock',price:1000,shop:'ショップ',bought:'2026-01-01',started:'',finished:'',memo:'メモ',recipe:'塗装',review:'感想',photos:[photo.id],folder:'https://example.com/photos',next:'右腕',theme:'つや消し',want:'塗装',notWant:'改造',refs:'書籍 p.1',futureField:{keep:true}};
      const r=await db.collection('kits').add(k);
      for(const type of ['memo','work','try','decide','done'])await db.collection('logs').add({kitId:r.id,type,date:'2026-01-01',memo:type,step:'塗装',minutes:12,ref:'参考',idea:'cand',created:123,photos:[photo.id]});
      window.original=JSON.parse(await exportBackup(true));
      window.noPhotos=JSON.parse(await exportBackup(false));
    }''')
    assert page.evaluate('noPhotos.kits[0].photos === undefined && noPhotos.logs.every(l=>l.photos === undefined)')
    page.evaluate('importBackup(parseBackup(JSON.stringify(original)), "add")')
    assert page.evaluate('kits.length === 2 && logs.length === 10')
    assert page.evaluate('logs.filter(l=>l.kitId===kits[1].id).length === 5')
    page.evaluate('importBackup(parseBackup(JSON.stringify(original)), "replace")')
    assert page.evaluate('kits.length === 1 && logs.length === 5')
    assert page.evaluate('''()=>{
      const {id,photos,...actual}=kits[0],{id:_i,photos:_p,...expected}=original.kits[0];
      return JSON.stringify(actual)===JSON.stringify(expected)&&photos.length===1&&logs.every(l=>l.kitId===id&&l.photos[0]===photos[0]);
    }''')
    assert page.evaluate('''async()=>{
      const blob=await tx('blobs','readonly',s=>s.get(kits[0].photos[0]));return blob instanceof Blob && blob.size>0;
    }''')
    page.locator('#openSettings').click()
    bad = page.evaluate("JSON.stringify({...original, logs:'invalid'})")
    page.locator('#bkText').fill(bad)
    page.locator('#bkMode').select_option('replace')
    page.locator('#bkRestore').click()
    assert page.evaluate('kits.length === 1 && logs.length === 5')
    assert '形式' in page.locator('#toast').inner_text()
    page.locator('#bkText').fill(page.evaluate('JSON.stringify(original)'))
    page.locator('#bkRestore').click()
    page.locator('#bkMode').select_option('add')
    page.locator('#bkRestore').click()  # mode change requires confirmation again
    assert page.evaluate('kits.length') == 1
    page.evaluate('''async()=>{
      const originalDB=db;let adds=0;
      db={collection:n=>{const c=originalDB.collection(n);return {...c,add:async row=>{if(++adds===2)throw new Error('quota');return c.add(row)}}}};
      try{await importBackup(parseBackup(JSON.stringify(original)),'replace');throw new Error('expected failure')}
      catch(e){if(e.message!=='quota')throw e}finally{db=originalDB}
    }''')
    assert page.evaluate('kits.length === 1 && logs.length === 5')
    page.evaluate("importBackup(parseBackup(JSON.stringify({...noPhotos,v:1,logs:noPhotos.logs.map(({type,...l})=>l)})),'replace')")
    assert page.evaluate('kits.length === 1 && logs.length === 5 && logs.every(l=>!l.type)')
    assert not errors, errors
    browser.close()
server.shutdown()
print('PASS: all kit/log fields and future fields, photos, add/replace links, invalid input protection, confirmation reset, quota rollback, v1 logs')
