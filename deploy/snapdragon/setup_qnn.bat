@echo off
setlocal
echo ====================================================
echo Qualcomm Neural Processing SDK (QNN) Setup
echo ====================================================

REM Modify these paths to point to your actual QNN SDK installation
set QNN_SDK_ROOT=C:\Qualcomm\QNN\2.22.6.240515
set ADSP_LIBRARY_PATH=%QNN_SDK_ROOT%\lib\hexagon-v68\unsigned

REM Prepend QNN binary paths to PATH
set PATH=%QNN_SDK_ROOT%\bin\x86_64-windows-msvc;%QNN_SDK_ROOT%\lib\x86_64-windows-msvc;%PATH%
set PATH=%QNN_SDK_ROOT%\bin\aarch64-windows-msvc;%QNN_SDK_ROOT%\lib\aarch64-windows-msvc;%PATH%

echo [INFO] QNN_SDK_ROOT set to %QNN_SDK_ROOT%
echo [INFO] Environment variables loaded for QNN EP Execution.
endlocal
