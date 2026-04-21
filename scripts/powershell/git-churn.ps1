#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'
& python3 (Join-Path $PSScriptRoot '..' 'python' 'git_churn.py') @args
exit $LASTEXITCODE
