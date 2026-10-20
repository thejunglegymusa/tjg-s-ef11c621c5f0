import json,subprocess,time,urllib.request,websocket,sys,base64
BASE=sys.argv[1]  # e.g. http://localhost:8765
prof='/tmp/tjgprof'; subprocess.run(['rm','-rf',prof])
p=subprocess.Popen(['google-chrome','--headless=new','--no-sandbox','--disable-gpu','--remote-debugging-port=9334','--remote-allow-origins=*','--user-data-dir='+prof,'--window-size=1920,1080','about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
time.sleep(2)
t=[x for x in json.load(urllib.request.urlopen('http://127.0.0.1:9334/json')) if x['type']=='page'][0]
ws=websocket.create_connection(t['webSocketDebuggerUrl']);n=[0];logs=[]
def cmd(m,**pr):
    n[0]+=1;ws.send(json.dumps({'id':n[0],'method':m,'params':pr}))
    while True:
        r=json.loads(ws.recv())
        if r.get('method')=='Runtime.exceptionThrown':logs.append(r['params']['exceptionDetails'].get('exception',{}).get('description','')[:200])
        if r.get('id')==n[0]:return r.get('result')
def ev(e):return cmd('Runtime.evaluate',expression=e,returnByValue=True,awaitPromise=True)['result'].get('value')
def shot(f):open(f,'wb').write(base64.b64decode(cmd('Page.captureScreenshot')['data']))
cmd('Page.enable');cmd('Runtime.enable');cmd('Network.enable')
res={}
# 1) old-Tizen emulation: Tizen UA, remove URLSearchParams + CSS inset before page scripts run
cmd('Network.setUserAgentOverride',userAgent='Mozilla/5.0 (SMART-TV; LINUX; Tizen 5.0) AppleWebKit/537.36 (KHTML, like Gecko) Version/5.0 TV Safari/537.36')
cmd('Page.addScriptToEvaluateOnNewDocument',source='try{delete window.URLSearchParams;window.URLSearchParams=undefined}catch(e){}')
cmd('Page.navigate',url=BASE+'/index.html?screen=lobby&debug=1');time.sleep(5)
res['old_layer_rect']=ev("var r=document.querySelector('.layer.on').getBoundingClientRect();[r.width,r.height]")
res['old_text']=ev("document.querySelector('.layer.on').innerText")
res['sw_controlled']=ev("!!navigator.serviceWorker.controller")
time.sleep(3);res['cache_keys']=ev("caches.keys().then(k=>caches.open(k[0])).then(c=>c.keys()).then(k=>k.map(x=>x.url.replace(location.origin,'')))")
shot('test/shot-oldtizen-lobby.png')
# 2) offline: cut network, reload (navigate) and check it still plays
cmd('Network.emulateNetworkConditions',offline=True,latency=0,downloadThroughput=-1,uploadThroughput=-1)
cmd('Page.navigate',url=BASE+'/index.html?screen=lobby&debug=1');time.sleep(5)
res['offline_text']=ev("document.querySelector('.layer.on')&&document.querySelector('.layer.on').innerText")
res['offline_img_cached']=ev("caches.match('"+BASE+"/media/sample.svg').then(r=>!!r)")
shot('test/shot-offline-lobby.png')
# 3) safeReload offline must NOT navigate away
ev("window.__mark=1");ev("safeReload()");time.sleep(2);res['safeReload_offline_kept_page']=ev("window.__mark===1")
cmd('Network.emulateNetworkConditions',offline=False,latency=0,downloadThroughput=-1,uploadThroughput=-1)
# 4) date-only parse + off-hours watchdog tick

res['offhours_ticks']=ev("data={screens:{default:'x'},playlists:{x:[]}};var t=ticks;next();ticks>t")
res['exceptions']=logs
# v4 checks
cmd('Network.emulateNetworkConditions',offline=False,latency=0,downloadThroughput=-1,uploadThroughput=-1)
cmd('Page.navigate',url=BASE+'/index.html?screen=lobby&debug=1');time.sleep(4)
res['v4_la_clock']=ev("JSON.stringify(la(new Date('2026-10-20T04:05:00Z')))")  # expect 21:05 Mon
res['v4_sched_tonight_905pm']=ev("active({schedule:{days:'0123456',from:'20:30',to:'23:00',start:'2026-10-19',end:'2026-10-19'}},new Date('2026-10-20T04:05:00Z'))")
res['v4_sched_tomorrow']=ev("active({schedule:{from:'20:30',to:'23:00',start:'2026-10-19',end:'2026-10-19'}},new Date('2026-10-21T04:05:00Z'))")
res['v4_overnight_tue1am_mononly']=ev("active({schedule:{days:'1',from:'22:00',to:'02:00'}},new Date('2026-10-20T08:00:00Z'))")  # Tue 1am PT, started Mon -> true
res['v4_overnight_mon1am_mononly']=ev("active({schedule:{days:'1',from:'22:00',to:'02:00'}},new Date('2026-10-19T08:00:00Z'))")  # Mon 1am -> false
res['v4_esc']=ev("esc('<img src=x onerror=alert(1)>')")
res['v4_web_block']=ev("WEB_OK.test('https://evil.com/')+','+WEB_OK.test('https://junglegymfun.com/x')+','+WEB_OK.test('https://junglegymfun.com.evil.com/')")
res['v4_media_block']=ev("[safeMedia('javascript:alert(1)'),safeMedia('//evil.com/a.png'),safeMedia('media/a.png')].join('|')")
res['v4_src_param_block']=ev("SRC")
res['v4_splash_first_paint']=None
cmd('Page.navigate',url=BASE+'/index.html?screen=lobby&src=https://evil.com/p.json');time.sleep(0.05)
res['v4_splash_first_paint']=ev("document.getElementById('A').innerText")
time.sleep(2);res['v4_evil_src_ignored']=ev("SRC")
# v5: old Chromium where hourCycle is ignored (and worst case: forced 12h output with dayPeriod)
for name,patch in [('hc_ignored',"o=Object.assign({},o);delete o.hourCycle;"),('forced_12h',"o=Object.assign({},o);delete o.hourCycle;o.hour12=true;")]:
    sid=cmd('Page.addScriptToEvaluateOnNewDocument',source="(function(){var D=Intl.DateTimeFormat;Intl.DateTimeFormat=function(l,o){o=o||{};"+patch+"return new D(l,o)};Intl.DateTimeFormat.prototype=D.prototype})()")['identifier']
    cmd('Page.navigate',url=BASE+'/index.html?screen=lobby&debug=1');time.sleep(4)
    res['v5_'+name+'_parts']=ev("JSON.stringify(FMT.formatToParts(new Date('2026-10-20T04:05:00Z')).map(function(x){return x.type+'='+x.value}))")
    res['v5_'+name+'_la']=ev("var t=la(new Date('2026-10-20T04:05:00Z'));pad(t.h)+':'+pad(t.mi)")
    res['v5_'+name+'_lobby_active']=ev("['2026-10-20T03:30:00Z','2026-10-20T04:05:00Z','2026-10-20T05:59:00Z','2026-10-20T06:00:00Z','2026-10-20T03:29:00Z'].map(function(d){return data.playlists.lobby.filter(function(x){return active(x,new Date(d))}).length+'/'+data.playlists.lobby.length}).join(' ')")
    res['v5_'+name+'_noon']=ev("var t=la(new Date('2026-10-19T19:05:00Z'));pad(t.h)+':'+pad(t.mi)")
    res['v5_'+name+'_midnight']=ev("var t=la(new Date('2026-10-19T07:05:00Z'));pad(t.h)+':'+pad(t.mi)")
    cmd('Page.removeScriptToEvaluateOnNewDocument',identifier=sid)
cmd('Page.navigate',url=BASE+'/index.html?screen=lobby&debug=1');time.sleep(4)
res['v5_player']=ev("JSON.parse(document.getElementById('dbg').textContent).player")
res['v5_dbg_la']=ev("JSON.parse(document.getElementById('dbg').textContent).la")
res['v5_csv_whitelist']=ev("JSON.stringify((function(j){return [j.refreshMinutes,j.__proto__===Object.prototype,j.evil,j.screens.default]})(csvToJson('screen,type,src,title,body\\n,config,,refreshMinutes,3\\n,config,,evil,1\\n,config,,__proto__,x\\n,config,,screens,x\\n')))")
res['v5_fail_delay']=ev("new Promise(function(r){data={screens:{default:'x'},playlists:{x:[{type:'image',src:'media/missing.png'},{type:'slide',title:'B'}]}};idx=0;var t0=Date.now();next();var i=setInterval(function(){if(document.querySelector('.layer.on').innerText.indexOf('B')>-1){clearInterval(i);r(Date.now()-t0)}},100);setTimeout(function(){r('timeout')},6000)})")
res['v5_range']=ev("fetch('media/sample.svg').then(()=>new Promise(r=>setTimeout(r,500))).then(()=>Promise.all([fetch('media/sample.svg',{headers:{Range:'bytes=0-9'}}).then(r=>r.status+' '+r.headers.get('content-range')+' '+r.headers.get('content-length')),fetch('media/sample.svg',{headers:{Range:'bytes=99999999-'}}).then(r=>r.status+' '+r.headers.get('content-range'))])).then(a=>a.join(' | '))")
res['v5_cache']=ev("caches.keys().then(k=>k.join(','))")
print(json.dumps(res,indent=1))
print('exceptions',logs);p.kill()
