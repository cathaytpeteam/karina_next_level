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
ck('Scenario 1 progress labels', 'progressName+=" - "+(S.missMode==="join"?"Join Pax":"Transit Pax")' in s)
# Scenario 2 routes + approved Final Call labels.
for x in [
 '$('+'"goCall"'+').onclick=()=>{clearCallCase();flow="call";S.order="zh";S.orderSet=false;go("calltype");};',
 '$('+'"callJoin"'+').onclick=()=>{clearCallForModeChange("join");S.callMode="join";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("callflight");};',
 '$('+'"callTransit"'+').onclick=()=>{clearCallForModeChange("transit");S.callMode="transit";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("callflight");};',
 '$('+'"callDirect"'+').onclick=()=>{clearCallForModeChange("direct");S.callMode="direct";S.callNoMessage=true;S.order="zh";S.orderSet=false;clearDrafts();go("preview");};'
]: ck('Scenario 2 route '+x.split('"')[1], x in s)
ck('Scenario 2 progress labels', 'progressName+=" - "+(S.callMode==="join"?"Join Pax":"Transit Pax")' in s)
ck('Progress calculation remains flow-index based', 'textContent:(idx+1)+"/"+f.steps.length' in s)
if not all(v for _,v in checks): sys.exit(1)
print('PASS navigation lock: Scenario 1 = 3 steps; Scenario 2 = 5 steps; routes and labels locked')
