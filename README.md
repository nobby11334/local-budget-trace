# まちの財政トレース

国の財源、自治体、事業、成果を出典付きでたどる独立した試作。チームみらい・行政の公式サイトではありません。

## 現在の収録範囲

- 全国1,741市区町村の2020〜2024年度の歳入・人口・財政指標（8,705団体年度）。2024年度は総務省原Excel表から再取込し、歳出の目的別・性質別内訳も収録。
- 文京区の2026年度一般会計当初予算を別枠表示。
- 重点支援地方交付金：文京区3事業・氷見市3事業の総事業費、国費充当額、実績、自治体の効果説明。
- 国の重点支援地方交付金：公式RS CSVから予算事業ID 7629、2024年度執行額、支出ブロック・支出先記録を収録。自治体の公表資料との接続は制度名による照合。
- 文京区一般会計の詳細ツリー：2024年度1,654項目、2025年度1,692項目・最大5階層。
- 文京区2024年度：主要施策203見出し、契約先付き4案件、指定管理者12報告の収入実績。
- 全国の最新予算・個別事業・契約先の網羅、都道府県自体の財政、自治体別交付額の全件突合は未実装。対応資料の自動取得は後述。

## 重要な集計上の制約

初版で使用した2026-04-24版Japan Dashboard CSVの歳出項目と、総務省原表の対応にずれを確認しました。例：文京区の教育費総額23,977,958千円が、加工CSVでは教育総務費として現れます。本版は2024年度の原表8ファイルを直接解析して修正。全1,741団体で目的別歳出＝性質別歳出＝概況の歳出総額が一致します。歳入は伊賀市のみ内訳合計が原表総額より1千円大きく、画面に差を表示。総額は概況の値を採用します。

2024年度は特別区財政調整交付金を地方交付税から分離。比率は元表の小数精度を保持し、特別区の財政力指数など原表に記載がない値はnullにしています。2020〜2023年度は従来の加工CSVで、原表再照合は未実施です。

国側RSのシート年度2025と実績年度2024を区別。支出ブロックAは総務省への予算移替えで、ブロックBは地方公共団体への交付です。A+Bを合算しません。支出先合計行と契約行も重複加算しません。Bの支出先は「その他」集約を含むため、個別自治体への金額を推定しません。国と自治体の制度名が同じことと、個別金額が突合できたことは区別します。

一般財源を特定事業へ比例配賦しません。国税・国債等の国側財源内訳は未接続です。

予算、交付決定、交付金充当額、実績報告、決算を同一視しません。実施量と成果、自己評価と独立した効果検証を区別します。年度をまたぐ事業を単年度決算と自動結合しません。

## ファイル

- `dist/index.html`, `style.css`, `app.js`: 依存パッケージなしの静的サイト。
- `dist/finance.json`: 全国財政の加工データ、出典、取得日、原ファイルハッシュ。
- `dist/national.json`: RS事業7629の国側データ、論理レコード番号、出典ZIP・SHA-256。
- `dist/validation.json`: 全国決算照合結果。
- `scripts/import_official_2024.py`: 総務省原表を市区町村コードで結合し、独立総額と検証。
- `scripts/import_rs_program.py`: RS CSVの合計行と明細行を区別して抽出・検証。
- `dist/trace.json`: 手動照合した6事業。金額は円、ページ・行番号を保持。
- `scripts/import_finance.py`: 公開ZIPから展開したCSVを再取込。

更新例：`python scripts/import_finance.py /path/to/extracted/20260424_resources_municipal-finance`

## 全国接続に向けた次の実装

データベースでは以下を別テーブルにします。

1. organizations: 自治体コード、法人番号、組織階層、制度上の区分、有効期間。
2. fiscal_facts: 主体、年度、会計範囲、予算段階、費目、原金額、単位、原資料位置。
3. programs: 国のRS事業ID、制度ID、自治体の事業ID、年度を独立管理。
4. funding_edges: 支払主体、受取主体、事業、金額、決定／支払／実績の区分、直接／間接補助、根拠。
5. outcomes: 指標定義、目標、実績、単位、測定期間、実施量／成果、評価主体、外部要因。
6. evidence: URL、原ファイルハッシュ、ページ、表・行、取得日、抽出法、照合者、改訂履歴。

照合状態は source-confirmed / candidate / unmatched を区別。AI抽出は候補作成までとし、金額と対応関係のレビュー後に確定します。一般財源はプールにとどめます。都道府県経由の補助はエッジを二段で表し、全国集計では内部取引を二重計上しません。

国の交付金制度を一つずつ選び、交付決定一覧→自治体実施計画→実績報告→行政評価の順で接続するのが次の段階です。

## 参考・出典

- https://www.digital.go.jp/resources/japandashboard/municipal-finance
- https://www.digital.go.jp/resources/japandashboard/local-finance-introduction
- https://www.city.bunkyo.lg.jp/b002/p005854.html
- https://www.city.bunkyo.lg.jp/documents/5648/r6-2.pdf
- https://www.city.himi.toyama.jp/material/files/group/11/R6koukakensyo.pdf
- https://www.city.bunkyo.lg.jp/documents/12708/r08_tosyoyosan_sokatsuhyo.pdf

参考サービス https://rs-vis.team-mir.ai/ は外部リンクのみで、コード・AI評価は転載していません。


## 原表再取込

`$CODEX_PRIMARY_RUNTIME_PYTHON scripts/import_official_2024.py /path/to/soumu2024`

必要な原表は総務省ページに掲載された `001061669`〜`001061672` および `001061674`〜`001061677` のxlsx。取り込み元URL・SHA-256は finance.json に保存。

`python scripts/import_rs_program.py /path/to/rs2025`

RS公式サイトの2025年度CSV（1-2, 2-1, 5-1）を展開したディレクトリを指定。合計額と契約金額を別レコードとして処理。

更新順序は Japan Dashboard 基礎データ→総務省2024原表の上書き→RS抽出。前段だけを再実行して公開しないこと。


## 支出ツリー（2024年度）

「支出ツリー」で目的別と性質別を切り替え、枝の開閉・項目検索・全展開・0円項目の表示・円表示・住民1人あたり表示が可能です。目的別には土木費→都市計画費→公園費、性質別には物件費→委託料などを収録。個別事業・契約先・支払先はこの統計細目に含まれません。

再生成：`$CODEX_PRIMARY_RUNTIME_PYTHON scripts/import_spending_tree.py /path/to/soumu2024`

生成物 `dist/spending-tree.json` は共通の階層定義と自治体ごとの列値配列を分離し、ツリーを初めて開いたときに取得します。元表の「うち」の非加算内数を除き、全自治体の各親子・ルート合計で完全一致を検証します。元表の「-」は集計上0として扱います。原データ取得日は2026年11月3日、ツリー機能追加日は11月4日です。

## Individual programs, contracts, and named recipients (2026-11-03)

The new `parties` view includes Bunkyo FY2024: 203 automatically extractable named expense headings from the major-policy overview (PDF pp.10–44), four published excellent daily-service outsourcing contracts, and 12 designated-manager evaluation reports' R6 income columns. This is a partial collection, not a complete program/contract/payment ledger. Separate records with identical names are retained because their scope/amount may differ. Amounts are never summed across these stages, overlapping policy headings, or gross receipts and refunds. Exact accounting-code joins from national financial-statistics tree leaves have not been established.

`dist/transactions.json` stores evidence URLs, physical PDF page numbers, amount types, relevant caveats, and PDF SHA-256 hashes. `scripts/import_bunkyo_parties.py <download-dir>` rebuilds it from `programs2024.pdf` and the 12 `managerN.pdf` files plus the source-URL manifest `managers.json`. Headings with unmapped Latin glyphs or wrapped amount labels are omitted; this is not a full program census. PDF digit CIDs19–28 map to 0–9 and CID15 to comma, checked against the rendered original p.11. Manager amounts are curated from FY2024 income columns and verified against extracted source pages.

The manager directory and FY2024 PDF disagree on the manager of Mejirodai exchange halls: the PDF names Japan Hoiku Service, which is shown with the discrepancy flagged. Gross specified-management-fee income is a recipient-side reported actual, not bank evidence, payer-side transaction verification, or net expenditure; published refunds are noted (housing 61,674,839 yen; Mori Ogai 22,407 yen). Academy and Mori Ogai amounts sum the distinct management-fee components shown on the same income table, with components preserved.

## Detailed local ledger tree (FY2024 Bunkyo general account)

The default expenditure-tree mode for Bunkyo displays the original local account classification, separate from national standardized financial-statistics purpose/nature classifications. It includes all 12 general-account chapters, 1,654 monetary nodes, and up to five levels: chapter, section, item, individual operation, and numbered expense component. It does not include special accounts, every prose-only numerical detail, or inferred joins to contracts/recipient income.

Reproduce with the primary Python runtime (pdfplumber installed):

```
python scripts/import_bunkyo_ledger.py /path/to/2seika.pdf
```

The source is https://www.city.bunkyo.lg.jp/documents/11735/2seika.pdf, physical pp.140–271. PDF text contains duplicate shifted spread layers; the importer retains the first text layer of one instance per spread, uses horizontal position for chapter/section/item levels, verifies duplicate payer-side business amounts across both table halves, and reads numbered subcomponents. One wrapped subcomponent on p.143 is explicitly transcribed and marked in source code. JSON includes amount in exact yen, budget where available, physical source page, hierarchy and PDF SHA-256. The importer asserts 1,654 nodes, 12 chapters, no parse orphans, 367 exact parent-child sum equalities, and chapter sum 135,937,867,776 yen equal to the source general-account total. Summaries and children are never summed together.

UI checks: default opening to general-administration sections; search expands ancestors and matching descendants; exact-yen display; five-level depth selection; expand/collapse all; zero filtering; original PDF anchors; filtered CSV download; mode switching. Local/national identically named categories must not be treated as the same scope without an explicit classification crosswalk.

## GitHub Pagesで公開する

リポジトリの **Settings → Pages → Build and deployment → Source** を **GitHub Actions** に設定してください。`main` へのpush又はActions画面からの手動実行で、`.github/workflows/pages.yml` が静的JavaScriptと会計データを検証し、`dist/` を公開します。対応する公式資料の取得・再集計も自動実行します（対象と停止条件は後述）。

公開先： https://nobby11334.github.io/local-budget-trace/

ローカルで確認する場合：

```sh
python3 scripts/validate_site.py
python3 -m http.server 8000 --directory dist
```

原資料のPDF・Excelはリポジトリに複製せず、出典URLと加工済みデータを収録しています。ソースコードのライセンスは未設定です。第三者資料の利用条件は各出典に従ってください。

## 公式資料の自動取得・更新

`.github/workflows/pages.yml` は **毎週火曜日06:17（日本時間）**、`main`へのpush、手動実行時に公式資料を確認します。更新・公開は同一workflow内で行います。`GITHUB_TOKEN`によるコミットが別のpush workflowを起動しないためです。自動更新は追加のシークレットなしで動きます。

対象：
- 文京区の一般会計詳細：2024・2025年度。決算委員会の一覧から今後の新年度も探索し、対応する表形式と金額照合に通ったものを自動追加。
- 全国2024年度：原表8Excelの修正版を再取得し、収録済みの抽出方式で再集計。
- 新年度の全国統計：公表リンクを検知して`needsAction`へ記録。年度固有の列構造の確認前には取り込まない。
- 契約先・指定管理者収入・交付金事業の個別レコード・RSデータは自動更新対象外。これらの収録年度は変えません。

`config/update-sources.json` に公式ソースを定義し、`scripts/auto_update.py` で取得・ハッシュ比較・ステージング・検証を行います。同一ハッシュのPDFは再解析しません。PDF表紙の年度、款・項・目の位置、個別業務の左右表の同額、全款合計と原資料の歳出総額、すべての親子合計を確認します。解析や金額照合に失敗したらステージを破棄し、コミット・公開を行いません。全国統計の一時的な取得エラーは旧データを維持し、その旨を記録して独立した文京区更新を継続できます。

成功時は取得結果・SHA-256・対応年度を`dist/update-status.json`と`dist/ledger-index.json`に記録し、公開画面にも確認時刻を表示します。詳細な失敗はActionsのログ、取得元の一時障害・新年度の取込待ちは公開JSONとStep Summaryで確認できます。GitHubの定期実行は時刻の厳密な保証がなく、混雑による遅延・リポジトリの非活動による停止等はGitHub側の仕様に従います。

ローカル実行：
```sh
python -m pip install -r requirements-update.txt
python -m unittest discover -s tests -v
python scripts/auto_update.py
```

2025年度の一般会計は1,692項目、369か所の親子合計と原資料歳出総額163,012,648,296円を照合しています。全国統計の表示年度と自治体詳細の年度は別々に選択します。

### 2025年度決算の全国速報（2026-11-04追加）

専用の「2025年度速報」画面で表示。完全な内訳を持つ全国統計年度（2020～2024）とは別に扱います。

- 全国47都道府県・1,741市区町村：総務省「令和7年度決算に基づく健全化判断比率・資金不足比率の概要（速報）」（2026-09-29）のExcelシート `1(2)` から、4つの健全化判断比率を収録。資金不足比率・公営企業別明細は今回の対象外。
- 大阪府41団体：2025年度普通会計の歳入・歳出総額、実質収支、経常収支比率。大阪市・堺市を除く。原表単位は百万円、丸め誤差を明示。
- 福岡県60団体：同じ項目を収録。原表単位は千円。歳入・歳出の県計と60団体合計を検証。
- 全国の2025年度税収内訳・目的別／性質別歳出詳細表は未収録。他県の総額は「未収録」であり、未公表を意味しません。全国の2025年度詳細ツリーが揃ったという表示はしません。
- `dist/latest-2025.json` に原表の数値・単位・行番号・URL・SHA-256を保持。「―」をゼロに変換せず、梼原町／檮原町のみ明示的に字体対応。自治体名のあいまい一致は使用しません。
- `scripts/import_latest_2025.py` は毎週の既存更新処理から実行。3原表の訂正を確認し、ネットワーク障害では前回の2025年度データ全体を保持。年度・列・単位・団体数・合計の不一致は公開前に停止。
- 速報値であり、後日の精査で変わる可能性があります。健全化判断比率を政策成果の評価には使用しません。CSVにも年度・単位・出典・速報を付記。
