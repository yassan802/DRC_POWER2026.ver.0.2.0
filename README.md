# DRC POWER2026 主電源基板

既存の `DRC_POWER2026.ver.0.2.0.kicad_pro` をKiCad 9以降で開いてください。回路図はルートを含む10シートです。プロジェクト設定と既存PCBファイルは維持しています。

- [作成報告と未解決事項](docs/DESIGN_REPORT.md)
- [全シートの回路図PDF](docs/main_power_schematic.pdf)
- [MCU全64端子の割り当て](docs/MCU_PIN_ASSIGNMENT.csv)
- [基板上BOM](docs/BOM.csv) / [基板外BOM](docs/OFFBOARD_BOM.csv)
- [ライブラリ照合と変更記録](docs/LIBRARY_VERIFICATION.md)
- [ERC結果](docs/ERC.rpt) / [接続監査](docs/CONNECTIVITY_AUDIT.json)

ERC 0件と、全124部品の端子・パッドの一致を確認しています。追加指示により、XT60採用継続、USB単独給電の許容、MCU電源4.436V以上を設計条件として記録しました。表示器DPは全12桁を6番アノード→SEG8、7番カソードと9番A～G共通→GRIDへ修正済みです。L1の実装ランドレビューと実機評価等は報告書を参照してください。

追加ライブラリは `lib/` にまとめ、`${KIPRJMOD}` で参照します。C4/C14は各出力の2個目の3300µFで、通常はDNPです。半田選択JP1は3Sが初期状態です。

`tools/build_schematic.py` は今回の回路図・ライブラリの作成元です。再実行すると回路図を再生成するため、手動編集後の再実行は意図した再生成時だけにしてください。`tools/validate_design.py` はKiCadが出力したネットリストを独立に検証します。
