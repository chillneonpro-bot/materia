@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3.13 -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    py -3.13 launcher.py
    goto :done
  )
  py -3.12 -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    py -3.12 launcher.py
    goto :done
  )
  py -3.11 -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    py -3.11 launcher.py
    goto :done
  )
)

where python >nul 2>nul
if %errorlevel%==0 (
  python launcher.py
  goto :done
)

echo Python 3.11, 3.12 ou 3.13 est necessaire.
echo Installez-le depuis https://www.python.org/downloads/windows/
pause
exit /b 1

:done
if not %errorlevel%==0 pause
endlocal
