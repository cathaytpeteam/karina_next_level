// Focused R1.2.1 checks. Run: node verify_fixes.cjs
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const html=fs.readFileSync(`${__dirname}/index.html`,'utf8');
const part=(start,end)=>html.slice(html.indexOf(start),html.indexOf(end,html.indexOf(start)));
const context=vm.createContext({assert});
vm.runInContext(`
const fields={phoneInput:'886983952902',dFlight:'407',delayTime:'18:00',altA:'CX',altN:'401',altTime:'19:00',callFlight:'407',callGate:'5'};
const v=id=>fields[id]||'';
const digits=s=>String(s).replace(/\\D/g,'');
const normalizeFlight=s=>String(Number(digits(s)));
const isFlt=s=>/^\\d{1,3}$/.test(s);
const isCarrier=s=>/^[A-Z0-9]{2}$/.test(s);
const isAir=s=>/^[A-Z]{2}$/.test(s);
const timeOk=id=>/^([01]\\d|2[0-3]):[0-5]\\d$/.test(v(id));
const normalizePhone=s=>/^\\d{11,12}$/.test(digits(s))?{digits:digits(s),blocked:false}:null;
const callFlightNumber=()=>v('callFlight');
const callGateFull=()=>v('callGate')?'B'+v('callGate'):'';
const dnGateFull=()=>v('gGate')?'B'+v('gGate'):'';
const S={phone:'886983952902',status:'possible',arrange:'known',callMode:'join'};
const stack=['phone','scenario','calltype','callflight','callgate','preview'];
let navPos=5,resetting=false,shown='',movement=null,popstate;
const showScreen=id=>{shown=id;};
const history={go:delta=>{movement=delta;}};
const window={addEventListener:(name,fn)=>{popstate=fn;}};
`,context);
vm.runInContext(part('  const GENERAL_CX_FLIGHTS=', '  function callFlightOk()'),context);
vm.runInContext(part('  const OK={','  function bagHint('),context);
vm.runInContext(part('  let backPending=false;', '  $("back").onclick='),context);
vm.runInContext(`
assert.equal(OK.preview(),true);
fields.callGate=''; assert.equal(OK.callgate(),false); assert.equal(OK.preview(),false);
navPos=4; popstate({state:{findPax:true,pos:5,id:'preview'}});
assert.equal(shown,'callgate'); assert.equal(movement,-1);
popstate({state:{findPax:true,pos:4,id:'callgate'}});
fields.callGate='5'; popstate({state:{findPax:true,pos:5,id:'preview'}});
assert.equal(shown,'preview'); assert.equal(OK.preview(),true);
fields.phoneInput='819012345678'; navPos=0;
popstate({state:{findPax:true,pos:5,id:'preview'}});
assert.equal(shown,'phone'); assert.equal(movement,-5); assert.equal(OK.preview(),false);
fields.phoneInput=''; assert.equal(firstInvalidStep(5),0);
fields.phoneInput='+886 983 952 902'; assert.equal(firstInvalidStep(5),-1);
for(const status of ['possible','delayed','unknown']){
 S.status=status;
 for(const flight of ['450','530','564']){
  fields.dFlight=flight; assert.equal(OK.dflight(),false);
  fields.dFlight='407'; fields.altN=flight; assert.equal(OK.darrange(),false);
 }
 fields.dFlight='407'; fields.altN='401'; assert.equal(OK.dflight(),true); assert.equal(OK.darrange(),true);
 fields.altN='407'; assert.equal(OK.darrange(),false);
 fields.altA='BR'; fields.altN='530'; assert.equal(OK.darrange(),true); fields.altA='CX';
}
S.status='gate'; S.gateStatus='cancelled';
for(const flight of ['450','530','564']){
 fields.dFlight=flight; assert.equal(OK.dflight(),true);
 fields.callFlight=flight; assert.equal(OK.callflight(),true);
}
`,context);
console.log('PASS R1.2.1: stale recipient, invalid Forward, send guard, HKG route validation, and unaffected Gate/Final Call flights');
