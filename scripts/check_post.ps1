param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$PostPath,

    [switch]$RunPipeline,

    [switch]$AllowDraft,

    [switch]$SkipRender
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Add-Issue {
    param([string]$Message)
    $script:issues.Add($Message) | Out-Null
}

$repoRoot = (& git rev-parse --show-toplevel).Trim()
if (-not $repoRoot) {
    throw "Run this script from inside the blog Git repository."
}

$candidate = if ([System.IO.Path]::IsPathRooted($PostPath)) {
    $PostPath
} else {
    Join-Path (Get-Location) $PostPath
}

if (-not (Test-Path -LiteralPath $candidate)) {
    throw "Post path does not exist: $PostPath"
}

$postFile = (Resolve-Path -LiteralPath $candidate).Path
$repoFull = (Resolve-Path -LiteralPath $repoRoot).Path
if (-not $postFile.StartsWith($repoFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Post path must be inside the blog repository: $postFile"
}

if ([System.IO.Path]::GetFileName($postFile) -ne "index.qmd") {
    throw "Post path must point to an index.qmd file."
}

$postDir = Split-Path -Parent $postFile
$relativePost = $postFile.Substring($repoFull.Length).TrimStart("\", "/")
$content = Get-Content -LiteralPath $postFile -Raw
$issues = [System.Collections.Generic.List[string]]::new()

if ($content -match "(?m)^draft:\s*true\s*$") {
    if ($AllowDraft) {
        Write-Host "Draft mode allowed: frontmatter contains draft: true."
    } else {
        Add-Issue "Frontmatter still contains draft: true. Use -AllowDraft while checking drafts."
    }
}

if ($content -match "(?m)^##\s+Introduction\s*$") {
    Add-Issue "Remove the stale '## Introduction' heading and start with the opening paragraph."
}

if ($content -match "plt\.show\s*\(") {
    Add-Issue "Remove plt.show(); Quarto displays figures automatically."
}

if ($content -match "(?m)^\s*from\s+\S+\s+import\s+\*") {
    Add-Issue "Remove wildcard imports."
}

$statsPath = Join-Path $postDir "stats\summary_stats.json"
if (($content -match "stats\[" -or $content -match "summary_stats\.json") -and -not (Test-Path -LiteralPath $statsPath)) {
    Add-Issue "The post references stats but stats\summary_stats.json is missing."
}

Push-Location $repoFull
try {
    $freezeTracked = (& git ls-files _freeze | Select-Object -First 1)
    if (-not $freezeTracked) {
        Add-Issue "_freeze is not tracked by Git."
    }

    & git check-ignore -q _site
    if ($LASTEXITCODE -ne 0) {
        Add-Issue "_site is not ignored by Git."
    }

    if ($issues.Count -gt 0) {
        Write-Host "Preflight failed for $relativePost"
        foreach ($issue in $issues) {
            Write-Host " - $issue"
        }
        exit 1
    }

    if ($RunPipeline) {
        $scriptDir = Join-Path $postDir "scripts"
        if (Test-Path -LiteralPath $scriptDir) {
            $python = Join-Path $repoFull ".venv\Scripts\python.exe"
            if (-not (Test-Path -LiteralPath $python)) {
                $python = "python"
            }

            Get-ChildItem -LiteralPath $scriptDir -Filter "*.py" |
                Where-Object { $_.Name -match "^\d+_.*\.py$" } |
                Sort-Object Name |
                ForEach-Object {
                    Write-Host "Running pipeline script: $($_.Name)"
                    Push-Location $postDir
                    try {
                        & $python $_.FullName
                    } finally {
                        Pop-Location
                    }
                }
        } else {
            Write-Host "No post scripts directory found; skipping pipeline."
        }
    }

    if (-not $SkipRender) {
        $quartoPython = Join-Path $repoFull ".venv\Scripts\python.exe"
        if (Test-Path -LiteralPath $quartoPython) {
            $env:QUARTO_PYTHON = $quartoPython
        }

        $quartoLocal = Join-Path $repoFull ".quarto-local"
        $quartoLocalAppData = Join-Path $quartoLocal "localappdata"
        $quartoLogDir = Join-Path $quartoLocal "logs"
        New-Item -ItemType Directory -Path $quartoLocalAppData -Force | Out-Null
        New-Item -ItemType Directory -Path $quartoLogDir -Force | Out-Null
        $env:LOCALAPPDATA = $quartoLocalAppData
        $env:DENO_DIR = Join-Path $quartoLocal "deno"
        $env:IPYTHONDIR = Join-Path $quartoLocal "ipython"
        $env:QUARTO_LOG = Join-Path $quartoLogDir "quarto.log"

        $freezeBefore = (& git status --porcelain -- _freeze)
        Write-Host "Rendering $relativePost"
        & quarto render $relativePost
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }

        $freezeAfter = (& git status --porcelain -- _freeze)
        if ($freezeAfter -ne $freezeBefore) {
            Write-Host "_freeze changed during render; review and commit the relevant updates."
        } else {
            Write-Host "_freeze did not change during render."
        }
    }

    Write-Host "Preflight passed for $relativePost"
} finally {
    Pop-Location
}
