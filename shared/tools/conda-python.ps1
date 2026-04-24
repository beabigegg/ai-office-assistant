$ErrorActionPreference = 'Stop'

$envName = if ($env:AI_OFFICE_CONDA_ENV) { $env:AI_OFFICE_CONDA_ENV } else { 'ai-office' }

function Resolve-CondaPython {
    if ($env:CONDA_PYTHON_EXE -and (Test-Path -LiteralPath $env:CONDA_PYTHON_EXE)) {
        return $env:CONDA_PYTHON_EXE
    }

    if ($env:CONDA_PREFIX) {
        $name = Split-Path -Leaf $env:CONDA_PREFIX
        if ($name -eq $envName) {
            $candidate = Join-Path $env:CONDA_PREFIX 'python.exe'
            if (Test-Path -LiteralPath $candidate) {
                return $candidate
            }
        }
    }

    if ($env:CONDA_EXE) {
        try {
            $condaBase = & $env:CONDA_EXE info --base 2>$null
            if ($condaBase) {
                $candidate = Join-Path $condaBase "envs\$envName\python.exe"
                if (Test-Path -LiteralPath $candidate) {
                    return $candidate
                }
            }
        } catch {
        }
    }

    $candidates = @()
    if ($env:USERPROFILE) {
        $candidates += @(
            (Join-Path $env:USERPROFILE ".conda\envs\$envName\python.exe"),
            (Join-Path $env:USERPROFILE "miniconda3\envs\$envName\python.exe"),
            (Join-Path $env:USERPROFILE "anaconda3\envs\$envName\python.exe")
        )
    }

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    throw "cannot locate conda env '$envName' python interpreter."
}

$pythonBin = Resolve-CondaPython
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:CONDA_PYTHON_EXE = $pythonBin

& $pythonBin @args
$exitCode = $LASTEXITCODE
if ($null -eq $exitCode) {
    $exitCode = 0
}
exit $exitCode
