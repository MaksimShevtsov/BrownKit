#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'
& python3 (Join-Path $PSScriptRoot '..' 'python' 'detect_stack.py') @args
exit $LASTEXITCODE
