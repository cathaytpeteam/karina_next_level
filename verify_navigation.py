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
# Exact flow step mappings: protects progress denominators and page sequence.
for key,v in lock['flows'].items():
    steps=','.join('"'+x+'"' for x in v['steps'])
    exact=f'{key}:{{name:"{v["name"]}",steps:[{steps}]}}'
    ck(f'{key} flow mapping', exact in s)
# Scenario 1 routes and labels must never move during Scenario 2 naming edits.
for x in [
 '$('+'"goMiss"'+').onclick=()=>{clearMissCase();flow="miss";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("misstype");};',
 '$('+'"missJoin"'+').onclick=()=>{clearMissForModeChange("join");flow="miss";S.missMode="join";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("mflight");};',
 '$('+'"missTransit"'+').onclick=()=>{clearMissForModeChange("transit");flow="miss";S.missMode="transit";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("mflight");};',
 '$('+'"missDirect"'+').onclick=()=>{clearMissForModeChange("direct");flow="call";S.missMode="direct";S.callMode="direct";S.callNoMessage=true;S.order="zh";S.orderSet=false;clearDrafts();go("preview");};'
]: ck('Scenario 1 route '+x.split('"')[1], x in s)
ck('Scenario 1 progress label order', 'flow==="miss" && cur!=="misstype" && (S.missMode==="join"||S.missMode==="transit")' in s and 'document.createTextNode(f.name+" - ")' in s and 'document.createTextNode(" - "+passengerType)' in s)
# Scenario 2 routes + approved Final Call labels.
for x in [
 '$('+'"goCall"'+').onclick=()=>{clearCallCase();flow="call";S.order="zh";S.orderSet=false;go("calltype");};',
 '$('+'"callJoin"'+').onclick=()=>{clearCallForModeChange("join");S.callMode="join";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("callflight");};',
 '$('+'"callTransit"'+').onclick=()=>{clearCallForModeChange("transit");S.callMode="transit";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("callflight");};',
 '$('+'"callDirect"'+').onclick=()=>{clearCallForModeChange("direct");S.callMode="direct";S.callNoMessage=true;S.order="zh";S.orderSet=false;clearDrafts();go("preview");};'
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
ck('Scenario 4 Flight Type is step 1/6', 'dp:{name:"Disrupted Pax",steps:["dstatus","dflight","dtransfer","darrange","darrive","preview"]}' in s)
ck('Scenario 4 entry routes to Flight Type', '$("goDp").onclick=()=>{clearDpCase();flow="dp";S.order="en";S.orderSet=false;go("dstatus");};' in s)
ck('Scenario 4 Flight Type labels', '<h1>Flight Type</h1>' in s and '>Tight Connection<' in s and '>Delayed<' in s and '>To be updated<' in s)
ck('Scenario 4 Flight Type hierarchy', 'id="stPossible" type="button" aria-pressed="false"' in s and 'choice passengerPrimary' in s and 'id="stDelayed"' in s and 'id="stUnknown"' in s)
ck('Scenario 4 step 1 continues to Disrupted flight', 'dstatus:()=>go("dflight")' in s)
if not all(v for _,v in checks): sys.exit(1)
print('PASS navigation lock: Scenario 1 = 3 steps; Scenario 2 = 4 steps with no SEC page; Scenario 4 Flight Type = step 1/6; Call Directly = 1/1; routes and labels locked')
