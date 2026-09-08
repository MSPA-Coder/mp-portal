/* Comportamento do site. Cada página é um documento próprio servido pelo nginx
   (o roteador por hash saiu na F5), então este arquivo é carregado nas sete e
   precisa sobreviver à ausência de qualquer bloco: o que não existe na página
   atual simplesmente não é ligado. Daí a checagem antes de cada seção — sem
   ela, um `qs` nulo interromperia o script e levaria junto o menu, o rodapé e
   o formulário. */
(function(){
"use strict";
var RM=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
var qs=function(s,c){return (c||document).querySelector(s)};
var qsa=function(s,c){return Array.prototype.slice.call((c||document).querySelectorAll(s))};
var pad=function(n){return (n<10?'0':'')+n};

/* ---------- relógio ---------- */
var DIAS=['DOM','SEG','TER','QUA','QUI','SEX','SAB'],MESES=['JAN','FEV','MAR','ABR','MAI','JUN','JUL','AGO','SET','OUT','NOV','DEZ'];
function tickClock(){var d=new Date();var t=pad(d.getHours())+':'+pad(d.getMinutes())+':'+pad(d.getSeconds());
 var uc=qs('#utilClock');if(uc){uc.textContent=DIAS[d.getDay()]+' '+pad(d.getDate())+' '+MESES[d.getMonth()]+' '+d.getFullYear()+' • '+t;}
 qsa('.cam-time').forEach(function(el){el.textContent=t;});}
tickClock();setInterval(tickClock,1000);

/* ---------- feed ---------- */
var EVTS=['Acesso autorizado — Portaria 01','Ronda concluída — Bloco B','Alarme verificado — Sem ocorrência','Visitante registrado — Recepção','CFTV — Diagnóstico automático OK','Portaria remota — Chamado atendido','Perímetro — Varredura concluída','Manutenção preventiva — Executada','Controle de acesso — Credencial liberada','Limpeza — Rotina do turno iniciada'];
var evIdx=0,feed=qs('#eventFeed');
if(feed){
 (function(){
  function pushEvent(){var d=new Date();var li=document.createElement('li');if(!RM)li.className='new';
   li.innerHTML='<b>'+pad(d.getHours())+':'+pad(d.getMinutes())+':'+pad(d.getSeconds())+'</b> — '+EVTS[evIdx%EVTS.length];evIdx++;
   feed.insertBefore(li,feed.firstChild);while(feed.children.length>4)feed.removeChild(feed.lastChild);}
  pushEvent();pushEvent();pushEvent();setInterval(pushEvent,4200);
 })();
}

/* ---------- scramble ---------- */
function scrambleEl(el){var fin=el.getAttribute('data-text')||el.textContent;
 if(RM){el.textContent=fin;return;}
 var chars='█▓▒░<>/#01',frame=0,total=Math.max(16,fin.length*1.6);
 (function run(){frame++;var reveal=Math.floor((frame/total)*fin.length),out='';
  for(var i=0;i<fin.length;i++){var c=fin[i];out+=(c===' '||c==='•'||c==='—'||c==='&'||i<reveal)?c:chars[(Math.random()*chars.length)|0];}
  el.textContent=out;if(frame<total)setTimeout(run,26);else el.textContent=fin;})();}

/* ---------- reveal + contadores ---------- */
var io=new IntersectionObserver(function(es){es.forEach(function(en){if(en.isIntersecting){en.target.classList.add('on');io.unobserve(en.target);}});},{threshold:.12});
qsa('.rv').forEach(function(el){io.observe(el);});
var cio=new IntersectionObserver(function(es){es.forEach(function(en){if(!en.isIntersecting)return;var el=en.target,target=parseInt(el.getAttribute('data-count'),10);cio.unobserve(el);
 if(RM){el.textContent=target;return;}var t0=null;
 function step(ts){if(!t0)t0=ts;var p=Math.min((ts-t0)/1100,1);el.textContent=Math.round(target*(1-Math.pow(1-p,3)));if(p<1)requestAnimationFrame(step);}
 requestAnimationFrame(step);});},{threshold:.6});
qsa('[data-count]').forEach(function(el){cio.observe(el);});

/* Qual aba abrir, lida da âncora: `/solucoes#int` continua sendo um link
   compartilhável, como era `#/solucoes/int` no roteador antigo. */
function abaDoHash(padrao){return location.hash.replace(/^#/,'')||padrao;}
/* `replaceState` e não `location.hash=`: a URL fica atualizada para copiar,
   sem empilhar histórico e sem o salto de rolagem que a âncora provocaria. */
function marcarHash(chave){
 if(!window.history||!history.replaceState)return;
 history.replaceState(null,'',location.pathname+'#'+chave);}

/* ---------- abas soluções ---------- */
var tabBtns=qsa('.tab-btn'),panels=qsa('.sol-panel');
if(tabBtns.length){
 (function(){
  function activateTab(key){var ok=false;
   tabBtns.forEach(function(b){var on=b.getAttribute('data-tab')===key;if(on)ok=true;
    b.classList.toggle('active',on);b.setAttribute('aria-selected',on?'true':'false');});
   if(!ok)key='seg';
   panels.forEach(function(p){p.classList.toggle('active',p.id==='pan-'+key);});
   return key;}
  tabBtns.forEach(function(b){b.addEventListener('click',function(){
   marcarHash(activateTab(b.getAttribute('data-tab')));});});
  activateTab(abaDoHash('seg'));
 })();
}

/* ---------- abas parceiros/clientes ---------- */
var pgBtns=qsa('.pg-tab');
if(pgBtns.length){
 (function(){
  function activatePTab(key){var ok=false;
   pgBtns.forEach(function(b){var on=b.getAttribute('data-ptab')===key;if(on)ok=true;
    b.classList.toggle('active',on);b.setAttribute('aria-selected',on?'true':'false');});
   if(!ok)key='parc';
   qs('#pan-parc').classList.toggle('active',key==='parc');
   qs('#pan-cli').classList.toggle('active',key==='cli');
   return key;}
  pgBtns.forEach(function(b){b.addEventListener('click',function(){
   marcarHash(activatePTab(b.getAttribute('data-ptab')));});});
  activatePTab(abaDoHash('parc'));
 })();
}

/* ---------- método: player + autoplay ---------- */
var MDATA=[
 {t:'Diagnóstico',d:'Visita técnica para entender o ambiente, os riscos, os fluxos de pessoas e veículos e as necessidades reais da operação.',c:['Relatório da visita','Mapa de riscos','Escopo preliminar']},
 {t:'Projeto',d:'Desenhamos a solução integrando tecnologia, equipes e procedimentos, com escopo, coberturas e responsabilidades definidos.',c:['Projeto técnico','Proposta comercial','Cronograma']},
 {t:'Implantação',d:'Instalação e integração de sistemas — CFTV, acesso, alarmes — e mobilização de equipes com treinamento e rotinas.',c:['Sistemas instalados','Equipes treinadas','Aceite do cliente']},
 {t:'Operação',d:'Execução diária com procedimentos padronizados, supervisão próxima e atendimento ágil a chamados e ocorrências.',c:['Rotinas padronizadas','Supervisão ativa','Atendimento a chamados']},
 {t:'Monitoramento',d:'Central acompanhando câmeras, alarmes e acessos 24 horas, com verificação e resposta a eventos em tempo real.',c:['Central 24h','Resposta a eventos','Registro de ocorrências']},
 {t:'Manutenção',d:'Manutenção preventiva, relatórios periódicos, indicadores de desempenho e planos de melhoria contínua da operação.',c:['Manutenção preventiva','Indicadores e relatórios','Plano de melhoria']}];
var autoBtn=qs('#mAuto');
if(autoBtn){
 (function(){
  var mIdx=0,mNodes=qsa('.m-node');
  var AUTO_MS=6000,autoOn=!RM,autoTimer=null;
  function mRender(anim){
   mNodes.forEach(function(n,i){n.classList.toggle('cur',i===mIdx);n.classList.toggle('done',i<mIdx);});
   qs('#mBar').style.width=(mIdx/(MDATA.length-1))*96+'%';
   qs('#mNum').textContent=pad(mIdx+1);
   qs('#mKick').textContent='ETAPA '+pad(mIdx+1)+' / '+pad(MDATA.length);
   qs('#mTitle').textContent=MDATA[mIdx].t;
   qs('#mDesc').textContent=MDATA[mIdx].d;
   qs('#mChips').innerHTML=MDATA[mIdx].c.map(function(x){return '<span>'+x+'</span>';}).join('');
   if(anim&&!RM){var det=qs('#mDetail');det.classList.remove('swap');void det.offsetWidth;det.classList.add('swap');}}
  function mAutoUI(){autoBtn.classList.toggle('on',autoOn);autoBtn.setAttribute('aria-pressed',autoOn?'true':'false');}
  function mStopAuto(){if(autoTimer){clearInterval(autoTimer);autoTimer=null;}}
  /* A condição `cur==='metodo'` do roteador some: aqui o player só existe
     porque esta É a página do método. Resta pausar com a aba em segundo plano. */
  function mStartAuto(){mStopAuto();autoTimer=setInterval(function(){
   if(autoOn&&!document.hidden){mIdx=(mIdx+1)%MDATA.length;mRender(true);}},AUTO_MS);}
  function mResetAuto(){mStopAuto();mStartAuto();}
  function mIr(passo){mIdx=(mIdx+passo+MDATA.length)%MDATA.length;mRender(true);mResetAuto();}
  mNodes.forEach(function(n){n.addEventListener('click',function(){mIdx=parseInt(n.getAttribute('data-i'),10);mRender(true);mResetAuto();});});
  qs('#mNext').addEventListener('click',function(){mIr(1);});
  qs('#mPrev').addEventListener('click',function(){mIr(-1);});
  autoBtn.addEventListener('click',function(){autoOn=!autoOn;mAutoUI();mResetAuto();});
  document.addEventListener('keydown',function(e){
   if(e.key==='ArrowRight')mIr(1);
   if(e.key==='ArrowLeft')mIr(-1);});
  mRender(false);mAutoUI();mStartAuto();
 })();
}

/* ---------- entrada da página ---------- */
/* O que o `route()` fazia a cada troca de tela agora acontece uma vez, no
   carregamento. O rótulo lateral já vem escrito no HTML — ele é conteúdo, não
   estado de roteador —, então o scramble parte do próprio texto. */
var tag=qs('#routeTag');if(tag)scrambleEl(tag);
qsa('[data-scramble]').forEach(function(s){scrambleEl(s);});
var hero=qs('#heroTitle');
if(hero){requestAnimationFrame(function(){hero.classList.add('on');});
 var eb=qs('#eyebrowScramble');if(eb)scrambleEl(eb);}

/* botões "próxima tela" */
qsa('.go-next').forEach(function(b){b.addEventListener('click',function(){
 var sec=b.closest('.screen');var nxt=sec?sec.nextElementSibling:null;
 if(nxt)nxt.scrollIntoView({behavior:RM?'auto':'smooth'});});});

/* header + menu */
var hd=qs('#siteHeader');
window.addEventListener('scroll',function(){hd.classList.toggle('scrolled',window.scrollY>8);},{passive:true});
var tg=qs('#navToggle');
tg.addEventListener('click',function(){var open=document.body.classList.toggle('nav-open');tg.setAttribute('aria-expanded',open?'true':'false');});

/* formulário
   O ENVIO E DO NAVEGADOR, NAO DAQUI. O formulario tem `action` e `method`: ele
   posta para a propria pagina, a aplicacao grava e responde com um 303 para a
   confirmacao. Nada aqui intercepta o `submit`, e isso e deliberado -- assim o
   contato continua funcionando com JavaScript desligado, que e o unico caminho
   que nao depende deste arquivo carregar.

   O que existia aqui era a simulacao de sucesso da epoca em que o site era
   estatico e nao tinha destino. Saiu junto com o backend de verdade. */
var form=qs('#ctaForm');
if(form){
 form.addEventListener('submit',function(){
  var botao=form.querySelector('button[type=submit]');
  if(botao){botao.disabled=true;botao.textContent='Enviando…';}
 });
}

/* marquee + ano */
var mq=qs('#mqTrack');if(mq)mq.innerHTML+=mq.innerHTML;
qs('#year').textContent=new Date().getFullYear();
})();
