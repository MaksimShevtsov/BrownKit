#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'
& python3 (Join-Path $PSScriptRoot '..' 'python' 'parse_coverage.py') @args
exit $LASTEXITCODE
