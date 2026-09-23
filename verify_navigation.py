#!/usr/bin/env python3
from pathlib import Path
import json,re,sys
r=Path(__file__).resolve().parent
s=(r/'index.html').read_text(encoding='utf-8')
lock=json.loads((r/'navigation-lock.json').read_text(encoding='utf-8'))
checks=[]
def ck(name,cond):
    checks.append((name,bool(cond)))
    print(('PASS' if cond else 'FAIL'),name)
def section(sid):
    m=re.search(r'<section\b[^>]*\bid="'+re.escape(sid)+r'"[^>]*>.*?</section>',s,re.S)
    return m.group(0) if m else ''
def obj_block(name):
    m=re.search(r'const\s+'+re.escape(name)+r'=\{(.*?)\n\s*\};',s,re.S)
    return m.group(1) if m else ''
def func_body(name):
    m=re.search(r'function\s+'+re.escape(name)+r'\([^)]*\)\s*\{',s)
    if not m:return ''
    i=m.end(); depth=1
    while i<len(s) and depth:
        if s[i]=='{': depth+=1
        elif s[i]=='}': depth-=1
        i+=1
    return s[m.end():i-1] if depth==0 else ''

# Exact flow step mappings: protects progress denominators and page sequence.
for key,v in lock['flows'].items():
    steps=','.join('"'+x+'"' for x in v['steps'])
    exact=f'{key}:{{name:"{v["name"]}",steps:[{steps}]}}'
    ck(f'{key} flow mapping', exact in s)

# Scenario 1 routes and labels must never move during other flow edits.
for x in [
 '$("goMiss").onclick=()=>{clearMissCase();flow="miss";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("misstype");};',
 '$("missJoin").onclick=()=>{clearMissForModeChange("join");flow="miss";S.missMode="join";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("mflight");};',
 '$("missTransit").onclick=()=>{clearMissForModeChange("transit");flow="miss";S.missMode="transit";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("mflight");};',
 '$("missDirect").onclick=()=>{clearMissForModeChange("direct");flow="call";S.missMode="direct";S.callMode="direct";S.callNoMessage=true;S.order="zh";S.orderSet=false;clearDrafts();go("preview");};'
]: ck('Scenario 1 route '+x.split('"')[1], x in s)
ck('Scenario 1 progress label order', 'flow==="miss" && cur!=="misstype" && (S.missMode==="join"||S.missMode==="transit")' in s and 'document.createTextNode(f.name+" - ")' in s and 'document.createTextNode(" - "+passengerType)' in s)

# Scenario 2 routes + approved Final Call labels.
for x in [
 '$("goCall").onclick=()=>{clearCallCase();flow="call";S.order="zh";S.orderSet=false;go("calltype");};',
 '$("callJoin").onclick=()=>{clearCallForModeChange("join");S.callMode="join";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("callflight");};',
 '$("callTransit").onclick=()=>{clearCallForModeChange("transit");S.callMode="transit";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("callflight");};',
 '$("callDirect").onclick=()=>{clearCallForModeChange("direct");S.callMode="direct";S.callNoMessage=true;S.order="zh";S.orderSet=false;clearDrafts();go("preview");};'
]: ck('Scenario 2 route '+x.split('"')[1], x in s)
ck('Scenario 2 progress label order', 'flow==="call" && cur!=="calltype" && (S.callMode==="join"||S.callMode==="transit")' in s and 'document.createTextNode(f.name+" - ")' in s and 'document.createTextNode(" - "+passengerType)' in s)
ck('Scenario 1 Back hides Passenger Type annotation', 'cur!=="misstype"' in s)
ck('Scenario 2 Back hides Passenger Type annotation', 'cur!=="calltype"' in s)
ck('Scenario 1 Passenger Type is progress step 1/3', 'miss:{name:"漏查",steps:["misstype","mflight","msec"]}' in s)
ck('Scenario 2 SEC page removed', 'id="s-callsec"' not in s and 'callSec' not in s and '"callsec"' not in s)
ck('Scenario 1 preview keeps completed 3/3', 'const missCompletedPreview=flow==="miss"&&cur==="preview"' in s)
ck('Progress calculation uses locked flow denominator', 'const progressText=(idx+1)+"/"+f.steps.length;' in s)
ck('Call Directly progress 1/1', 'textContent:"1/1"' in s and 'document.createTextNode(" - Call Directly")' in s and 'const directName=S.missMode==="direct"?"漏查":"Final Call";' in s)
ck('Browser Back/Forward state direction', 'history.replaceState({findPax:true,pos:0,id:"phone"}' in s and 'history.pushState({findPax:true,pos:navPos,id}' in s and 'navPos=st.pos;' in s and 'showScreen(st.id);' in s)

# Scenario 4 structural + behavior regression checks.
dstatus=section('s-dstatus')
dflight=section('s-dflight')
ck('Scenario 4 Flight Type is step 1/6', 'dp:{name:"Disrupted Pax",steps:["dstatus","dflight","dtransfer","darrange","darrive","preview"]}' in s)
ck('Scenario 4 entry routes to Flight Type', '$("goDp").onclick=()=>{clearDpCase();flow="dp";S.order="en";S.orderSet=false;go("dstatus");};' in s)
ck('Scenario 4 Flight Type labels', '<h1>Flight Type</h1>' in dstatus and '>Tight Connection<' in dstatus and '>Delayed<' in dstatus and '>To be updated<' in dstatus)
ck('Scenario 4 Flight Type hierarchy', 'choice passengerPrimary' in dstatus and 'id="stPossible"' in dstatus and dstatus.count('choice passengerSecondary')==2 and 'id="stDelayed"' in dstatus and 'id="stUnknown"' in dstatus)
ck('Scenario 4 Flight Type has no delayed-time field', 'delayWrap' not in dstatus and 'delayTime' not in dstatus and '<input' not in dstatus)
ck('Scenario 4 delayed time merged into step 2/6', all(x in dflight for x in ['id="dFlight"','id="delayWrap"','Delayed to','id="delayTime"']) and dflight.index('id="dFlight"') < dflight.index('id="delayWrap"') < dflight.index('id="delayTime"'))

# Flight Type uses the same default heading placement as Passenger Type: no special center override.
css=(re.search(r'<style>(.*?)</style>',s,re.S) or [None,''])[1]
centered=False
for sel,body in re.findall(r'([^{}]+)\{([^{}]*)\}',css,re.S):
    if '#s-dstatus h1' in sel and 'text-align:center' in re.sub(r'\s+','',body):
        centered=True
ck('Scenario 4 Flight Type title placement matches Passenger Type', not centered)
ck('Scenario 4 Flight Type header matches Passenger Type', 'const hasWho=cur!=="phone"&&cur!=="calltype"&&cur!=="misstype"&&cur!=="dstatus"' in s)

# Choice pages navigate immediately; there is no footer/Next and no NEXT[dstatus] path.
ck('Scenario 4 Flight Type footer/Next hidden', 'const showFoot=cur!=="scenario"&&cur!=="calltype"&&cur!=="misstype"&&cur!=="dstatus";' in s)
next_block=obj_block('NEXT')
ck('Scenario 4 Flight Type has no NEXT handler', 'dstatus:' not in next_block)
sel_body=func_body('selectDpFlightType')
ck('Scenario 4 selection helper clears stale delay on branch change', 'S.status&&S.status!==nextStatus' in sel_body and '$("delayTime").value="";' in sel_body)
ck('Scenario 4 selection helper immediately opens step 2/6', 'S.status=nextStatus;' in sel_body and 'go("dflight");' in sel_body)
for bid,status in [('stPossible','possible'),('stDelayed','delayed'),('stUnknown','unknown')]:
    ck(f'Scenario 4 {bid} direct navigation', f'$("{bid}").onclick=()=>selectDpFlightType("{status}");' in s)

# Validation ownership: only Delayed requires delayed time, and only on step 2/6.
ok_block=obj_block('OK')
hint_block=obj_block('HINT')
ck('Scenario 4 Flight Type selection itself is always continuable', 'dstatus:()=>S.status==="possible"||S.status==="delayed"||S.status==="unknown"' in ok_block and 'delayTime' not in re.search(r'dstatus:\(\)=>[^,\n]*',ok_block).group(0))
ck('Scenario 4 Delayed time validates on step 2/6 only', 'dflight:()=>isFlt(v("dFlight"))&&generalCxOk(v("dFlight"))&&(S.status!=="delayed"||timeOk("delayTime"))' in ok_block)
ck('Scenario 4 To be updated has no delay-time dependency', 'S.status!=="delayed"||timeOk("delayTime")' in ok_block)
ck('Scenario 4 delayed hint belongs to step 2/6', 'dflight:()=>!isFlt(v("dFlight"))?"1–3 digits":(!generalCxOk(v("dFlight"))?"":(S.status==="delayed"?timeHint("delayTime"):""))' in hint_block and 'dstatus:()=>""' in hint_block)
ck('Scenario 4 delay field visibility belongs to dflight', 'if(cur==="dflight"){' in s and '$("delayWrap").hidden=S.status!=="delayed";' in s and 'if(cur==="dstatus")' in s)


ck('Scenario 4 disrupted flight has explicit TPE departure whitelist', 'const TPE_DEPARTURE_FLIGHTS=GENERAL_CX_FLIGHTS;' in s and 'const generalCxOk=raw=>TPE_DEPARTURE_FLIGHTS.has' in s)
ck('Scenario 4 disrupted flight visibly marks non-whitelist flight', 'id="dFlight"' in dflight and '$("dFlight").closest(".field").classList.toggle("bad",!!dn&&!generalCxOk(dn));' in s)
ck('Scenario 4 Delayed valid 3-digit flight auto-focuses Delayed to', 'id==="dFlight" && S.status==="delayed" && this.value.length===3 && generalCxOk(this.value)' in s and '$("delayTime").focus()' in s)
ck('Scenario 4 Delayed to remains editable HHMM input', 'id="delayTime" inputmode="numeric" maxlength="5"' in dflight and '["delayTime","altTime","arriveTime"].forEach' in s and 'fmtTime(this);render();' in s)

if not all(v for _,v in checks): sys.exit(1)
print('PASS navigation lock: Scenario 1 = 3 steps; Scenario 2 = 4 steps with no SEC page; Scenario 4 Flight Type is direct-navigation 1/6, Delayed time is on 2/6 only; Call Directly = 1/1; routes, validation ownership, title placement, and history behavior locked')
