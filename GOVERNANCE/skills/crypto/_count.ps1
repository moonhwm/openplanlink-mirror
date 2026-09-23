$files = @('pqc-assessment.md','crypto-law-compliance.md','gm-algorithm.md','rhel10-crypto.md','key-lifecycle.md')
$base = 'C:\Users\欧阳宏俊\Documents\kimi\tasks\2026-08-27\22-20-45-c3ffff44\harmony-app\GOVERNANCE\skills\crypto\'
foreach ($f in $files) {
  $t = Get-Content -Raw -Encoding UTF8 ($base + $f)
  $body = ($t -split '### 自我评估')[0]
  $n = ([regex]::Matches($body, '[\u4e00-\u9fff]')).Count
  Write-Output ($f + ' body-hanzi=' + $n)
}
