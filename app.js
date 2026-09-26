(function(){
  "use strict";
  const $=id=>document.getElementById(id);
  const COPY=window.FIND_PAX_COPY;
  const copy=id=>COPY[id];
  const copyObj=id=>COPY[id];
  document.querySelectorAll('[data-scenario-label="joining"]').forEach(el=>{const t=copy("s.passenger.joining");el.textContent=t;el.closest("button").setAttribute("aria-label",t+" & Message");});
  document.querySelectorAll('[data-scenario-label="transit"]').forEach(el=>{const t=copy("s.passenger.transit");el.textContent=t;el.closest("button").setAttribute("aria-label",t+" & Message");});
  const replaceChildrenCompat=(el,...nodes)=>{while(el.firstChild)el.removeChild(el.firstChild);nodes.forEach(node=>el.appendChild(node));};
  const digits=s=>String(s||"").replace(/\D/g,"");
  const v=id=>$(id).value;

  const blocked=new Set(["85289648964","85262374313"]);
  const flagFor=cc=>cc&&cc.length===2?String.fromCodePoint(...[...cc].map(ch=>127397+ch.charCodeAt(0))):"🌐";
  const regionName=cc=>{try{return new Intl.DisplayNames(["en"],{type:"region"}).of(cc)||cc}catch(e){return cc}};
  const phoneLabel=cc=>cc?flagFor(cc)+" "+cc:"";

  // ==== [phone validation] ====
  function buildPhoneMeta(){
    const lp=window.libphonenumber, byCode={};
    if(!lp||!lp.getCountries||!lp.getCountryCallingCode) return {byCode,codes:[]};
    lp.getCountries().forEach(cc=>{
      const code=String(lp.getCountryCallingCode(cc));
      (byCode[code]||(byCode[code]=[])).push(cc);
    });
    return {byCode,codes:Object.keys(byCode).sort((a,b)=>b.length-a.length)};
  }
  let PHONE_META=buildPhoneMeta();
  let phoneLibReady=PHONE_META.codes.length>0;
  const callingCodeFor=n=>PHONE_META.codes.find(code=>n.startsWith(code))||"";

  function activatePhoneLibrary(){
    if(!window.libphonenumber) return false;
    PHONE_META=buildPhoneMeta();
    phoneLibReady=PHONE_META.codes.length>0;
    if(phoneLibReady){
      const input=$("phoneInput");
      if(input) input.dispatchEvent(new Event("input",{bubbles:false}));
    }
    return phoneLibReady;
  }
  let phoneLibLoading=false, phoneLibAttempts=0;
  function retryPhoneLibrary(){
    phoneLibLoading=false;
    if(!phoneLibReady&&phoneLibAttempts<4){
      phoneLibAttempts++;
      setTimeout(loadPhoneLibrary,250);
    }
  }
  function loadPhoneLibrary(){
    if(activatePhoneLibrary()) return;
    if(phoneLibLoading) return;
    const old=document.querySelector('script[data-phone-lib="1"]');
    if(old&&!old.dataset.failed){
      phoneLibLoading=true;
      setTimeout(()=>{if(!phoneLibReady){old.dataset.failed="1";retryPhoneLibrary();}},2000);
      return;
    }
    if(old) old.remove();
    const script=document.createElement("script");
    script.src="./libphonenumber-max.js";
    script.async=true;
    script.dataset.phoneLib="1";
    phoneLibLoading=true;
    script.onload=()=>{
      phoneLibLoading=false;
      if(!activatePhoneLibrary()) retryPhoneLibrary();
    };
    script.onerror=()=>{script.dataset.failed="1";retryPhoneLibrary();};
    document.head.appendChild(script);
  }

  function detectCountryEarly(raw){
    const n=digits(raw), lp=window.libphonenumber;
    if(!n) return null;
    // Show the country badge as soon as the calling code is typed, even while
    // the bundled phone metadata is still loading. Full validation follows.
    if(n.startsWith("886")) return {country:"TW",label:phoneLabel("TW")};
    if(!lp) return null;
    const code=callingCodeFor(n);
    if(!code) return null;
    const regions=PHONE_META.byCode[code]||[];
    try{
      const ph=lp.parsePhoneNumberFromString("+"+n);
      if(ph&&ph.country) return {country:ph.country,label:phoneLabel(ph.country)};
    }catch(e){}
    if(regions.length===1){
      const cc=regions[0];
      return {country:cc,label:phoneLabel(cc)};
    }
    return null;
  }

  function validatePhone(raw){
    const n=digits(raw), lp=window.libphonenumber;
    if(!n||!lp||!PHONE_META.codes.length) return null;

    // Japan (+81): SMS-capable mobile numbers only. Accept the international
    // mobile part directly (90/80/70/60 + 8 digits), or tolerate 1..3 zeroes
    // immediately after 81 (the normal domestic trunk 0 plus up to two extra
    // leading zeroes). Always normalize to E.164: 81 + 10 mobile digits.
    if(n.startsWith("81")){
      const localJP=n.slice(2);
      for(let drop=0;drop<=3;drop++){
        if(drop>0 && localJP.slice(0,drop)!=="0".repeat(drop)) break;
        const mobile=localJP.slice(drop);
        if(/^[6789]0\d{8}$/.test(mobile) && !mobile.startsWith("800")){
          return {digits:"81"+mobile,country:"JP",callingCode:"81"};
        }
      }
      // A number explicitly beginning with Japan's calling code must not fall
      // through to generic validation (blocks 020, 050, toll-free and landlines).
      return null;
    }

    const code=callingCodeFor(n);
    if(!code) return null;
    const local=n.slice(code.length), regions=PHONE_META.byCode[code]||[];

    // Try the raw national number first, then tolerate 1..3 extra zeroes
    // immediately after the country calling code. A candidate is accepted only
    // when libphonenumber says it is valid; the returned number is always the
    // library's canonical E.164 digits, which removes domestic trunk zeroes.
    for(let drop=0;drop<=3;drop++){
      if(drop>0 && local.slice(0,drop)!=="0".repeat(drop)) break;
      const national=local.slice(drop);
      if(!national) continue;
      const candidate=code+national;
      if(candidate.length>15) continue;

      let ph=null;
      try{ ph=lp.parsePhoneNumberFromString("+"+candidate); }catch(e){}
      if(ph && typeof ph.isValid==="function"){
        if(!ph.isValid()) continue;
        if(ph.country && regions.length && !regions.includes(ph.country)) continue;
        const out=String(ph.number||"").replace(/^\+/,"");
        if(!out || out.length>15) continue;
        return {digits:out,country:ph.country||(regions[0]||""),callingCode:code};
      }
    }
    return null;
  }

  function blockedCandidateFor(raw){
    const n=digits(raw), code=callingCodeFor(n);
    if(!n||!code) return "";
    const local=n.slice(code.length);
    for(let drop=0;drop<=3;drop++){
      if(drop>0 && local.slice(0,drop)!=="0".repeat(drop)) break;
      const national=local.slice(drop);
      if(!national) continue;
      const candidate=code+national;
      if(blocked.has(candidate)) return candidate;
    }
    return "";
  }

  function normalizePhone(raw){
    const n=digits(raw);

    // Blacklisted canned/test numbers must always surface the dedicated warning,
    // even when libphonenumber itself considers that exact number invalid. This
    // check also tolerates the same 1–3 zeroes after the calling code as normal
    // phone normalization, so the blacklist cannot be bypassed by trunk zeroes.
    const blockedDigits=blockedCandidateFor(n);
    if(blockedDigits){
      const code=callingCodeFor(blockedDigits), regions=PHONE_META.byCode[code]||[];
      let country=regions.length===1?regions[0]:"";
      try{
        const ph=window.libphonenumber&&window.libphonenumber.parsePhoneNumberFromString("+"+blockedDigits);
        if(ph&&ph.country) country=ph.country;
      }catch(e){}
      return {digits:blockedDigits,country,callingCode:code,blocked:true};
    }

    const p=validatePhone(n);
    if(!p) return null;
    return {...p,blocked:blocked.has(p.digits)};
  }

  // ==== [state] ====
  const S={phone:"",country:"",status:"",arrange:"",gateStatus:"",gateGo:"",gateTarget:"",order:"zh",orderSet:false,callNoMessage:false,callMode:"",missMode:""};
  // ==== [flow definitions] ====
  const FLOWS={
    miss:{name:copy("progress.flow.miss"),steps:["misstype","mflight","msec"]},
    call:{name:copy("progress.flow.call"),steps:["calltype","callflight","callgate","preview"]},
    wpp:{name:copy("progress.flow.wpp"),steps:["wflight","bag1","bag2","preview"]},
    dp:{name:copy("progress.flow.dp"),steps:["dstatus","dflight","dtransfer","darrange","darrive","preview"]}
  };
  const DP_BRANCH_FLOWS={
    dpgate:{name:copy("progress.flow.dp"),steps:["dstatus","dflight","dnew","dgateaction","preview"]}
  };
  let flow="", cur="phone", resetting=false;
  const stack=["phone"];
  let navPos=0;
  try{history.replaceState({findPax:true,pos:0,id:"phone"},"");}catch(e){}

  // ==== [field validation] ====
  const isAir=s=>/^[A-Z]{2}$/.test(s);
  const isCarrier=s=>/^[A-Z0-9]{2}$/.test(s);
  const isFlt=s=>/^\d{1,3}$/.test(s);
  const normalizeFlight=s=>{const d=digits(s);return d?String(Number(d)):"";};
  function normalizeFlightField(id){
    const el=$(id);
    if(el&&isFlt(el.value)) el.value=normalizeFlight(el.value);
  }
  function timeState(id){
    const d=digits(v(id));
    if(d.length<4) return d.length?"partial":"empty";
    return (+d.slice(0,2)<=23 && +d.slice(2)<=59)?"ok":"bad";
  }
  const timeOk=id=>timeState(id)==="ok";
  function timeHint(id){
    const t=timeState(id);
    return t==="empty"?copy("hint.time.empty"):t==="partial"?copy("hint.time.partial"):t==="bad"?copy("error.time.invalid"):"";
  }
  function fmtTime(el){
    const d=digits(el.value).slice(0,4);
    el.value=d.length>=3?d.slice(0,2)+":"+d.slice(2):d;
  }
  function normalizeCallGate(raw){
    let x=String(raw||"").toUpperCase().replace(/[^1-9R]/g,"");
    if(!x) return "";
    const m=x.match(/[1-9]/), d=m?m[0]:"";
    if(!d) return "";
    return d==="1"&&x.includes("R")?"1R":d;
  }
  function callGateNumber(){
    const x=normalizeCallGate(v("callGate"));
    return /^(?:[1-9]|1R)$/.test(x)?x:"";
  }
  function callGateFull(){
    const z=v("callGateZone"), n=callGateNumber();
    return copyObj("rules.gate.zones").includes(z)&&n&&!(z!==copy("rules.gate.b1rZone")&&n===copy("rules.gate.b1rNumber"))?z+n:"";
  }
  function dnGateFull(){
    const z=v("gGateZone"), x=normalizeCallGate(v("gGate"));
    return copyObj("rules.gate.zones").includes(z)&&/^(?:[1-9]|1R)$/.test(x)&&!(z!==copy("rules.gate.b1rZone")&&x===copy("rules.gate.b1rNumber"))?z+x:"";
  }
  // Header number, grouped the way the destination country writes it (+886 983 952 902).
  // Falls back to the plain +digits if the phone library is not ready or cannot parse it.
  function groupedPhone(d){
    try{
      const lp=window.libphonenumber, ph=lp&&lp.parsePhoneNumberFromString("+"+d);
      if(ph) return ph.formatInternational();
    }catch(e){}
    return "+"+d;
  }
  function callFlightNumber(){
    const d=digits(v("callFlight")).slice(0,3);
    return /^\d{1,3}$/.test(d)?String(Number(d)):"";
  }
  function callFlightFull(){
    const n=callFlightNumber();
    return n?"CX"+n:"";
  }
  // ==== [flight and gate rules] ====
  const HOME_IATA=copy("rules.sec.homeIata");
  const SEC_PREFIXES=copyObj("rules.sec.prefixes");
  function secPrefixesFor(flight){
    const r=SEC_PREFIXES[String(Number(digits(flight)))];
    return r?[r.join,r.transit]:[HOME_IATA];
  }
  function secPrefix(flight,mode){
    const r=SEC_PREFIXES[String(Number(digits(flight)))];
    if(mode==="transit") return r?r.transit:"";
    return HOME_IATA;
  }
  function secPrefixOk(flight,prefix){
    return secPrefixesFor(flight).includes(String(prefix||"").toUpperCase());
  }
  const GENERAL_CX_FLIGHTS=new Set(copyObj("rules.cx.general"));
  const TRANSIT_FLIGHTS=new Set(copyObj("rules.cx.transit"));
  const TRANSIT_ORIGIN_IATA=copyObj("rules.transit.origins");
  const TPE_NON_ORIGIN_TRANSIT_FLIGHTS=new Set(copyObj("rules.cx.nonTpeOriginTransit"));
  const TPE_DEPARTURE_FLIGHTS=new Set([...GENERAL_CX_FLIGHTS].filter(n=>!TPE_NON_ORIGIN_TRANSIT_FLIGHTS.has(n)));
  const generalCxOk=raw=>GENERAL_CX_FLIGHTS.has(String(Number(digits(raw))));
  const tpeDepartureCxOk=raw=>TPE_DEPARTURE_FLIGHTS.has(String(Number(digits(raw))));
  const transitCxOk=raw=>TRANSIT_FLIGHTS.has(String(Number(digits(raw))));
  const sameProtectedCxFlight=(airline,raw,originalRaw)=>String(airline||"").toUpperCase()==="CX"&&isFlt(raw)&&isFlt(originalRaw)&&normalizeFlight(raw)===normalizeFlight(originalRaw);
  const protectFlightOk=(airline,raw,originalRaw)=>String(airline||"").toUpperCase()!=="CX"||(tpeDepartureCxOk(raw)&&!sameProtectedCxFlight(airline,raw,originalRaw));
  const tpeDepartureBlocked=(airline,raw)=>String(airline||"").toUpperCase()==="CX"&&isFlt(raw)&&tpeDepartureCxOk(raw);
  const transitOriginIata=raw=>TRANSIT_ORIGIN_IATA[String(Number(digits(raw)))]||"";
  const TRANSIT_DESTINATIONS=copyObj("rules.transit.destinations");
  const TRANSIT_SMS_ROUTE_JA=copyObj("rules.transit.smsRouteJa");
  const TRANSIT_DESTINATION_CODES=copyObj("rules.transit.destinationCodes");
  function tpeDestination(n){
    return TRANSIT_DESTINATIONS[n]||TRANSIT_DESTINATIONS["451"];
  }
  const DP_HKG_FLIGHTS=new Set([...TPE_DEPARTURE_FLIGHTS].filter(n=>tpeDestination(n).en==="Hong Kong"));
  const disruptedFlightOk=raw=>(S.status==="gate"?TPE_DEPARTURE_FLIGHTS:DP_HKG_FLIGHTS).has(normalizeFlight(raw));
  function callFlightOk(){
    const n=callFlightNumber();
    if(!n) return false;
    if(S.callMode==="transit") return transitCxOk(n);
    if(S.callMode==="join") return generalCxOk(n);
    return false;
  }

  // Flight-related inputs turn red only when the entered value can no longer satisfy its rule.
  function markInvalidFields(){
    const bad=(id,cond)=>{const el=$(id);if(el){const f=el.closest(".field");if(f)f.classList.toggle("bad",!!cond);}};
    const filled=id=>v(id)!=="";
    // While typing, keep a partial value neutral if it can still match an allowed flight.
    const typing=id=>document.activeElement===$(id);
    const canStillMatch=(raw,set)=>{const d=digits(raw);if(!d)return true;const n=String(Number(d));if(d.length>=3)return set.has(n);for(const x of set){if(x.startsWith(n))return true;}return false;};
    const listBad=(id,raw,set)=>filled(id)&&!set.has(String(Number(digits(raw))))&&(!typing(id)||!canStillMatch(raw,set));
    const codeBad=id=>filled(id)&&!isCarrier(v(id))&&!(typing(id)&&v(id).length<2);
    // Scenario 1 flight number follows the selected passenger-type rule.
    bad("mFlight",filled("mFlight")&&(!isFlt(v("mFlight"))||(S.missMode==="transit"&&listBad("mFlight",v("mFlight"),TRANSIT_FLIGHTS))||(S.missMode==="join"&&listBad("mFlight",v("mFlight"),GENERAL_CX_FLIGHTS))));
    bad("mSec",filled("mSec")&&(!isFlt(v("mSec"))||+v("mSec")>copy("rules.sec.max")));
    // Scenario 3 · Wrong Pick-up flight number
    bad("wFlight",filled("wFlight")&&!isFlt(v("wFlight")));
    // Scenario 4 · Disrupted Pax
    bad("dFlight",listBad("dFlight",v("dFlight"),S.status==="gate"?TPE_DEPARTURE_FLIGHTS:DP_HKG_FLIGHTS));
    bad("tN",codeBad("tA")||(filled("tN")&&!isFlt(v("tN")))||tpeDepartureBlocked(v("tA"),v("tN")));
    const altIsCx=String(v("altA")||"").toUpperCase()==="CX";
    bad("altN",codeBad("altA")||(filled("altN")&&!isFlt(v("altN")))||(altIsCx&&listBad("altN",v("altN"),DP_HKG_FLIGHTS))||sameProtectedCxFlight(v("altA"),v("altN"),v("dFlight")));
    ["delayTime","altTime","arriveTime","gDepTime"].forEach(id=>bad(id,timeState(id)==="bad"));
    bad("gNewN",listBad("gNewN",v("gNewN"),TPE_DEPARTURE_FLIGHTS)||sameProtectedCxFlight("CX",v("gNewN"),v("dFlight")));
    // Final Call flight number follows the selected passenger-type rule.
    const cn=callFlightNumber();
    bad("callFlight",!!cn&&((S.callMode==="transit"&&listBad("callFlight",cn,TRANSIT_FLIGHTS))||(S.callMode==="join"&&listBad("callFlight",cn,GENERAL_CX_FLIGHTS))));
  }

  const OK={
    phone:()=>{const p=normalizePhone(v("phoneInput"));return !!p&&!p.blocked;},
    mflight:()=>isFlt(v("mFlight"))&&(S.missMode==="transit"?transitCxOk(v("mFlight")):S.missMode==="join"?generalCxOk(v("mFlight")):true),
    msec:()=>isFlt(v("mSec"))&&+v("mSec")<=copy("rules.sec.max"),
    wflight:()=>isFlt(v("wFlight")),
    bag1:()=>isAir(v("b1a"))&&/^\d{6}$/.test(v("b1n")),
    bag2:()=>isAir(v("b2a"))&&/^\d{6}$/.test(v("b2n")),
    dflight:()=>isFlt(v("dFlight"))&&generalCxOk(v("dFlight"))&&(S.status!=="delayed"||timeOk("delayTime"))&&(S.status!=="gate"||S.gateStatus==="cancelled"||(S.gateStatus==="delayed"&&timeOk("delayTime")))&&disruptedFlightOk(v("dFlight")),
    dtransfer:()=>isCarrier(v("tA"))&&isFlt(v("tN"))&&!tpeDepartureBlocked(v("tA"),v("tN")),
    dstatus:()=>S.status==="possible"||S.status==="delayed"||S.status==="unknown"||S.status==="gate",
    dnew:()=>isFlt(v("gNewN"))&&protectFlightOk("CX",v("gNewN"),v("dFlight"))&&!!dnGateFull()&&timeOk("gDepTime"),
    dgateaction:()=> (S.gateTarget==="original"||S.gateTarget==="new")&&(S.gateGo==="asap"||S.gateGo==="wait"),
    darrange:()=>S.arrange==="unknown"||(S.arrange==="known"&&isCarrier(v("altA"))&&isFlt(v("altN"))&&protectFlightOk(v("altA"),v("altN"),v("dFlight"))&&timeOk("altTime")&&(v("altA")!=="CX"||disruptedFlightOk(v("altN")))),
    darrive:()=>timeOk("arriveTime"),
    callflight:()=>{
      const n=callFlightNumber();
      if(!n) return false;
      if(S.callMode==="transit") return transitCxOk(n);
      if(S.callMode==="join") return generalCxOk(n);
      return false;
    },
    callgate:()=>!!callGateFull(),
    preview:()=>firstInvalidStep(navPos)===-1
  };
  // Recheck visited prerequisites after edits made through browser history.
  function firstInvalidStep(targetPos){
    const p=normalizePhone(v("phoneInput"));
    if(!p||p.blocked||p.digits!==S.phone) return 0;
    for(let i=1;i<targetPos;i++){
      const id=stack[i];
      if(id!=="preview"&&OK[id]&&!OK[id]()) return i;
    }
    return -1;
  }
  // ==== [hints and validation messages] ====
  function bagHint(a,n){
    if(!isAir(v(a))) return copy("hint.airline.letters");
    const l=v(n).length; return l<6?(l?(6-l)+" more digits":copy("hint.bag.six")):"";
  }
  const HINT={
    phone:()=>{const n=digits(v("phoneInput"));if(!n||!phoneLibReady)return "";const p=normalizePhone(n);if(p&&p.blocked)return copy("error.phone.blocked");return !p?copy("hint.phone.invalid"):"";},
    mflight:()=>!isFlt(v("mFlight"))?copy("hint.flight.digits"):(S.missMode==="transit"&&!transitCxOk(v("mFlight"))?copy("hint.transit.cx"):(S.missMode==="join"&&!generalCxOk(v("mFlight"))?"":"")),
    msec:()=>{const x=v("mSec");return !x?copy("hint.sec.range"):(+x>copy("rules.sec.max")?copy("error.sec.max"):"");},
    wflight:()=>isFlt(v("wFlight"))?"":copy("hint.flight.digits"),
    bag1:()=>bagHint("b1a","b1n"),
    bag2:()=>bagHint("b2a","b2n"),
    dflight:()=>!isFlt(v("dFlight"))?copy("hint.flight.digits"):(!generalCxOk(v("dFlight"))?"":((S.status==="delayed"||(S.status==="gate"&&S.gateStatus==="delayed"))&&timeState("delayTime")==="bad"?copy("error.time.invalid"):"")),
    dtransfer:()=>!isCarrier(v("tA"))?copy("hint.airline.carrier"):(!isFlt(v("tN"))?copy("hint.flight.digits"):(tpeDepartureBlocked(v("tA"),v("tN"))?copy("error.flight.tpe"):"")),
    dstatus:()=>"",
    dnew:()=>{
      if(timeState("gDepTime")==="bad") return copy("error.time.invalid");
      if(sameProtectedCxFlight("CX",v("gNewN"),v("dFlight"))) return copy("error.protect.same");
      if(isFlt(v("gNewN"))&&!tpeDepartureCxOk(v("gNewN"))) return copy("error.protect.tpe");
      return "";
    },
    darrange:()=>{
      if(S.arrange!=="known") return "";
      if(!isCarrier(v("altA"))) return copy("hint.airline.carrier");
      if(!isFlt(v("altN"))) return copy("hint.flight.digits");
      if(sameProtectedCxFlight(v("altA"),v("altN"),v("dFlight"))) return copy("error.protect.same");
      if(String(v("altA")||"").toUpperCase()==="CX"&&!tpeDepartureCxOk(v("altN"))) return copy("error.protect.tpe");
      return timeHint("altTime");
    },
    darrive:()=>timeHint("arriveTime"),
    callflight:()=>{
      const n=callFlightNumber();
      if(!n) return copy("hint.flight.number");
      if(S.callMode==="transit"&&!transitCxOk(n)) return copy("hint.transit.cx");
      if(S.callMode==="join"&&!generalCxOk(n)) return "";
      return "";
    },
    callgate:()=>"",
    preview:()=>copy("hint.preview.check")
  };
  const NEXT={
    phone:()=>{const p=normalizePhone(v("phoneInput"));if(!p||p.blocked)return;if(S.phone&&p.digits!==S.phone)clearCaseData();S.phone=p.digits;S.country=p.country||"";go("scenario");},
    mflight:()=>{normalizeFlightField("mFlight");go("msec");}, msec:()=>go("preview"),
    wflight:()=>{normalizeFlightField("wFlight");go("bag1");}, bag1:()=>go("bag2"), bag2:()=>go("preview"),
    dflight:()=>{normalizeFlightField("dFlight");if(S.status==="gate")go("dnew");else go("dtransfer");}, dtransfer:()=>{normalizeFlightField("tN");go("darrange");},
    darrange:()=>{if(S.arrange==="known")normalizeFlightField("altN");go("darrive");}, darrive:()=>go("preview"),
    dnew:()=>{normalizeFlightField("gNewN");go("dgateaction");},
    dgateaction:()=>go("preview"),
    callflight:()=>{const n=callFlightNumber();if(n)$("callFlight").value=n;go("callgate");},
    callgate:()=>go("preview"),
    preview:()=>send()
  };

  // ---- messages ----------------------------------------------------------
  function dateCode(){
    try{
      const parts=new Intl.DateTimeFormat("en-GB",{timeZone:"Asia/Taipei",day:"2-digit",month:"short"}).formatToParts(new Date());
      const day=(parts.find(x=>x.type==="day")||{}).value||"";
      const month=(parts.find(x=>x.type==="month")||{}).value||"";
      if(day&&month) return day+month;
    }catch(e){}
    const d=new Date(Date.now()+8*60*60*1000);
    return String(d.getUTCDate()).padStart(2,"0")+["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][d.getUTCMonth()];
  }
  // ==== [message generation] ====
  function fillCopy(id, values){
    let out=String(copy(id)||"");
    Object.keys(values||{}).forEach(k=>{out=out.split("{"+k+"}").join(String(values[k]));});
    return out;
  }
  function bilingual(zh,en,zhFirst){ return zhFirst?zh+"\n\n"+en:en+"\n\n"+zh; }
  function textMiss(zhFirst){
    const flight=String(Number(v("mFlight"))), tag=flight+"/"+String(Number(v("mSec"))).padStart(3,"0");
    if(S.order==="ja") return copy("s1.join.ja");
    const zh=fillCopy("s1.join.zh",{flight_number:flight});
    const en=fillCopy("s1.join.en",{flight_number:flight});
    return bilingual(zh,en,zhFirst)+"\n\n"+tag;
  }
  function textMissTransit(zhFirst){
    if(S.order==="ja") return copy("s1.transit.ja");
    return bilingual(copy("s1.transit.zh"),copy("s1.transit.en"),zhFirst);
  }
  function textWpp(zhFirst){
    const vals={"Arrival Flight":"CX"+v("wFlight"),"Bag Tag 1":v("b1a")+v("b1n"),"Bag Tag 2":v("b2a")+v("b2n")};
    return bilingual(fillCopy("s3.zh",vals),fillCopy("s3.en",vals),zhFirst);
  }
  function textDp(zhFirst){
    const f="CX"+v("dFlight"), tf=v("tA")+v("tN"), alt=v("altA")+v("altN");
    if(S.status==="gate"){
      const n=normalizeFlight(v("gNewN")), nf="CX"+n, dest=tpeDestination(n);
      const st=S.gateStatus==="delayed"?"delayed":"cancelled";
      const target=S.gateTarget==="new"?"new":"original";
      const go=S.gateGo==="wait"?"wait":"asap";
      const vals={"Disrupted Flight":f,"Delay Time":v("delayTime"),"New Flight":nf,"Gate":dnGateFull(),"Dep Time":v("gDepTime"),"DestinationZh":dest.zh,"DestinationEn":dest.en};
      const zh=fillCopy("s4.zh.gate."+st+"."+target+"."+go,vals);
      const en=fillCopy("s4.en.gate."+st+"."+target+"."+go,vals);
      return bilingual(zh,en,zhFirst);
    }
    const status=S.status==="delayed"?"delayed":S.status==="unknown"?"unknown":"possible";
    const arrange=S.arrange==="known"?"known":"airport";
    const vals={"Disrupted Flight":f,"Connecting Flight":tf,"Delay Time":v("delayTime"),"Alternative Flight":alt,"Alternative Departure Time":v("altTime"),"Arrive Airport Before":v("arriveTime")};
    return bilingual(fillCopy("s4.zh."+status+"."+arrange,vals),fillCopy("s4.en."+status+"."+arrange,vals),zhFirst);
  }
  function taipeiTime(){
    try{
      return new Intl.DateTimeFormat("en-GB",{timeZone:"Asia/Taipei",hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).format(new Date());
    }catch(e){
      const d=new Date(Date.now()+8*60*60*1000);
      return String(d.getUTCHours()).padStart(2,"0")+":"+String(d.getUTCMinutes()).padStart(2,"0");
    }
  }
  function textJoin(zhFirst){
    const flight=callFlightFull(), gate=callGateFull(), dest=tpeDestination(callFlightNumber());
    const vals={Flight:flight,Gate:gate,DestinationZh:dest.zh,DestinationEn:dest.en};
    if(S.order==="ja") return fillCopy("s2.join.ja",vals);
    return bilingual(fillCopy("s2.join.zh",vals),fillCopy("s2.join.en",vals),zhFirst);
  }
  function textTransit(zhFirst){
    const n=callFlightNumber(), flight=callFlightFull(), gate=callGateFull(), dest=TRANSIT_DESTINATIONS[n]||{zh:"",en:"",ja:""};
    const route=TRANSIT_SMS_ROUTE_JA[n]||{from:"",to:dest.ja};
    const vals={Flight:flight,Gate:gate,DestinationZh:dest.zh,DestinationEn:dest.en,OriginJa:route.from,DestinationJaShort:route.to,TaipeiTime:taipeiTime()};
    if(S.order==="ja") return fillCopy("s2.transit.ja",vals);
    return bilingual(fillCopy("s2.transit.zh",vals),fillCopy("s2.transit.en",vals),zhFirst);
  }
  function textCall(zhFirst){ return S.callMode==="transit"?textTransit(zhFirst):textJoin(zhFirst); }
  function buildText(){
    const zf=S.order==="zh";
    return flow==="miss"?(S.missMode==="transit"?textMissTransit(zf):textMiss(zf)):flow==="call"?textCall(zf):flow==="wpp"?textWpp(zf):textDp(zf);
  }
  function buildRows(){
    // The passenger number stays in the header, including Confirm details.
    const rows=[];
    if(flow==="call"){
      if(S.callNoMessage){
        rows.push(["Phone Number",(S.country?flagFor(S.country)+" ":"")+groupedPhone(S.phone)]);
      }else{
        rows.push(["Flight",callFlightFull()]);
        if(S.callMode==="transit"){const origin=transitOriginIata(callFlightNumber());if(origin)rows.push(["Dep from",origin]);}
        {const code=TRANSIT_DESTINATION_CODES[callFlightNumber()];if(code)rows.push(["Destination",code]);}
        rows.push(["Go to Gate",callGateFull()]);
      }
    }else if(flow==="miss"){
      rows.push(["Flight","CX"+String(Number(v("mFlight")))],["Sec",(secPrefix(v("mFlight"),S.missMode)||"")+" "+String(Number(v("mSec"))).padStart(3,"0")]);if(S.missMode==="transit"){const origin=transitOriginIata(v("mFlight"));if(origin)rows.push(["Dep from",origin]);const code=TRANSIT_DESTINATION_CODES[normalizeFlight(v("mFlight"))];if(code)rows.push(["Destination",code]);}
    }else if(flow==="wpp"){
      rows.push(["Arrival Flight","CX"+v("wFlight")],["Bag Tag 1",v("b1a")+v("b1n"),null,"unclaimed"],["Bag Tag 2",v("b2a")+v("b2n")]);
    }else if(flow==="dp"&&S.status==="gate"){
      rows.push(["Disrupted flight","CX"+v("dFlight")]);
      rows.push(["Protect to","CX"+v("gNewN")+" / dep "+v("gDepTime")],["Proceed to Gate",S.gateTarget==="original"?"CX"+v("dFlight"):"CX"+v("gNewN")+" / "+dnGateFull()]);
    }else if(flow==="dp"){
      rows.push(["Disrupted flight","CX"+v("dFlight")],["Connecting flight",v("tA")+v("tN")]);
      rows.push(["Arrangement",S.arrange==="known" ? "Protect to "+v("altA")+v("altN")+" / dep "+v("altTime") : "Arrange in airport"]);
      rows.push(["Arrive airport before",v("arriveTime")]);
    }
    return rows;
  }

  // ==== [message draft state] ====
  // Edits are kept per language so switching order never throws work away,
  // and the whole draft is dropped as soon as any underlying field changes.
  const edits={};
  let msgSig=null;
  function sig(){
    return [flow,S.phone,S.status,S.arrange,
      v("mFlight"),v("mSec"),v("wFlight"),v("b1a"),v("b1n"),v("b2a"),v("b2n"),
      v("dFlight"),v("tA"),v("tN"),v("delayTime"),v("altA"),v("altN"),v("altTime"),v("arriveTime"),
      v("callFlight"),v("callGateZone"),v("callGate"),S.callNoMessage,S.callMode,S.missMode,
      S.gateStatus,S.gateGo,S.gateTarget,v("gNewN"),v("gGateZone"),v("gGate"),v("gDepTime")
    ].join("\u241F");
  }
  function clearDrafts(){ delete edits.zh; delete edits.en; delete edits.ja; msgSig=null; }
  function syncDrafts(){
    const s=sig();
    if(s!==msgSig){ msgSig=s; delete edits.zh; delete edits.en; delete edits.ja; }
  }
  function currentText(){
    const t=edits[S.order];
    return (typeof t==="string")?t:buildText();
  }

  // ---- WhatsApp ----------------------------------------------------------
  function openWA(text){
    const encoded=text?encodeURIComponent(text):"";
    const appUrl="whatsapp://send?phone="+encodeURIComponent(S.phone)+(encoded?"&text="+encoded:"");
    const webUrl="https://wa.me/"+S.phone+(encoded?"?text="+encoded:"");

    // Prefer WhatsApp's custom URL scheme so Android does not depend on the
    // phone's per-app "open supported links" setting. If no app handles the
    // scheme, fall back to wa.me after a short delay. Cancel the fallback as
    // soon as the page is hidden because that means WhatsApp was launched.
    let fallbackTimer=null;
    let appLaunched=false;

    const cleanup=()=>{
      if(fallbackTimer!==null){ clearTimeout(fallbackTimer); fallbackTimer=null; }
      document.removeEventListener("visibilitychange",onVisibilityChange);
      window.removeEventListener("pagehide",onPageHide);
    };
    const onVisibilityChange=()=>{
      if(document.hidden){ appLaunched=true; cleanup(); }
    };
    const onPageHide=()=>{ appLaunched=true; cleanup(); };

    document.addEventListener("visibilitychange",onVisibilityChange);
    window.addEventListener("pagehide",onPageHide,{once:true});

    fallbackTimer=setTimeout(()=>{
      cleanup();
      if(!appLaunched&&!document.hidden) window.location.href=webUrl;
    },2500);

    try{
      window.location.href=appUrl;
    }catch(e){
      cleanup();
      window.location.href=webUrl;
    }
  }
  function send(){
    if((flow==="miss" || (flow==="call"&&(S.callMode==="join"||S.callMode==="transit")))&&S.order==="ja"){ sendSMS(); return; }
    if(flow==="call"&&S.callNoMessage){openWA("");return;}
    syncDrafts();
    openWA(currentText());
  }

  // Japanese SMS mode: Scenario 1, Scenario 2 Join Pax, and Scenario 2 Transit Pax.
  function sendSMS(){
    if(!(flow==="miss" || (flow==="call"&&(S.callMode==="join"||S.callMode==="transit")))) return;
    syncDrafts();
    const recipient="+"+S.phone;
    const encoded=encodeURIComponent(currentText());
    const ua=navigator.userAgent||"";
    const isiOS=/iPad|iPhone|iPod/.test(ua)||(navigator.platform==="MacIntel"&&navigator.maxTouchPoints>1);
    // iOS expects &body= after the recipient; Android uses ?body=.
    window.location.href="sms:"+recipient+(isiOS?"&":"?")+"body="+encoded;
  }

  // ---- navigation --------------------------------------------------------
  function closePreviewEditor(){
    const m=$("msg"), panel=$("msgPanel");
    if(!m) return;
    if(document.activeElement===m) m.blur();
    if(panel) panel.hidden=true;
    m.readOnly=true;
    $("viewLabel").textContent=copy("label.view.closed");
    $("msgToggle").setAttribute("aria-expanded","false");
    $("s-preview").classList.remove("preview-focus");
  }
  function showScreen(id){
    if(id!=="preview") closePreviewEditor();
    // Back/Forward restores the flow that owns the screen and its progress title.
    if(id==="misstype") flow="miss";
    else if(id==="calltype") flow="call";
    else if(id==="preview"&&S.missMode==="direct"&&S.callNoMessage) flow="call";
    cur=id;
    document.querySelectorAll(".screen").forEach(s=>s.hidden=true);
    $("s-"+id).hidden=false;
    render();
    $("main").scrollTop=0;
  }
  function focusFirst(id){
    const inp=$("s-"+id).querySelector("input:not(.code)");
    if(inp&&inp.offsetParent!==null){try{inp.focus({preventScroll:true});}catch(e){inp.focus();}}
  }
  function go(id){
    if(navPos<stack.length-1) stack.splice(navPos+1);
    stack.push(id);
    navPos=stack.length-1;
    try{history.pushState({findPax:true,pos:navPos,id},"");}catch(e){}
    showScreen(id);
    focusFirst(id);
  }
  let backPending=false;
  window.addEventListener("popstate",e=>{
    backPending=false;
    if(resetting){resetting=false;return;}
    const st=e.state;
    if(st&&st.findPax&&Number.isInteger(st.pos)&&st.pos>=0&&st.pos<stack.length&&stack[st.pos]===st.id){
      if(st.pos>navPos){
        const invalid=firstInvalidStep(st.pos);
        if(invalid!==-1){
          navPos=invalid;
          showScreen(stack[invalid]);
          history.go(invalid-st.pos);
          return;
        }
      }
      navPos=st.pos;
      showScreen(st.id);
    }
  });
  $("back").onclick=()=>{
    if(navPos<=0||backPending) return;
    backPending=true;
    try{history.back();}
    catch(e){
      backPending=false;
      navPos--;
      showScreen(stack[navPos]);
    }
  };

  function clearInvalidMarks(ids){ids.forEach(id=>{const el=$(id);if(!el)return;const f=el.closest(".field");if(f)f.classList.remove("bad");});}
  function clearMissCase(){
    ["mFlight","mSec"].forEach(id=>$(id).value="");
    clearInvalidMarks(["mFlight","mSec"]);
    S.missMode="";
    clearDrafts();
  }
  function clearCallCase(){
    ["callFlight","callGate"].forEach(id=>$(id).value="");
    clearInvalidMarks(["callFlight","callGate"]);
    $("callGateZone").value="B";
    S.callMode="";S.callNoMessage=false;
    clearDrafts();
  }
  function clearWppCase(){
    ["wFlight","b1n","b2n"].forEach(id=>$(id).value="");
    clearInvalidMarks(["wFlight","b1a","b1n","b2a","b2n"]);
    ["b1a","b2a"].forEach(id=>$(id).value="CX");
    clearDrafts();
  }
  function clearDpGateFields(){
    ["gNewN","gGate","gDepTime"].forEach(id=>$(id).value="");
    clearInvalidMarks(["gNewN","gGate","gDepTime"]);
    $("gGateZone").value="B";
    S.gateStatus="";S.gateGo="";S.gateTarget="";
  }
  function clearDpCase(){
    ["dFlight","tN","delayTime","altN","altTime","arriveTime"].forEach(id=>$(id).value="");
    clearInvalidMarks(["dFlight","tA","tN","delayTime","altA","altN","altTime","arriveTime"]);
    ["tA","altA"].forEach(id=>$(id).value="CX");
    S.status="";S.arrange="";
    clearDpGateFields();
    clearDrafts();
  }
  function clearMissForModeChange(nextMode){
    if(S.missMode && S.missMode!==nextMode){
      ["mFlight","mSec"].forEach(id=>$(id).value="");
      clearDrafts();
    }
  }
  function clearCallForModeChange(nextMode){
    if(S.callMode && S.callMode!==nextMode){
      ["callFlight","callGate"].forEach(id=>$(id).value="");
      $("callGateZone").value="B";
      clearDrafts();
    }
  }

  function clearCaseData(){
    clearMissCase();
    clearCallCase();
    clearWppCase();
    clearDpCase();
    S.order="zh";S.orderSet=false;flow="";
    clearDrafts();
    const m=$("msg");
    m.value="";m.readOnly=true;delete m.dataset.edited;
    $("msgPanel").hidden=true;
    $("viewLabel").textContent=copy("label.view.closed");
    $("msgToggle").setAttribute("aria-expanded","false");
    $("s-preview").classList.remove("preview-focus");
  }
  function clearFields(){
    $("phoneInput").value="";
    clearCaseData();
    S.phone="";S.country="";
    $("badge").hidden=true;
    $("warn").classList.remove("show");
    $("phoneField").classList.remove("bad");
  }
  function resetAll(){
    clearFields();
    const depth=navPos;
    stack.length=0;stack.push("phone");navPos=0;
    if(depth>0){resetting=true;setTimeout(()=>{resetting=false;},1200);try{history.go(-depth);}catch(e){resetting=false;}}
    showScreen("phone");
  }

  // ==== [render] ====
  function render(){
    $("app").classList.toggle("phoneHome",cur==="phone");
    const directPreview=cur==="preview"&&flow==="call"&&S.callNoMessage;
    const hasWho=cur!=="phone"&&cur!=="calltype"&&cur!=="misstype"&&cur!=="dstatus"&&!directPreview&&S.phone;
    $("back").hidden=cur==="phone";
    $("who").hidden=!hasWho;
    if(hasWho){
      $("whoFlag").textContent=S.country?flagFor(S.country):"";
      $("whoNum").textContent=groupedPhone(S.phone);
    }
    const f=flow&&(flow==="dp"&&S.status==="gate"&&cur!=="dstatus"?DP_BRANCH_FLOWS.dpgate:FLOWS[flow]), rawIdx=f?f.steps.indexOf(cur):-1;
    // Scenario 1 counts Passenger Type as step 1/3. Its read-only preview is the
    // completed result of step 3, so keep 3/3 visible there.
    const missCompletedPreview=flow==="miss"&&cur==="preview"&&(S.missMode==="join"||S.missMode==="transit");
    const idx=missCompletedPreview?f.steps.length-1:rawIdx;
    const directProgress=directPreview;
    $("bar").hidden=idx<0&&!directProgress;
    function renderProgressTitle(label,count){
      replaceChildrenCompat($("step"),
        Object.assign(document.createElement("span"),{className:"progressLabel",textContent:label}),
        document.createTextNode(" "),
        Object.assign(document.createElement("span"),{className:"progressCount",textContent:count})
      );
    }
    if(directProgress){
      $("barFill").style.width="100%";
      const directName=S.missMode==="direct"?copy("progress.flow.miss"):(S.callMode==="direct"?copy("progress.flow.direct"):copy("progress.flow.call"));
      renderProgressTitle(directName,"1/1");
    }else if(idx>=0){
      $("barFill").style.width=((idx+1)/f.steps.length*100)+"%";
      const progressText=(idx+1)+"/"+f.steps.length;
      const passengerType=flow==="miss" && cur!=="misstype" && (S.missMode==="join"||S.missMode==="transit")
        ? (S.missMode==="join"?copy("s.passenger.joining"):copy("s.passenger.transit"))
        : flow==="call" && cur!=="calltype" && (S.callMode==="join"||S.callMode==="transit")
          ? (S.callMode==="join"?copy("s.passenger.joining"):copy("s.passenger.transit")) : "";
      const disruptedType=flow==="dp" && cur!=="dstatus"
        ? (S.status==="possible"?copy("progress.dp.possible"):S.status==="delayed"?copy("progress.dp.delayed"):S.status==="unknown"?copy("progress.dp.unknown"):S.status==="gate"?copy("progress.dp.gate"):"") : "";
      if((flow==="miss"||flow==="call")&&passengerType){
        renderProgressTitle(f.name+" - "+passengerType,progressText);
      }else if(flow==="dp"&&disruptedType){
        renderProgressTitle(f.name+" - "+disruptedType,progressText);
      }else{
        renderProgressTitle(f.name,progressText);
      }
    }else $("step").textContent="";

    // status / arrange option state
    if(cur==="msec"){$("mSecPrefix").textContent=secPrefix(v("mFlight"),S.missMode)||"—";}
    if(cur==="dstatus"){
      $("stPossible").setAttribute("aria-pressed",S.status==="possible");
      $("stDelayed").setAttribute("aria-pressed",S.status==="delayed");
      $("stUnknown").setAttribute("aria-pressed",S.status==="unknown");
      $("stGate").setAttribute("aria-pressed",S.status==="gate");
    }
    if(cur==="dflight"){
      $("gStatusWrap").hidden=S.status!=="gate";
      $("gsDelayed").setAttribute("aria-pressed",S.status==="gate"&&S.gateStatus==="delayed");
      $("gsCancelled").setAttribute("aria-pressed",S.status==="gate"&&S.gateStatus==="cancelled");
      const gateDelay=S.status==="gate", delayOpen=gateDelay&&S.gateStatus==="delayed";
      $("delayWrap").classList.toggle("gateDelay",gateDelay);
      $("delayWrap").hidden=!gateDelay&&S.status!=="delayed";
      $("delayWrap").classList.toggle("gateDelayOpen",delayOpen);
    }
    [["callGateR","callGate","callGateZone"],["gGateR","gGate","gGateZone"]].forEach(([bid,iid,zid])=>{
      const g=v(iid), on=g==="1R";
      $(bid).hidden=v(zid)!=="B"||!/^1R?$/.test(g);
      $(bid).setAttribute("aria-pressed",on);
      $(bid).textContent=on?"B1R":"B1R?";
      $(bid).setAttribute("aria-label",on?"Gate B1R selected, tap to change back to B1":"Change gate to B1R");
    });
    if(cur==="dnew"||cur==="dgateaction"){
      $("gOriginalFlight").textContent="CX"+(normalizeFlight(v("dFlight"))||"—");
      $("gProtectedFlight").textContent="CX"+(normalizeFlight(v("gNewN"))||"—");
      $("gOriginalFlight").setAttribute("aria-pressed",S.gateTarget==="original");
      $("gProtectedFlight").setAttribute("aria-pressed",S.gateTarget==="new");
      $("gpAsap").setAttribute("aria-pressed",S.gateGo==="asap");
      $("gpWait").setAttribute("aria-pressed",S.gateGo==="wait");
    }
    if(cur==="darrange"){
      $("arKnown").setAttribute("aria-pressed",S.arrange==="known");
      $("arUnknown").setAttribute("aria-pressed",S.arrange==="unknown");
      $("altWrap").hidden=S.arrange!=="known";
    }
    if(cur==="preview"){
      const sum=$("sum");sum.textContent="";
      const rows=buildRows();
      sum.hidden=rows.length===0;
      rows.forEach(r=>{
        const d=document.createElement("div"),t=document.createElement("dt"),dd=document.createElement("dd");
        t.textContent=r[0];
        if(r[2]){const sub=document.createElement("small");sub.textContent=r[2];sub.lang="zh-Hant";t.appendChild(sub);}
        if(flow==="dp" && r[0]==="Arrangement" && S.arrange==="known"){
          const flight=v("altA")+v("altN"), parts=r[1].split(flight);
          dd.appendChild(document.createTextNode(parts[0]||""));
          const a=document.createElement("span");a.className="flightAccent";a.textContent=flight;dd.appendChild(a);
          dd.appendChild(document.createTextNode(parts[1]||""));
        }else if(flow==="wpp" && r[3]==="unclaimed"){
          dd.classList.add("bagConfirmValue");
          const note=document.createElement("span");note.className="bagConfirmNote";note.lang="zh-Hant";note.textContent=copy("label.bag.unclaimed");dd.appendChild(note);
          const value=document.createElement("span");value.textContent=r[1];dd.appendChild(value);
        }else dd.textContent=r[1];
        d.appendChild(t);d.appendChild(dd);sum.appendChild(d);
      });
      const callOnly=flow==="call"&&S.callNoMessage;
      $("previewLangTitle").hidden=callOnly;
      $("previewLangSeg").hidden=callOnly;
      $("msgToggle").hidden=callOnly;
      if(callOnly){
        $("msgPanel").hidden=true;
        $("msg").readOnly=true;
        $("s-preview").classList.remove("preview-focus");
      }else{
        // Japanese is available for the supported Scenario 1 and Scenario 2 message paths.
        const scenario2Ja=flow==="call"&&(S.callMode==="join"||S.callMode==="transit");
        const japanesePath=flow==="miss"||scenario2Ja;
        $("ordJa").hidden=!japanesePath;
        $("ordJa").disabled=false;
        $("ordJa").title="";
        $("previewLangTitle").textContent=copy("label.preview.language");
        $("ordEn").style.order=flow==="dp"?"-1":"";
        if(S.order==="ja"&&!japanesePath){ S.order=flow==="dp"?"en":"zh"; S.orderSet=false; }
        if(!S.orderSet) S.order=flow==="dp"?"en":"zh";
        $("ordZh").setAttribute("aria-pressed",S.order==="zh");
        $("ordEn").setAttribute("aria-pressed",S.order==="en");
        $("ordJa").setAttribute("aria-pressed",S.order==="ja");
        syncDrafts();
        $("msg").value=currentText();
        $("msg").lang=S.order==="ja"?"ja":(S.order==="zh"?"zh-Hant":"en");
        $("previewOrderLabel").textContent=S.order==="ja"?copy("label.preview.jaOnly"):(S.order==="en"?copy("label.preview.enFirst"):copy("label.preview.zhFirst"));
        const previewOpen=!$("msgPanel").hidden;
        $("msgToggle").setAttribute("aria-expanded",previewOpen);
        $("viewLabel").textContent=previewOpen?copy("label.view.open"):copy("label.view.closed");
        $("s-preview").classList.toggle("preview-focus",previewOpen);
        $("msg").readOnly=true;
      }
    }

    markInvalidFields();
    const showFoot=cur!=="scenario"&&cur!=="calltype"&&cur!=="misstype"&&cur!=="dstatus";
    $("foot").hidden=!showFoot;
    const ok=OK[cur]?OK[cur]():false;
    const hint=$("hint");
    // Keep validation warnings visible in the footer.
    const text=HINT[cur]?HINT[cur]():"";
    hint.textContent=text;
    hint.style.display=cur==="preview"?"none":"";
    hint.classList.toggle("bad",["error.time.invalid","error.sec.max","error.phone.blocked","error.flight.tpe","error.protect.tpe","error.protect.same"].some(id=>text===copy(id)));
    const cta=$("cta");
    const callOnly=cur==="preview"&&flow==="call"&&S.callNoMessage;
    $("main").classList.toggle("preview-open",cur==="preview"&&!$("msgPanel").hidden);
    cta.disabled=!ok;
    const japaneseSMS=cur==="preview"&&(flow==="miss"||(flow==="call"&&(S.callMode==="join"||S.callMode==="transit")))&&S.order==="ja";
    cta.textContent=cur==="preview"
      ?(japaneseSMS?copy("cta.sms.ja"):(flow==="call"?(S.callNoMessage?copy("cta.whatsapp.call"):copy("cta.whatsapp.send")):copy("cta.whatsapp.send")))
      :copy("cta.next");
    cta.lang=japaneseSMS?"ja":"en";
  }
  $("cta").onclick=function(){ if(!this.disabled&&NEXT[cur]) NEXT[cur](); };

  // ==== [event wiring] ====
  $("phoneInput").addEventListener("input",function(){
    this.value=digits(this.value).slice(0,18);
    const p=normalizePhone(this.value), early=p?null:detectCountryEarly(this.value), b=$("badge");
    const cc=(p&&p.country)||(early&&early.country)||"";
    b.hidden=!cc;
    if(cc) b.textContent=phoneLabel(cc);
    const bl=!!(p&&p.blocked);
    $("warn").classList.toggle("show",bl);
    $("phoneField").classList.toggle("bad",bl);
    render();
  });
  const numInputs={mFlight:3,mSec:3,wFlight:3,b1n:6,b2n:6,dFlight:3,tN:3,altN:3,gNewN:3};
  Object.keys(numInputs).forEach(id=>$(id).addEventListener("input",function(){
    this.value=digits(this.value).slice(0,numInputs[id]);
    render();
    if(id==="dFlight" && S.status==="delayed" && this.value.length===3 && generalCxOk(this.value)){
      requestAnimationFrame(()=>{try{$("delayTime").focus();}catch(e){}});
    }
  }));
  ["mFlight","wFlight","dFlight","tN","altN","gNewN"].forEach(id=>$(id).addEventListener("blur",function(){normalizeFlightField(id);render();}));
  ["b1a","b2a"].forEach(id=>$(id).addEventListener("input",function(){this.value=this.value.replace(/[^A-Za-z]/g,"").toUpperCase().slice(0,2);render();}));
  ["tA","altA"].forEach(id=>$(id).addEventListener("input",function(){this.value=this.value.replace(/[^A-Za-z0-9]/g,"").toUpperCase().slice(0,2);render();}));
  ["delayTime","altTime","arriveTime","gDepTime"].forEach(id=>{
    const el=$(id);
    el.addEventListener("input",function(){fmtTime(this);render();});
    el.addEventListener("focus",function(){if(this.select)this.select();});
  });

  $("callFlight").addEventListener("input",function(){this.value=digits(this.value).slice(0,3);render();});
  $("callFlight").addEventListener("blur",function(){const n=callFlightNumber();if(n)this.value=n;render();});
  [["callGateR","callGate","callGateZone"],["gGateR","gGate","gGateZone"]].forEach(([bid,iid,zid])=>{
    const normalize=()=>{
      const el=$(iid);
      el.value=normalizeCallGate(el.value);
      if(v(zid)==="C"&&el.value==="1R") el.value="1";
      render();
    };
    $(iid).addEventListener("input",normalize);
    $(iid).addEventListener("blur",normalize);
    $(zid).addEventListener("change",normalize);
    // Keep the numeric keyboard open while toggling the B1R suggestion.
    $(bid).addEventListener("pointerdown",e=>e.preventDefault());
    $(bid).onclick=()=>{
      if(v(zid)!=="B"||!/^1R?$/.test(v(iid))) return;
      $(iid).value=v(iid)==="1R"?"1":"1R";
      render();
    };
  });
  $("goMiss").onclick=()=>{clearMissCase();flow="miss";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("misstype");};
  $("missJoin").onclick=()=>{clearMissForModeChange("join");flow="miss";S.missMode="join";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("mflight");};
  $("missTransit").onclick=()=>{clearMissForModeChange("transit");flow="miss";S.missMode="transit";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("mflight");};
  $("goCall").onclick=()=>{clearCallCase();flow="call";S.order="zh";S.orderSet=false;go("calltype");};
  $("callJoin").onclick=()=>{clearCallForModeChange("join");S.callMode="join";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("callflight");};
  $("callTransit").onclick=()=>{clearCallForModeChange("transit");S.callMode="transit";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("callflight");};
  $("goDirect").onclick=()=>{clearCallCase();flow="call";S.missMode="";S.callMode="direct";S.callNoMessage=true;S.order="zh";S.orderSet=false;clearDrafts();go("preview");};
  $("goWpp").onclick=()=>{clearWppCase();flow="wpp";S.order="zh";S.orderSet=false;go("wflight");};
  $("goDp").onclick=()=>{clearDpCase();flow="dp";S.order="en";S.orderSet=false;go("dstatus");};

  function selectDpFlightType(nextStatus){
    if(S.status&&S.status!==nextStatus) $("delayTime").value="";
    if(S.status==="gate"&&nextStatus!=="gate") clearDpGateFields();
    S.status=nextStatus;
    go("dflight");
  }
  $("stPossible").onclick=()=>selectDpFlightType("possible");
  $("stUnknown").onclick=()=>selectDpFlightType("unknown");
  $("stDelayed").onclick=()=>selectDpFlightType("delayed");
  $("stGate").onclick=()=>selectDpFlightType("gate");
  $("gsDelayed").onclick=()=>{S.gateStatus="delayed";render();try{$("delayTime").focus();}catch(e){}};
  $("gOriginalFlight").onclick=()=>{S.gateTarget="original";render();};
  $("gProtectedFlight").onclick=()=>{S.gateTarget="new";render();};
  $("gpAsap").onclick=()=>{S.gateGo="asap";render();};
  $("gpWait").onclick=()=>{S.gateGo="wait";render();};
  $("gsCancelled").onclick=()=>{S.gateStatus="cancelled";$("delayTime").value="";render();};
  (function fitStepTitle(){
    const el=$("step"); if(!el) return;
    let busy=false;
    const fit=()=>{
      if(busy) return; busy=true;
      el.style.fontSize="";
      if(el.textContent && el.clientWidth>0){
        let fs=parseFloat(getComputedStyle(el).fontSize)||20;
        while(el.scrollWidth>el.clientWidth+0.5 && fs>13){fs-=0.5;el.style.fontSize=fs+"px";}
      }
      busy=false;
    };
    try{new MutationObserver(fit).observe(el,{childList:true,characterData:true,subtree:true});}catch(e){}
    window.addEventListener("resize",fit,{passive:true});
    if(window.visualViewport) window.visualViewport.addEventListener("resize",fit,{passive:true});
    if(document.fonts&&document.fonts.ready) document.fonts.ready.then(fit);
    fit();
  })();
  document.addEventListener("focusout",e=>{if(e.target&&e.target.tagName==="INPUT")setTimeout(()=>{if(!document.activeElement||document.activeElement.tagName!=="INPUT"||document.activeElement!==e.target)render();},0);});
  $("arUnknown").onclick=()=>{S.arrange="unknown";render();};
  $("arKnown").onclick=()=>{S.arrange="known";render();try{$("altN").focus();}catch(e){}};

  function setOrder(o){S.order=o;S.orderSet=true;syncDrafts();$("msg").value=currentText();render();}
  $("ordZh").onclick=()=>setOrder("zh");
  $("ordEn").onclick=()=>setOrder("en");
  $("ordJa").onclick=()=>{ if(flow==="miss" || (flow==="call"&&(S.callMode==="join"||S.callMode==="transit"))) setOrder("ja"); };
  $("msgToggle").onclick=()=>{
    if(flow==="call"&&S.callNoMessage) return;
    const m=$("msg"), panel=$("msgPanel"), open=panel.hidden;
    panel.hidden=!open;
    $("msgToggle").setAttribute("aria-expanded",open);
    $("viewLabel").textContent=open?"View ▴":"View ▾";
    if(open){syncDrafts();m.value=currentText();m.readOnly=true;}
    else {closePreviewEditor();}
    $("s-preview").classList.toggle("preview-focus",open);
    render();
    if(open) $("main").scrollTop=0;
  };


  document.addEventListener("keydown",e=>{
    if(e.key==="Enter"&&e.target&&e.target.tagName==="INPUT"&&!$("cta").disabled&&!$("foot").hidden){e.preventDefault();$("cta").click();}
  });

  // reduce browser autofill / keyboard suggestions
  document.querySelectorAll("input").forEach(el=>{
    el.setAttribute("autocomplete","off");
    el.setAttribute("autocorrect","off");
    el.setAttribute("autocapitalize","off");
    el.setAttribute("spellcheck","false");
  });

  // iOS + Android keyboard avoidance. Use the visual viewport rather than the
  // layout viewport, keep the CTA in the visible area, and scroll only the
  // active control into the space above the CTA.
  const vv=window.visualViewport;
  if(vv){
    let vvFrame=0, settleTimer=0;
    // Keyboard = an editable field is focused AND the visible height dropped well below its resting height.
    // Works whether the browser shrinks only the visual viewport (iOS, Chrome) or resizes the whole
    // layout viewport (many in-app WebViews such as LINE on Android).
    let base=Math.max(window.innerHeight,vv.height), baseW=window.innerWidth;
    const editing=()=>{const a=document.activeElement;return !!a&&(a.tagName==="INPUT"||a.tagName==="TEXTAREA");};
    const keyboardOpen=()=>{
      if(window.innerWidth!==baseW){baseW=window.innerWidth;base=Math.max(window.innerHeight,vv.height);}
      base=Math.max(base,window.innerHeight,vv.height);
      return vv.scale<1.05&&editing()&&base-vv.height>120;
    };
    const revealWorkspace=()=>{
      const el=document.activeElement;
      if(!keyboardOpen()||!el||!["INPUT","TEXTAREA"].includes(el.tagName)) return;
      const main=$("main"), foot=$("foot");
      if(!main||!foot||foot.hidden) return;
      const screen=el.closest(".screen");
      const mr=main.getBoundingClientRect(), fr=foot.getBoundingClientRect();
      const top=mr.top+6, bottom=Math.min(mr.bottom,fr.top)-6, available=bottom-top;
      const fields=screen ? [...screen.querySelectorAll(".field")].filter(f=>{
        const r=f.getBoundingClientRect(), cs=getComputedStyle(f);
        return cs.display!=="none" && cs.visibility!=="hidden" && r.width>0 && r.height>0;
      }) : [];
      // Treat all visible fields on this page as one work area so pages with
      // Flight + DEP (or other multi-field forms) stay visible together.
      const rects=fields.map(f=>f.getBoundingClientRect());
      let wt=rects.length?Math.min(...rects.map(r=>r.top)):0;
      let wb=rects.length?Math.max(...rects.map(r=>r.bottom)):0;
      if(rects.length && wb-wt<=available){
        if(wb>bottom) main.scrollBy({top:wb-bottom+8,behavior:"auto"});
        else if(wt<top) main.scrollBy({top:wt-top-8,behavior:"auto"});
        return;
      }
      // If the complete work area physically cannot fit, keep the active field
      // visible while leaving the content scrollable for the neighbouring fields.
      const field=el.closest(".field");const er=field ? field.getBoundingClientRect() : el.getBoundingClientRect();
      if(er.bottom>bottom) main.scrollBy({top:er.bottom-bottom+8,behavior:"auto"});
      else if(er.top<top) main.scrollBy({top:er.top-top-8,behavior:"auto"});
    };
    const syncNow=()=>{
      vvFrame=0;
      const open=keyboardOpen(), app=$("app");
      app.classList.toggle("kb",open);
      app.style.setProperty("--vh",open?Math.round(vv.height)+"px":"100%");
      app.style.setProperty("--vt",open?Math.round(vv.offsetTop)+"px":"0px");
      if(open) revealWorkspace();
    };
    const sync=()=>{
      if(vvFrame) cancelAnimationFrame(vvFrame);
      vvFrame=requestAnimationFrame(syncNow);
      clearTimeout(settleTimer);
      settleTimer=setTimeout(()=>{syncNow();revealWorkspace();},180);
    };
    vv.addEventListener("resize",sync,{passive:true});
    window.addEventListener("resize",sync,{passive:true});
    vv.addEventListener("scroll",sync,{passive:true});
    document.addEventListener("focusin",()=>{setTimeout(sync,30);setTimeout(sync,260)});
    document.addEventListener("focusout",()=>setTimeout(sync,120));
    sync();
  }

  // Always start blank: undo any form state the browser restored on relaunch / reload / bfcache.
  clearFields();
  showScreen("phone");
  const startPhoneLibrary=()=>requestAnimationFrame(()=>requestAnimationFrame(loadPhoneLibrary));
  startPhoneLibrary();
  window.addEventListener("pageshow",e=>{if(e.persisted) resetAll();});

  // ---- phone-input idle window -------------------------------------------
  // Typing the phone number takes ~3 s. Work that must not compete with the
  // first paint or the keyboard opening runs here, one small task per idle
  // slot, so keystrokes are never blocked. Every task is optional: failures are
  // ignored and nothing here changes validation, state or what is displayed.
  const idle=window.requestIdleCallback
    ? fn=>requestIdleCallback(fn,{timeout:1000})
    : fn=>setTimeout(fn,50);
  const PHONE_WINDOW_DELAY_MS=600;
  let libWarmTries=0;
  const phoneWindowTasks=[
    // First real parse inside libphonenumber builds its metadata lazily; do it
    // now so the first keystroke's validation is not the slow one.
    function warmPhoneLibrary(){
      if(!phoneLibReady){ if(++libWarmTries<20) phoneWindowTasks.push(warmPhoneLibrary); return false; }
      ["85291234567","886912345678","819012345678","85289648964"].forEach(n=>{normalizePhone(n);detectCountryEarly(n);});
    },
    // Intl/ICU data (Asia/Taipei time zone, region names) loads on first use.
    function warmIntl(){
      try{new Intl.DateTimeFormat("en-GB",{timeZone:"Asia/Taipei",hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).format(new Date());}catch(e){}
      try{new Intl.DateTimeFormat("en-GB",{timeZone:"Asia/Taipei",day:"2-digit",month:"short"}).formatToParts(new Date());}catch(e){}
      try{new Intl.DisplayNames(["en"],{type:"region"}).of("HK");}catch(e){}
    },
    // Decode the next screen's icons so Scenario appears without a decode hitch.
    function decodeNextScreen(){
      document.querySelectorAll("#s-scenario img").forEach(img=>{try{if(img.decode) img.decode().catch(()=>{});}catch(e){}});
    },
    // Service Worker registration and cache refresh last: network + disk I/O.
    // The worker revalidates every cached file here (in parallel), never at launch.
    function startServiceWorker(){
      if(!("serviceWorker" in navigator)) return;
      navigator.serviceWorker.register("sw.js",{updateViaCache:"none"})
        .then(reg=>{const w=reg.active;if(w) w.postMessage({type:"refresh"});})
        .catch(()=>{});
    }
  ];
  const runPhoneWindow=()=>idle(deadline=>{
    let deferred=false;
    while(phoneWindowTasks.length){
      const task=phoneWindowTasks.shift();
      try{deferred=task()===false;}catch(e){}
      if(deferred||!deadline||typeof deadline.timeRemaining!=="function"||deadline.timeRemaining()<8) break;
    }
    // A deferred task (phone library still loading) is retried a little later.
    if(phoneWindowTasks.length) setTimeout(runPhoneWindow,deferred?150:0);
  });
  const openPhoneWindow=()=>setTimeout(runPhoneWindow,PHONE_WINDOW_DELAY_MS);
  if(document.readyState==="complete") openPhoneWindow();
  else window.addEventListener("load",openPhoneWindow,{once:true});
})();
