"""python3 tests/test_reliability.py (Python Playwright, Chromium)."""
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
    page.add_init_script("window.realOpen=indexedDB.open.bind(indexedDB);if(!sessionStorage.getItem('allow-test-storage'))indexedDB.open=()=>{throw new Error('denied')}")
    page.goto(f'http://127.0.0.1:{server.server_port}',wait_until='domcontentloaded')
    page.locator('#retryStorage').wait_for()
    assert page.locator('#addKit').is_disabled()
    assert page.evaluate('db === null')
    page.evaluate("()=>{indexedDB.open=realOpen;sessionStorage.setItem('allow-test-storage','1')}")
    page.locator('#retryStorage').click()
    page.wait_for_function('db !== null')
    page.evaluate("db.collection('kits').add({name:'元の名前',status:'stock',grade:'HG'})")
    page.evaluate('''async()=>{
      const put=IDBObjectStore.prototype.put;
      IDBObjectStore.prototype.put=function(...args){const r=put.apply(this,args);this.transaction.abort();return r};
      let failed=false;try{await db.collection('kits').doc(kits[0].id).update({name:'保存失敗した名前'})}catch(e){failed=true}finally{IDBObjectStore.prototype.put=put}
      if(!failed||kits[0].name!=='元の名前')throw Error('failed update mutated memory');
      await Promise.all([db.collection('kits').doc(kits[0].id).update({model:'RX-TEST'}),db.collection('kits').doc(kits[0].id).update({jan:'4901234567894'})]);
      if(kits[0].model!=='RX-TEST'||kits[0].jan!=='4901234567894')throw Error('concurrent updates lost fields');
    }''')
    page.reload(wait_until='domcontentloaded')
    page.wait_for_function('db !== null && kits.length === 1')
    assert page.evaluate("kits[0].name==='元の名前' && kits[0].model==='RX-TEST'")
    page.locator('#list .kit').click()
    page.evaluate("REC.text='二重記録防止';REC.type='work';REC.min='-1'")
    page.evaluate('saveRecord()')
    assert page.evaluate('logs.length === 0')
    page.evaluate("REC.min='10'")
    page.evaluate('Promise.all([saveRecord(),saveRecord()])')
    assert page.evaluate('logs.length === 1')
    page.evaluate('''async()=>{
      REC={...newRec(),text:'記録だけは保存',next:'次の作業'};
      const original=db;
      db={collection:name=>{const c=original.collection(name);if(name!=='kits')return c;return {...c,doc:id=>({...c.doc(id),update:async()=>{throw Error('update failed')}})}}};
      try{await saveRecord()}finally{db=original}
    }''')
    assert page.evaluate("logs.length===2 && REC.text === ''")
    assert '記録は保存しました' in page.locator('#toast').inner_text()
    page.evaluate('''async()=>{
      const c=document.createElement('canvas');c.width=c.height=1;const b=await new Promise(r=>c.toBlob(r));
      REC={...newRec(),text:'失敗でも残る入力',files:[new File([b],'test.png',{type:'image/png'})]};
      const original=db,oldAssets=assets;window.uploaded=[];window.removed=[];
      assets={...oldAssets,async upload(...args){const r=await oldAssets.upload(...args);uploaded.push(r.id);return r},async delete(id){removed.push(id);await oldAssets.delete(id)}};
      db={collection:name=>{const col=original.collection(name);return name==='logs'?{...col,add:async()=>{throw Error('quota')}}:col}};
      try{await saveRecord()}finally{db=original;assets=oldAssets}
      if(uploaded.length!==1||removed[0]!==uploaded[0]||await assets.read(uploaded[0]))throw Error('orphan photo');
    }''')
    assert page.evaluate("REC.text==='失敗でも残る入力' && logs.length===2")
    browser.close()
server.shutdown()
print('PASS: storage unavailable/retry, aborted transaction, concurrent field updates, negative minutes, duplicate save guard, partial success, photo cleanup/input preservation')
