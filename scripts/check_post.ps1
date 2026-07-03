param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$PostPath,

    [switch]$RunPipeline,

    [switch]$AllowDraft,

    [switch]$SkipRender
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (& git rev-parse --show-toplevel).Trim()
if (-not $repoRoot) {
    throw "Run this script from inside the blog Git repository."
}

$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $python = "python"
}

$tool = Join-Path $repoRoot "tools\check_post.py"
if (-not (Test-Path -LiteralPath $tool)) {
    throw "Missing tool: $tool"
}

$args = @($tool, $PostPath)
if ($RunPipeline) {
    $args += "--run-pipeline"
}
if ($AllowDraft) {
    $args += "--allow-draft"
}
if ($SkipRender) {
    $args += "--skip-render"
}

& $python @args
exit $LASTEXITCODE
