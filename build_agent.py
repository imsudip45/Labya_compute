#!/usr/bin/env python3
"""
Autonomous Build Script for Labhya Compute Agent
Compiles the Python desktop agent client into a standalone executable,
packages it into a Nullsoft Installer (.exe setup), and places both
in the static downloads folder of the Next.js frontend website.
"""

import os
import sys
import shutil
import subprocess

def log(msg):
    print(f"[BUILD LOG] {msg}", flush=True)

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    agent_script = os.path.join(root_dir, "backend", "agent", "agent_gui.py")
    dist_dest = os.path.join(root_dir, "frontend", "public", "downloads")
    
    log(f"Project root: {root_dir}")
    log(f"Agent script source: {agent_script}")
    log(f"Target distribution folder: {dist_dest}")
    
    # 1. Ensure PyInstaller is installed
    try:
        import PyInstaller
        log("PyInstaller is already installed.")
    except ImportError:
        log("PyInstaller not found. Installing now...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "requests"], check=True)
        log("PyInstaller installed successfully.")
    
    # 2. Run PyInstaller to build executable
    log("Building standalone executable with PyInstaller...")
    build_cmd = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        "--name", "LabhyaComputeAgent",
        agent_script
    ]
    
    try:
        subprocess.run(build_cmd, check=True)
        log("PyInstaller build finished successfully.")
    except subprocess.CalledProcessError as e:
        log(f"Error: PyInstaller build failed: {e}")
        sys.exit(1)
        
    binary_name = "LabhyaComputeAgent.exe" if sys.platform.startswith("win") else "LabhyaComputeAgent"
    compiled_file = os.path.join(root_dir, "dist", binary_name)
    
    if not os.path.exists(compiled_file):
        log(f"Error: Compiled file not found at expected location: {compiled_file}")
        sys.exit(1)
        
    # 3. Compile NSIS Installer Setup if on Windows
    nsis_path = r"C:\Program Files (x86)\NSIS\makensis.exe"
    nsis_compiled = False
    
    if sys.platform.startswith("win") and os.path.exists(nsis_path):
        log("NSIS compiler found. Packaging into Windows Installer (.exe setup)...")
        nsis_script_content = r"""
!define APPNAME "Labhya Compute Host Agent"
!define COMPANYNAME "Labhya Compute"
!define DESCRIPTION "Desktop agent client to host and lease GPU compute resources"
!define VERSIONMAJOR 1
!define VERSIONMINOR 0
!define VERSIONBUILD 0

SetCompressor lzma
OutFile "dist\LabhyaComputeAgentSetup.exe"
InstallDir "$PROGRAMFILES64\${APPNAME}"
InstallDirRegKey HKLM "Software\${COMPANYNAME}\${APPNAME}" "Install_Dir"
RequestExecutionLevel admin

Page directory
Page instfiles

UninstPage uninstConfirm
UninstPage instfiles

Section "Install"
  SetOutPath $INSTDIR
  File "dist\LabhyaComputeAgent.exe"
  
  WriteRegStr HKLM "SOFTWARE\${COMPANYNAME}\${APPNAME}" "Install_Dir" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayName" "${APPNAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayVersion" "${VERSIONMAJOR}.${VERSIONMINOR}.${VERSIONBUILD}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "Publisher" "${COMPANYNAME}"
  
  WriteUninstaller "uninstall.exe"
  
  CreateDirectory "$SMPROGRAMS\${APPNAME}"
  CreateShortcut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\LabhyaComputeAgent.exe" "" "$INSTDIR\LabhyaComputeAgent.exe" 0
  CreateShortcut "$SMPROGRAMS\${APPNAME}\Uninstall.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe" 0
  CreateShortcut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\LabhyaComputeAgent.exe" "" "$INSTDIR\LabhyaComputeAgent.exe" 0
SectionEnd

Section "Uninstall"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
  DeleteRegKey HKLM "SOFTWARE\${COMPANYNAME}\${APPNAME}"
  
  Delete "$INSTDIR\LabhyaComputeAgent.exe"
  Delete "$INSTDIR\uninstall.exe"
  
  Delete "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk"
  Delete "$SMPROGRAMS\${APPNAME}\Uninstall.lnk"
  Delete "$DESKTOP\${APPNAME}.lnk"
  
  RMDir "$SMPROGRAMS\${APPNAME}"
  RMDir "$INSTDIR"
SectionEnd
"""
        nsi_file = os.path.join(root_dir, "installer.nsi")
        with open(nsi_file, "w", encoding="utf-8") as f:
            f.write(nsis_script_content)
            
        try:
            subprocess.run([nsis_path, nsi_file], check=True)
            nsis_compiled = True
            log("Installer setup packaging completed successfully.")
        except subprocess.CalledProcessError as e:
            log(f"Warning: NSIS packaging failed: {e}")
        finally:
            if os.path.exists(nsi_file):
                os.remove(nsi_file)
    else:
        log("NSIS compiler not found or not on Windows. Skipping installer setup packaging.")

    # 4. Create target directory and copy binary & raw Python script
    os.makedirs(dist_dest, exist_ok=True)
    destination_file = os.path.join(dist_dest, binary_name)
    destination_py = os.path.join(dist_dest, "LabhyaComputeAgent.py")
    
    log(f"Copying compiled binary to destination: {destination_file}")
    shutil.copy2(compiled_file, destination_file)
    log(f"[SUCCESS] Executable successfully deployed to web portal at /downloads/{binary_name}")

    if nsis_compiled:
        setup_src = os.path.join(root_dir, "dist", "LabhyaComputeAgentSetup.exe")
        setup_dest = os.path.join(dist_dest, "LabhyaComputeAgentSetup.exe")
        if os.path.exists(setup_src):
            log(f"Copying Installer Setup to destination: {setup_dest}")
            shutil.copy2(setup_src, setup_dest)
            log(f"[SUCCESS] Installer setup successfully deployed to web portal at /downloads/LabhyaComputeAgentSetup.exe")

    log(f"Copying raw Python script to destination: {destination_py}")
    shutil.copy2(agent_script, destination_py)
    log(f"[SUCCESS] Python script successfully deployed to web portal at /downloads/LabhyaComputeAgent.py")
    
    # 5. Clean up PyInstaller build files
    log("Cleaning up intermediate build files...")
    for folder in ["build", "dist"]:
        path = os.path.join(root_dir, folder)
        if os.path.exists(path):
            shutil.rmtree(path)
            
    spec_file = os.path.join(root_dir, "LabhyaComputeAgent.spec")
    if os.path.exists(spec_file):
        os.remove(spec_file)
        
    log("[SUCCESS] Cleanup finished. Build pipeline complete!")

if __name__ == "__main__":
    main()
