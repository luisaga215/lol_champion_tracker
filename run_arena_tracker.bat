@echo off
title League of Legends Arena Tracker Setup
color 0b

echo ==============================================================
echo       League of Legends Arena Champion Tracker Starter
echo ==============================================================
echo.

:: Check if Docker is installed
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed on this PC.
    echo Please download and install Docker Desktop from:
    echo https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b
)

:: Check if Docker daemon is running
echo Checking if Docker Desktop is running...
docker info >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Docker Desktop is installed but NOT running.
    echo Please start the "Docker Desktop" application from your Start Menu
    echo and wait for the green indicator at the bottom-left to show.
    echo.
    echo Once Docker is running, press any key to try again...
    pause >nul
    
    :: Re-check daemon
    docker info >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Docker is still not running. Exiting.
        pause
        exit /b
    )
)

echo [OK] Docker is running.
echo.

:: Start container using Docker Compose
echo Starting the Tracker application (building container and setting up database)...
docker compose version >nul 2>nul
if %errorlevel% == 0 (
    docker compose up -d --build
) else (
    docker-compose up -d --build
)

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to start container. Check the errors above.
    pause
    exit /b
)

echo.
echo [OK] Container is running!
echo Waiting 5 seconds for the database and champion portraits to sync...
timeout /t 5 /nobreak >nul

:: Open default web browser
echo.
echo Opening the Champion Tracker in your browser...
start http://localhost:3000

echo.
echo ==============================================================
echo  ALL DONE!
echo  The tracker is ready at: http://localhost:3000
echo.
echo  To stop the application in the future:
echo  1. Open a command prompt here and run: docker compose down
echo  2. Or stop it inside the Docker Desktop app interface.
echo ==============================================================
echo.
pause
