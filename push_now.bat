@echo off
title GitHub Push — AI Interview Platform
color 0A
echo.
echo ============================================
echo   Pushing to GitHub...
echo ============================================
echo.

cd /d "d:\final_project_"

echo [Step 1] Initializing git repo...
git init
echo Done.

echo.
echo [Step 2] Setting remote origin...
git remote remove origin 2>nul
git remote add origin https://github.com/finalprojectphasez-ops/final_project.git
echo Done.

echo.
echo [Step 3] Staging all files...
git add .
echo Done.

echo.
echo [Step 4] Creating commit...
git commit -m "Initial commit: AI-Powered Interview Practice Platform"
echo Done.

echo.
echo [Step 5] Pushing to GitHub...
git branch -M main
git push -u origin main

echo.
echo ============================================
if %ERRORLEVEL% EQU 0 (
    echo   SUCCESS! Code pushed to GitHub!
    echo   https://github.com/finalprojectphasez-ops/final_project
) else (
    echo   FAILED. See error above.
    echo   You may need to login with your GitHub PAT token.
)
echo ============================================
echo.
pause
