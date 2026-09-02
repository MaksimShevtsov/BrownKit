#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'
& python3 (Join-Path $PSScriptRoot '..' 'python' 'gate_verdict.py') @args
exit $LASTEXITCODE
