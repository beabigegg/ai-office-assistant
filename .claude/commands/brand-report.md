---
name: brand-report
description: |
  公司品牌報告路由。適用於需要 Panjit 品牌母片、公司色盤、內部報告慣例
  或公司標準版型的報告任務。
---

產出公司品牌格式報告：

1. 先判斷任務是否屬 generic Office generation，必要時先交給 `office-report-engine`
2. 若明確需要公司品牌母片、公司色彩或內部交付慣例，使用 `report-builder` agent
3. 由 `report-builder` 決定是否切到 `pptx-brand-master`、Marp 混合流程、或 generic route
4. 完成後回報最終路由、輸出檔路徑、驗證結果

步驟：
- generic Excel/Word/PPT 建立或修改先考慮 `office-report-engine`
- 若需求明示公司品牌母片、Panjit 視覺語言或內部格式慣例，使用 `report-builder` agent
- 若是 PPT 公司母片任務，依 `report-builder` 指引讀取 `pptx-brand-master` skill
- 回報是否走 overlay 路由，以及最終輸出結果
