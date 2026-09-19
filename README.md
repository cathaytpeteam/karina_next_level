# 漏查 LATE

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
