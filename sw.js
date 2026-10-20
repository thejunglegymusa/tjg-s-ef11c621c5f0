// TJG signage service worker v6.1 (bg() wraps waitUntil calls made after respondWith): shell network-first with cache fallback; media cache-first with full Range support; only touches caches named tjg-signage-*.
var C='tjg-signage-v6-1',PFX='tjg-signage-',SHELL=['./','index.html','qr.js','playlist.json'],MEDIA=/\.(png|jpe?g|gif|webp|svg|mp4|webm)$/i;
self.addEventListener('install',function(e){e.waitUntil(caches.open(C).then(function(c){return c.addAll(SHELL)}).then(function(){return self.skipWaiting()}))});
self.addEventListener('activate',function(e){e.waitUntil(caches.keys().then(function(k){return Promise.all(k.filter(function(x){return x.indexOf(PFX)===0&&x!==C}).map(function(x){return caches['delete'](x)}))}).then(function(){return self.clients.claim()}))});
function precache(list){var keep=list.map(function(u){return new URL(u,self.registration.scope).href});
 return caches.open(C).then(function(c){return Promise.all(keep.map(function(u){return c.match(u).then(function(h){if(!h)return c.add(u)['catch'](function(){})})})).then(function(){
  return c.keys().then(function(ks){return Promise.all(ks.filter(function(q){return MEDIA.test(new URL(q.url).pathname)&&keep.indexOf(q.url)<0}).map(function(q){return c['delete'](q)}))})})})}
self.addEventListener('message',function(e){if(!e.data||!e.data.precache||!e.data.precache.map)return;var p=precache(e.data.precache)['catch'](function(){});if(e.waitUntil)e.waitUntil(p)});
function bg(e,p){p=p['catch'](function(){});try{e.waitUntil(p)}catch(x){}return p}
function key(u){return u.replace(/([?&])t=\d+&?/,'$1').replace(/[?&]$/,'')}
function fullB(b,h){return new Response(b,{status:200,headers:{'Content-Type':h.headers.get('Content-Type')||'application/octet-stream','Content-Length':String(b.size),'Accept-Ranges':'bytes'}})}
function full(h){return h.blob().then(function(b){return fullB(b,h)})}
/* Range parsing: single range only. bytes=S-E, bytes=S-, bytes=-N. Multi-range or malformed -> full 200. Unsatisfiable -> 416. */
function ranged(r,e){var url=r.url;return caches.match(url).then(function(h){
 if(!h){ // not cached yet: pass through, and cache the full file in the background so it works offline next time
  bg(e,caches.open(C).then(function(c){return c.match(url).then(function(x){if(!x)return fetch(url).then(function(res){if(res.ok&&res.status===200)return c.put(url,res)})})})['catch'](function(){}));
  return fetch(r)}
 var hdr=String(r.headers.get('range')||'').replace(/\s+/g,'');
 if(hdr.indexOf(',')>-1)return full(h);
 var m=/^bytes=(\d*)-(\d*)$/.exec(hdr);if(!m||(m[1]===''&&m[2]===''))return full(h);
 return h.blob().then(function(b){var n=b.size,s,en;
  if(m[1]===''){var N=+m[2];if(N===0)return new Response('',{status:416,headers:{'Content-Range':'bytes */'+n}});s=Math.max(0,n-N);en=n-1}
  else{s=+m[1];en=m[2]===''?n-1:Math.min(+m[2],n-1);if(m[2]!==''&&+m[2]<s)return fullB(b,h)}
  if(s>=n)return new Response('',{status:416,headers:{'Content-Range':'bytes */'+n}});
  return new Response(b.slice(s,en+1),{status:206,headers:{'Content-Type':h.headers.get('Content-Type')||'video/mp4','Content-Range':'bytes '+s+'-'+en+'/'+n,'Content-Length':String(en-s+1),'Accept-Ranges':'bytes'}})})})}
self.addEventListener('fetch',function(e){var r=e.request;if(r.method!=='GET')return;var u=new URL(r.url);
 if(u.origin!==location.origin)return; // v6: player only ever fetches same-origin
 if(/[?&]probe=/.test(u.search))return; // reload probe must hit network
 if(MEDIA.test(u.pathname)){
  if(r.headers.get('range')){e.respondWith(ranged(r,e)['catch'](function(){return new Response('',{status:504})}));return}
  e.respondWith(caches.match(r.url).then(function(h){return h||fetch(r).then(function(res){if(res.ok&&res.status===200){var cp=res.clone();bg(e,caches.open(C).then(function(c){return c.put(r.url,cp)})['catch'](function(){}))}return res})})['catch'](function(){return new Response('',{status:504})}));return}
 e.respondWith(fetch(r).then(function(res){if(res.ok&&res.status===200){var cp=res.clone();bg(e,caches.open(C).then(function(c){return c.put(key(r.url),cp)})['catch'](function(){}))}return res})['catch'](function(){
  return caches.match(key(r.url)).then(function(h){return h||(r.mode==='navigate'?caches.match('index.html'):caches.match(key(r.url),{ignoreSearch:true}))}).then(function(h){return h||new Response('',{status:504})})}))});
