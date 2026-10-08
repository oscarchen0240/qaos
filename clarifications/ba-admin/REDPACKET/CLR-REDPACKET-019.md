# CLR-REDPACKET-019：紅包入帳（分數增加）與場次的關係：最後一局輸光使場次歸零結束後才開啟紅包，分數由 0 轉正時是否建立新場次；紅包入帳歸屬哪個場次（紅包明細的場次編號是產生當下的場次，可能與入帳時不同）；場館日結報表「依場次明細」維度的期初／期末餘額是否含紅包

- 產品 / 功能：ba-admin / REDPACKET
- 規格：SPEC-REDPACKET-001 v0.1  §§線上與機台的差異 L31
- 相關需求：REQ-REDPACKET-025
- 提出者：agent-spec-analyst（2026-10-08）
- 狀態：OPEN

## 背景
REQ-REDPACKET-025：機台帳號為一台機台所有玩家共用，紅包在機台場館屬於機台、不屬於玩家：累計是整台機台跨玩家的流水，達標當下坐在台前的人開啟並取得。參加對象為該場館所有機台帳號（不參與會員等級），僅預設規則且固定開啟；活動幣種固定 TWD 不顯示；派發幣種為核心貨幣 TWD。

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
依賴此決策點的斷言只能 exploratory，或不能引用衝突的任何一側

## 已查文件
- SPEC-REDPACKET-001 v0.1（590d35efdb11…）
- SPEC-SYSADMIN-001 v0.1（688ddf35ab03…）
- SPEC-REPORTS-001 v0.1（a4ec6b0d93ef…）
- SPEC-SITELIST-001 v0.6（b57f48c699cc…）
- SPEC-PLATFORMRULE-001 v0.2（b36b764b7756…）
- SPEC-DAILYREPORT-001 v0.2（7930c1fb9c11…）
- SPEC-ARCADE-001 v0.7（0e216890e8a3…）
- SPEC-COMMON-001 v0.2（d31569007fd5…）

## 已確定的部分
- SPEC-ARCADE-001 v0.7 §場次（第 510 行）：「開分或入金完成使分數由 0 轉為有餘額，建立新場次」
- SPEC-ARCADE-001 v0.7 §場次（第 513 行）：「| 歸零結束 | 分數因投注輸完歸 0 時結束 |」

## 還需決定的事
紅包入帳（分數增加）與場次的關係：最後一局輸光使場次歸零結束後才開啟紅包，分數由 0 轉正時是否建立新場次；紅包入帳歸屬哪個場次（紅包明細的場次編號是產生當下的場次，可能與入帳時不同）；場館日結報表「依場次明細」維度的期初／期末餘額是否含紅包
- 細節：new_session_on_redpacket_credit
- 細節：credit_session_attribution
- 細節：session_dimension_balance

## PM 回覆
（待回覆）

