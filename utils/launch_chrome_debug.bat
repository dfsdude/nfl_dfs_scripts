@echo off
REM Launch Chrome with remote debugging enabled for Selenium automation
REM This allows the Python script to connect to your logged-in Chrome session

echo.
echo ================================================================
echo Starting Chrome with Remote Debugging
echo ================================================================
echo.
echo This will open Chrome with remote debugging enabled on port 9222
echo.
echo IMPORTANT: 
echo   1. Log into FantasyPros in the Chrome window that opens
echo   2. Keep this window open while running the scraper script
echo   3. Run: python utils/scrape_fantasypros.py -o data/fantasypros/
echo.
echo Press any key to launch Chrome...
pause > nul

REM Create profile directory if it doesn't exist
if not exist "C:\selenium\ChromeProfile" mkdir "C:\selenium\ChromeProfile"

REM Try common Chrome installation paths
set CHROME_PATH=""

if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) else if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
) else (
    echo ERROR: Could not find Chrome installation
    echo Please update the script with your Chrome path
    pause
    exit /b 1
)

echo Using Chrome: %CHROME_PATH%
echo.

REM Launch Chrome with remote debugging
start "" %CHROME_PATH% --remote-debugging-port=9222 --user-data-dir="C:/selenium/ChromeProfile"

echo.
echo Chrome launched! Log into FantasyPros, then run the scraper script.
echo.
pause
