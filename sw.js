// TJG signage offline cache v5. Shell+playlist network-first; media cache-first; Range served from cache; navigate falls back to shell; unused media evicted.
var C='tjg-signage-v5',SHELL=['./','index.html','playlist.json'],MEDIA=/\.(png|jpe?g|gif|webp|svg|mp4|webm)$/i;
self.addEventListener('install',function(e){e.waitUntil(caches.open(C).then(function(c){return c.addAll(SHELL)}).then(function(){return self.skipWaiting()}))});
self.addEventListener('activate',function(e){e.waitUntil(caches.keys().then(function(k){return Promise.all(k.filter(function(x){return x!==C}).map(function(x){return caches.delete(x)}))}).then(function(){return self.clients.claim()}))});
self.addEventListener('message',function(e){if(!e.data||!e.data.precache)return;var keep=e.data.precache.map(function(u){return new URL(u,self.registration.scope).href});
 caches.open(C).then(function(c){keep.forEach(function(u){c.match(u).then(function(h){if(!h)c.add(u)['catch'](function(){})})});
  c.keys().then(function(ks){ks.forEach(function(q){if(MEDIA.test(new URL(q.url).pathname)&&keep.indexOf(q.url)<0)c['delete'](q)})})})});
function key(u){return u.replace(/([?&])t=\d+&?/,'$1').replace(/[?&]$/,'')}
function ranged(r){return caches.match(r.url).then(function(h){if(!h)return fetch(r);return h.blob().then(function(b){var n=b.size,
 m=/bytes=(\d+)-(\d*)/.exec(r.headers.get('range')||''),s=m?+m[1]:0,e=m&&m[2]?Math.min(+m[2],n-1):n-1;
 if(s>=n||s>e)return new Response('',{status:416,headers:{'Content-Range':'bytes */'+n}});
 return new Response(b.slice(s,e+1),{status:206,headers:{'Content-Type':h.headers.get('Content-Type')||'video/mp4','Content-Range':'bytes '+s+'-'+e+'/'+n,'Content-Length':String(e-s+1),'Accept-Ranges':'bytes'}})})})}
self.addEventListener('fetch',function(e){var r=e.request;if(r.method!=='GET')return;var u=new URL(r.url);
 if(u.searchParams&&u.searchParams.get('probe'))return; // reload probe must hit network
 if(MEDIA.test(u.pathname)){
  if(r.headers.get('range')){e.respondWith(ranged(r)['catch'](function(){return new Response('',{status:504})}));return}
  e.respondWith(caches.match(r.url).then(function(h){return h||fetch(r).then(function(res){if(res.ok&&res.status===200){var cp=res.clone();caches.open(C).then(function(c){c.put(r.url,cp)})}return res})})['catch'](function(){return new Response('',{status:504})}));return}
 if(u.origin!==location.origin&&!/output=csv|\.json/.test(r.url))return;
 e.respondWith(fetch(r).then(function(res){if(res.ok){var cp=res.clone();caches.open(C).then(function(c){c.put(key(r.url),cp)})}return res})['catch'](function(){
  return caches.match(key(r.url)).then(function(h){return h||(r.mode==='navigate'?caches.match('index.html'):caches.match(key(r.url),{ignoreSearch:true}))})}))});
