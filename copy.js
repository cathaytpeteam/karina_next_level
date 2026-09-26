// Find Pax copy and rule data. Stable IDs are hash-locked by the release verifier.
(function(){
  "use strict";
  window.FIND_PAX_COPY = Object.freeze({
  "s.passenger.joining": "Joining Passenger",
  "s.passenger.transit": "Transit Passenger",
  "progress.flow.miss": "漏查",
  "progress.flow.call": "Final Call",
  "progress.flow.wpp": "Wrong Pick-up",
  "progress.flow.dp": "Disrupted Pax",
  "progress.flow.direct": "Call Directly",
  "progress.dp.possible": "Tight connection",
  "progress.dp.delayed": "Flight delayed",
  "progress.dp.unknown": "Flight Suspended",
  "progress.dp.gate": "Already at Gate",
  "label.bag.unclaimed": "無人領取的行李",
  "label.preview.language": "Language",
  "label.preview.jaOnly": "日本語のみ",
  "label.preview.enFirst": "English first",
  "label.preview.zhFirst": "中文在前",
  "label.view.open": "View ▴",
  "label.view.closed": "View ▾",
  "cta.sms.ja": "SMSを送信",
  "cta.whatsapp.call": "Call on WhatsApp",
  "cta.whatsapp.send": "Send on WhatsApp",
  "cta.next": "Next",
  "hint.time.empty": "HHMM",
  "hint.time.partial": "HHMM, for example 0811",
  "error.time.invalid": "Invalid time (00:00–23:59)",
  "hint.airline.letters": "Airline code: 2 letters",
  "hint.airline.carrier": "Airline code: 2 letters/digits",
  "hint.flight.digits": "1–3 digits",
  "hint.flight.number": "Flight number: 1–3 digits",
  "hint.bag.six": "6 digits",
  "hint.phone.invalid": "Invalid or incomplete phone number",
  "error.phone.blocked": "罐頭號碼 無用",
  "hint.sec.range": "0–580",
  "error.sec.max": "Max 580",
  "error.flight.tpe": "Departs TPE — not allowed",
  "error.protect.same": "Same as Flight from TPE — not allowed",
  "error.protect.tpe": "CX flight must depart TPE",
  "hint.preview.check": "Check details before sending",
  "hint.transit.cx": "Transit: CX450 / CX451 / CX530 / CX531 / CX564 / CX565",
  "rules.cx.general": [
    "407",
    "489",
    "477",
    "499",
    "461",
    "450",
    "564",
    "530",
    "495",
    "443",
    "421",
    "473",
    "565",
    "451",
    "531",
    "479",
    "469",
    "463",
    "465",
    "401",
    "403"
  ],
  "rules.cx.transit": [
    "450",
    "451",
    "530",
    "531",
    "564",
    "565"
  ],
  "rules.cx.nonTpeOriginTransit": [
    "450",
    "530",
    "564"
  ],
  "rules.sec.max": 580,
  "rules.sec.homeIata": "TPE",
  "rules.sec.prefixes": {
    "450": {
      "join": "TPE",
      "transit": "HKG"
    },
    "530": {
      "join": "TPE",
      "transit": "HKG"
    },
    "564": {
      "join": "TPE",
      "transit": "HKG"
    },
    "451": {
      "join": "TPE",
      "transit": "NRT"
    },
    "531": {
      "join": "TPE",
      "transit": "NGO"
    },
    "565": {
      "join": "TPE",
      "transit": "KIX"
    }
  },
  "rules.transit.origins": {
    "450": "HKG",
    "530": "HKG",
    "564": "HKG",
    "451": "NRT",
    "531": "NGO",
    "565": "KIX"
  },
  "rules.transit.destinations": {
    "450": {
      "zh": "東京成田",
      "en": "Tokyo Narita",
      "ja": "東京（成田）"
    },
    "564": {
      "zh": "大阪關西",
      "en": "Osaka Kansai",
      "ja": "大阪（関西）"
    },
    "530": {
      "zh": "名古屋中部",
      "en": "Nagoya Chubu",
      "ja": "名古屋（中部）"
    },
    "451": {
      "zh": "香港",
      "en": "Hong Kong",
      "ja": "香港"
    },
    "565": {
      "zh": "香港",
      "en": "Hong Kong",
      "ja": "香港"
    },
    "531": {
      "zh": "香港",
      "en": "Hong Kong",
      "ja": "香港"
    }
  },
  "rules.transit.destinationCodes": {
    "450": "NRT",
    "564": "KIX",
    "530": "NGO",
    "451": "HKG",
    "565": "HKG",
    "531": "HKG"
  },
  "rules.transit.smsRouteJa": {
    "450": {
      "from": "香港",
      "to": "東京"
    },
    "530": {
      "from": "香港",
      "to": "名古屋"
    },
    "564": {
      "from": "香港",
      "to": "大阪"
    },
    "451": {
      "from": "東京",
      "to": "香港"
    },
    "531": {
      "from": "名古屋",
      "to": "香港"
    },
    "565": {
      "from": "大阪",
      "to": "香港"
    }
  },
  "rules.gate.zones": [
    "B",
    "C"
  ],
  "rules.gate.b1rZone": "B",
  "rules.gate.b1rNumber": "1R",
  "s1.join.zh": "您好，這裡是國泰航空桃園機場辦事處。\n\n由於桃園機場安檢人員發現您的寄艙行李內可能含有不可寄艙的物品，須請您在場一同進行開箱檢查，並視乎結果將有關物品改為手提或棄置。因此，您的行李目前暫時留於辦理登機手續櫃位旁安檢處，尚未能安排裝載上機。如您：\n\n⦁ 尚未進入離境禁區：請即返回 4 號辦理登機手續櫃位，與我們的職員聯絡。\n\n⦁ 已進入離境禁區：如尚未通過離境檢查，請在辦理離境手續或通過 e-Gate 之前，向桃園機場職員說明情況，再返回確認您的行李。\n\n⦁ 已通過離境檢查：請前往 CX{flight_number} 航班登機閘口等候國泰航空職員，我們會協助您跟進。\n\n請注意：如您未能返回辦理登機手續櫃位旁安檢處，而上述物品經確認不符合桃園機場寄艙行李保安規定，有關物品將需要棄置，國泰航空無法代為轉交、存放或保管。\n\n為確保您的行李能在航班起飛前完成檢查並安排裝載，請您盡快返回或聯絡國泰航空職員，多謝您的理解及配合。",
  "s1.join.en": "Hello, this is Cathay Pacific at Taoyuan Airport.\n\nAirport Security found an item in your checked baggage that may not be permitted. It must be opened and inspected in your presence, and the item will then be moved to your hand baggage or disposed of. Your baggage is being held at the security area beside the check-in counter and cannot be loaded yet. If you:\n\n⦁ Have not entered the departure area: Please return to Counter 4 immediately and contact our staff.\n\n⦁ Are in the departure area but have not passed immigration: Please inform airport staff before using immigration or the e-Gates, then return to have your baggage checked.\n\n⦁ Have passed immigration: Please go to the CX{flight_number} gate and wait for our staff, who will assist you.\n\nNote: If you cannot return and the item is confirmed not to be permitted in checked baggage, it will need to be disposed of. We regret that Cathay Pacific is unable to forward, store or keep the item for you.\n\nPlease return or contact our staff as soon as possible so that your baggage can be inspected and loaded before departure. Thank you for your understanding and cooperation.",
  "s1.join.ja": "【キャセイパシフィック航空】預け手荷物のX線再検査に立会いが必要です。出国審査前は至急4番カウンターへ。保安検査後・出国審査前は係員に申し出て4番へお戻りください。出国審査後はゲート係員にお申し出ください。お越しいただけない場合、荷物が搭載できない可能性があります。",
  "s1.transit.zh": "您好：這裡是國泰航空桃園機場辦公室。\n\n由於您的寄艙行李未能通過桃園機場的轉機X 光安全檢查。因此，您的行李目前暫時留在\n轉機行李檢查處，未能安排裝載上機。\n\n為了確保您的行李可以在航班起飛前順利完成檢查並安排裝載，麻煩您盡快返回登機閘口聯繫國泰航空職員，我們會協助您跟進。\n\n多謝您的理解和配合",
  "s1.transit.en": "Hello, this is Cathay Pacific at Taoyuan Airport.\n\nYour checked baggage did not pass the transfer X-ray security screening and is currently being held at the screening area.\n\nPlease return to the boarding gate as soon as possible and contact our staff for assistance, so we can arrange for your baggage to be loaded before departure.\n\nThank you for your cooperation.",
  "s1.transit.ja": "【キャセイパシフィック航空】お預け手荷物は桃園空港の乗り継ぎX線検査で確認が必要です。至急搭乗ゲートのスタッフまでお申し出ください。",
  "s2.join.zh": "最後召集：乘搭 {Flight}航班前往 {DestinationZh} 的旅客，登機閘口為 {Gate}。請您立即前往 {Gate} 號登機閘口登機，登機將於起飛前 15 分鐘截止。國泰航空敬上",
  "s2.join.en": "FINAL CALL: Passengers on flight {Flight} to {DestinationEn}, your boarding gate is {Gate}. Please go to Gate {Gate} immediately for boarding. Boarding closes 15 minutes before departure. Cathay Pacific",
  "s2.join.ja": "【キャセイパシフィック航空】{Flight}便は最終搭乗案内中です。搭乗口は出発15分前に締め切ります。至急{Gate}番搭乗口へお越しください。",
  "s2.transit.zh": "最後召集：乘搭 {Flight}航班前往 {DestinationZh} 的旅客，登機閘口為 {Gate}。請您立即前往 {Gate} 號登機閘口登機，登機將於起飛前 15 分鐘截止。您須先通過轉機區隨身行李保安檢查。國泰航空敬上。",
  "s2.transit.en": "FINAL CALL: Passengers on flight {Flight} to {DestinationEn}, your boarding gate is {Gate}. Please go to Gate {Gate} immediately for boarding. Boarding closes 15 minutes before departure. You must first pass the transfer security check for carry-on baggage. Cathay Pacific.",
  "s2.transit.ja": "【キャセイパシフィック航空】{Flight}便（{OriginJa}発・台北経由{DestinationJaShort}行き）は{Gate}番搭乗口で最終案内中です。台湾の入国審査へは進まず、到着された方向へお戻りいただき、桃園空港の乗り継ぎ保安検査場で手荷物検査を受け、至急搭乗口へお越しください。台北時間{TaipeiTime}現在。",
  "s3.zh": "您好：\n\n這是桃園機場國泰航空行李辦公室。\n\n我們發現一件搭乘 {Arrival Flight} 抵達台北後無人領取的行李，該行李的行李牌號碼 {Bag Tag 1} 登記於您的名下。\n\n目前另有一名旅客正在尋找一件外觀相似的行李。\n\n請您協助確認您所領取的行李，其行李牌號碼是否為 {Bag Tag 2}？\n\n您也可以直接拍攝您所領取行李的行李牌照片並傳送給我們確認。\n\n為了避免耽誤您的行程，請您務必儘速聯絡我們，以確保您拿到的是正確的行李。\n\nEmail: tpe8bag@cathaypacific.com\nTel: +88627727630\n\n謝謝您的配合。",
  "s3.en": "Hello,\n\nThis is the Cathay Pacific Baggage Services Office at Taoyuan Airport.\n\nWe found one piece of unclaimed baggage from {Arrival Flight} arriving in Taipei. The baggage tag number {Bag Tag 1} is registered under your name.\n\nAnother passenger is currently looking for a similar bag.\n\nCould you please confirm whether the baggage you collected has the baggage tag number {Bag Tag 2}?\n\nYou may also simply take a photo of the baggage tag on the bag you collected and send it to us for verification.\n\nTo avoid any disruption to your journey, please contact us as soon as possible so that we can ensure you have collected the correct baggage.\n\nEmail: tpe8bag@cathaypacific.com\nTel: +88627727630\n\nThank you for your cooperation.",
  "s4.zh.possible.known": "您好：\n這裡是國泰航空桃園機場辦公室\n\n由於您前往香港的{Disrupted Flight}航班，在香港轉機時間較為緊湊，因此，如果台灣往香港航班如果有延誤，可能會影響到您在香港轉機的第二程{Connecting Flight} 航班，我們很樂意為閣下提供提早出發的台灣往香港航班選擇：{Alternative Flight} 航班，起飛時間為{Alternative Departure Time}。\n\n如果您能在{Arrive Airport Before}前抵達機場，我們可以為您更改航班提早出發前往香港，抵達香港後的續程航班則不做更改。\n\n我們在桃園機場第一航廈4號櫃檯，請您到達機場後直接與櫃檯職員聯繫。\n\n多謝您的理解和配合。",
  "s4.zh.possible.airport": "您好：\n這裡是國泰航空桃園機場辦公室\n\n由於您前往香港的{Disrupted Flight}航班，在香港轉機時間較為緊湊，因此，如果台灣往香港航班如果有延誤，可能會影響到您在香港轉機的第二程{Connecting Flight} 航班，我們很樂意為閣下提供提早出發的台灣往香港航班選擇。\n\n如果您能在{Arrive Airport Before}前抵達機場，我們可以為您更改航班提早出發前往香港，抵達香港後的續程航班則不做更改。\n\n我們在桃園機場第一航廈4號櫃檯，請您到達機場後直接與櫃檯職員聯繫。\n\n多謝您的理解和配合。",
  "s4.zh.delayed.known": "您好：\n\n這裡是國泰航空桃園機場辦公室\n\n由於您前往香港的{Disrupted Flight}航班，目前已經延遲至{Delay Time}，因此會影響您在香港轉機的行程 {Connecting Flight} 航班，我們將會為您安排替代的航班{Alternative Flight}，起飛時間為{Alternative Departure Time}。\n\n如果您能在{Arrive Airport Before}前抵達機場，我們可以為您更改航班提早出發前往香港，抵達香港後的續程航班則不做更改。\n\n我們在桃園機場第一航廈4號櫃檯，請您到達機場後直接與櫃檯職員聯繫。\n\n多謝您的理解和配合。",
  "s4.zh.delayed.airport": "您好：\n\n這裡是國泰航空桃園機場辦公室\n\n由於您前往香港的{Disrupted Flight}航班，目前已經延遲至{Delay Time}，因此會影響您在香港轉機的行程 {Connecting Flight} 航班，我們很樂意為閣下提供提早出發的台灣往香港航班選擇。\n\n如果您能在{Arrive Airport Before}前抵達機場，我們可以為您更改航班提早出發前往香港，抵達香港後的續程航班則不做更改。\n\n我們在桃園機場第一航廈4號櫃檯，請您到達機場後直接與櫃檯職員聯繫。\n\n多謝您的理解和配合。",
  "s4.zh.unknown.known": "您好：\n\n這裡是國泰航空桃園機場辦公室\n\n由於您前往香港的{Disrupted Flight}航班，目前航班及起飛動態尚未確定，因此會影響到您在香港轉機的行程 {Connecting Flight} 航班，我們將會為您安排替代的航班{Alternative Flight}，起飛時間為{Alternative Departure Time}。\n\n如果您能在{Arrive Airport Before}前抵達機場，我們可以為您更改航班提早出發前往香港，抵達香港後的續程航班則不做更改。\n\n我們在桃園機場第一航廈4號櫃檯，請您到達機場後直接與櫃檯職員聯繫。\n\n多謝您的理解和配合。",
  "s4.zh.unknown.airport": "您好：\n\n這裡是國泰航空桃園機場辦公室\n\n由於您前往香港的{Disrupted Flight}航班，目前航班及起飛動態尚未確定，因此會影響到您在香港轉機的行程 {Connecting Flight} 航班，我們很樂意為閣下提供提早出發的台灣往香港航班選擇。\n\n如果您能在{Arrive Airport Before}前抵達機場，我們可以為您更改航班提早出發前往香港，抵達香港後的續程航班則不做更改。\n\n我們在桃園機場第一航廈4號櫃檯，請您到達機場後直接與櫃檯職員聯繫。\n\n多謝您的理解和配合。",
  "s4.en.possible.known": "Hello,\n\nThis is Cathay Pacific at Taoyuan Airport.\n\nTo allow more time for your connection in Hong Kong, as any delay to your flight {Disrupted Flight} from Taiwan to Hong Kong may affect your onward flight {Connecting Flight}, we would be pleased to offer you the option of taking an earlier flight from Taiwan to Hong Kong — {Alternative Flight}, departing at {Alternative Departure Time}.\n\nIf you are able to arrive at the airport before {Arrive Airport Before}, we can change your flight to an earlier departure to Hong Kong. Your onward flight from Hong Kong will remain unchanged.\n\nWe are located at Counter 4, Terminal 1 of Taoyuan Airport. Please contact our staff at the counter directly when you arrive at the airport.\n\nThank you for your understanding and cooperation.",
  "s4.en.possible.airport": "Hello,\n\nThis is Cathay Pacific at Taoyuan Airport.\n\nTo allow more time for your connection in Hong Kong, as any delay to your flight {Disrupted Flight} from Taiwan to Hong Kong may affect your onward flight {Connecting Flight}, we would be pleased to offer you the option of taking an earlier flight from Taiwan to Hong Kong.\n\nIf you are able to arrive at the airport before {Arrive Airport Before}, we can change your flight to an earlier departure to Hong Kong. Your onward flight from Hong Kong will remain unchanged.\n\nWe are located at Counter 4, Terminal 1 of Taoyuan Airport. Please contact our staff at the counter directly when you arrive at the airport.\n\nThank you for your understanding and cooperation.",
  "s4.en.delayed.known": "Hello,\n\nThis is Cathay Pacific at Taoyuan Airport.\n\nYour flight {Disrupted Flight} to Hong Kong is currently delayed until {Delay Time}, which may affect your onward flight {Connecting Flight} from Hong Kong. We will arrange an alternative flight {Alternative Flight}, departing at {Alternative Departure Time}.\n\nIf you are able to arrive at the airport before {Arrive Airport Before}, we can change your flight to an earlier departure to Hong Kong. Your onward flight from Hong Kong will remain unchanged.\n\nWe are located at Counter 4, Terminal 1 of Taoyuan Airport. Please contact our staff at the counter directly when you arrive at the airport.\n\nThank you for your understanding and cooperation.",
  "s4.en.delayed.airport": "Hello,\n\nThis is Cathay Pacific at Taoyuan Airport.\n\nYour flight {Disrupted Flight} to Hong Kong is currently delayed until {Delay Time}, which may affect your onward flight {Connecting Flight} from Hong Kong. We would be pleased to offer you the option of taking an earlier flight from Taiwan to Hong Kong.\n\nIf you are able to arrive at the airport before {Arrive Airport Before}, we can change your flight to an earlier departure to Hong Kong. Your onward flight from Hong Kong will remain unchanged.\n\nWe are located at Counter 4, Terminal 1 of Taoyuan Airport. Please contact our staff at the counter directly when you arrive at the airport.\n\nThank you for your understanding and cooperation.",
  "s4.en.unknown.known": "Hello,\n\nThis is Cathay Pacific at Taoyuan Airport.\n\nThe current status and departure time of your flight {Disrupted Flight} to Hong Kong have not yet been confirmed, which may affect your onward flight {Connecting Flight} from Hong Kong. We will arrange an alternative flight {Alternative Flight}, departing at {Alternative Departure Time}.\n\nIf you are able to arrive at the airport before {Arrive Airport Before}, we can change your flight to an earlier departure to Hong Kong. Your onward flight from Hong Kong will remain unchanged.\n\nWe are located at Counter 4, Terminal 1 of Taoyuan Airport. Please contact our staff at the counter directly when you arrive at the airport.\n\nThank you for your understanding and cooperation.",
  "s4.en.unknown.airport": "Hello,\n\nThis is Cathay Pacific at Taoyuan Airport.\n\nThe current status and departure time of your flight {Disrupted Flight} to Hong Kong have not yet been confirmed, which may affect your onward flight {Connecting Flight} from Hong Kong. We would be pleased to offer you the option of taking an earlier flight from Taiwan to Hong Kong.\n\nIf you are able to arrive at the airport before {Arrive Airport Before}, we can change your flight to an earlier departure to Hong Kong. Your onward flight from Hong Kong will remain unchanged.\n\nWe are located at Counter 4, Terminal 1 of Taoyuan Airport. Please contact our staff at the counter directly when you arrive at the airport.\n\nThank you for your understanding and cooperation.",
  "s4.zh.gate.delayed.original.asap": "您好：這裡是國泰航空桃園機場辦事處。\n由於您乘搭的 {Disrupted Flight} 航班現已延誤至 {Delay Time}，我們可為您安排改搭 {New Flight} 航班前往{DestinationZh}（預定起飛時間為 {Dep Time}）。請盡快前往 {Disrupted Flight} 航班登機閘口與國泰航空職員聯絡。\n多謝您的理解及配合。",
  "s4.zh.gate.delayed.original.wait": "您好：這裡是國泰航空桃園機場辦事處。\n由於您乘搭的 {Disrupted Flight} 航班現已延誤至 {Delay Time}，我們可為您安排改搭 {New Flight} 航班前往{DestinationZh}（預定起飛時間為 {Dep Time}）。請前往 {Disrupted Flight} 航班登機閘口等候國泰航空職員，我們會協助您辦理。\n多謝您的理解及配合。",
  "s4.zh.gate.delayed.new.asap": "您好：這裡是國泰航空桃園機場辦事處。\n由於您乘搭的 {Disrupted Flight} 航班現已延誤至 {Delay Time}，我們可為您安排改搭 {New Flight} 航班前往{DestinationZh}（預定起飛時間為 {Dep Time}）。如欲乘搭此航班，請盡快前往 {New Flight} 航班 {Gate} 號登機閘口與國泰航空職員聯絡。\n多謝您的理解及配合。",
  "s4.zh.gate.delayed.new.wait": "您好：這裡是國泰航空桃園機場辦事處。\n由於您乘搭的 {Disrupted Flight} 航班現已延誤至 {Delay Time}，我們可為您安排改搭 {New Flight} 航班前往{DestinationZh}（預定起飛時間為 {Dep Time}）。如欲乘搭此航班，請前往 {New Flight} 航班 {Gate} 號登機閘口等候國泰航空職員，我們會協助您辦理。\n多謝您的理解及配合。",
  "s4.zh.gate.cancelled.original.asap": "您好：這裡是國泰航空桃園機場辦事處。\n由於您乘搭的 {Disrupted Flight} 航班已取消，我們可為您安排改搭 {New Flight} 航班前往{DestinationZh}（預定起飛時間為 {Dep Time}）。請盡快前往 {Disrupted Flight} 航班登機閘口與國泰航空職員聯絡。\n多謝您的理解及配合。",
  "s4.zh.gate.cancelled.original.wait": "您好：這裡是國泰航空桃園機場辦事處。\n由於您乘搭的 {Disrupted Flight} 航班已取消，我們可為您安排改搭 {New Flight} 航班前往{DestinationZh}（預定起飛時間為 {Dep Time}）。請前往 {Disrupted Flight} 航班登機閘口等候國泰航空職員，我們會協助您辦理。\n多謝您的理解及配合。",
  "s4.zh.gate.cancelled.new.asap": "您好：這裡是國泰航空桃園機場辦事處。\n由於您乘搭的 {Disrupted Flight} 航班已取消，我們可為您安排改搭 {New Flight} 航班前往{DestinationZh}（預定起飛時間為 {Dep Time}）。如欲乘搭此航班，請盡快前往 {New Flight} 航班 {Gate} 號登機閘口與國泰航空職員聯絡。\n多謝您的理解及配合。",
  "s4.zh.gate.cancelled.new.wait": "您好：這裡是國泰航空桃園機場辦事處。\n由於您乘搭的 {Disrupted Flight} 航班已取消，我們可為您安排改搭 {New Flight} 航班前往{DestinationZh}（預定起飛時間為 {Dep Time}）。如欲乘搭此航班，請前往 {New Flight} 航班 {Gate} 號登機閘口等候國泰航空職員，我們會協助您辦理。\n多謝您的理解及配合。",
  "s4.en.gate.delayed.original.asap": "Hello, this is Cathay Pacific at Taoyuan Airport.\nYour flight {Disrupted Flight} is now delayed to {Delay Time}. We can arrange for you to take flight {New Flight} to {DestinationEn} (scheduled departure {Dep Time}). Please proceed to the gate for flight {Disrupted Flight} as soon as possible and contact our staff.\nThank you for your understanding and cooperation.",
  "s4.en.gate.delayed.original.wait": "Hello, this is Cathay Pacific at Taoyuan Airport.\nYour flight {Disrupted Flight} is now delayed to {Delay Time}. We can arrange for you to take flight {New Flight} to {DestinationEn} (scheduled departure {Dep Time}). Please go to the gate for flight {Disrupted Flight} and wait for our staff, who will assist you.\nThank you for your understanding and cooperation.",
  "s4.en.gate.delayed.new.asap": "Hello, this is Cathay Pacific at Taoyuan Airport.\nYour flight {Disrupted Flight} is now delayed to {Delay Time}. We can arrange for you to take flight {New Flight} to {DestinationEn} (scheduled departure {Dep Time}). If you would like to take this flight, please proceed to Gate {Gate} for flight {New Flight} as soon as possible and contact our staff.\nThank you for your understanding and cooperation.",
  "s4.en.gate.delayed.new.wait": "Hello, this is Cathay Pacific at Taoyuan Airport.\nYour flight {Disrupted Flight} is now delayed to {Delay Time}. We can arrange for you to take flight {New Flight} to {DestinationEn} (scheduled departure {Dep Time}). If you would like to take this flight, please go to Gate {Gate} for flight {New Flight} and wait for our staff, who will assist you.\nThank you for your understanding and cooperation.",
  "s4.en.gate.cancelled.original.asap": "Hello, this is Cathay Pacific at Taoyuan Airport.\nYour flight {Disrupted Flight} has been cancelled. We can arrange for you to take flight {New Flight} to {DestinationEn} (scheduled departure {Dep Time}). Please proceed to the gate for flight {Disrupted Flight} as soon as possible and contact our staff.\nThank you for your understanding and cooperation.",
  "s4.en.gate.cancelled.original.wait": "Hello, this is Cathay Pacific at Taoyuan Airport.\nYour flight {Disrupted Flight} has been cancelled. We can arrange for you to take flight {New Flight} to {DestinationEn} (scheduled departure {Dep Time}). Please go to the gate for flight {Disrupted Flight} and wait for our staff, who will assist you.\nThank you for your understanding and cooperation.",
  "s4.en.gate.cancelled.new.asap": "Hello, this is Cathay Pacific at Taoyuan Airport.\nYour flight {Disrupted Flight} has been cancelled. We can arrange for you to take flight {New Flight} to {DestinationEn} (scheduled departure {Dep Time}). If you would like to take this flight, please proceed to Gate {Gate} for flight {New Flight} as soon as possible and contact our staff.\nThank you for your understanding and cooperation.",
  "s4.en.gate.cancelled.new.wait": "Hello, this is Cathay Pacific at Taoyuan Airport.\nYour flight {Disrupted Flight} has been cancelled. We can arrange for you to take flight {New Flight} to {DestinationEn} (scheduled departure {Dep Time}). If you would like to take this flight, please go to Gate {Gate} for flight {New Flight} and wait for our staff, who will assist you.\nThank you for your understanding and cooperation."
});
})();
