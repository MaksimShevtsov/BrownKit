#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'
$script = Join-Path (Join-Path (Join-Path $PSScriptRoot '..') 'python') 'gate_verdict.py'
& python3 $script @args
exit $LASTEXITCODE
