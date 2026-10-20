/* Minimal local QR encoder (ES5). Byte mode, ECC level M, versions 1-6 (up to 106 bytes). No network. qrSvg(text,fg,bg) -> SVG string or '' */
var QR=(function(){
 var EC=[0,10,16,26,18,24,16],BL=[0,1,1,1,2,2,4],TOT=[0,26,44,70,100,134,172],AL=[0,0,18,22,26,30,34];
 var EXP=[],LOG=[],i,x=1;for(i=0;i<255;i++){EXP[i]=x;LOG[x]=i;x<<=1;if(x&256)x^=0x11d}
 function mul(a,b){return a&&b?EXP[(LOG[a]+LOG[b])%255]:0}
 function gen(n){var g=[1],k,j;for(k=0;k<n;k++){var ng=[];for(j=0;j<=g.length;j++)ng[j]=0;for(j=0;j<g.length;j++){ng[j]^=g[j];ng[j+1]^=mul(g[j],EXP[k])}g=ng}return g}
 function rs(data,n){var g=gen(n),r=[],k,j;for(k=0;k<n;k++)r[k]=0;for(k=0;k<data.length;k++){var f=data[k]^r[0];r.shift();r.push(0);for(j=0;j<n;j++)r[j]^=mul(g[j+1],f)}return r}
 function utf8(s){var o=[],k,c;s=unescape(encodeURIComponent(s));for(k=0;k<s.length;k++){c=s.charCodeAt(k);o.push(c)}return o}
 function make(text){var b=utf8(text),v,k;for(v=1;v<=6;v++)if(b.length+2<=TOT[v]-EC[v]*BL[v])break;if(v>6)return null;
  var cap=TOT[v]-EC[v]*BL[v],bits=[];function put(val,n){for(var q=n-1;q>=0;q--)bits.push((val>>>q)&1)}
  put(4,4);put(b.length,8);for(k=0;k<b.length;k++)put(b[k],8);put(0,Math.min(4,cap*8-bits.length));while(bits.length%8)bits.push(0);
  var dat=[];for(k=0;k<bits.length;k+=8){var c=0;for(var q=0;q<8;q++)c=c<<1|bits[k+q];dat.push(c)}for(k=0;dat.length<cap;k++)dat.push(k%2?0x11:0xEC);
  var nb=BL[v],bs=cap/nb,blocks=[],ecs=[],out=[];for(k=0;k<nb;k++){blocks.push(dat.slice(k*bs,(k+1)*bs));ecs.push(rs(blocks[k],EC[v]))}
  for(k=0;k<bs;k++)for(q=0;q<nb;q++)out.push(blocks[q][k]);for(k=0;k<EC[v];k++)for(q=0;q<nb;q++)out.push(ecs[q][k]);
  var N=17+4*v,M=[],F=[],r,c2;for(r=0;r<N;r++){M[r]=[];F[r]=[];for(c2=0;c2<N;c2++){M[r][c2]=0;F[r][c2]=0}}
  function set(r,c,d){M[r][c]=d?1:0;F[r][c]=1}
  function finder(r0,c0){for(var dr=-1;dr<=7;dr++)for(var dc=-1;dc<=7;dc++){var rr=r0+dr,cc=c0+dc;if(rr<0||cc<0||rr>=N||cc>=N)continue;
   var on=(dr>=0&&dr<=6&&(dc===0||dc===6))||(dc>=0&&dc<=6&&(dr===0||dr===6))||(dr>=2&&dr<=4&&dc>=2&&dc<=4);set(rr,cc,on)}}
  finder(0,0);finder(0,N-7);finder(N-7,0);
  for(k=8;k<N-8;k++){set(6,k,k%2===0);set(k,6,k%2===0)}
  if(AL[v]){var a=AL[v];for(r=-2;r<=2;r++)for(c2=-2;c2<=2;c2++)set(a+r,a+c2,Math.max(Math.abs(r),Math.abs(c2))!==1)}
  set(N-8,8,1);
  for(k=0;k<9;k++){F[8][k]=1;F[k][8]=1}for(k=0;k<8;k++){F[8][N-1-k]=1;F[N-1-k][8]=1}
  var all=[];for(k=0;k<out.length;k++)put2(out[k]);function put2(cw){for(var q=7;q>=0;q--)all.push((cw>>>q)&1)}
  var bi=0,up=true;for(c2=N-1;c2>0;c2-=2){if(c2===6)c2=5;for(var t=0;t<N;t++){r=up?N-1-t:t;for(var j=0;j<2;j++){var cc=c2-j;if(F[r][cc])continue;
   var d=bi<all.length?all[bi]:0;bi++;if((r+cc)%2===0)d^=1;M[r][cc]=d}}up=!up}
  /* format: ECC M (00), mask 0 */
  var fd=0,fb=fd<<10;for(k=14;k>=10;k--)if((fb>>>k)&1)fb^=0x537<<(k-10);var fmt=((fd<<10)|fb)^0x5412;
  for(k=0;k<=5;k++)M[k][8]=(fmt>>>k)&1;M[7][8]=(fmt>>>6)&1;M[8][8]=(fmt>>>7)&1;M[8][7]=(fmt>>>8)&1;for(k=9;k<15;k++)M[8][14-k]=(fmt>>>k)&1;
  for(k=0;k<8;k++)M[8][N-1-k]=(fmt>>>k)&1;for(k=8;k<15;k++)M[N-15+k][8]=(fmt>>>k)&1;M[N-8][8]=1;
  return M}
 function svg(text,fg,bg){var M=make(String(text||''));if(!M)return'';var N=M.length,q=4,S=N+2*q,p='',r,c;
  for(r=0;r<N;r++)for(c=0;c<N;c++)if(M[r][c])p+='M'+(c+q)+' '+(r+q)+'h1v1h-1z';
  return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 '+S+' '+S+'" shape-rendering="crispEdges"><rect width="'+S+'" height="'+S+'" fill="'+(bg||'#fff')+'"/><path d="'+p+'" fill="'+(fg||'#000')+'"/></svg>'}
 return{matrix:make,svg:svg}})();
