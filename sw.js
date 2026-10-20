// Offline cache. Shell + playlist network-first; media cache-first (precached when playlist loads).
var C='tjg-signage-v2';
self.addEventListener('install',function(e){e.waitUntil(caches.open(C).then(function(c){return c.addAll(['./','index.html','playlist.json'])}));self.skipWaiting()});
self.addEventListener('activate',function(e){e.waitUntil(caches.keys().then(function(k){return Promise.all(k.filter(function(x){return x!==C}).map(function(x){return caches.delete(x)}))}).then(function(){return self.clients.claim()}))});
self.addEventListener('message',function(e){if(e.data&&e.data.precache)caches.open(C).then(function(c){e.data.precache.forEach(function(u){c.match(u).then(function(h){if(!h)c.add(u).catch(function(){})})})})});
function key(u){return u.replace(/[?&]t=\d+/,'')}
self.addEventListener('fetch',function(e){var r=e.request;if(r.method!=='GET'||r.headers.get('range'))return;
 var u=new URL(r.url),media=/\.(png|jpe?g|gif|webp|svg|mp4|webm)$/i.test(u.pathname);
 if(media){e.respondWith(caches.match(r.url).then(function(h){return h||fetch(r).then(function(res){if(res.ok){var cp=res.clone();caches.open(C).then(function(c){c.put(r.url,cp)})}return res})}));return}
 if(u.origin!==location.origin&&!/output=csv|\.json/.test(r.url))return;
 e.respondWith(fetch(r).then(function(res){if(res.ok){var cp=res.clone();caches.open(C).then(function(c){c.put(key(r.url),cp)})}return res}).catch(function(){return caches.match(key(r.url))}))});
