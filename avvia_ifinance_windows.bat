@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_DIR=%ROOT_DIR%frontend"

echo Avvio backend IFinance sulla porta 8011...
start "IFinance Backend" /D "%BACKEND_DIR%" cmd /k "call conda activate IFinanceTA && python -m uvicorn app.main:app --host 127.0.0.1 --port 8011 --reload"

echo Avvio frontend React/Vite sulla porta 5173...
start "IFinance Frontend" /D "%FRONTEND_DIR%" cmd /k "npm run dev -- --host 127.0.0.1"

echo.
echo Backend:  http://localhost:8011/docs
echo Frontend: http://localhost:5173
echo.
echo Sono state aperte due finestre del terminale.
pause
