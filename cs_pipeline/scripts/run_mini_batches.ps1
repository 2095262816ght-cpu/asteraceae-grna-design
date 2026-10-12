$base = Split-Path -Parent $PSScriptRoot
$sw = [Diagnostics.Stopwatch]::StartNew()
$ok = 0
foreach ($i in 0..39) {
    $tag = "{0:00}" -f $i
    & "$base\tools\cas-offinder\cas-offinder.exe" "$base\data\mini_$tag.txt" G0 "$base\results\off_mini_$tag.txt" 2>&1 | Out-Null
    if (Test-Path "$base\results\off_mini_$tag.txt") {
        $ok++
        if ($i % 10 -eq 0) { Write-Host "mini $i done ($([math]::Round($sw.Elapsed.TotalMinutes,1))min)" }
    } else {
        Write-Host "mini $i FAILED"
    }
}
Write-Host "batches ok: $ok/40, total $([math]::Round($sw.Elapsed.TotalMinutes,1)) min"
# 合并
if ($ok -eq 40) {
    Get-Content "$base\results\off_mini_*.txt" | Set-Content "$base\results\offtarget_raw_0924.txt" -Encoding ascii
    Write-Host "merged: $([math]::Round((Get-Item "$base\results\offtarget_raw_0924.txt").Length/1MB,1)) MB"
}
