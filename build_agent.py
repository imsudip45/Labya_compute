#!/usr/bin/env python3
"""
Autonomous Build Script for Labhya Compute Agent
Compiles the Python desktop agent client into a standalone executable
and places it in the static downloads folder of the Next.js frontend website.
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
    # --noconsole prevents terminal window spawn (it is a GUI app)
    # --onefile packages everything into a single binary
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
        
    # Determine compiled filename based on OS (.exe for Windows)
    binary_name = "LabhyaComputeAgent.exe" if sys.platform.startswith("win") else "LabhyaComputeAgent"
    compiled_file = os.path.join(root_dir, "dist", binary_name)
    
    if not os.path.exists(compiled_file):
        log(f"Error: Compiled file not found at expected location: {compiled_file}")
        sys.exit(1)
        
    # 3. Create target directory and copy binary
    os.makedirs(dist_dest, exist_ok=True)
    destination_file = os.path.join(dist_dest, binary_name)
    
    log(f"Copying compiled binary to destination: {destination_file}")
    shutil.copy2(compiled_file, destination_file)
    log(f"[SUCCESS] Executable successfully deployed to web portal at /downloads/{binary_name}")
    
    # 4. Clean up PyInstaller build files (optional but keeps workspace clean)
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
