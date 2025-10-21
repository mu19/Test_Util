@echo off
chcp 65001 > nul
echo ====================================
echo 로그 파일 내용
echo ====================================
echo.

set LOG_DIR=%APPDATA%\LogCollector\logs

if exist "%LOG_DIR%\*.log" (
    for /f %%f in ('dir /b /o-d "%LOG_DIR%\*.log"') do (
        echo [파일: %%f]
        type "%LOG_DIR%\%%f"
        echo.
        goto :done
    )
) else (
    echo 로그 파일이 없습니다.
)

:done
pause
