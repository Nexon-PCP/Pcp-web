@echo off
cd C:\PCP_WEB

REM Verificar se o arquivo .env.telegram existe
if not exist ".env.telegram" (
    echo.
    echo ========================================
    echo AVISO: Arquivo .env.telegram nao encontrado!
    echo ========================================
    echo.
    echo Crie o arquivo .env.telegram com:
    echo TELEGRAM_BOT_TOKEN=seu_token_aqui
    echo TELEGRAM_USER_ID=seu_id_aqui
    echo.
    pause
)

REM Abrir navegador
start http://127.0.0.1:5000

REM Iniciar aplicacao
echo.
echo ========================================
echo Iniciando PCP Web...
echo ========================================
echo.
echo A aplicacao estara disponivel em:
echo http://127.0.0.1:5000
echo.
echo Telegram Notifier: ATIVADO
echo Verificacao a cada 5 minutos
echo.
echo Pressione Ctrl+C para parar a aplicacao
echo ========================================
echo.

python app.py

pause
