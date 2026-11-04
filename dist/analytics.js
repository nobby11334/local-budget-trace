'use strict';
(()=>{
 const id='G-YR559ZB1GS',key='budget-trace-analytics-disabled',production=location.hostname==='nobby11334.github.io'&&location.pathname.startsWith('/local-budget-trace/');
 const names={overview:'まちの財政',latest:'2025年度速報',tree:'支出ツリー',parties:'事業・契約・支払先',national:'国から地域へ',trace:'財源から成果へ',compare:'自治体を比べる',sources:'出典と接続状況',municipality_picker:'自治体を選択'};
 let initialized=false,lastKey='';
 function disabled(){try{return localStorage.getItem(key)==='true'}catch{return false}}
 window['ga-disable-'+id]=disabled();
 function initialize(){
  if(initialized)return;
  initialized=true;window.dataLayer=window.dataLayer||[];
  window.gtag=window.gtag||function(){window.dataLayer.push(arguments)};
  window.gtag('consent','default',{analytics_storage:'granted',ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied'});
  window.gtag('js',new Date());
  let referrer='';try{const r=new URL(document.referrer);referrer=r.origin+r.pathname}catch{}
  // Standard page_view only. app_view below is a separate event, never a manual page_view.
  window.gtag('config',id,{send_page_view:true,allow_google_signals:false,allow_ad_personalization_signals:false,page_location:location.origin+location.pathname,page_referrer:referrer});
  const script=document.createElement('script');script.async=true;script.src='https://www.googletagmanager.com/gtag/js?id='+id;document.head.appendChild(script);
 }
 function track(input){
  if(!production||disabled())return;
  let view=Object.hasOwn(names,input.view)?input.view:'overview';
  let code=/^\d{5}$/.test(input.city?.code||'')?input.city.code:'';
  if(!code&&!['latest','national','sources'].includes(view))view='municipality_picker';
  if(['national','sources','municipality_picker'].includes(view))code='';
  const year=view==='latest'?'2025':view==='national'?'2024':view==='sources'||view==='municipality_picker'?'':view==='tree'&&input.treeMode==='ledger'?input.ledgerYear:input.year;
  const data={view_name:view,view_label:names[view],municipality_code:code||'all',prefecture:code?input.city.pref:'全国',fiscal_year:/^20\d{2}$/.test(year||'')?year:'',tree_mode:view==='tree'&&['ledger','purpose','nature'].includes(input.treeMode)?input.treeMode:''};
  const next=JSON.stringify(data);if(next===lastKey)return;
  lastKey=next;initialize();window.gtag('event','app_view',{...data,send_to:id});
 }
 window.budgetAnalytics={track};
 const dialog=document.getElementById('analyticsInfo'),toggle=document.getElementById('toggleAnalytics'),status=document.getElementById('analyticsPreference');
 function updatePreference(){status.textContent=disabled()?'このブラウザーではアクセス解析を停止しています。':'このブラウザーではアクセス解析が有効です。';toggle.textContent=disabled()?'アクセス解析を有効にする':'このブラウザーでアクセス解析を停止する'}
 document.getElementById('openAnalyticsInfo')?.addEventListener('click',()=>{updatePreference();dialog.showModal()});
 document.getElementById('closeAnalyticsInfo')?.addEventListener('click',()=>dialog.close());
 toggle?.addEventListener('click',()=>{
  const stop=!disabled();
  try{localStorage.setItem(key,String(stop))}catch{status.textContent='設定を保存できませんでした。ブラウザーの保存設定をご確認ください。';return}
  window['ga-disable-'+id]=stop;
  if(stop){for(const name of document.cookie.split(';').map(v=>v.trim().split('=')[0]).filter(v=>/^_ga(?:_|$)/.test(v))){for(const domain of ['',location.hostname,'.'+location.hostname])document.cookie=name+'=; Max-Age=0; Path=/; SameSite=Lax'+(domain?'; Domain='+domain:'')}}
  location.reload();
 });
})();
