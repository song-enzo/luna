$log = "$PSScriptRoot\tunnel_url.txt"
$date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$date] Starting cloudflared tunnel..." | Out-File $log
$proc = Start-Process -FilePath (Get-Command cloudflared).Source -ArgumentList "tunnel","--url","http://localhost:8766" -WindowStyle Hidden -PassThru
$proc.Id | Out-File -Append $log
Wait-Process -Id $proc.Id
