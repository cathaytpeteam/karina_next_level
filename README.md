# Find Pax

跨平台 GitHub Pages / PWA，支援 iPhone Safari / iOS PWA、Android Chrome / Android PWA 與桌面瀏覽器。

## 電話國家 / 國旗

Phone 頁會先把輸入轉成純數字，再依國際電話國碼在本機判斷國家，例如：

- `852...` → 🇭🇰 HK
- `886...` → 🇹🇼 TW
- `44...` → 🇬🇧 UK
- `81...` → 🇯🇵 JP

不使用外部國碼 API。要調整國家資料，請在 `index.html` 搜尋 `countryCodes`。

## 罐頭號碼封鎖機制

目前 Trip.com 罐頭號碼：

`85289648964`

程式會移除 `+`、空格、`-` 等非數字字元後再比對，所以 `+852 89648964`、`852 8964 8964`、`85289648964` 都會被視為同一號碼。

完全符合時：

- 顯示 `罐頭號碼 無用`（紅色、22px、粗體、置中）
- `Next` 停用
- 無法進入 Scenario
- 國旗 / 國家提示仍保留
- 修改任一數字後，警告自動消失並恢復正常流程

### 以後新增或刪除罐頭號碼

在 `index.html` 搜尋：

```js
const blockedPhones=new Set(["85289648964"]);
```

例如新增第二個號碼：

```js
const blockedPhones=new Set(["85289648964","886912345678"]);
```

請一律使用「國碼 + 電話號碼」的純數字格式。

提示文字要修改時，在 `index.html` 搜尋 `罐頭號碼 無用`。

## 頁面流程

- Phone：沒有 Back。
- Scenario：Back → Phone。
- `1 漏查` → Flight → SEC → WhatsApp。
- `2 Call Pax` → 直接開 WhatsApp，訊息 `您好`。
- Flight：Back → Scenario；固定 `CX`，輸入 0–999。
- SEC：Back → Flight；輸入 0–580，送出時補成三位數。
- Back 不會清除已輸入內容。

識別碼格式：`cx{flight}/sec{sec}/{DD}{mmm}`，例如 `cx565/sec002/20sep`。

## PWA / 快取維護

每次發布新版，請同步提高 `sw.js` 的 `CACHE` 版本，例如：

```js
locha-v9-20260920
```

下一版可改為 `locha-v9-20260920`。這可降低手機 PWA 卡住舊版的情況。

發布後可先用 `?v=8` 之類的網址參數在 Safari / Chrome 確認新版。若主畫面 PWA 仍是舊版，再移除舊 PWA、清除該網站資料後重新加入主畫面。

## 主要檔案

- `index.html`：UI、流程、國碼/國旗、罐頭號碼、WhatsApp 邏輯
- `sw.js`：Service Worker / cache
- `manifest.webmanifest`：PWA 設定
- `README.md`：維護說明
- `icon-*.png` / `apple-touch-icon.png`：App 圖示

## 視覺

主綠色：`#005D63`

版面維持跨平台 responsive，不針對單一手機型號寫死。


## v10 App icon

主畫面 App icon 已改為扁平風格：站直的人物雙手舉起行李箱。
同一圖案已套用至 `apple-touch-icon.png`、`icon-192.png`、`icon-512.png`
以及 maskable icons。若 iPhone 主畫面仍顯示舊 icon，需移除舊捷徑後再由 Safari
「分享 → 加入主畫面」，因 iOS 可能保留舊的主畫面 icon。


## Release v1.0

此版本正式命名為 **v1.0**。

Phone 輸入頁的畫面最下方中央加入目前的 App 圖示：
站直人物雙手舉起行李箱。此圖示僅作視覺識別，不影響電話輸入、國碼判斷、
罐頭號碼封鎖或 Next 流程。


### v1.0 UI adjustment

- `罐頭號碼 無用`：24px、紅色、粗體、置中。
- Phone 頁最下方中央圖示改用選定的「雙手舉行李」版本。
- 底部圖示縮小為約 22px，作為低調的頁面識別。


## Find Pax naming / phone-page icon

- PWA `name`：`Find Pax`
- PWA `short_name`：`Find Pax`
- iPhone 主畫面名稱：`Find Pax`
- 瀏覽器頁面標題：`Find Pax`
- Phone 頁底部 icon：90 × 90px


## Approved icon

所有圖示已統一使用核准版本：站直人物雙手舉起米色行李箱。
包含 iPhone、Android/PWA、maskable icons，以及 Phone 頁底部 90 × 90px 圖示。
其他 icon 提案不再使用。


## Phone bottom icon fix

- Phone 頁底部圖示維持 90 × 90px。
- Phone 頁使用透明背景 PNG（去背）。
- 圖示固定在畫面底部中央。
- 偵測到手機螢幕鍵盤開啟時，底部圖示會暫時隱藏，避免遮住 Next / 輸入區。
- 鍵盤收起後，圖示自動回到底部中央。
- App / PWA 主畫面 icon 仍維持核准版白底圖示，避免影響 iOS / Android 桌面圖示呈現。


## v1.1 — Wrongly Pick-up

第二頁新增 `3 Wrongly Pick-up`。

流程：
`Wrongly Pick-up → Flight Number → Bag Tag 1 → Bag Tag 2 → Message Order → WhatsApp`

- Scenario 1「漏查」不顯示行李 icon。
- Scenario 3 使用行李 icon。
- Flight 固定顯示 CX，輸入 1–3 碼航班數字。
- Bag Tag 1 / 2 預設航空公司代碼 CX；兩碼代碼可編輯，只接受英文字母並自動轉大寫。
- Bag Tag 號碼固定 6 碼數字；未滿 6 碼不能 Next。
- Message Order：
  1. 中文在上
  2. English First
- 中英文內容相同，只切換排列順序。
- 使用第一頁已輸入的電話號碼開啟 WhatsApp。


### 優先語言頁面
標題：`優先語言`

按鈕：
1. `中文`
2. `English`

功能不變：選中文時中文訊息在上；選 English 時英文訊息在上。


## v1.2 — 漏查優先語言

`1 漏查` 流程更新為：
`漏查 → Flight Number → SEC → 優先語言 → WhatsApp`

優先語言頁：
1. `中文`：中文訊息在上、英文在下。
2. `English`：英文訊息在上、中文在下。

原本漏查中英文訊息內容與最後的 `cx{flight}/sec{sec}/{DD}{mmm}` identifier 均不變，只切換中英文排列順序。


## v1.3 — Disrupted Pax

第二頁新增 `4 Disrupted Pax`。

頁面：
- `Disrupted flight number`
- `Flight status`
- `Flight arrange`
- `Pax should be arrive before ?`
- `Preferred Language`

Flight status 三個實際選項（App 不顯示 A/B/C 代號）：
- 今天可能會延遲
- 目前已經延遲至（必填時間）
- 目前航班及起飛動態尚未確定

Flight arrange 兩個實際選項（App 不顯示 C/D 等代號）：
- 已知替代航班：必填替代 CX 航班號碼與起飛時間
- 尚未確定替代航班

抵達桃園機場時間必填。

全 App 原本「優先語言」標題統一改為 `Preferred Language`，選項仍為 `中文` / `English`。


## App rename
App 顯示名稱、HTML title、iPhone Web App title、PWA manifest name / short_name 已統一改為 `Find Pax`。


## v1.4 — Transfer flight number

Disrupted Pax 在 `Flight status` 後新增必填頁：
- `Transfer flight number`
- 固定 `CX` 前綴 + 1–3 位數字
- App 不顯示討論用的 F 代號

流程：
`Disrupted flight number → Flight status → Transfer flight number → Flight arrange → Pax should be arrive before ? → Preferred Language → WhatsApp`

WhatsApp 中英文訊息都會帶入受影響的香港轉機航班號碼。
