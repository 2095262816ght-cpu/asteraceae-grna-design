@echo off
setlocal
if defined PYTHON_EXE (
    "%PYTHON_EXE%" "%~dp0RNAfold_shim.py" %*
) else (
    python "%~dp0RNAfold_shim.py" %*
)
