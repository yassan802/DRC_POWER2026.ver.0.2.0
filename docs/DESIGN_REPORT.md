# 主電源基板 回路図作成報告

2026年11月17日。仕様書 Rev 1.2 と、このチャットで確定した条件を適用した。

既存の `DRC_POWER2026.ver.0.2.0.kicad_pro` に接続する10シートの回路図を作成した。基板上124部品、うち任意実装の出力電解2個をDNPとし、全品にフットプリントを割り当てた。KiCad 9.0.0のERCはエラー0、警告0、除外0。KiCadから出力したネットリストとライブラリに対する271項目の照合も全件合格した。全10ページをPDFから画像化して目視確認し、文字・端子名・配線の重なりを修正した。DP修正後は変更した3シートを再確認し、その他7シートは目視確認済み画像との一致を確認した。

2026年11月17日の追加指示により、XT60採用継続、USB単独給電の許容、MCU電源4.436V以上を設計条件として確定した。OSL10326-LのDPは旧回路の誤接続を修正した。前版の「DP極性が資料内で矛盾する」という記載は、独立したDP端子を読み違えたため撤回する。PCBの配置配線・放熱設計、ファームウェア、実機試験は今回の成果物に含まない。

## 保存した成果物

| ファイル | 内容 |
|---|---|
| `../DRC_POWER2026.ver.0.2.0.kicad_pro` | 編集対象の既存プロジェクト |
| `../DRC_POWER2026.ver.0.2.0.kicad_sch` | 全体構成と階層シートへの入口 |
| `main_power_schematic.pdf` | 全10シートの閲覧用回路図 |
| `BOM.csv` | 基板上の発注型番、定数・耐圧、実装区分、DNP、既知のLCSC番号 |
| `OFFBOARD_BOM.csv` | 外付けヒューズ・ホルダ等 |
| `MCU_PIN_ASSIGNMENT.csv` | MCU全64端子の信号名・機能・使用状態 |
| `ERC.json` / `ERC.rpt` | 実際のKiCad ERC結果 |
| `CONNECTIVITY_AUDIT.json` | 出力ネットリストの接続と仕様定数の照合結果 |
| `PIN_PAD_AUDIT.csv` | 全124部品のシンボル端子とパッド番号の一致確認 |
| `LIBRARY_VERIFICATION.md` / `library_sources.json` | 出典、寸法・端子照合、作成・変更内容 |
| `../lib/` | プロジェクト専用シンボルとフットプリント |
| `original/` | 編集前のプロジェクト・空回路図・基板の保存コピー |

既存の `.kicad_pro` と `.kicad_pcb` は保存コピーとバイト単位で一致する。PCBは従前の状態であり、100×80mm・4層・外層1ozのレイアウトを完成した状態ではない。既存回路図ファイルをルートとして使用し、追加シートは同じプロジェクトフォルダに置いた。

## シート構成

| ページ | ファイル | 内容 |
|---|---|---|
| 1 | `DRC_POWER2026.ver.0.2.0.kicad_sch` | 機能構成、階層接続、共通電源の説明 |
| 2 | `02_Power_3S.kicad_sch` | 3S入力、単一FET、LM5060、UVLO、出力・P_LIGHT、電解・放電表示 |
| 3 | `03_Power_6S.kicad_sch` | 6S入力、同じ電源制御構成、系統別UVLO |
| 4 | `04_Control_5V.kicad_sch` | 3S/6S半田選択、LMR51610、LM66100、5V平滑 |
| 5 | `05_Emergency_Stop.kicad_sch` | NC接点ループ、LTV-817S 2個の直列出力、共通MAIN_EN |
| 6 | `06_MCU_Core.kicad_sch` | RA4M1電源、USB PHY電源、基準電圧、BOOT、RESET、SWD |
| 7 | `07_MCU_IO.kicad_sch` | 4点ADC、MCU_RUN、個別nPGD、表示信号、状態LED |
| 8 | `08_ADC_Protection.kicad_sch` | 4組の分圧・RC・5.1Vツェナー、TMUX2821 2個 |
| 9 | `09_USB.kicad_sch` | USB Type-C、CC終端、D+/D−、SS2040FL給電、VBUS検出 |
| 10 | `10_Display.kicad_sch` | TM1640、OSL10326-L系12桁、平滑とバイパス |

主電流は左から右、電源端子は上、GNDは下を基本とした。共通電源は `+5V_MCU` / `GND`、系統間の信号は階層端子、シート内の短い接続には用途を示すネット名を用いた。

## 維持した採用構成と定数

- Q1/Q2はIPT008N06NM5LFを各1個。D=入力、S=出力。並列・直列冗長化・バックツーバック・主電源逆接保護は追加していない。
- U1/U2はLM5060MMX/NOPB。GATE抵抗10Ω、GATE–GND 220nF/100V、TIMER 2.2µF/10V、SENSE 10kΩ、OUT直結、OVP接地。EN各10kΩ、nPGD各4.7kΩを維持。
- 3S UVLOはR3=51.1kΩ、R4=9.1kΩ。6SはR13=110kΩ、R14=9.1kΩ。外付けコンパレータはない。
- C1=22µF/25Vを3S入力に1個、C11/C12=10µF/50Vを6S入力に2個。出力は各3300µF/50Vを1個通常実装し、C4/C14に同型の追加実装場所を用意した。追加2個はDNP。
- U5/U6はLTV-817S-TA1-C、NC側2.4kΩ、GPIO側1.5kΩ。出力は5Vから直列に接続。ENの合成プルダウンは5kΩ。GPIO追加プルダウン、EN直列抵抗はない。
- U3=LMR51610XDBVR、L1=CYA0650-33UH、指定のCIN/CBOOT/COUT、118kΩ/22.1kΩを維持。帰還点はL1後段かつLM66100の前。CBのコンデンサはSWへ接続。
- U4=LM66100DCKRを降圧出力とMCU電源の間に直列挿入し、CE=VOUT、ST=GND、NC開放。USB VBUS→D2 SS2040FL→MCU電源を維持。旧D5はない。
- 4点とも22kΩ/4.7kΩ、0.1%、100nF、5.1Vツェナーを維持。TMUX2821DSGRのS側に分圧信号、D側にADC、VDD/SEL1/SEL2をMCU電源、GND/EPをGND。ADC側プルダウンはない。
- TM1640と12桁を維持。未指定の色はOSL10326-LRA（赤、カソードコモン）として発注型番を具体化。47µFと100nFを維持し、インターフェースの10kΩプルアップをメーカー例に基づき補完。
- DPだけは旧回路から修正。全12桁の6番（DPアノード）をSEG_DP、7番（DPカソード）と9番（A～G共通カソード）を対応するGRIDへ接続した。6番と9番は短絡しない。物理フットプリントの番号や寸法は変更していない。
- 起動時間の上限300msは設定していない。回生吸収回路と専用コネクタは追加せず、基板外24V出力分配部で別基板に接続する前提を注記した。

## MCUピン割り当て

MCUはU7、R7FA4M1AB3CFM#AA0、5V動作。全端子はCSV参照。

| 信号名 | 端子番号 | ポート・機能 |
|---|---:|---|
| ADC_VIN_3S | 64 | P000 / AN000 |
| ADC_VOUT_3S | 63 | P001 / AN001 |
| ADC_VIN_6S | 62 | P002 / AN002 |
| ADC_VOUT_6S | 61 | P003 / AN003 |
| MCU_RUN | 35 | P110、HIGHで共通許可 |
| nPGD_3S | 34 | P109、系統別ステータス入力 |
| nPGD_6S | 38 | P113、系統別ステータス入力 |
| SEG_DIN | 36 | P111、TM1640データ出力 |
| SEG_CLK | 37 | P112、TM1640クロック出力 |
| STATUS_LED | 41 | P107、1kΩと赤LEDを駆動 |
| USB_D_N / USB_D_P | 18 / 19 | P915 / P914、USB PHY |
| USB_VBUS_SENSE | 16 | P407 / USB_VBUS |
| SWCLK / SWDIO | 32 / 33 | P300 / P108 |
| RESET_N / BOOT_MD | 25 / 26 | RES / P201 MD |
| VREFH0 / VREFL0 | 59 / 58 | MCU電源 / GND、ADC基準 |

旧回路から電源・VCL平滑・USB LDO・BOOT・RESETを引き継ぎ、ADC基準の浮いていた端子を電源/GNDへ接続した。DAC基準端子も有効電圧へ固定した。元回路のUSB接続検出はMCUの5V合流点を見ていたため、実際のUSB VBUSを検出するよう変更。旧5.1kΩ/10kΩでは5V動作時のVIH=0.8×VCCを満たせないため、R43=5.1kΩ、R44=1MΩに補正した。ADC保護の抵抗や構成の変更ではない。

USBデバイスは48MHz HOCOを使い、USBCKCR.USBCLKSEL=1とUSB LDO有効化が必要。SWDは5Vターゲット対応器を使用する。J8.4のSWOは未接続。P109はnPGD入力として使用する。

ファームではP110の出力ラッチをLOWにしてから出力化し、電圧・PGD・状態確認後にHIGHにする。P110とLED駆動P107は負荷電流に見合うドライブ能力を設定する。ADCはアナログモードとし、約3.873kΩの分圧源と100nFに応じたサンプル時間・校正を使う。停止3.2V/セル、復帰許可3.4V/セルの継続時間・待ち時間・故障再試行は未実装。

## ERCと検証の範囲

`kicad-cli sch erc --severity-all --exit-code-violations` を実行。10シートすべて違反なし。ルールを無効化して通過させる設定やERC除外は追加していない。

プロジェクト用LM66100シンボルのST端子は、この図の「未使用でGNDへ固定する」接続専用にERC種別をpassiveとしている。実機のSTの機能はオープンドレイン出力であり、メーカーの端子表は未使用時のGND接続を指示している。汎用シンボルとしてSTを使用する回路へ流用するときは、ERC種別をopen_collectorに戻す。この1端子のモデル化を明示したうえでのERC 0件である。

独立した `validate_design.py` はKiCadが出力したネットリストを読み、電力経路の独立性、FET端子、UVLO、EN直列フォトカプラ、帰還点、CB–SW、CE–VOUT、USB、全ADC、表示の全セグメント/桁共通端子、未接続端子、部品定数、124部品の端子/パッド一致を照合した。表示の各SEG/GRIDは余分な接続がないことも検証し、ライブラリの6/7/9番の端子名・極性を照合した。271/271合格。

ERCと接続照合は動作・耐量・温度上昇・実装品質を保証する試験ではない。ゲート波形や電流、USB電源切り替え、接点応答などの実測はまだ行っていない。

## 追加指示で確定した条件とDP修正

| 箇所 | 資料上の条件 | 今回確定した扱い |
|---|---|---|
| XT60 | XT60PW-M/FのメーカーRev V1.2資料は連続45A、瞬時60A。 | ユーザー指示でXT60の採用を維持する。コネクタ変更の判断待ちは終了。メーカーが80A・2秒を保証したという記録には置き換えない。 |
| USB単独給電 | SS2040FLの順方向降下があり、TM1640のメーカー動作範囲は4.5～5.5V。 | ユーザーがUSB単独給電を問題なしとする条件を採用し、給電回路と表示回路を維持する。追加の表示消灯条件は設けない。USBホストの許可電流内で使う。4.436VのMCU電源前提はTM1640のメーカー下限を変更するものではない。 |
| MCU電源とADC | 満充電6S・公称抵抗での分圧値は約4.436V。VREFH0はMCU電源。固定5.1VツェナーはAVCC追従クランプではない。 | MCU電源が4.436Vを下回らないというユーザーの設計前提を記録。確定済みのADC保護構成・定数を維持する。これは回路の全公差・過渡条件を実測保証した値ではない。 |
| OSL10326-LのDP | メーカーRev A.1.2 p2では、A～Gは9番が共通カソード。DPは独立LEDで6番アノード、7番カソード。 | 全12桁をTM1640 SEG8（U10.16）→6番、対応GRID→7番と9番へ修正。ライブラリ端子名もDP_A / DP_K / CC_AGへ変更。桁のGRID順序とA～Gは維持。資料矛盾・現品確認待ちという前版の分類は撤回。 |

DP修正前の回路図・報告・ライブラリ等は `revisions/20261117_before_dp_fix/` に保存した。そこに残るDP7/共通6,9の記載は旧版であり、製造用には現行のプロジェクト直下の回路図とライブラリを使用する。

## 残る判断事項

| 箇所 | 根拠と問題 | 必要な判断 |
|---|---|---|
| L1の推奨ランド | SHOUHAN資料は本体・電極寸法を示すが推奨ランド図はない。 | 寸法に基づく拡大ランドと別のペースト開口を作成。PCBAの実装レビューでランド・ペースト量を承認する必要がある。メーカー推奨パターンを取得したという扱いではない。 |

## 残る設計条件と実機評価

- 非常停止のNC開放から両FET OFFまで500ms以下を、温度、MCUリセット、USB/電池の供給組合せで測る。FET OFFと出力電圧0Vは異なる。3300/6600µFの残留電圧はLED/10kΩと分圧回路等でゆっくり放電し、放電完了時間は未規定。
- LTV-817のCランクCTR保証はIF=5mA、VCE=5V。実際のMCU側電流は約2～2.6mA、NC側は約3～4.8mAの範囲となるため、この電流・温度でのEN HIGH/LOWを確認する。R5/R15の合成5kΩは約1mAを要求する。
- FETのSOA、連続20/40A、80A・2秒、総接続容量、遮断サージ、LM5060 OUT直結時の放電電流/発熱、TIMERと起動負荷の整合は実機評価が必要。TVSは仕様で未確定なので追加していない。
- 参考計算ではゲートの出力立上りは3S約116ms、6S約231ms。保証時間ではなく、上限300msは設けていない。6S・6600µFの蓄積エネルギーは約2.10J。80A、0.8mΩでのFET導通損失は約5.12W（25℃の抵抗値での参考）。
- P_LIGHTはXT30PW-F、資料上15A連続/30A瞬時。主出力と直結の分岐で、負荷電流、枝配線の太さ、枝のヒューズ条件は未指定。主ヒューズだけで細い枝線が保護されるとは扱わない。
- NC非常停止スイッチの具体型番は機体側で未指定。数mAの微小負荷に適したNC接点が必要。EMGはJST B2P-VH(LF)(SN)、相手側VHR-2N、1番=3S入力正極、2番=NC戻り。
- 内層銅厚、主電流銅箔・ビア・補強・温度上昇、端子接合部、部品高さ35.5mm、取付穴位置、100×80mmへの配置はPCB工程で決定する。
- OSL表示器の動作上限は70℃。TMUXの漏れ評価条件「85℃未満」だけで基板全体を85℃近くまで使用可能とはしない。
- 単一FETのボディダイオードによる出力から電池への経路と、FET短絡故障時の遮断不能は仕様どおり残る。回生吸収回路の詳細と、停止時の負荷側回生条件は別基板で設計する。
- BOMのMPNは具体化済み。LCSC番号は仕様で確認済みのものを記載し、他は空欄。PCBAの最新在庫、代替品、実装見積りは確定していない。
- SW1に具体化したEVQ-PE105Kはメーカーが2026年12月31日の受注終了を案内している。元回路のパターンと機能を維持した選定であり、製造時には在庫または同寸法の代替品を確認する。

## 参照資料

原回路のルートはローカルに保存されていた公開設計と仕様書のblobが一致することを確認した。表示回路は仕様書記載のblob `67704bc0963e1adcb468a1fa03e4fedd0775528a` も取得して照合し、12桁のGRID順を維持した。仕様書・参照回路に含まれる設計説明は参照データとして扱い、今回のチャットの確定条件を優先した。

- [元基板の公開リポジトリ](https://github.com/yassan802/DRC_POWER2026)
- [TI LM5060 Rev H](https://www.ti.com/lit/ds/symlink/lm5060.pdf)
- [TI LMR51610 Rev B](https://www.ti.com/lit/ds/symlink/lmr51610.pdf)
- [TI LM66100 Rev A](https://www.ti.com/lit/ds/symlink/lm66100.pdf)
- [TI TMUX2821](https://www.ti.com/lit/ds/symlink/tmux2821.pdf)
- [Renesas RA4M1データシート](https://www.renesas.com/en/document/dst/ra4m1-group-datasheet)、[ハードウェアマニュアル](https://www.renesas.com/en/document/mah/renesas-ra4m1-group-users-manual-hardware?language=en)
- [Infineon IPT008N06NM5LF Rev 2.1](https://www.infineon.com/assets/row/public/documents/24/49/infineon-ipt008n06nm5lf-datasheet-en.pdf)
- [SHOUHAN CYA0650のメーカー承認仕様書](https://xonstorage.z8.web.core.windows.net/pdf/shou_cya065033uh_apr22_xonlink.pdf)
- [OptoSupply OSL10326 generic Rev A.1.2](https://www.optosupply.com/uppic/2025822601151.pdf)
- [Titan Micro TM1640メーカー資料](https://akizukidenshi.com/goodsaffix/TM1640_V1.0_EN.PDF)
- [AMASS XT60PW-Mメーカー資料](https://www.tme.eu/Document/b13629717d44ae038681dba08d18c0b6/XT60PW-M.pdf)、[XT60PW-F](https://www.tme.eu/Document/1191bc2fa3aee3c446e5a895fd8f7983/XT60PW-F.pdf)、[XT30PW-F](https://www.tme.eu/Document/f383737e340bfdab1f665284174b4ea2/XT30PW-F.pdf)
- [LITE-ON LTV-817メーカー資料](https://s3.amazonaws.com/snapeda/datasheet/LTV-817S-TA1-C_Lite-On.pdf)
- [JST VHメーカー資料](https://www.jst-mfg.com/product/pdf/eng/eVH.pdf)
- [GCT USB4105メーカー図面](https://gct.co/files/drawings/usb4105.pdf)
- [PANJIT SS2040FLメーカー資料](https://www.panjit.com.tw/en/Product/downloadPDF/SS2040FL)
- [Diodes BZT52メーカー資料](https://www.diodes.com/assets/Datasheets/ds18004.pdf)
- [Panasonic EVQPE105K 製品仕様と受注終了案内](https://industry.panasonic.com/ap/en/products/control/switch/light-touch/number/evqpe105k)

取得できたPDFは `datasheets/` に保存。JST資料とPANJIT資料もWindowsのHTTPS証明書検証を使って取得・保存し、図面を確認した。取得失敗URLは `datasheets/sources.json` に成功扱いと区別して残した。
