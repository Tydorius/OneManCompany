@echo off
setlocal

REM ====================================================================
REM  run_tests.bat - Run pytest in isolated process, write results
REM  to a file so the calling session never blocks or dies.
REM
REM  Usage:
REM    run_tests.bat                          (run all unit tests)
REM    run_tests.bat tests\unit\core\         (run specific path)
REM    run_tests.bat tests\unit\core\ -k foo  (with extra pytest args)
REM
REM  Results file: .test-results\result.txt
REM    Line 1:  PASS or FAIL
REM    Line 2:  timestamp
REM    Line 3:  exit code
REM    Line 4:  command run
REM    Line 5+: pytest output
REM ====================================================================

REM --- Resolve project root (where this script lives) ---
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%"

REM --- Results directory ---
set "RESULTS_DIR=.test-results"
if not exist "%RESULTS_DIR%" mkdir "%RESULTS_DIR%"

REM --- Timestamp ---
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value ^| find "="') do set "TS=%%I"
set "TIMESTAMP=%TS:~0,4%-%TS:~4,2%-%TS:~6,2% %TS:~8,2%:%TS:~10,2%:%TS:~12,2%"

REM --- Determine test target ---
if "%~1"=="" (
    set "TEST_TARGET=tests\unit\"
) else (
    set "TEST_TARGET=%~1"
)

REM --- Collect extra args ---
shift
set "EXTRA_ARGS="
:collect_args
if "%~1"=="" goto :done_collect
set "EXTRA_ARGS=%EXTRA_ARGS% %~1"
shift
goto :collect_args
:done_collect

REM --- Results file ---
set "RESULT_FILE=%RESULTS_DIR%\result.txt"
set "TEMP_FILE=%RESULTS_DIR%\result_tmp.txt"

REM --- Write initial marker so callers know tests are running ---
echo RUNNING > "%RESULT_FILE%"
echo %TIMESTAMP% >> "%RESULT_FILE%"

REM --- Run pytest ---
set "PYTHON=.venv\Scripts\python.exe"

if exist "%PYTHON%" (
    "%PYTHON%" -m pytest %TEST_TARGET% %EXTRA_ARGS% -v --tb=short >> "%RESULT_FILE%" 2>&1
) else (
    echo FAIL > "%RESULT_FILE%"
    echo %TIMESTAMP% >> "%RESULT_FILE%"
    echo 127 >> "%RESULT_FILE%"
    echo ERROR: python.exe not found in .venv\Scripts\ >> "%RESULT_FILE%"
    echo Make sure the virtual environment is set up. >> "%RESULT_FILE%"
    exit /b 127
)

REM --- Capture exit code ---
set "EXIT_CODE=%ERRORLEVEL%"

REM --- Build final result file with status header ---
if %EXIT_CODE% equ 0 (
    echo PASS > "%TEMP_FILE%"
) else (
    echo FAIL > "%TEMP_FILE%"
)
echo %TIMESTAMP% >> "%TEMP_FILE%"
echo %EXIT_CODE% >> "%TEMP_FILE%"
echo command: pytest %TEST_TARGET% %EXTRA_ARGS% >> "%TEMP_FILE%"

REM Append the pytest output (skip the 2 RUNNING header lines)
more +2 "%RESULT_FILE%" >> "%TEMP_FILE%"
move /y "%TEMP_FILE%" "%RESULT_FILE%" > nul

exit /b %EXIT_CODE%
