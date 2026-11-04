'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync('dist/analytics.js','utf8');
function setup({host='nobby11334.github.io',disabled=false}={}){
 const saved=new Map(disabled?[['budget-trace-analytics-disabled','true']]:[]),nodes=new Map(),scripts=[];
 const node=()=>({textContent:'',addEventListener(type,fn){this[type]=fn},showModal(){this.open=true},close(){this.open=false}});
 const document={referrer:'https://example.com/link?private=secret#fragment',cookie:'',head:{appendChild:s=>scripts.push(s)},createElement:()=>({}),getElementById(id){if(!nodes.has(id))nodes.set(id,node());return nodes.get(id)}};
 const context={window:{},document,location:{hostname:host,pathname:'/local-budget-trace/',origin:'https://'+host,reload(){}},localStorage:{getItem:k=>saved.get(k),setItem:(k,v)=>saved.set(k,v)},URL};
 vm.runInNewContext(source,context);return {...context,nodes,scripts};
}
const city={code:'13105',pref:'東京都'},input={view:'overview',city,year:'2024',treeMode:'ledger'};
const events=c=>(c.window.dataLayer||[]).map(a=>Array.from(a)).filter(a=>a[0]==='event');
test('one Google config and app_view per distinct view; no manual page_view duplicates',()=>{
 const c=setup();c.window.budgetAnalytics.track(input);c.window.budgetAnalytics.track({...input,search:'do not send me'});
 assert.equal(c.scripts.length,1);assert.equal(events(c).length,1);assert.equal(events(c)[0][1],'app_view');
 assert(!JSON.stringify(c.window.dataLayer).includes('do not send me'));
 const config=Array.from(c.window.dataLayer.find(a=>a[0]==='config'))[2];
 assert.equal(config.page_referrer,'https://example.com/link');assert.equal(config.allow_google_signals,false);assert.equal(config.allow_ad_personalization_signals,false);
 c.window.budgetAnalytics.track({...input,view:'latest'});c.window.budgetAnalytics.track({...input,view:'latest',year:'2023'});
 assert.equal(events(c).length,2);assert.equal(events(c)[1][2].fiscal_year,'2025');
 c.window.budgetAnalytics.track(input);assert.equal(events(c).length,3);
});
test('preview and persisted opt-out never load Google or queue events',()=>{
 for(const c of [setup({host:'terminal.local'}),setup({disabled:true})]){c.window.budgetAnalytics.track(input);assert.equal(c.scripts.length,0);assert.equal(events(c).length,0)}
});
test('municipality and tree classification changes are measured; same view is deduplicated',()=>{
 const c=setup();c.window.budgetAnalytics.track(input);c.window.budgetAnalytics.track({...input,city:{code:'40130',pref:'福岡県'}});
 c.window.budgetAnalytics.track({...input,view:'tree',treeMode:'ledger',ledgerYear:'2025'});
 c.window.budgetAnalytics.track({...input,view:'tree',treeMode:'ledger',ledgerYear:'2025'});
 c.window.budgetAnalytics.track({...input,view:'tree',treeMode:'purpose'});
 assert.equal(events(c).length,4);assert.equal(events(c)[2][2].fiscal_year,'2025');assert.equal(events(c)[3][2].fiscal_year,'2024');
});
test('opt-out immediately blocks subsequent events; no locality is invented for the picker',()=>{
 const c=setup();c.window.budgetAnalytics.track({view:'overview',year:'2024'});c.window.budgetAnalytics.track({view:'tree',year:'2024'});
 assert.equal(events(c).length,1);assert.equal(events(c)[0][2].municipality_code,'all');assert.equal(events(c)[0][2].view_name,'municipality_picker');
 c.nodes.get('toggleAnalytics').click();c.window.budgetAnalytics.track(input);assert.equal(events(c).length,1);assert.equal(c.window['ga-disable-G-YR559ZB1GS'],true);
});
