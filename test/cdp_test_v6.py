import json,subprocess,time,urllib.request,websocket,sys,base64,os
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
BASE=sys.argv[1];OUT=sys.argv[2] if len(sys.argv)>2 else '.'
def chrome(port,tz=None,ua=None):
    prof='/tmp/tjgprof6_%d'%port;subprocess.run(['rm','-rf',prof]);env=dict(os.environ)
    if tz:env['TZ']=tz
    p=subprocess.Popen(['google-chrome','--headless=new','--no-sandbox','--disable-gpu','--autoplay-policy=no-user-gesture-required','--remote-debugging-port=%d'%port,'--remote-allow-origins=*','--user-data-dir='+prof,'--window-size=1920,1080','about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=env)
    time.sleep(2);t=[x for x in json.load(urllib.request.urlopen('http://127.0.0.1:%d/json'%port)) if x['type']=='page'][0]
    ws=websocket.create_connection(t['webSocketDebuggerUrl']);n=[0];logs=[]
    def cmd(m,**pr):
        n[0]+=1;ws.send(json.dumps({'id':n[0],'method':m,'params':pr}))
        while True:
            r=json.loads(ws.recv())
            if r.get('method')=='Runtime.exceptionThrown':logs.append(r['params']['exceptionDetails'].get('exception',{}).get('description','')[:200])
            if r.get('method')=='Log.entryAdded' and 'Content Security Policy' in r['params']['entry'].get('text',''):logs.append('CSP:'+r['params']['entry']['text'][:160])
            if r.get('id')==n[0]:return r.get('result')
    def ev(e):
        r=cmd('Runtime.evaluate',expression=e,returnByValue=True,awaitPromise=True);return r['result'].get('value',r.get('exceptionDetails',{}).get('text'))
    def shot(f):open(f,'wb').write(base64.b64decode(cmd('Page.captureScreenshot')['data']))
    cmd('Page.enable');cmd('Runtime.enable');cmd('Network.enable');cmd('Log.enable')
    return p,cmd,ev,shot,logs
res={}
# ---- A: templates, screenshots, security, cache scoping ----
p,cmd,ev,shot,logs=chrome(9341)
cmd('Page.navigate',url=BASE+'/robots.txt');time.sleep(1)
ev("Promise.all([caches.open('other-app').then(c=>c.put('/x',new Response('keep'))),caches.open('tjg-signage-v5').then(c=>c.put('/y',new Response('old')))])")
cmd('Page.navigate',url=BASE+'/index.html?screen=showcase&v=6');time.sleep(6)
res['A_caches_after_activate']=ev("caches.keys().then(k=>k.sort().join(','))")  # expect other-app kept, tjg-signage-v5 gone, tjg-signage-v6 present
res['A_no_iframes']=ev("document.getElementsByTagName('iframe').length")
res['A_csp']=ev("document.querySelector('meta[http-equiv]').content.match(/frame-src[^;]*/)[0]+' | '+document.querySelector('meta[http-equiv]').content.match(/connect-src[^;]*/)[0]")
res['A_types']=ev("Object.keys(TYPES).join(',')")
res['A_web_item_skipped']=ev("TYPES.web===undefined&&pick.call(null).every(function(x){return x.type!=='web'})")
res['A_safeMedia']=ev("JSON.stringify(['media/a.png','media\\\\..\\\\x.png','media\\\\a.png','media/../a.png','/media/a.png','//evil.com/a.png','javascript:alert(1)','media//a.png','https://evil.com/a.png','media/sub/b.mp4'].map(safeMedia))")
res['A_safeUrl']=ev("JSON.stringify(['https://junglegymfun.com/','javascript:alert(1)','http://x.com','https://x.com/\"><script>'].map(safeUrl))")
res['A_esc']=ev("esc('<img src=x onerror=alert(1)> [[ph]]')")
res['A_src_param']=None
names=['title','promo-ffv','promo-standard','promo-premium','schedule-classes','schedule-hours','announcement','list','image','video','clock']
ev("clearTimeout(timer)")
for i,nm in enumerate(names):
    ev("clearTimeout(timer);idx=%d;next();clearTimeout(timer)"%i);time.sleep(1.6 if nm!='video' else 2.5)
    res['A_shot_'+nm]=ev("document.querySelector('.layer.on').getAttribute('data-type')+' :: '+document.querySelector('.layer.on').innerText.replace(/\\n/g,' / ').slice(0,90)")
    shot(OUT+'/screenshot-v6-%02d-%s.png'%(i+1,nm))
res['A_qr_svg_present']=ev("idx=1;next();clearTimeout(timer);!!document.querySelector('.layer.on .qr svg path')")
cmd('Page.navigate',url=BASE+'/index.html?screen=lobby&src=https://evil.com/p.json');time.sleep(3);res['A_evil_src_ignored']=ev("SRC")
cmd('Page.navigate',url=BASE+'/index.html?screen=lobby&src=//evil.com/p.json');time.sleep(2);res['A_evil_src2_ignored']=ev("SRC")
res['A_lobby_unchanged_types']=ev("data.playlists.lobby.map(x=>x.type+':'+x.title).join(' | ')")
res['A_lobby_905pm']=ev("data.playlists.lobby.filter(x=>active(x,new Date('2026-10-20T04:05:00Z'))).length")
res['A_exceptions']=list(logs);p.kill()
# ---- B: fixtures online/offline + Range ----
p,cmd,ev,shot,logs=chrome(9342)
cmd('Page.navigate',url=BASE+'/index.html?screen=fixtures&v=6');time.sleep(4)
cmd('Page.navigate',url=BASE+'/index.html?screen=fixtures&v=6');time.sleep(3)  # now SW-controlled
res['B_sw_controlled']=ev("!!navigator.serviceWorker.controller")
def play_check(tag):
    ev("clearTimeout(timer);idx=0;next();clearTimeout(timer)");time.sleep(1.5)
    res[tag+'_image']=ev("var i=document.querySelector('.layer.on img');i?i.naturalWidth+'x'+i.naturalHeight:'none'")
    ev("clearTimeout(timer);idx=1;next()");time.sleep(3)
    res[tag+'_video']=ev("var v=document.querySelector('.layer.on video');v?JSON.stringify({t:Math.round(v.currentTime*10)/10,ready:v.readyState,err:v.error&&v.error.code,dur:v.duration,src:v.currentSrc.replace(location.origin,'')}):'none'")
    res[tag+'_video_served_by_sw']=ev("performance.getEntriesByType('resource').filter(e=>/fixture.mp4/.test(e.name)).map(e=>e.workerStart>0).join(',')")
    time.sleep(3.5);res[tag+'_video_ended_advanced']=ev("document.querySelector('.layer.on').getAttribute('data-type')")
def range_check(tag):
    js="""(function(){var u='media/fixture.mp4?mv=6',H=['bytes=0-9','bytes=-10','bytes=39000-','bytes=abc','bytes=0-1,5-6','bytes=99999999-','bytes=-0','bytes=10-5'];
    return Promise.all(H.map(function(h){return fetch(u,{headers:{Range:h}}).then(function(r){return r.arrayBuffer().then(function(b){return h+' -> '+r.status+' '+(r.headers.get('content-range')||'-')+' len='+b.byteLength})})}))})().then(a=>a)"""
    res[tag+'_range']=ev(js)
time.sleep(2);res['B_cache_keys']=ev("caches.open('tjg-signage-v6').then(c=>c.keys()).then(k=>k.map(x=>x.url.replace(location.origin,'')))")
play_check('B_online');range_check('B_online')
cmd('Network.setCacheDisabled',cacheDisabled=True)  # no HTTP memory/disk cache: offline media must come from the SW cache
cmd('Network.emulateNetworkConditions',offline=True,latency=0,downloadThroughput=-1,uploadThroughput=-1)
cmd('Page.navigate',url=BASE+'/index.html?screen=fixtures&v=6');time.sleep(4)
res['B_offline_loaded']=ev("!!data&&document.title")
play_check('B_offline');range_check('B_offline')
shot(OUT+'/test/shot-v6-offline-fixtures.png')
res['B_exceptions']=list(logs);p.kill()
# ---- C: Pacific time without formatToParts, TV zone set to Tokyo and to UTC ----
inst=['2026-10-20T04:05:00Z','2026-03-08T09:59:00Z','2026-03-08T10:00:00Z','2026-11-01T08:59:00Z','2026-11-01T09:00:00Z','2026-12-31T23:30:00Z','2027-03-14T10:00:00Z','2026-07-04T19:00:00Z','2026-10-19T07:05:00Z']
exp=[datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(ZoneInfo('America/Los_Angeles')).strftime('%Y-%m-%d %H:%M %a') for s in inst]
for tz,port in [('Asia/Tokyo',9343),('UTC',9344)]:
    for mode,patch in [('noFTP',"try{delete Intl.DateTimeFormat.prototype.formatToParts}catch(e){}"),('throws',"Intl.DateTimeFormat.prototype.formatToParts=function(){throw Error('x')}"),('noIntl',"try{window.Intl=undefined}catch(e){}")]:
        p,cmd,ev,shot,logs=chrome(port,tz=tz)
        cmd('Page.addScriptToEvaluateOnNewDocument',source=patch)
        cmd('Page.navigate',url=BASE+'/index.html?screen=lobby&debug=1');time.sleep(3)
        got=ev("JSON.stringify(%s.map(function(s){var t=la(new Date(s));return t.ymd+' '+pad(t.h)+':'+pad(t.mi)+' '+['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][t.dow]+' '+t.src}))"%json.dumps(inst))
        try:got=json.loads(got)
        except Exception:res['C_%s_%s_raw'%(tz,mode)]=str(got)+' exc='+str(logs);p.kill();continue
        ok=all(g.startswith(e) and g.endswith('manual') for g,e in zip(got,exp))
        res['C_%s_%s'%(tz,mode)]=('PASS' if ok else 'FAIL')+' tvLocal='+ev("new Date('2026-10-20T04:05:00Z').getHours()+'h'")+' lobby@21:05='+str(ev("data.playlists.lobby.filter(x=>active(x,new Date('2026-10-20T04:05:00Z'))).length"))
        if not ok:res['C_%s_%s_detail'%(tz,mode)]=list(zip(got,exp))
        p.kill()
print(json.dumps(res,indent=1));json.dump(res,open(OUT+'/test/v6-results.json','w'),indent=1)
