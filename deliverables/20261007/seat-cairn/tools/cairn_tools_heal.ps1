# 工具自愈：从 HEAD 恢复本席 exp/ 工具（应对未跟踪文件被外部删除）
$seat = "C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928"
$repo = "C:\Users\欧阳宏俊\openplanlink-mirror"
$n = 0
foreach ($spec in @(
  @{g='deliverables/20261006/seat-cairn/tools/baseline_digest.py'; t="$seat\exp\baseline_digest.py"},
  @{g='deliverables/20261007/seat-cairn/tools/disclosure_scan.py'; t="$seat\exp\disclosure_scan.py"},
  @{g='deliverables/20261007/seat-cairn/tools/mk_challenge.py';  t="$seat\exp\mk_challenge.py"},
  @{g='deliverables/20261007/seat-cairn/tools/mk_announce.py';   t="$seat\exp\mk_announce.py"},
  @{g='deliverables/20261007/seat-cairn/tools/console_report.py';t="$seat\exp\console_report.py"},
  @{g='deliverables/20261007/seat-cairn/tools/push_all.py';      t="$seat\exp\push_all.py"}
)) {
  if (-not (Test-Path $spec.t)) {
    $c = & git -C $repo show ("HEAD:" + $spec.g) 2>$null
    if ($c) { ($c -join "`n") | Set-Content $spec.t -Encoding UTF8 -NoNewline; $n++; Write-Output ("  恢复 " + (Split-Path $spec.t -Leaf)) }
  }
}
Write-Output ("  共恢复 " + $n + " 件")
