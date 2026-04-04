# PC -> GitHub -> VPS. Run: see push-and-deploy.cmd in repo root or SERVER_RUNBOOK 8.5
# ASCII only (Windows PowerShell 5.1 + UTF-8 without BOM).

param(
    [string] $SshTarget = $env:TG_MINI_APP_DEPLOY_SSH,
    [string] $GitRemote = "github",
    [string] $Branch = "main",
    [string] $ServerPath = "/srv/tg_mini_app",
    [string] $CommitMessage = "",
    [string] $ServerGitRemote = "",
    [switch] $SkipPush,
    [switch] $SkipDeploy,
    [switch] $CheckOnly,
    # If set, do not auto-commit; exit when there are uncommitted changes
    [switch] $RequireExplicitCommit
)

$ErrorActionPreference = "Stop"

# Script lives in .../scripts/ ; repo root is parent (works no matter current directory)
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else {
    Split-Path -Parent -Path $MyInvocation.MyCommand.Path
}
$root = Split-Path -Parent -Path $scriptDir
Set-Location -LiteralPath $root

Write-Host "Repo root: $root" -ForegroundColor DarkGray

function Test-CommandExists {
    param([string] $Name)
    return [bool](Get-Command -Name $Name -ErrorAction SilentlyContinue)
}

if (-not (Test-Path -LiteralPath (Join-Path $root ".git"))) {
    Write-Error "Not a git repo: $root (missing .git)"
    exit 1
}

if (-not (Test-CommandExists "git")) {
    Write-Error "git not found in PATH. Install Git for Windows or add it to PATH."
    exit 1
}

if (-not $SkipDeploy -and -not $CheckOnly -and -not (Test-CommandExists "ssh")) {
    Write-Error "ssh not found in PATH. Install OpenSSH client or Git for Windows (ssh.exe)."
    exit 1
}

$remoteCheck = & git remote 2>$null
if ($remoteCheck -notcontains $GitRemote) {
    Write-Host "Git remotes:" -ForegroundColor Yellow
    & git remote -v
    Write-Error "Remote '$GitRemote' not found. Use -GitRemote NAME or: git remote add github <url>"
    exit 1
}

if ($CheckOnly) {
    $sshOk = Test-CommandExists "ssh"
    Write-Host "git: OK | ssh: $(if ($sshOk) { 'OK' } else { 'MISSING (needed for deploy)' }) | remote: $GitRemote | .git: OK" -ForegroundColor Green
    exit 0
}

function Invoke-Git {
    param([string[]] $GitArguments)
    & git @GitArguments
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not $SkipPush) {
    if ($CommitMessage) {
        Invoke-Git @("add", "-A")
        $porcelain = git status --porcelain
        if ($porcelain) {
            Invoke-Git @("commit", "-m", $CommitMessage)
        } else {
            Write-Host "Nothing to commit." -ForegroundColor DarkGray
        }
    }

    $left = git status --porcelain
    if ($left) {
        if ($RequireExplicitCommit) {
            Write-Host "Uncommitted changes:" -ForegroundColor Yellow
            git status -s
            Write-Host ""
            Write-Host "Fix: commit manually OR use -CommitMessage 'summary' OR omit -RequireExplicitCommit for auto-commit"
            exit 1
        }
        $defaultMsg = "chore(deploy): sync $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
        Write-Host "Uncommitted changes -> auto commit: $defaultMsg" -ForegroundColor Yellow
        Invoke-Git @("add", "-A")
        Invoke-Git @("commit", "-m", $defaultMsg)
        $left = git status --porcelain
        if ($left) {
            Write-Error "Working tree still dirty after commit."
            exit 1
        }
    }

    Write-Host "==> git push $GitRemote $Branch" -ForegroundColor Cyan
    Invoke-Git @("push", $GitRemote, $Branch)
}

if (-not $SkipDeploy) {
    if (-not $SshTarget) {
        Write-Host "Missing SSH target. Use:" -ForegroundColor Yellow
        Write-Host "  -SshTarget user@host"
        Write-Host "  or set env TG_MINI_APP_DEPLOY_SSH=user@host"
        exit 1
    }

    $remote = ""
    if ($ServerGitRemote) {
        $remote = "GIT_REMOTE=$ServerGitRemote "
    }
    $remoteCmd = "cd $ServerPath && ${remote}bash deploy/server-update.sh"

    Write-Host "==> ssh $SshTarget (server update)" -ForegroundColor Cyan
    & ssh $SshTarget $remoteCmd
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not $SkipPush -and -not $SkipDeploy) {
    Write-Host "Done: pushed to GitHub and server deploy finished." -ForegroundColor Green
} elseif (-not $SkipPush) {
    Write-Host "Done: pushed to GitHub." -ForegroundColor Green
} elseif (-not $SkipDeploy) {
    Write-Host "Done: server deploy finished." -ForegroundColor Green
} else {
    Write-Host "Done." -ForegroundColor Green
}
