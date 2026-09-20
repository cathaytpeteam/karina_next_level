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


## v1.5 fixed
修正 3 Wrongly Pick-up 與 4 Disrupted Pax 無法點入的問題。補齊實際 HTML 頁面，重新整理首頁四個按鈕版面，並套用使用者提供的飛機＋時鐘圖示。Disrupted Pax 包含 Transfer flight number，且所有語言頁標題為 Preferred Language。


## v1.6 — Dual-system QA / bug fixes

針對 iPhone Safari / 加到主畫面，以及 Android Chrome / PWA 做靜態檢查與修正：

- 修正 Back 按鈕同時綁定兩套事件造成的導覽衝突。
- 修正文字型選項在手機上被擠進 64px 欄位的版面問題。
- 修正完成一次 WhatsApp 後，Wrongly Pick-up 的航空公司前綴 `CX` 被清空。
- 重置時同步清除 Disrupted Pax 的延誤時間/替代航班展開狀態。
- WhatsApp `wa.me` 路徑統一使用純國際號碼（不在路徑中加入 `+`）。
- Wrongly Pick-up 與其他功能統一使用相同 WhatsApp 開啟/重置流程。
- Service Worker 預先快取 `./` 與 `index.html`，提高 iOS/Android 主畫面離線啟動可靠度。
- 移除重複的 Apple touch icon 宣告。
- Disrupted Pax 圖示改成真正透明背景的版本，避免棋盤格背景。
- 按鈕加入 `appearance:none` / `touch-action:manipulation`，降低 Safari 與 Chrome 的原生樣式差異。


## v1.7 — iPhone/Android layout hotfix
修正 Flight status 等純文字選項在 iOS Safari 被壓進原本 icon grid 欄位、造成中文字逐字換行的問題。
這些頁面的按鈕改用獨立 flex 版面，不再繼承首頁三欄 grid。
同時更新 Service Worker cache key，避免手機繼續讀到舊 CSS。


## v1.8 — Flight arrange wording / HHMM keyboard input

- Flight arrange 內部選項改為 `Protected to` 與 `Protected – not confirmed`。
- Disrupted Pax 所有時間欄位不再使用原生 Time Picker。
- 改用 numeric keypad 輸入四碼 HHMM；例如 `0811` 自動格式化為 `08:11`。
- 驗證：HH 00–23、MM 00–59；無效時間不能進入下一步。
- 保留原本 WhatsApp 訊息內容邏輯；上述 wording 僅供內部介面快速辨識。


## v1.9 — Bag Tag guidance
Wrongly Pick-up：
- Bag Tag 1 顯示「沒有人拿走的行李」
- Bag Tag 2 顯示「被拿錯，目前找不到的行李」
- Bag Tag 1 / 2 的預設航空公司代碼 `CX` 加大、加粗；仍可編輯其他兩碼航空公司代碼。

## v1.10 — Editable transfer airline code
- Transfer flight number 的航空公司代碼預設 `CX`，但可直接編輯。
- 限制 2 個英文字母，自動轉大寫。
- WhatsApp 訊息使用實際輸入的航空公司代碼。

## v1.11 — Disrupted Pax page order
流程調整為：
`Disrupted flight number → Transfer flight number → Flight status → Flight arrange → Pax should be arrive before ? → Preferred Language → WhatsApp`

Transfer flight airline code 仍預設 CX 且可編輯；其他 v1.10 功能不變。

## v1.12 — Transfer flight input clarity
- Transfer flight number 拆成兩個清楚的輸入區：
  - Airline：預設 CX，可編輯 2 碼航空公司代碼。
  - Flight number：獨立數字欄位，手機使用 numeric keypad，1–3 碼。
- 避免游標停在 CX 後方時讓使用者誤以為可直接接著輸入數字。
- v1.11 的頁面順序及既有訊息邏輯維持不變。

## v1.13 — Clean transfer input
- 移除 Transfer flight number 輸入區上方的 `Airline` / `Flight number` 顯示文字。
- 保留左右分開的航空公司代碼與航班號碼輸入區。
- 航空公司代碼預設 CX、可編輯；航班號碼仍使用數字鍵盤。

## v1.14 — Editable protected airline
- Flight arrange 的 Protected to 航班航空公司代碼預設 `CX`，現在也可編輯。
- 限制 2 個英文字母並自動轉大寫。
- 替代航班 WhatsApp 內容使用實際輸入的航空公司代碼。

## v1.15 — Bag Tag typography/layout
- 調整 Bag Tag 1 / Bag Tag 2 的標題與中文說明間距。
- 中文說明改為較小的輔助文字層級，避免和主標題搶視覺。
- 說明與輸入框保留清楚間距；既有功能不變。

## v1.16 — Bag Tag airline prefix colour
- Bag Tag 1 / 2 的預設航空公司代碼 `CX` 改為與 App 主題一致的綠色。
- 保留加粗、加大與可編輯功能。

## v1.17 — Bag Tag Chinese explanation prominence
- Bag Tag 1 / 2 中文說明不再縮小。
- 中文說明改為 24px、粗體、主題綠色，保持明顯且易讀。
- 保留 v1.16 的 CX 綠色、加粗、加大與可編輯功能。

## v1.18
- Bag Tag 2 中文說明改為「疑似被客人Wrong P帶走的行李」。
