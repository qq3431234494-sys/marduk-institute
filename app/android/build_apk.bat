@echo off
chcp 65001 >nul
echo ============================================
echo   MARDUK INSTITUTE - Android APK Build
echo ============================================
echo.

set ANDROID_DIR=%~dp0

echo Prerequisites:
echo   1. Android Studio installed (with SDK 34)
echo   2. ANDROID_HOME environment variable set
echo   3. Java JDK 17+
echo.

set GRADLE_CMD=

if exist "%ANDROID_DIR%gradlew.bat" (
    set GRADLE_CMD=%ANDROID_DIR%gradlew.bat
    echo [INFO] Found local gradlew.bat
) else if exist "%ANDROID_DIR%gradlew" (
    set GRADLE_CMD=%ANDROID_DIR%gradlew
    echo [INFO] Found local gradlew
) else (
    where gradle >nul 2>&1
    if not errorlevel 1 (
        echo [INFO] Generating Gradle wrapper...
        cd /d "%ANDROID_DIR%"
        gradle wrapper --gradle-version 8.0 2>nul
        if errorlevel 1 (
            echo.
            echo ERROR: Cannot create Gradle wrapper.
            echo.
            echo Please do ONE of the following:
            echo.
            echo   Option A: Install Gradle and retry
            echo     https://gradle.org/install/
            echo.
            echo   Option B: Open in Android Studio
            echo     File ^> Open ^> select: %ANDROID_DIR%
            echo     Build ^> Build Bundle(s) / APK(s) ^> Build APK(s)
            echo.
            echo   Option C: Install Gradle wrapper manually
            echo     cd %ANDROID_DIR%
            echo     gradle wrapper --gradle-version 8.0
            echo.
            pause
            exit /b 1
        )
        set GRADLE_CMD=%ANDROID_DIR%gradlew.bat
    ) else (
        echo.
        echo ERROR: Gradle not found.
        echo.
        echo Please do ONE of the following:
        echo.
        echo   Option A: Install Gradle
        echo     https://gradle.org/install/
        echo     Then run: gradle wrapper --gradle-version 8.0
        echo.
        echo   Option B: Open in Android Studio (RECOMMENDED)
        echo     File ^> Open ^> select: %ANDROID_DIR%
        echo     Build ^> Build Bundle(s) / APK(s) ^> Build APK(s)
        echo.
        pause
        exit /b 1
    )
)

echo.
echo [1/2] Building debug APK...
cd /d "%ANDROID_DIR%"
call %GRADLE_CMD% assembleDebug

if errorlevel 1 (
    echo.
    echo ERROR: Build failed.
    echo.
    echo Try opening the project in Android Studio instead:
    echo   File ^> Open ^> select the android folder
    echo   Build ^> Build Bundle(s) / APK(s) ^> Build APK(s)
    pause
    exit /b 1
)

echo [2/2] Locating APK...
set APK_PATH=%ANDROID_DIR%app\build\outputs\apk\debug\app-debug.apk
if exist "%APK_PATH%" (
    echo.
    echo ============================================
    echo   BUILD SUCCESSFUL!
    echo.
    echo   APK: %APK_PATH%
    echo.
    echo   Install with:
    echo     adb install -r "%APK_PATH%"
    echo.
    echo   Or copy to phone and install directly.
    echo ============================================
) else (
    echo APK not found at expected path. Check build output.
)

pause
