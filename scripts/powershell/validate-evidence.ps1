#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'
& python3 (Join-Path $PSScriptRoot '..' 'python' 'validate_evidence.py') @args
exit $LASTEXITCODE
