$ErrorActionPreference = "Stop"

$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigPath = Join-Path $AppDir "config.ini"
$global:QueueBusy = $false

function Read-IniFile($path) {
    $ini = @{}
    $section = ""
    $lines = [System.IO.File]::ReadAllLines($path, [System.Text.Encoding]::UTF8)
    foreach ($rawLine in $lines) {
        $line = $rawLine.Trim()
        if ($line.Length -eq 0) { continue }
        if ($line.StartsWith(";")) { continue }
        if ($line.StartsWith("#")) { continue }
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

function Ensure-Dir($path) {
    if ($path -and -not [System.IO.Directory]::Exists($path)) {
        [System.IO.Directory]::CreateDirectory($path) | Out-Null
    }
}

function Write-Log($message) {
    $ini = Read-IniFile $ConfigPath
    $logFile = Get-Cfg $ini "paths" "log_file" "C:\LunaPrint\logs\receiver.log"
    Ensure-Dir ([System.IO.Path]::GetDirectoryName($logFile))
    $line = "[" + (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + "] " + $message
    [System.IO.File]::AppendAllText($logFile, $line + [Environment]::NewLine, [System.Text.Encoding]::UTF8)
}

function Write-State($status, $detail) {
    $ini = Read-IniFile $ConfigPath
    $stateFile = Get-Cfg $ini "paths" "state_file" "C:\LunaPrint\logs\state.txt"
    Ensure-Dir ([System.IO.Path]::GetDirectoryName($stateFile))
    $safeDetail = [string]$detail
    $safeDetail = $safeDetail.Replace([Environment]::NewLine, " ")
    $lines = @(
        "time=" + (Get-Date -Format "yyyy-MM-dd HH:mm:ss"),
        "status=" + $status,
        "detail=" + $safeDetail
    )
    [System.IO.File]::WriteAllText($stateFile, ($lines -join [Environment]::NewLine), [System.Text.Encoding]::UTF8)
}

function UrlDecode($text) {
    if ($text -eq $null) { return "" }
    return [System.Uri]::UnescapeDataString($text.Replace("+", " "))
}

function Parse-FormBody($body) {
    $data = @{}
    $pairs = $body.Split("&")
    foreach ($pair in $pairs) {
        if ($pair.Length -eq 0) { continue }
        $idx = $pair.IndexOf("=")
        if ($idx -lt 0) {
            $key = UrlDecode $pair
            $value = ""
        } else {
            $key = UrlDecode $pair.Substring(0, $idx)
            $value = UrlDecode $pair.Substring($idx + 1)
        }
        $data[$key] = $value
    }
    return $data
}

function CsvCell($value) {
    if ($value -eq $null) { $value = "" }
    $text = [string]$value
    $text = $text.Replace('"', '""')
    return '"' + $text + '"'
}

function Write-JobCsv($ini, $data) {
    $dataFile = Get-Cfg $ini "paths" "data_file" "C:\LunaPrint\data\current_job.csv"
    Ensure-Dir ([System.IO.Path]::GetDirectoryName($dataFile))
    $fieldsText = Get-Cfg $ini "print" "fields" "job_id,order_id,customer_code,customer_name,address_code,style_code,style_name,fabric,composition,color,size,qty,wash_label,header_text,note"
    $fields = @()
    foreach ($field in $fieldsText.Split(",")) {
        $trimmed = $field.Trim()
        if ($trimmed.Length -gt 0) { $fields += $trimmed }
    }
    $values = @()
    foreach ($field in $fields) {
        if ($data.ContainsKey($field)) {
            $values += (CsvCell $data[$field])
        } else {
            $values += '""'
        }
    }
    $content = ($fields -join ",") + [Environment]::NewLine + ($values -join ",") + [Environment]::NewLine
    $encoding = New-Object System.Text.UTF8Encoding($true)
    [System.IO.File]::WriteAllText($dataFile, $content, $encoding)
    return $dataFile
}

function Safe-FilePart($value) {
    $text = [string]$value
    if ($text.Length -eq 0) { $text = "job" }
    foreach ($ch in [System.IO.Path]::GetInvalidFileNameChars()) {
        $text = $text.Replace([string]$ch, "_")
    }
    return $text
}

function Write-QueueCsv($ini, $data) {
    $inputDir = Get-Cfg $ini "queue" "input" "D:\BarTender_Print\Input"
    Ensure-Dir $inputDir

    $fieldsText = Get-Cfg $ini "print" "fields" "job_id,order_id,customer_code,customer_name,address_code,art_code,brand,style_code,style_name,fabric,composition,origin,color,size,qty,wash_symbols,wash_label,header_text,note"
    $fields = @()
    foreach ($field in $fieldsText.Split(",")) {
        $trimmed = $field.Trim()
        if ($trimmed.Length -gt 0) { $fields += $trimmed }
    }

    $values = @()
    foreach ($field in $fields) {
        if ($data.ContainsKey($field)) {
            $values += (CsvCell $data[$field])
        } else {
            $values += '""'
        }
    }

    $jobId = ""
    if ($data.ContainsKey("job_id")) { $jobId = Safe-FilePart $data["job_id"] }
    if ($jobId.Length -eq 0) { $jobId = "job" }
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss_fff"
    $fileName = "luna_" + $stamp + "_" + $jobId + ".csv"
    $tmpPath = Join-Path $inputDir ($fileName + ".tmp")
    $finalPath = Join-Path $inputDir $fileName
    $content = ($fields -join ",") + [Environment]::NewLine + ($values -join ",") + [Environment]::NewLine
    $encoding = New-Object System.Text.UTF8Encoding($true)
    [System.IO.File]::WriteAllText($tmpPath, $content, $encoding)
    Move-Item -LiteralPath $tmpPath -Destination $finalPath -Force
    Write-State "QUEUED" ("file=" + $fileName)
    return $fileName
}

function Unique-Destination($folder, $fileName) {
    $target = Join-Path $folder $fileName
    if (-not [System.IO.File]::Exists($target)) { return $target }
    $name = [System.IO.Path]::GetFileNameWithoutExtension($fileName)
    $ext = [System.IO.Path]::GetExtension($fileName)
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss_fff"
    return (Join-Path $folder ($name + "_" + $stamp + $ext))
}

function Get-DefaultPrinterName() {
    $printer = Get-WmiObject -Class Win32_Printer | Where-Object { $_.Default -eq $true } | Select-Object -First 1
    if ($printer -eq $null) { return "" }
    return [string]$printer.Name
}

function Run-BarTender($ini, $dataFile) {
    $bartender = Get-Cfg $ini "paths" "bartender_exe" "C:\Program Files (x86)\Seagull\BarTender Suite\bartend.exe"
    $template = Get-Cfg $ini "paths" "template" "C:\LunaPrint\templates\scuba.btw"
    $printer = Get-Cfg $ini "print" "printer" ""
    $copies = Get-Cfg $ini "print" "copies" "1"
    $dryRun = (Get-Cfg $ini "print" "dry_run" "0").ToLower()
    $showBarTender = (Get-Cfg $ini "print" "show_bartender" "1").ToLower()

    if ($printer.Length -eq 0 -or $printer -eq "__DEFAULT__") {
        $printer = Get-DefaultPrinterName
    }
    if ($printer.Length -eq 0) {
        Write-State "ERROR" "No default printer"
        throw "No default printer found on Win7"
    }

    $args = @('/F="' + $template + '"', '/D="' + $dataFile + '"', '/C=' + $copies)
    $args += '/PRN="' + $printer + '"'
    $args += "/P"
    $args += "/X"
    $commandText = '"' + $bartender + '" ' + ($args -join " ")
    Write-Log ("command " + $commandText)

    if ($dryRun -eq "1" -or $dryRun -eq "true" -or $dryRun -eq "yes") {
        Write-State "DRY_RUN" "BarTender not called"
        return "DRY_RUN " + $commandText
    }
    if (-not [System.IO.File]::Exists($bartender)) {
        Write-State "ERROR" "BarTender not found"
        throw ("BarTender not found: " + $bartender)
    }
    if (-not [System.IO.File]::Exists($template)) {
        Write-State "ERROR" "Template not found"
        throw ("Template not found: " + $template)
    }

    $windowStyle = "Normal"
    if ($showBarTender -eq "0" -or $showBarTender -eq "false" -or $showBarTender -eq "no") {
        $windowStyle = "Hidden"
    }
    Write-Log ("starting bartender window=" + $windowStyle)
    $process = Start-Process -FilePath $bartender -ArgumentList $args -Wait -PassThru -WindowStyle $windowStyle
    Write-Log ("bartender exit_code=" + $process.ExitCode)
    Write-State "BARTENDER_EXIT" ("exit_code=" + $process.ExitCode)
    if ($process.ExitCode -ne 0) {
        throw ("BarTender exited with code " + $process.ExitCode)
    }
    return "PRINTED"
}

function Process-QueueOnce() {
    if ($global:QueueBusy) { return }
    $global:QueueBusy = $true
    try {
        $ini = Read-IniFile $ConfigPath
        $inputDir = Get-Cfg $ini "queue" "input" "D:\BarTender_Print\Input"
        $processingDir = Get-Cfg $ini "queue" "processing" "D:\BarTender_Print\Processing"
        $archiveDir = Get-Cfg $ini "queue" "archive" "D:\BarTender_Print\Archive"
        $errorDir = Get-Cfg $ini "queue" "error" "D:\BarTender_Print\Error"
        Ensure-Dir $inputDir
        Ensure-Dir $processingDir
        Ensure-Dir $archiveDir
        Ensure-Dir $errorDir

        $files = @(Get-ChildItem -LiteralPath $inputDir -Filter "*.csv" | Sort-Object LastWriteTime)
        foreach ($file in $files) {
            $processingPath = Unique-Destination $processingDir $file.Name
            try {
                Move-Item -LiteralPath $file.FullName -Destination $processingPath -Force
                Write-State "PRINTING" ("file=" + [System.IO.Path]::GetFileName($processingPath))
                Write-Log ("queue printing " + $processingPath)
                $result = Run-BarTender $ini $processingPath
                $archivePath = Unique-Destination $archiveDir ([System.IO.Path]::GetFileName($processingPath))
                Move-Item -LiteralPath $processingPath -Destination $archivePath -Force
                Write-State "PRINTED" ("file=" + [System.IO.Path]::GetFileName($archivePath))
                Write-Log ("queue printed " + $result + " archive=" + $archivePath)
            } catch {
                Write-Log ("queue error " + $_.Exception.Message)
                $errorName = [System.IO.Path]::GetFileName($processingPath)
                $errorPath = Unique-Destination $errorDir $errorName
                if ([System.IO.File]::Exists($processingPath)) {
                    Move-Item -LiteralPath $processingPath -Destination $errorPath -Force
                }
                Write-State "ERROR" $_.Exception.Message
            }
        }
    } finally {
        $global:QueueBusy = $false
    }
}

function Send-Text($context, $statusCode, $text) {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($text)
    $context.Response.StatusCode = $statusCode
    $context.Response.ContentType = "text/plain; charset=utf-8"
    $context.Response.ContentLength64 = $bytes.Length
    $context.Response.OutputStream.Write($bytes, 0, $bytes.Length)
    $context.Response.OutputStream.Close()
}

function Has-Token($context, $ini) {
    $expectedToken = Get-Cfg $ini "receiver" "token" ""
    if ($expectedToken.Length -eq 0) { return $true }
    $actualToken = $context.Request.Headers["X-Luna-Print-Token"]
    $queryToken = $context.Request.QueryString["token"]
    if ($actualToken -eq $expectedToken) { return $true }
    if ($queryToken -eq $expectedToken) { return $true }
    return $false
}

function Send-Diag($context) {
    $ini = Read-IniFile $ConfigPath
    if (-not (Has-Token $context $ini)) {
        Send-Text $context 403 "BAD_TOKEN"
        return
    }
    $bartender = Get-Cfg $ini "paths" "bartender_exe" "C:\Program Files (x86)\Seagull\BarTender Suite\bartend.exe"
    $template = Get-Cfg $ini "paths" "template" "C:\LunaPrint\templates\scuba.btw"
    $dataFile = Get-Cfg $ini "paths" "data_file" "C:\LunaPrint\data\current_job.csv"
    $stateFile = Get-Cfg $ini "paths" "state_file" "C:\LunaPrint\logs\state.txt"
    $printer = Get-Cfg $ini "print" "printer" ""
    $inputDir = Get-Cfg $ini "queue" "input" "D:\BarTender_Print\Input"
    $processingDir = Get-Cfg $ini "queue" "processing" "D:\BarTender_Print\Processing"
    $archiveDir = Get-Cfg $ini "queue" "archive" "D:\BarTender_Print\Archive"
    $errorDir = Get-Cfg $ini "queue" "error" "D:\BarTender_Print\Error"
    if ($printer.Length -eq 0 -or $printer -eq "__DEFAULT__") {
        $printer = Get-DefaultPrinterName
    }

    $text = "receiver=OK" + [Environment]::NewLine
    $text += "bartender_exists=" + [System.IO.File]::Exists($bartender) + [Environment]::NewLine
    $text += "template_exists=" + [System.IO.File]::Exists($template) + [Environment]::NewLine
    $text += "data_exists=" + [System.IO.File]::Exists($dataFile) + [Environment]::NewLine
    $text += "printer_configured=" + ($printer.Length -gt 0) + [Environment]::NewLine
    $text += "queue_input_exists=" + [System.IO.Directory]::Exists($inputDir) + [Environment]::NewLine
    $text += "queue_input_csv=" + $(if ([System.IO.Directory]::Exists($inputDir)) { @([System.IO.Directory]::GetFiles($inputDir, "*.csv")).Count } else { 0 }) + [Environment]::NewLine
    $text += "queue_processing_csv=" + $(if ([System.IO.Directory]::Exists($processingDir)) { @([System.IO.Directory]::GetFiles($processingDir, "*.csv")).Count } else { 0 }) + [Environment]::NewLine
    $text += "queue_archive_csv=" + $(if ([System.IO.Directory]::Exists($archiveDir)) { @([System.IO.Directory]::GetFiles($archiveDir, "*.csv")).Count } else { 0 }) + [Environment]::NewLine
    $text += "queue_error_csv=" + $(if ([System.IO.Directory]::Exists($errorDir)) { @([System.IO.Directory]::GetFiles($errorDir, "*.csv")).Count } else { 0 }) + [Environment]::NewLine
    if ([System.IO.File]::Exists($stateFile)) {
        $text += [System.IO.File]::ReadAllText($stateFile, [System.Text.Encoding]::UTF8)
    } else {
        $text += "status=NO_PRINT_ATTEMPT"
    }
    Send-Text $context 200 $text
}

$ini = Read-IniFile $ConfigPath
$hostName = Get-Cfg $ini "receiver" "host" "+"
$port = Get-Cfg $ini "receiver" "port" "9876"
$prefix = "http://" + $hostName + ":" + $port + "/"

$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add($prefix)
$listener.Start()
Write-Log ("receiver started " + $prefix)

Process-QueueOnce

while ($true) {
    Process-QueueOnce
    $contextTask = $listener.GetContextAsync()
    while (-not $contextTask.IsCompleted) {
        Start-Sleep -Milliseconds 500
        Process-QueueOnce
    }
    $context = $contextTask.Result
    try {
        $path = $context.Request.Url.AbsolutePath
        if ($context.Request.HttpMethod -eq "GET" -and $path -eq "/health") {
            Send-Text $context 200 "OK"
            continue
        }
        if ($context.Request.HttpMethod -eq "GET" -and $path -eq "/diag") {
            Send-Diag $context
            continue
        }
        if ($context.Request.HttpMethod -ne "POST" -or $path -ne "/print") {
            Send-Text $context 404 "NOT_FOUND"
            continue
        }

        $reader = New-Object System.IO.StreamReader($context.Request.InputStream, [System.Text.Encoding]::UTF8)
        $body = $reader.ReadToEnd()
        $reader.Close()
        $data = Parse-FormBody $body

        $ini = Read-IniFile $ConfigPath
        $expectedToken = Get-Cfg $ini "receiver" "token" ""
        if ($expectedToken.Length -gt 0) {
            $actualToken = $context.Request.Headers["X-Luna-Print-Token"]
            if (($actualToken -eq $null -or $actualToken -ne $expectedToken) -and ((-not $data.ContainsKey("token")) -or $data["token"] -ne $expectedToken)) {
                Send-Text $context 403 "BAD_TOKEN"
                continue
            }
        }

        $dataFile = Write-JobCsv $ini $data
        $queueFile = Write-QueueCsv $ini $data
        Write-Log ("job " + $data["job_id"] + " current_csv=" + $dataFile + " queue_file=" + $queueFile)
        Send-Text $context 200 ("OK QUEUED " + $queueFile)
    } catch {
        Write-Log ("error " + $_.Exception.Message)
        Write-State "ERROR" $_.Exception.Message
        Send-Text $context 500 ("ERROR " + $_.Exception.Message)
    }
}
