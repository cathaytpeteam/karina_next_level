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
const blocked=new Set(["85289648964","85262374313"]);
```

例如新增第二個號碼：

```js
const blocked=new Set(["85289648964","85262374313","886912345678"]);
```

請一律使用「國碼 + 電話號碼」的純數字格式。

(變數名稱為 `blocked`,舊版文件誤寫為 `blockedPhones`,已更正。)

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
const CACHE="find-pax-v1.30.1-bugfix-20260920";
```

每次發布請把版本號與日期一併更新，這可降低手機 PWA 卡住舊版的情況。

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

## v1.19 — Clean split fields
- Transfer flight number 移除灰色 `450` placeholder，未輸入時保持空白。
- Bag Tag 1 / 2 改為與 Transfer flight 相同的左右分隔欄位：左側航空公司代碼、右側 6 位數字。
- Bag Tag 數字欄位不顯示灰色範例文字。
- 航空公司代碼仍可編輯，既有驗證與流程不變。

## v1.20 — Transfer flight default CX
- Transfer flight 的航空公司代碼預設顯示 `CX`。
- `CX` 仍可直接修改為其他兩碼航空公司代碼。
- 右側航班號碼保持空白，不顯示 450 或其他灰色範例。

## v1.21 — Full typography & layout polish
- 全站統一主標題、Back、選項、輸入內容、Next 的字級、粗細、留白與圓角節奏。
- Bag Tag 中文說明維持醒目大字，不縮小。
- 可修改航空公司代碼的欄位限定為：Bag Tag 1/2、Transfer flight number、Protected to。
- 以上三類預設 CX 並保留可編輯；其他 CX 航班欄位維持原本固定邏輯。
- Transfer flight 右側不顯示 450 或灰色 placeholder。
- 不更改既有流程、WhatsApp 文案或驗證規則。

## v1.24 — GitHub-ready update
- Disrupted flight + TPE
- Connecting flight + HKG
- Protected to → Will Protect to
- Protected - not confirmed → Not decided yet
- Pax should be arrive before ? → Pax should arrive before ?
- Flight arrange → Flight arrangement
- 單一輸入欄位頁面的表單向上 15%。
- 第一頁底部 icon 放大 1.4 倍至 126×126。

## v1.25 — Canned phone number
- 新增罐頭號碼 `85262374313`。
- 原有 `85289648964` 保留。
- 兩個號碼輸入時皆顯示 `罐頭號碼 無用` 並停用 Next。

## v1.26 — Transparent icon cleanup
- 修正 `disrupted-pax-icon-v2.png` 黑色背景，改為真正透明 PNG。
- 修正 `phone-bottom-icon.png` 周圍黑白背景／雜邊，改為真正透明 PNG。
- 保留原本 teal 人物／飛機、米色行李與圖案設計。
- App 主 icon 維持原本白底設計。

## v1.27 — Fixed light mode
- Find Pax 固定使用淺色模式，不跟隨手機深色主題。
- 頁面背景、輸入框與表單元件固定白底。
- 保留 Cathay 綠 `#005D63` 與既有 UI 配色。
- iPhone Safari / Home Screen PWA 與 Android Chrome / PWA 均套用 light color scheme。
- manifest 與 browser theme color 固定為白色。
- 其他流程、文字、罐頭號碼與透明 icon 維持 v1.26。

## v1.28 — Reduce Android autofill/history popups
- 全 App form/input 關閉 browser autocomplete。
- 關閉 autocorrect、autocapitalize、spellcheck，降低 Android Chrome / 鍵盤的歷史輸入干擾。
- 保留原本 `inputmode` 與欄位驗證，所以電話、航班號、Bag Tag、HHMM 的鍵盤類型不變。
- 注意：Gboard / Samsung Keyboard 自己的剪貼簿或個人化建議由手機鍵盤控制，網頁無法完全禁止。

## v1.29 — Dynamic keyboard-safe layout + Protected split field
- 移除以固定百分比猜測鍵盤高度的做法。
- 支援 Visual Viewport 的手機會依「實際可視高度」動態計算需要上移的距離。
- 鍵盤關閉後版面自動回復正常位置。
- Will Protect to 的替代航班改為與 Connecting flight 一致的 `CX │ 航班號` 分隔欄位。
- 替代航班時間 HHMM 維持獨立欄位。
- CX 仍預設存在、可修改，既有驗證與 WhatsApp 組字邏輯不變。

## v1.30 — Universal keyboard-safe mode
- 鍵盤避讓改為全 App 套用，不再只針對單一輸入頁。
- 依每支手機 `visualViewport` 的實際可視高度判斷鍵盤佔用空間。
- 鍵盤開啟時優先確保「目前輸入欄位 + Next」完整位於鍵盤上方。
- 必要時頁面自動捲動，而不是使用固定 15% 位移。
- 鍵盤開啟時縮短標題／上方留白；裝飾 icon 若符合現有 class 會縮小，增加操作空間。
- 鍵盤關閉後恢復正常頁面配置。
- v1.29 的 Will Protect to `CX │ 航班號` + 獨立 HHMM 保留。

## v1.31 — Complete UI update
- 主題色改為較明亮 Cathay-style teal `#2D9FA3`。
- `Will Protect to` 改為 `Will protect to`。
- 所有航班編號盡量以整組置中，航空公司與數字距離縮短。
- Connecting flight / Will protect to / Bag Tag 移除中間直線分隔。
- 航空公司代碼：28px / 800 / teal。
- 航班與 Bag Tag 數字：28px / 700 / 深灰黑。
- 所有 HHMM 時間欄位：縮短高度、水平置中、28px / 700。
- 保留 TPE / HKG、固定淺色模式、透明 icon、罐頭號碼、自動格式化 HHMM。
- 保留 v1.30 全 App 動態鍵盤避讓：依每支手機實際鍵盤/可視高度自動調整，優先保留輸入欄位與 Next。
- 補齊 manifest.webmanifest 與 sw.js，ZIP 可直接解壓覆蓋 GitHub Pages。

## v1.30.1 — Bug fixes
- 鍵盤避讓改用實際存在的 `.page`（原 `.screen` 沒有任何元素使用，導致無作用）。
- `.page` 改為 `100dvh` 且可垂直捲動，內容較高時（例如 Will Protect to 展開）Next 不再被擠出畫面。
- 發送 WhatsApp 後重置時，Connecting flight 與 Will Protect to 的航空公司代碼也會回到 `CX`。
- 進入頁面時自動聚焦數字欄，而不是航空公司代碼欄。
- 瀏覽器返回若導致電話號碼為空，會自動回到 Phone 頁，避免開出沒有號碼的 wa.me。
- 修正 `dpArrangeNext` 的 `this` 判斷。
- Service Worker 只快取成功的同源回應，並以 `waitUntil` 包住快取寫入。
- 替代航班中文訊息在航班號與「起飛時間」之間補上逗號。
- `disrupted-pax-icon-v2.png` 移除最右側一排不透明像素。

## v2.0 — UI refresh (基於 v1.30.1)

整個 UI 重新排版，並全面改為英文介面（訊息內容本身維持原本的中英文）。流程、罐頭號碼封鎖、國碼判斷與訊息文字維持原本邏輯。

- 頂部固定顯示收件對象（國旗 + 號碼）、進度條與 `n / N` 步驟。
- Next 固定在畫面底部，鍵盤開啟時會跟著移到鍵盤上方；按鈕上方一行小字說明目前缺什麼（例如 `2 more digits`）。
- 所有流程最後都有 `Confirm and send` 預覽頁：顯示摘要與完整訊息，並可切換 `Chinese first` / `English first`（記住上次選擇），按 `Send on WhatsApp` 才會開啟 WhatsApp。`2 Call Pax` 仍直接開啟。
- Flight status：選 `May be delayed today` / `Not confirmed yet` 會直接前進；選 `Delayed to` 才顯示時間欄與 Next。Flight arrangement 同理（`Will protect to` 顯示航班與時間欄，`Not decided yet` 直接前進）。
- 航班 / Bag Tag / Connecting flight / Will protect to 使用同一種輸入欄樣式；可編輯的航空公司代碼預設 `CX`，發送後重置也會恢復 `CX`。
- 進入頁面時自動聚焦數字欄。瀏覽器 / Android 返回鍵與畫面 Back 同步。
- 固定淺色模式（`color-scheme: light only`）；主色改為較深的 `#00747A`，白字對比約 5.9:1；已移除 `user-scalable=no`，允許縮放。
- 移除底部大圖示；`phone-bottom-icon.png` 與 `disrupted-pax-icon-v2.png` 不再使用，可從 GitHub 刪除（留著也不影響）。
- `sw.js` CACHE：`find-pax-v2.0-ui-refresh-20260920`，預先快取清單已移除不再使用的兩張圖。

注意：舊 PWA 若仍顯示舊版，請先用 `?v=2` 網址開一次，或移除舊主畫面捷徑後重新加入。


## v2.1 — Bug fixes(基於 v2.0)

本次只修 bug 與版面一致性,**未更動任何介面文字或 WhatsApp 訊息內容**。

### 訊息殘留修正(最重要)
- 送出 WhatsApp 後重置時,一併清空訊息預覽框內容、草稿狀態與展開狀態。
  修正「下一位客人會看到／收到上一位客人已編輯訊息」的問題。
- 從預覽頁 Back 回去修改任何欄位後,訊息會自動重建,不再停留在舊版本。
  作法:以所有輸入欄位組成簽章,簽章一變動即丟棄舊草稿。
- 切換 `中文` / `English` 不再清空已編輯內容。
  編輯內容改為依語言分別保存,切回去可完整取回。

### 介面提示
- 移除 `.hint:not(.bad){display:none}`。Next 按鈕上方的提示恢復顯示
  (例如 `2 more digits`、`6 digits`、`HHMM, for example 0811`、`Airline code: 2 letters`)。
- `Invalid time (00:00–23:59)` 與 `Max 580` 會以紅色標示。
- 提示列固定保留一行高度,出現／消失時 Next 不再跳動。
- 罐頭號碼不再同時在畫面中段與底部重複顯示,只保留中段紅色警告框。

### 版面一致性
- 修正 CSS 選擇器 `#s-transfer` → `#s-dtransfer`。Connecting flight 的
  航空公司代碼與航班號碼欄位,現在與 Bag Tag / Will protect to 使用同一種幾何。
- SEC 頁(`#s-msec`)納入同一套置中窄欄版面,與前一頁 Flight number 的數字位置對齊。
- `font-weight:750` 改為 `700`(750 非標準字重,PingFang TC 不支援,
  原本就會被瀏覽器降成 700;改寫以確保 iOS / Android 呈現一致)。
- 新增 `max-width:380px` 斷點:窄螢幕 Android 上縮小情境列的 icon、
  編號與字級,避免 `Wrongly Pick-up` 這類較長標籤被擠出畫面。
- 輸入文字顏色 `#263737` 改為 CSS 變數 `--input-ink`(顏色不變)。
- 移除無效規則 `#s-scenario > h1{display:none}`(該頁沒有 h1)。
- 移除正式版殘留的 `window.__fp` 除錯物件。

### 無障礙
- 中文內容區塊(罐頭號碼警告、Bag Tag 說明、Flight status 選項、
  `中文` 按鈕、訊息編輯框)加上 `lang="zh-Hant"`,
  避免螢幕閱讀器以英文發音規則唸中文。HTML 根層維持 `lang="en"`。

### Service Worker
- CACHE 版本更新為 `find-pax-v2.1-bugfix-20260921`。
- 預快取清單補上 `phone-bottom-icon.png` 與 `disrupted-pax-icon-v2.png`
  (v2.0 說明稱兩張圖已移除,但程式實際仍在使用,會造成離線首次開啟破圖)。

### 本次刻意不改的項目
以下為設計決定或另行處理,非 bug:
- `中文` / `English` 維持上下排列。
- 預覽頁不顯示 Flight status。
- 可編輯與不可編輯的 `CX` 外觀維持相同。
- 時間欄位維持無格式提示文字。
- 情境 1 與情境 3 的圖示相似度,待另行設計。
- Scenario 頁的寫死配色 `#EEF3F7` / `#DDF2F2` 維持原樣。
- `2 Call Pax` 維持直接開啟 WhatsApp,不加確認步驟。


## v2.2 — 移除「記住上次輸入」+ Bug 修正(基於 v2.1)

未更動任何介面文字或 WhatsApp 訊息內容。

### 移除上次輸入自動帶入
- 移除 `localStorage` 的 `fp-order`(原本會記住上次選的 `中文` / `English`);啟動時會順手清掉舊的殘留值。v2.1 內「記住上次選擇」的說明不再適用。
- 所有 `<input>` / `<textarea>` 在 HTML 內直接加上 `autocomplete="off"`,避免瀏覽器在重新整理 / 重開 PWA 時還原表單內容。
- 啟動、`load`、`pageshow`(bfcache 還原)時一律清空所有欄位並回到預設(`CX`、`中文`)。
- 送出 WhatsApp 後重置時,訊息語言順序也回到 `中文`。

### Bug 修正
- 電話貼上:原本 `maxlength=15` 在過濾前計算,貼上 `+886 912 345 678` 這類含空格/加號的號碼會被截掉末幾碼。改為先取純數字再限制 15 位。
- `Flight status` / `Flight arrangement`:切換選項後,先前輸入的無效時間不再讓紅色錯誤提示殘留(此時 Next 其實是可按的)。
- 罐頭號碼紅色警告改放在電話欄正下方(原本因 DOM 順序被圖示擠到畫面最底)。
- 雙指縮放不再被誤判成「鍵盤開啟」而壓縮版面。
- Service Worker 自動重新載入:首次安裝不再重載;只在停在空白 Phone 頁時才切換新版,避免作業中途被重整而遺失已輸入資料。
- `history.go()` 重置後的 `resetting` 旗標加上逾時保護,避免下一次 Back 被吃掉。
- `sw.js`:離線時只有頁面導覽才回退到 `index.html`(不再把 HTML 當成圖片回傳);查詢字串(`?v=8`)不影響快取比對。CACHE 更新為 `find-pax-v2.2-no-carryover-bugfix-20260921`。

## v2.2.1 — 文字調整
- `Pax should arrive airport before ?` → `Ask pax arrive airport before ?`
- `Confirm Details` → `Confirm details`(Call Pax 確認頁與預覽頁)
- 時間欄位標籤 `DEP` → `dep`(該標籤不再強制轉大寫)
- 預覽頁摘要 `To` → `Send to`
- `sw.js` CACHE:`find-pax-v2.2.1-text-20260921`

## v2.2.2 — 文字調整
- 預覽頁 `Protect to ... / DEP` → `/ dep`
- `Not decided yet` → `Arrange in airport`(選項按鈕與預覽頁摘要)
- `sw.js` CACHE:`find-pax-v2.2.2-text-20260921`

## v2.2.3 — Call Pax 不預填訊息
- `2 Call Pax` 開啟 WhatsApp 時不再帶入 `您好`,只開啟對話。
- 情境 1 / 3 / 4 預覽頁第一列為 `Send to`;情境 2 確認頁維持 `Call`。
- `sw.js` CACHE:`find-pax-v2.2.3-call-blank-20260921`

## v2.2.4 — 預覽頁精簡 + 鍵盤偵測補強
- 確認頁(`Confirm details`)標題、摘要列、`Pax Prefer Language` 與中英按鈕的字級/間距縮小,`Message Preview and Edit` 在 iPhone / 一般 Android 上不用捲動即可看到(iPhone SE 也在可視範圍內)。
- `Message Preview and Edit` 改為品牌色外框按鈕,更容易看出可以點開。文字內容不變。
- 鍵盤偵測:改為記錄「未輸入時的最高視窗高度」,並要求目前有輸入框聚焦才判定鍵盤開啟。
  這讓「鍵盤開啟時直接縮小版面」的手機 WebView(例如部分 LINE 內建瀏覽器)也能套用鍵盤避讓,不再只有 visualViewport 縮小的情況才有效。
- 補上 `window.resize` 監聽。
- `sw.js` CACHE:`find-pax-v2.2.4-preview-compact-20260921`

## v2.2.5 — 文字調整
- 確認頁(漏查)摘要列 `SEC` → `sec`
- `sw.js` CACHE:`find-pax-v2.2.5-sec-20260921`

## v2.2.6 — 文字調整
- `2 Call Pax` → `2 Call Passenger`
- `3 Wrongly Pick-up` → `3 Wrong Pick-up`(選單按鈕與流程進度列名稱)
- `sw.js` CACHE:`find-pax-v2.2.6-labels-20260921`

## v2.2.7 — Disrupted Pax 語言按鈕順序
- 4 Disrupted Pax 確認頁:`English` 在上、`中文` 在下。1 漏查 / 3 Wrong Pick-up 維持 `中文` 在上。
- 預設選取仍是 `中文`,訊息內容與排列邏輯不變。
- `sw.js` CACHE:`find-pax-v2.2.7-dp-lang-order-20260921`

## v2.2.8 — 預設語言 = 排在第一個的按鈕
- 4 Disrupted Pax:預設選取 `English`(排第一)。1 漏查 / 3 Wrong Pick-up:預設 `中文`。
- 使用者手動選過語言後,同一次作業內保留其選擇;送出重置後回到預設。
- `sw.js` CACHE:`find-pax-v2.2.8-dp-default-en-20260921`
