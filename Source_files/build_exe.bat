@echo off
rem Build a single-file exe plus SEM-Images\test images into dist\
cd /d "%~dp0"
py -m PyInstaller --noconfirm --clean --onefile --windowed --name CPO-File-Generator ^
  --hidden-import PIL._tkinter_finder ^
  --exclude-module pandas --exclude-module pytest --exclude-module IPython ^
  --exclude-module scipy.optimize --exclude-module scipy.stats --exclude-module scipy.signal ^
  --exclude-module scipy.interpolate --exclude-module scipy.spatial --exclude-module scipy.integrate ^
  --exclude-module scipy.io --exclude-module scipy.fft --exclude-module scipy.cluster ^
  --exclude-module scipy.odr --exclude-module scipy.misc --exclude-module scipy.datasets ^
  --exclude-module matplotlib.tests --exclude-module numpy.tests --exclude-module PIL.ImageQt ^
  --exclude-module PyQt5 --exclude-module PyQt6 --exclude-module PySide2 --exclude-module PySide6 ^
  --exclude-module wx --exclude-module gi --exclude-module cairo --exclude-module tornado ^
  --exclude-module jupyter --exclude-module notebook --exclude-module sqlite3 ^
  --exclude-module lib2to3 --exclude-module pip --exclude-module setuptools --exclude-module xmlrpc ^
  run_cpogen.py
if errorlevel 1 exit /b 1
set "T=dist\SEM-Images\test images"
if not exist "%T%" mkdir "%T%"
copy /y "SEM-Images\*.jpg" "%T%" >nul
echo Built dist\CPO-File-Generator.exe
