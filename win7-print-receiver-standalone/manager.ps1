$ErrorActionPreference = "SilentlyContinue"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigPath = Join-Path $AppDir "config.ini"
$ReceiverPath = Join-Path $AppDir "receiver.ps1"
$StartHiddenPath = Join-Path $AppDir "start-hidden.vbs"
$Token = "luna-win7-print"
$global:ReallyExit = $false

function Read-IniFile($path) {
    $ini = @{}
    $section = ""
    if (-not [System.IO.File]::Exists($path)) { return $ini }
    $lines = [System.IO.File]::ReadAllLines($path, [System.Text.Encoding]::UTF8)
    foreach ($rawLine in $lines) {
        $line = $rawLine.Trim()
        if ($line.Length -eq 0) { continue }
        if ($line.StartsWith(";") -or $line.StartsWith("#")) { continue }
        if ($line.StartsWith("[") -and $line.EndsWith("]")) {
            $section = $line.Substring(1, $line.Length - 2)
            if (-not $ini.ContainsKey($section)) { $ini[$section] = @{} }
            continue
        }
        $idx = $line.IndexOf("=")
        if ($idx -lt 0) { continue }
        $key = $line.Substring(0, $idx).Trim()
        $value = $line.Substring($idx + 1).Trim()
        if (-not $ini.ContainsKey($section)) { $ini[$section] = @{} }
        $ini[$section][$key] = $value
    }
    return $ini
}

function Get-Cfg($ini, $section, $key, $default) {
    if ($ini.ContainsKey($section) -and $ini[$section].ContainsKey($key)) {
        return $ini[$section][$key]
    }
    return $default
}

function Set-IniValue($path, $sectionName, $keyName, $value) {
    $lines = New-Object System.Collections.ArrayList
    if ([System.IO.File]::Exists($path)) {
        [void]$lines.AddRange([System.IO.File]::ReadAllLines($path, [System.Text.Encoding]::UTF8))
    }
    $sectionIndex = -1
    $nextSectionIndex = $lines.Count
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i].Trim() -eq ("[" + $sectionName + "]")) {
            $sectionIndex = $i
            for ($j = $i + 1; $j -lt $lines.Count; $j++) {
                if ($lines[$j].Trim().StartsWith("[") -and $lines[$j].Trim().EndsWith("]")) {
                    $nextSectionIndex = $j
                    break
                }
            }
            break
        }
    }
    if ($sectionIndex -lt 0) {
        [void]$lines.Add("")
        [void]$lines.Add("[" + $sectionName + "]")
        [void]$lines.Add($keyName + "=" + $value)
    } else {
        $keyIndex = -1
        for ($i = $sectionIndex + 1; $i -lt $nextSectionIndex; $i++) {
            if ($lines[$i].Trim().StartsWith($keyName + "=")) {
                $keyIndex = $i
                break
            }
        }
        if ($keyIndex -ge 0) {
            $lines[$keyIndex] = $keyName + "=" + $value
        } else {
            $lines.Insert($nextSectionIndex, $keyName + "=" + $value)
        }
    }
    [System.IO.File]::WriteAllLines($path, [string[]]$lines, [System.Text.Encoding]::UTF8)
}

function Get-Printers() {
    @(Get-WmiObject -Class Win32_Printer | Sort-Object Name)
}

function Get-DefaultPrinterName() {
    $printer = Get-WmiObject -Class Win32_Printer | Where-Object { $_.Default -eq $true } | Select-Object -First 1
    if ($printer -eq $null) { return "" }
    return [string]$printer.Name
}

function Get-ReceiverProcesses() {
    @(Get-WmiObject Win32_Process -Filter "Name = 'powershell.exe'" | Where-Object { $_.CommandLine -like "*receiver.ps1*" })
}

function Is-ReceiverRunning() {
    return ((Get-ReceiverProcesses).Count -gt 0)
}

function Start-Receiver() {
    if (Is-ReceiverRunning) { return }
    Start-Process -FilePath "wscript.exe" -ArgumentList ('"' + $StartHiddenPath + '"') -WindowStyle Hidden
    Start-Sleep -Milliseconds 800
}

function Stop-Receiver() {
    $processes = Get-ReceiverProcesses
    foreach ($process in $processes) {
        Stop-Process -Id $process.ProcessId -Force
    }
    Start-Sleep -Milliseconds 500
}

function Test-LocalHealth() {
    try {
        $client = New-Object System.Net.WebClient
        $client.Encoding = [System.Text.Encoding]::UTF8
        $text = $client.DownloadString("http://127.0.0.1:9876/health")
        return ($text.Trim() -eq "OK")
    } catch {
        return $false
    }
}

function Get-LanAddresses() {
    $items = @()
    $configs = Get-WmiObject Win32_NetworkAdapterConfiguration | Where-Object { $_.IPEnabled -eq $true }
    foreach ($cfg in $configs) {
        foreach ($ip in $cfg.IPAddress) {
            if ($ip -match "^\d+\.\d+\.\d+\.\d+$" -and -not $ip.StartsWith("169.254.")) {
                $items += ("http://" + $ip + ":9876")
            }
        }
    }
    return ($items -join [Environment]::NewLine)
}

function Get-DiagText() {
    try {
        $client = New-Object System.Net.WebClient
        $client.Encoding = [System.Text.Encoding]::UTF8
        $client.Headers.Add("X-Luna-Print-Token", $Token)
        return $client.DownloadString("http://127.0.0.1:9876/diag")
    } catch {
        return "diag=NOT_AVAILABLE"
    }
}

$form = New-Object System.Windows.Forms.Form
$form.Text = "Luna 打印接收器"
$form.Size = New-Object System.Drawing.Size(560, 430)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedSingle"
$form.MaximizeBox = $false

$title = New-Object System.Windows.Forms.Label
$title.Text = "Luna 打印接收器"
$title.Font = New-Object System.Drawing.Font("Microsoft YaHei", 14, [System.Drawing.FontStyle]::Bold)
$title.Location = New-Object System.Drawing.Point(16, 14)
$title.Size = New-Object System.Drawing.Size(300, 28)
$form.Controls.Add($title)

$printerLabel = New-Object System.Windows.Forms.Label
$printerLabel.Text = "打印机"
$printerLabel.Location = New-Object System.Drawing.Point(18, 60)
$printerLabel.Size = New-Object System.Drawing.Size(70, 24)
$form.Controls.Add($printerLabel)

$printerCombo = New-Object System.Windows.Forms.ComboBox
$printerCombo.Location = New-Object System.Drawing.Point(90, 56)
$printerCombo.Size = New-Object System.Drawing.Size(310, 26)
$printerCombo.DropDownStyle = "DropDownList"
$form.Controls.Add($printerCombo)

$refreshBtn = New-Object System.Windows.Forms.Button
$refreshBtn.Text = "刷新"
$refreshBtn.Location = New-Object System.Drawing.Point(410, 55)
$refreshBtn.Size = New-Object System.Drawing.Size(55, 28)
$form.Controls.Add($refreshBtn)

$saveBtn = New-Object System.Windows.Forms.Button
$saveBtn.Text = "保存"
$saveBtn.Location = New-Object System.Drawing.Point(470, 55)
$saveBtn.Size = New-Object System.Drawing.Size(55, 28)
$form.Controls.Add($saveBtn)

$startBtn = New-Object System.Windows.Forms.Button
$startBtn.Text = "启动接收"
$startBtn.Location = New-Object System.Drawing.Point(20, 98)
$startBtn.Size = New-Object System.Drawing.Size(90, 32)
$form.Controls.Add($startBtn)

$stopBtn = New-Object System.Windows.Forms.Button
$stopBtn.Text = "停止接收"
$stopBtn.Location = New-Object System.Drawing.Point(120, 98)
$stopBtn.Size = New-Object System.Drawing.Size(90, 32)
$form.Controls.Add($stopBtn)

$testBtn = New-Object System.Windows.Forms.Button
$testBtn.Text = "测试连接"
$testBtn.Location = New-Object System.Drawing.Point(220, 98)
$testBtn.Size = New-Object System.Drawing.Size(90, 32)
$form.Controls.Add($testBtn)

$folderBtn = New-Object System.Windows.Forms.Button
$folderBtn.Text = "打开目录"
$folderBtn.Location = New-Object System.Drawing.Point(320, 98)
$folderBtn.Size = New-Object System.Drawing.Size(90, 32)
$form.Controls.Add($folderBtn)

$hideBtn = New-Object System.Windows.Forms.Button
$hideBtn.Text = "隐藏"
$hideBtn.Location = New-Object System.Drawing.Point(420, 98)
$hideBtn.Size = New-Object System.Drawing.Size(55, 32)
$form.Controls.Add($hideBtn)

$exitBtn = New-Object System.Windows.Forms.Button
$exitBtn.Text = "退出"
$exitBtn.Location = New-Object System.Drawing.Point(480, 98)
$exitBtn.Size = New-Object System.Drawing.Size(45, 32)
$form.Controls.Add($exitBtn)

$statusBox = New-Object System.Windows.Forms.TextBox
$statusBox.Location = New-Object System.Drawing.Point(20, 145)
$statusBox.Size = New-Object System.Drawing.Size(505, 225)
$statusBox.Multiline = $true
$statusBox.ScrollBars = "Vertical"
$statusBox.ReadOnly = $true
$statusBox.Font = New-Object System.Drawing.Font("Consolas", 9)
$form.Controls.Add($statusBox)

$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Application
$notify.Text = "Luna 打印接收器"
$notify.Visible = $true

function Load-PrintersToCombo() {
    $printerCombo.Items.Clear()
    $printers = Get-Printers
    foreach ($printer in $printers) {
        [void]$printerCombo.Items.Add($printer.Name)
    }
    $ini = Read-IniFile $ConfigPath
    $current = Get-Cfg $ini "print" "printer" "__DEFAULT__"
    if ($current -eq "__DEFAULT__" -or $current.Length -eq 0) {
        $current = Get-DefaultPrinterName
    }
    if ($current.Length -gt 0 -and $printerCombo.Items.Contains($current)) {
        $printerCombo.SelectedItem = $current
    } elseif ($printerCombo.Items.Count -gt 0) {
        $printerCombo.SelectedIndex = 0
    }
}

function Update-Status() {
    $running = Is-ReceiverRunning
    $health = Test-LocalHealth
    $ini = Read-IniFile $ConfigPath
    $configuredPrinter = Get-Cfg $ini "print" "printer" ""
    $text = ""
    $text += "接收器进程: " + $(if ($running) { "运行中" } else { "未运行" }) + [Environment]::NewLine
    $text += "本机连接: " + $(if ($health) { "OK" } else { "未连接" }) + [Environment]::NewLine
    $text += "已保存打印机: " + $configuredPrinter + [Environment]::NewLine
    $text += "局域网地址:" + [Environment]::NewLine + (Get-LanAddresses) + [Environment]::NewLine
    $text += "诊断:" + [Environment]::NewLine + (Get-DiagText)
    $statusBox.Text = $text
}

$refreshBtn.Add_Click({
    Load-PrintersToCombo
    Update-Status
})

$saveBtn.Add_Click({
    if ($printerCombo.SelectedItem -eq $null) {
        [System.Windows.Forms.MessageBox]::Show("没有选择打印机。", "Luna")
        return
    }
    Set-IniValue $ConfigPath "print" "printer" ([string]$printerCombo.SelectedItem)
    [System.Windows.Forms.MessageBox]::Show("已保存打印机。", "Luna")
    Update-Status
})

$startBtn.Add_Click({
    Start-Receiver
    Update-Status
})

$stopBtn.Add_Click({
    Stop-Receiver
    Update-Status
})

$testBtn.Add_Click({
    Update-Status
})

$folderBtn.Add_Click({
    Start-Process explorer.exe $AppDir
})

$hideBtn.Add_Click({
    $form.Hide()
})

$exitBtn.Add_Click({
    $global:ReallyExit = $true
    $notify.Visible = $false
    $form.Close()
})

$notify.Add_DoubleClick({
    $form.Show()
    $form.WindowState = "Normal"
    $form.Activate()
})

$form.Add_FormClosing({
    if (-not $global:ReallyExit) {
        $_.Cancel = $true
        $form.Hide()
        $notify.ShowBalloonTip(2000, "Luna 打印接收器", "程序已隐藏，双击托盘图标可打开。", [System.Windows.Forms.ToolTipIcon]::Info)
    }
})

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 5000
$timer.Add_Tick({ Update-Status })

Load-PrintersToCombo
Start-Receiver
Update-Status
$timer.Start()

[void]$form.ShowDialog()
