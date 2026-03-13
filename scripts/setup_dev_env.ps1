<#
.SYNOPSIS
    band-score-to-midi ローカル開発環境セットアップ

.DESCRIPTION
    以下を自動インストール・設定します:
      1. Java 21 (Eclipse Temurin) — Audiveris 実行に必要
      2. Poppler — pdfinfo / pdftoppm による PDF 前処理に必要
      3. Audiveris 5.3+ JAR — GitHub Releases から取得し config/audiveris.properties を更新

    実行要件:
      - winget (Windows Package Manager)  ← Java に使用
      - Chocolatey                        ← Poppler に使用
      - 管理者権限で PowerShell を起動すること

.PARAMETER AudiverisDir
    Audiveris を展開するディレクトリ (デフォルト: C:\Tools\Audiveris)

.PARAMETER SkipJava
    Java のインストールをスキップする

.PARAMETER SkipPoppler
    Poppler のインストールをスキップする

.PARAMETER SkipAudiveris
    Audiveris のダウンロードをスキップする

.EXAMPLE
    .\scripts\setup_dev_env.ps1
    .\scripts\setup_dev_env.ps1 -AudiverisDir "D:\Tools\Audiveris"
    .\scripts\setup_dev_env.ps1 -SkipJava -SkipPoppler
#>

param(
    [string]$AudiverisDir = "C:\Tools\Audiveris",
    [switch]$SkipJava,
    [switch]$SkipPoppler,
    [switch]$SkipAudiveris
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# ── ヘルパー ──────────────────────────────────────────────────────
function Write-Step { param([string]$Msg) Write-Host "`n==> $Msg" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Msg) Write-Host "[OK]   $Msg" -ForegroundColor Green }
function Write-Skip { param([string]$Msg) Write-Host "[SKIP] $Msg" -ForegroundColor Yellow }
function Write-Fail { param([string]$Msg) Write-Host "[FAIL] $Msg" -ForegroundColor Red; exit 1 }

function Refresh-Path {
    $machine = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $user    = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = ($machine, $user | Where-Object { $_ }) -join ";"
}

function Read-IniValue {
    param([string]$Path, [string]$Key)
    foreach ($line in Get-Content $Path -Encoding UTF8) {
        if ($line -match "^\s*$([regex]::Escape($Key))\s*=\s*(.+?)\s*$") { return $Matches[1] }
    }
    return $null
}

function Set-IniValue {
    param([string]$Path, [string]$Key, [string]$Value)
    $lines = Get-Content $Path -Encoding UTF8
    $replaced = $false
    $lines = $lines | ForEach-Object {
        if ($_ -match "^\s*$([regex]::Escape($Key))\s*=") {
            $replaced = $true
            "$Key = $Value"
        } else { $_ }
    }
    if (-not $replaced) { $lines += "$Key = $Value" }
    $lines | Set-Content $Path -Encoding UTF8 -Force
}

# ── 管理者権限確認 ─────────────────────────────────────────────────
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "管理者権限が必要です。PowerShell を「管理者として実行」してから再度実行してください。" -ForegroundColor Red
    exit 1
}

$projectRoot   = Split-Path -Path $PSScriptRoot -Parent
$propertiesPath = Join-Path $projectRoot "config\audiveris.properties"

# ══════════════════════════════════════════════════════════════════
# 1. Java 21 (Eclipse Temurin)
# ══════════════════════════════════════════════════════════════════
if (-not $SkipJava) {
    Write-Step "Java 17+ の確認・インストール"

    $javaCmd = Get-Command java -ErrorAction SilentlyContinue
    $needInstall = $true

    if ($javaCmd) {
        $verLine = (& java -version 2>&1 | Select-Object -First 1) -as [string]
        if ($verLine -match 'version "(\d+)') {
            $major = [int]$Matches[1]
            # 旧形式 "1.8.x" → メジャーは 2 番目のセグメント
            if ($major -eq 1 -and $verLine -match 'version "1\.(\d+)') { $major = [int]$Matches[1] }
            if ($major -ge 17) {
                Write-Skip "Java $major は既インストール済み ($($javaCmd.Source))"
                $needInstall = $false
            } else {
                Write-Host "Java $major を検出 (< 17) → アップグレードします"
            }
        }
    }

    if ($needInstall) {
        Write-Host "winget で Eclipse Temurin 21 をインストールします..."
        winget install --id EclipseAdoptium.Temurin.21.JDK `
            --accept-source-agreements --accept-package-agreements `
            --silent --scope machine
        Refresh-Path
        if (Get-Command java -ErrorAction SilentlyContinue) {
            Write-Ok "Java 21 をインストールしました"
        } else {
            Write-Host "[WARN] インストール完了。新しいターミナルを開くと java コマンドが有効になります。" -ForegroundColor Yellow
        }
    }
} else {
    Write-Skip "Java インストールをスキップしました (-SkipJava)"
}

# ══════════════════════════════════════════════════════════════════
# 2. Poppler (pdfinfo / pdftoppm)
# ══════════════════════════════════════════════════════════════════
if (-not $SkipPoppler) {
    Write-Step "Poppler の確認・インストール"

    $pdfinfo  = Get-Command pdfinfo  -ErrorAction SilentlyContinue
    $pdftoppm = Get-Command pdftoppm -ErrorAction SilentlyContinue

    if ($pdfinfo -and $pdftoppm) {
        Write-Skip "Poppler は既インストール済み ($($pdfinfo.Source))"
    } else {
        if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
            Write-Fail "Chocolatey が見つかりません。https://chocolatey.org/install からインストールしてください。"
        }
        Write-Host "Chocolatey で Poppler をインストールします..."
        choco install poppler -y --no-progress
        Refresh-Path
        if (Get-Command pdfinfo -ErrorAction SilentlyContinue) {
            Write-Ok "Poppler をインストールしました"
        } else {
            Write-Host "[WARN] インストール完了。新しいターミナルを開くと pdfinfo / pdftoppm コマンドが有効になります。" -ForegroundColor Yellow
        }
    }
} else {
    Write-Skip "Poppler インストールをスキップしました (-SkipPoppler)"
}

# ══════════════════════════════════════════════════════════════════
# 3. Audiveris JAR
# ══════════════════════════════════════════════════════════════════
if (-not $SkipAudiveris) {
    Write-Step "Audiveris JAR の確認・セットアップ"

    # 有効な JAR パスを決定（環境変数 → properties の順）
    $envJar    = $env:AUDIVERIS_JAR
    $configJar = Read-IniValue -Path $propertiesPath -Key "audiveris.jar"
    $effective = if ($envJar) { $envJar } else { $configJar }

    if ($effective -and (Test-Path $effective)) {
        Write-Skip "Audiveris JAR は既に存在します: $effective"
    } else {
        Write-Host "Audiveris JAR が見つかりません。GitHub Releases から取得します..."

        # GitHub API で最新リリース情報を取得
        $apiUrl  = "https://api.github.com/repos/Audiveris/audiveris/releases/latest"
        $headers = @{ "User-Agent" = "band-score-to-midi-setup/1.0" }

        try {
            $release = Invoke-RestMethod -Uri $apiUrl -Headers $headers -TimeoutSec 30
        } catch {
            Write-Host ""
            Write-Host "[FAIL] GitHub API の呼び出しに失敗しました: $_" -ForegroundColor Red
            Write-Host "       手動で ZIP をダウンロードして $AudiverisDir に展開し、"
            Write-Host "       config/audiveris.properties の audiveris.jar を JAR パスに書き換えてください。"
            exit 1
        }

        Write-Host "最新リリース: $($release.tag_name)"

        # ZIP アセットを探す（Windows 優先 → 最大サイズ）
        $asset = $release.assets |
            Where-Object { $_.name -like "*windows*" -and $_.name -like "*.zip" } |
            Select-Object -First 1
        if (-not $asset) {
            $asset = $release.assets |
                Where-Object { $_.name -like "*.zip" } |
                Sort-Object size -Descending |
                Select-Object -First 1
        }
        if (-not $asset) {
            Write-Host ""
            Write-Host "[FAIL] ダウンロード可能な ZIP アセットが見つかりませんでした。" -ForegroundColor Red
            Write-Host "       https://github.com/Audiveris/audiveris/releases から手動でダウンロードしてください。"
            exit 1
        }

        $tmpZip = Join-Path $env:TEMP "audiveris_setup.zip"
        Write-Host "ダウンロード中: $($asset.browser_download_url)"
        Write-Host "(ファイルサイズ: $([math]::Round($asset.size / 1MB, 1)) MB)"
        Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $tmpZip -TimeoutSec 300

        Write-Host "展開先: $AudiverisDir"
        if (Test-Path $AudiverisDir) { Remove-Item $AudiverisDir -Recurse -Force }
        New-Item -ItemType Directory -Path $AudiverisDir -Force | Out-Null
        Expand-Archive -Path $tmpZip -DestinationPath $AudiverisDir -Force
        Remove-Item $tmpZip -Force

        # 展開された一番外側のフォルダが余分にある場合はフラット化する
        $children = Get-ChildItem -Path $AudiverisDir
        if ($children.Count -eq 1 -and $children[0].PSIsContainer) {
            $innerDir = $children[0].FullName
            Get-ChildItem -Path $innerDir | Move-Item -Destination $AudiverisDir
            Remove-Item $innerDir -Recurse -Force
        }

        # JAR を探す（lib/ 配下 → 全体 / sources・javadoc は除外 / サイズ最大を採用）
        $jar = Get-ChildItem -Path $AudiverisDir -Recurse -Filter "*.jar" |
            Where-Object { $_.Name -notmatch "sources|javadoc|test" } |
            Sort-Object Length -Descending |
            Select-Object -First 1

        if (-not $jar) {
            Write-Fail "JAR ファイルが見つかりませんでした。$AudiverisDir を確認してください。"
        }

        $jarPath = $jar.FullName -replace "\\", "/"
        Set-IniValue -Path $propertiesPath -Key "audiveris.jar" -Value $jarPath
        Write-Ok "config/audiveris.properties を更新しました"
        Write-Host "       audiveris.jar = $jarPath"
    }
} else {
    Write-Skip "Audiveris セットアップをスキップしました (-SkipAudiveris)"
}

# ══════════════════════════════════════════════════════════════════
# 完了メッセージ
# ══════════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host " セットアップ完了" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""
Write-Host "次のステップ:"
Write-Host "  1. このターミナルを閉じて新しい PowerShell を開く (PATH 反映のため)"
Write-Host "  2. 動作確認:"
Write-Host "       .\scripts\check_local_runtime.ps1"
Write-Host ""
