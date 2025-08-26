#!/usr/bin/env python3
"""
Labhya Agent GUI Launcher
A modern GUI for registering and running the Labhya Compute agent
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import subprocess
import threading
import os
import sys
import json
import requests
from pathlib import Path
import platform
import webbrowser
import shutil
import time
try:
    import pynvml
except Exception:
    pynvml = None

class LabhyaLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Labhya Compute Agent Launcher")
        self.root.geometry("600x500")  # Increased size
        self.root.resizable(True, True)  # Allow resizing
        self.root.minsize(500, 400)  # Minimum size
        
        # Center the window
        self.center_window()
        
        # Set modern style
        self.setup_styles()
        
        # Agent executable path - check current directory first
        self.agent_exe = None
        
        # Define possible paths for the agent executable
        self.possible_paths = []
        if getattr(sys, 'frozen', False):
            # Running as executable - check directory where launcher is located
            base_dir = Path(sys.executable).parent
        else:
            # Running as script - check current working directory and script directory
            base_dir = Path(__file__).resolve().parent
        
        # Add possible paths (check current directory first)
        self.possible_paths.extend([
            base_dir / "labhya-agent.exe",           # Same directory as launcher
            Path.cwd() / "labhya-agent.exe",        # Current working directory
            base_dir / "agent" / "dist" / "labhya-agent.exe",  # Agent dist folder
            base_dir / "agent" / "labhya-agent.exe", # Agent folder
            Path("labhya-agent.exe"),                # Relative to current dir
            Path("agent/dist/labhya-agent.exe"),     # Relative agent dist
            Path("agent/labhya-agent.exe")           # Relative agent folder
        ])
        
        # Try to find the agent executable
        for path in self.possible_paths:
            if path.exists():
                self.agent_exe = path
                break
        
        if not self.agent_exe:
            # Fallback: try PATH
            from shutil import which
            found = which("labhya-agent.exe")
            if found:
                self.agent_exe = Path(found)
        
        # User state
        self.is_registered = False
        self.current_user = None
        
        # Agent process
        self.agent_process = None
        
        # Prerequisites status
        self.prereq_ok = False
        
        # Create GUI
        self.create_widgets()
        
        # Check registration status
        self.check_registration_status()
        # Check environment prerequisites
        self.refresh_prereq_status()
    
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_styles(self):
        """Setup modern styles for the GUI"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        self.root.configure(bg='#f0f0f0')
        
        # Configure styles
        style.configure('Title.TLabel', font=('Segoe UI', 16, 'bold'), background='#f0f0f0')
        style.configure('Subtitle.TLabel', font=('Segoe UI', 10), background='#f0f0f0', foreground='#666666')
        style.configure('Action.TButton', font=('Segoe UI', 10, 'bold'), padding=10)
        style.configure('Status.TLabel', font=('Segoe UI', 9), background='#f0f0f0')
        style.configure('Stop.TButton', font=('Segoe UI', 10, 'bold'), padding=10, background='#ff4444')
    
    def create_widgets(self):
        """Create the main GUI widgets"""
        # Configure grid weights for responsive layout
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure main frame grid weights
        main_frame.grid_rowconfigure(5, weight=1)  # Log frame gets extra space
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Labhya Compute Agent", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        subtitle_label = ttk.Label(main_frame, text="GPU Rental Platform", style='Subtitle.TLabel')
        subtitle_label.grid(row=1, column=0, columnspan=2, pady=(0, 20))
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="15")
        status_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        
        self.status_label = ttk.Label(status_frame, text="Checking registration status...", style='Status.TLabel')
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        self.gpu_info_label = ttk.Label(status_frame, text="", style='Status.TLabel')
        self.gpu_info_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Action buttons frame
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=3, column=0, columnspan=2, pady=(0, 20))
        
        # Setup environment button (initially hidden)
        self.setup_btn = ttk.Button(
            action_frame,
            text="Setup Environment (WSL2 + Ubuntu + Docker)",
            style='Action.TButton',
            command=self.run_setup_wizard
        )
        self.setup_btn.grid(row=0, column=0, padx=(0, 10))
        
        # Register button (initially hidden)
        self.register_btn = ttk.Button(
            action_frame, 
            text="Register GPU", 
            style='Action.TButton',
            command=self.register_gpu
        )
        self.register_btn.grid(row=0, column=1, padx=(10, 10))
        
        # Start agent button (initially hidden)
        self.start_btn = ttk.Button(
            action_frame, 
            text="Start Agent", 
            style='Action.TButton',
            command=self.start_agent
        )
        self.start_btn.grid(row=0, column=2, padx=(10, 0))
        
        # Stop agent button (initially hidden)
        self.stop_btn = ttk.Button(
            action_frame, 
            text="Stop Agent", 
            style='Stop.TButton',
            command=self.stop_agent
        )
        self.stop_btn.grid(row=0, column=2, padx=(10, 0))

        # Refresh status button
        self.refresh_btn = ttk.Button(
            action_frame,
            text="Refresh Status",
            style='Action.TButton',
            command=self.refresh_prereq_status
        )
        self.refresh_btn.grid(row=0, column=3, padx=(10, 0))
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Log frame with better styling
        log_frame = ttk.LabelFrame(main_frame, text="📋 Agent Logs", padding="10")
        log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Configure log frame grid weights
        log_frame.grid_rowconfigure(1, weight=1)  # Log text gets extra space
        log_frame.grid_columnconfigure(0, weight=1)
        
        # Log header with controls
        log_header = tk.Frame(log_frame)
        log_header.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        
        log_title = tk.Label(log_header, text="Real-time Agent Output", 
                            font=('Segoe UI', 10, 'bold'), 
                            fg='#2c3e50')
        log_title.pack(side=tk.LEFT)
        
        # Clear log button
        clear_log_btn = tk.Button(log_header, text="Clear Log", 
                                 command=lambda: self.log_text.delete(1.0, tk.END),
                                 font=('Segoe UI', 8),
                                 fg='#7f8c8d', bg='#ecf0f1',
                                 relief=tk.FLAT, bd=0,
                                 padx=10, pady=2,
                                 cursor='hand2')
        clear_log_btn.pack(side=tk.RIGHT)
        
        # Log text area with better styling
        self.log_text = tk.Text(log_frame, height=12, width=70, 
                               font=('Consolas', 9),
                               bg='#2c3e50', fg='#ecf0f1',
                               insertbackground='#ecf0f1',
                               selectbackground='#3498db',
                               relief=tk.FLAT, bd=0)
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        # Live GPU Metrics frame (hidden until agent running)
        self.metrics_frame = ttk.LabelFrame(main_frame, text="Live GPU Metrics", padding="10")
        self.metrics_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.metrics_frame.grid_remove()

        self.metrics_vars = {
            'util': tk.StringVar(value='-'),
            'mem': tk.StringVar(value='-'),
            'temp': tk.StringVar(value='-'),
            'power': tk.StringVar(value='-'),
            'fan': tk.StringVar(value='-'),
            'clocks': tk.StringVar(value='-'),
        }
        # layout
        row = 0
        ttk.Label(self.metrics_frame, text="Utilization").grid(row=row, column=0, sticky=tk.W, padx=(0,8)); ttk.Label(self.metrics_frame, textvariable=self.metrics_vars['util']).grid(row=row, column=1, sticky=tk.W); row+=1
        ttk.Label(self.metrics_frame, text="Memory").grid(row=row, column=0, sticky=tk.W, padx=(0,8)); ttk.Label(self.metrics_frame, textvariable=self.metrics_vars['mem']).grid(row=row, column=1, sticky=tk.W); row+=1
        ttk.Label(self.metrics_frame, text="Temperature").grid(row=row, column=0, sticky=tk.W, padx=(0,8)); ttk.Label(self.metrics_frame, textvariable=self.metrics_vars['temp']).grid(row=row, column=1, sticky=tk.W); row+=1
        ttk.Label(self.metrics_frame, text="Power").grid(row=row, column=0, sticky=tk.W, padx=(0,8)); ttk.Label(self.metrics_frame, textvariable=self.metrics_vars['power']).grid(row=row, column=1, sticky=tk.W); row+=1
        ttk.Label(self.metrics_frame, text="Fan").grid(row=row, column=0, sticky=tk.W, padx=(0,8)); ttk.Label(self.metrics_frame, textvariable=self.metrics_vars['fan']).grid(row=row, column=1, sticky=tk.W); row+=1
        ttk.Label(self.metrics_frame, text="Clocks").grid(row=row, column=0, sticky=tk.W, padx=(0,8)); ttk.Label(self.metrics_frame, textvariable=self.metrics_vars['clocks']).grid(row=row, column=1, sticky=tk.W); row+=1

        self.metrics_thread = None
        self.metrics_stop_evt = None
        
        # Initially hide all buttons
        self.setup_btn.grid_remove()
        self.register_btn.grid_remove()
        self.start_btn.grid_remove()
        self.stop_btn.grid_remove()
    
    def log(self, message):
        """Add message to log"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def check_registration_status(self):
        """Check if the user is already registered"""
        def check():
            try:
                # Check if agent executable exists
                if not self.agent_exe.exists():
                    self.log("Error: labhya-agent.exe not found!")
                    self.status_label.config(text="Error: Agent executable not found")
                    return
                
                # Try to get existing GPUs (this will tell us if user is registered)
                # For now, we'll assume not registered and show register button
                self.is_registered = False
                self.update_ui()
                
            except Exception as e:
                self.log(f"Error checking status: {e}")
                self.status_label.config(text="Error checking registration status")
        
        # Run in thread to avoid blocking UI
        threading.Thread(target=check, daemon=True).start()
    
    def update_ui(self):
        """Update UI based on registration status"""
        # Gate actions on prerequisites
        if not self.prereq_ok:
            self.status_label.config(text="Environment not ready – click Setup to install WSL2, Ubuntu 20.04, and Docker Desktop")
            self.setup_btn.grid()
            self.register_btn.grid_remove()
            self.start_btn.grid_remove()
            self.stop_btn.grid_remove()
            return

        if self.is_registered:
            self.status_label.config(text=f"Registered as: {self.current_user}")
            self.setup_btn.grid_remove()
            self.register_btn.grid_remove()
            self.start_btn.grid()
            self.stop_btn.grid_remove()
            # Show metrics frame when registered (even if agent not running)
            self.metrics_frame.grid()
            self.start_metrics_stream()
        else:
            self.status_label.config(text="Not registered - Register your GPU to start")
            self.setup_btn.grid_remove()
            self.register_btn.grid()
            self.start_btn.grid_remove()
            self.stop_btn.grid_remove()

    # ---------------- Prerequisites ----------------
    def refresh_prereq_status(self):
        def check_all():
            try:
                if platform.system() != 'Windows':
                    self.log("This launcher currently supports Windows setup only.")
                    self.prereq_ok = False
                    self.status_label.config(text="Unsupported OS – Windows required")
                    self.update_ui()
                    return

                wsl_ok = self.check_wsl_enabled()
                ubuntu_ok = self.check_ubuntu_installed()
                if not ubuntu_ok:
                    # Also accept specific Ubuntu distro names seen in the system
                    for distro in ("Ubuntu-22.04", "Ubuntu-20.04", "Ubuntu"):
                        try:
                            rr = subprocess.run([self._wsl_cmd(), "-d", distro, "--", "true"], capture_output=True, text=True, timeout=8)
                            if rr.returncode == 0:
                                self.log(f"✅ Ubuntu distribution available: {distro}")
                                ubuntu_ok = True
                                break
                        except Exception:
                            continue
                docker_installed = self.check_docker_installed()
                docker_running = self.check_docker_running() if docker_installed else False

                self.prereq_ok = all([wsl_ok, ubuntu_ok, docker_installed, docker_running])

                missing = []
                if not wsl_ok:
                    missing.append('WSL2')
                if not ubuntu_ok:
                    missing.append('Ubuntu')
                if not docker_installed:
                    missing.append('Docker Desktop')
                elif not docker_running:
                    missing.append('Docker (start it)')

                if self.prereq_ok:
                    self.log("✅ Prerequisites OK: WSL2, Ubuntu, Docker Desktop running")
                    self.status_label.config(text="Environment ready")
                else:
                    self.log("⚠️  Prerequisites missing: " + ", ".join(missing))
                    self.status_label.config(text=f"Environment not ready – missing: {', '.join(missing)}")
                self.update_ui()
            except Exception as e:
                self.log(f"Error checking prerequisites: {e}")
                self.prereq_ok = False
                self.status_label.config(text="Error checking prerequisites")
                self.update_ui()
        threading.Thread(target=check_all, daemon=True).start()

    def run_setup_wizard(self):
        """Guide user through WSL2, Ubuntu 20.04 and Docker setup. Attempts automation where possible."""
        def run():
            try:
                self.progress.start()
                self.log("=== Environment Setup Wizard ===")

                # 1) Enable WSL and Virtual Machine Platform (requires admin)
                self.log("Enabling WSL and Virtual Machine Platform features (requires Administrator)…")
                try:
                    # Launch elevated PowerShell to enable features
                    ps_cmd = (
                        'Start-Process PowerShell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass '
                        'dism /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart; '
                        'dism /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart; '
                        'wsl --set-default-version 2"'
                    )
                    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=60)
                    self.log("Requested WSL feature enable. A reboot may be required.")
                except Exception as e:
                    self.log(f"Could not auto-enable WSL features: {e}")

                # 2) Install Ubuntu 22.04
                if not self.check_ubuntu_installed():
                    self.log("Installing Ubuntu 22.04… (this may open a system window)")
                    try:
                        subprocess.run([self._wsl_cmd(), "--install", "-d", "Ubuntu-22.04"], timeout=180)
                        self.log("Ubuntu 22.04 installation initiated. Complete initialization on first launch if prompted.")
                    except Exception as e:
                        self.log(f"Could not auto-install Ubuntu 22.04: {e}")
                        self.log("Open Microsoft Store and install 'Ubuntu 22.04 LTS' manually.")
                        # Try direct product link for Ubuntu 22.04 LTS, fallback to search
                        if sys.platform.startswith('win'):
                            webbrowser.open("ms-windows-store://pdp/?productid=9PN20MSR04DW")
                        webbrowser.open("https://apps.microsoft.com/store/detail/ubuntu-2204-lts/9PN20MSR04DW")

                # 3) Install Docker Desktop
                if not self.check_docker_installed():
                    self.log("Opening Docker Desktop download page…")
                    webbrowser.open("https://www.docker.com/products/docker-desktop/")
                    self.log("Download and install Docker Desktop. When finished, start Docker Desktop.")

                # 4) Ensure Docker is running and using WSL2 engine
                self.log("Ensuring Docker Desktop is running…")
                # Try a simple docker info to trigger autostart if available
                self.check_docker_running()
                self.log("Make sure Docker Desktop is set to use WSL 2 backend and Ubuntu-22.04 is enabled under Resources > WSL Integration.")

                # Final re-check
                self.log("Re-checking prerequisites…")
                self.refresh_prereq_status()
                self.log("Setup wizard finished.")
            finally:
                self.progress.stop()
        threading.Thread(target=run, daemon=True).start()

    def check_wsl_enabled(self) -> bool:
        try:
            r = subprocess.run([self._wsl_cmd(), "--status"], capture_output=True, text=True)
            if r.returncode == 0:
                out = (r.stdout or r.stderr or "").lower()
                if "default version: 2" in out:
                    self.log("✅ WSL present (default version 2)")
                else:
                    self.log("⚠️  WSL present but default version is not 2. Will attempt to set.")
                    subprocess.run([self._wsl_cmd(), "--set-default-version", "2"], capture_output=True)
                return True
            self.log("❌ WSL not available")
            return False
        except FileNotFoundError:
            self.log("❌ wsl.exe not found")
            return False

    def _wsl_cmd(self) -> str:
        # Prefer absolute path to avoid PATH and WOW64 redirection issues
        system_root = os.environ.get('SystemRoot', r'C:\Windows')
        candidates = [
            os.path.join(system_root, 'Sysnative', 'wsl.exe'),  # visible to 32-bit processes
            os.path.join(system_root, 'System32', 'wsl.exe'),   # visible to 64-bit processes
            'wsl',
        ]
        for c in candidates:
            try:
                if c == 'wsl':
                    return c
                if os.path.exists(c):
                    return c
            except Exception:
                continue
        return 'wsl'

    def check_ubuntu_installed(self) -> bool:
        try:
            # Use quiet list to avoid table parsing and locales
            r = subprocess.run([self._wsl_cmd(), "-l", "-q"], capture_output=True, text=True)
            if r.returncode == 0:
                lines = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
                # Accept any Ubuntu distribution (20.04 preferred but not required)
                found = any(ln.lower().startswith("ubuntu") for ln in lines)
                if found:
                    self.log("✅ Ubuntu distribution detected: " + ", ".join(lines))
                    return True
                else:
                    # Fallback to verbose listing for some Windows builds
                    rv = subprocess.run([self._wsl_cmd(), "-l", "-v"], capture_output=True, text=True)
                    out = (rv.stdout or rv.stderr or "")
                    if any("ubuntu" in ln.lower() for ln in out.splitlines()):
                        self.log("✅ Ubuntu distribution detected (verbose)")
                        return True
                    # Log raw outputs to aid troubleshooting
                    self.log(f"WSL -l -q output: {r.stdout.strip()} | err: {r.stderr.strip()}")
                    self.log(f"WSL -l -v output: {(rv.stdout or '').strip()}")
                    # As a last resort, try launching Ubuntu once to ensure registration
                    try:
                        self.log("Attempting to launch default Ubuntu to finalize registration…")
                        subprocess.run([self._wsl_cmd(), "-d", "Ubuntu", "--", "true"], capture_output=True, timeout=10)
                    except Exception:
                        pass
            self.log("❌ Ubuntu distribution not found")
            return False
        except Exception as e:
            self.log(f"❌ Unable to query WSL distributions: {e}")
            return False

    def _docker_cmd(self) -> str:
        # Try PATH first
        path = shutil.which('docker')
        if path:
            return path
        # Fallback common Docker Desktop path
        candidate = r"C:\\Program Files\\Docker\\Docker\\resources\\bin\\docker.exe"
        return candidate if os.path.exists(candidate) else 'docker'

    def check_docker_installed(self) -> bool:
        try:
            r = subprocess.run([self._docker_cmd(), "--version"], capture_output=True, text=True)
            if r.returncode == 0:
                self.log(f"✅ Docker installed: {r.stdout.strip()}")
                return True
            self.log("❌ Docker not installed")
            return False
        except FileNotFoundError:
            self.log("❌ Docker not installed")
            return False

    def check_docker_running(self) -> bool:
        try:
            r = subprocess.run([self._docker_cmd(), "info"], capture_output=True, text=True, timeout=20)
            if r.returncode == 0:
                self.log("✅ Docker Desktop is running")
                return True
            self.log("❌ Docker Desktop not running")
            # On Windows, also check service state as a hint
            try:
                svc = subprocess.run(["sc", "query", "com.docker.service"], capture_output=True, text=True)
                if 'RUNNING' in svc.stdout.upper():
                    self.log("ℹ️ Docker service RUNNING but CLI not ready yet. Give it a few seconds.")
            except Exception:
                pass
            # Try to auto-start Docker Desktop
            self.start_docker_desktop()
            # Poll for readiness up to ~60s
            for _ in range(30):
                rr = subprocess.run([self._docker_cmd(), "info"], capture_output=True, text=True)
                if rr.returncode == 0:
                    self.log("✅ Docker Desktop started and is now running")
                    return True
                time.sleep(2)
            return False
        except Exception:
            self.log("❌ Unable to contact Docker daemon")
            return False

    def start_docker_desktop(self):
        """Attempt to launch Docker Desktop on Windows."""
        try:
            candidates = [
                r"C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe",
                os.path.expandvars(r"%LocalAppData%\\Docker\\Docker\\Docker Desktop.exe"),
            ]
            for exe in candidates:
                if exe and os.path.exists(exe):
                    self.log(f"Starting Docker Desktop: {exe}")
                    subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
                    return
        except Exception as e:
            self.log(f"Unable to auto-start Docker Desktop: {e}")

    def check_docker_ready(self) -> bool:
        return self.check_docker_installed() and self.check_docker_running()
    
    def register_gpu(self):
        """Register GPU with the platform"""
        # Create a custom registration dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("GPU Registration")
        dialog.geometry("500x520")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Configure dialog background
        dialog.configure(bg='#f0f0f0')
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (520 // 2)
        dialog.geometry(f"500x520+{x}+{y}")
        
        # Variables
        email_var = tk.StringVar()
        password_var = tk.StringVar()
        price_var = tk.IntVar(value=100)
        
        # Create main container with padding
        main_container = tk.Frame(dialog, bg='#f0f0f0', padx=35, pady=35)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Title with better styling
        title_frame = tk.Frame(main_container, bg='#f0f0f0')
        title_frame.pack(fill=tk.X, pady=(0, 25))
        
        title_label = tk.Label(title_frame, text="🚀 GPU Registration", 
                              font=('Segoe UI', 18, 'bold'), 
                              fg='#2c3e50', bg='#f0f0f0')
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, text="Register your GPU to start earning", 
                                 font=('Segoe UI', 10), 
                                 fg='#7f8c8d', bg='#f0f0f0')
        subtitle_label.pack(pady=(5, 0))
        
        # Form container
        form_frame = tk.Frame(main_container, bg='#f0f0f0')
        form_frame.pack(fill=tk.X, pady=(0, 25))
        
        # Email field
        email_frame = tk.Frame(form_frame, bg='#f0f0f0')
        email_frame.pack(fill=tk.X, pady=(0, 15))
        
        email_label = tk.Label(email_frame, text="Email Address", 
                              font=('Segoe UI', 10, 'bold'), 
                              fg='#2c3e50', bg='#f0f0f0', anchor='w')
        email_label.pack(fill=tk.X, pady=(0, 5))
        
        email_entry = tk.Entry(email_frame, textvariable=email_var, 
                              font=('Segoe UI', 10), 
                              relief=tk.FLAT, bd=0, 
                              highlightthickness=1, highlightcolor='#3498db',
                              highlightbackground='#bdc3c7')
        email_entry.pack(fill=tk.X, ipady=8)
        
        # Password field
        password_frame = tk.Frame(form_frame, bg='#f0f0f0')
        password_frame.pack(fill=tk.X, pady=(0, 15))
        
        password_label = tk.Label(password_frame, text="Password", 
                                 font=('Segoe UI', 10, 'bold'), 
                                 fg='#2c3e50', bg='#f0f0f0', anchor='w')
        password_label.pack(fill=tk.X, pady=(0, 5))
        
        password_entry = tk.Entry(password_frame, textvariable=password_var, show='*',
                                 font=('Segoe UI', 10), 
                                 relief=tk.FLAT, bd=0,
                                 highlightthickness=1, highlightcolor='#3498db',
                                 highlightbackground='#bdc3c7')
        password_entry.pack(fill=tk.X, ipady=8)
        
        # Price field
        price_frame = tk.Frame(form_frame, bg='#f0f0f0')
        price_frame.pack(fill=tk.X, pady=(0, 15))
        
        price_label = tk.Label(price_frame, text="Price per Hour (NPR)", 
                              font=('Segoe UI', 10, 'bold'), 
                              fg='#2c3e50', bg='#f0f0f0', anchor='w')
        price_label.pack(fill=tk.X, pady=(0, 5))
        
        price_entry = tk.Entry(price_frame, textvariable=price_var,
                              font=('Segoe UI', 10), 
                              relief=tk.FLAT, bd=0,
                              highlightthickness=1, highlightcolor='#3498db',
                              highlightbackground='#bdc3c7')
        price_entry.pack(fill=tk.X, ipady=8)
        
        # Buttons container - make sure it's visible
        button_container = tk.Frame(main_container, bg='#f0f0f0')
        button_container.pack(fill=tk.X, pady=(30, 10))
        
        def on_register():
            email = email_var.get().strip()
            password = password_var.get().strip()
            price = price_var.get()
            
            if not email or not password:
                messagebox.showerror("Error", "Please fill in all fields!")
                return
            
            if price <= 0:
                messagebox.showerror("Error", "Price must be greater than 0!")
                return
            
            dialog.destroy()
            self._perform_registration(email, password, price)
        
        def on_cancel():
            dialog.destroy()
        
        # Register button - make it very prominent
        register_btn = tk.Button(button_container, text="🚀 Register GPU", 
                                command=on_register,
                                font=('Segoe UI', 13, 'bold'),
                                fg='white', bg='#27ae60',
                                relief=tk.FLAT, bd=0,
                                padx=40, pady=15,
                                cursor='hand2')
        register_btn.pack(side=tk.RIGHT, padx=(20, 0))
        
        # Cancel button
        cancel_btn = tk.Button(button_container, text="Cancel", 
                              command=on_cancel,
                              font=('Segoe UI', 11),
                              fg='#7f8c8d', bg='#ecf0f1',
                              relief=tk.FLAT, bd=0,
                              padx=25, pady=12,
                              cursor='hand2')
        cancel_btn.pack(side=tk.RIGHT)
        
        # Hover effects
        def on_enter(e):
            e.widget['bg'] = '#229954' if e.widget == register_btn else '#d5dbdb'
        
        def on_leave(e):
            e.widget['bg'] = '#27ae60' if e.widget == register_btn else '#ecf0f1'
        
        register_btn.bind('<Enter>', on_enter)
        register_btn.bind('<Leave>', on_leave)
        cancel_btn.bind('<Enter>', on_enter)
        cancel_btn.bind('<Leave>', on_leave)
        
        # Focus on email entry
        email_entry.focus()
        
        # Bind Enter key to register
        dialog.bind('<Return>', lambda e: on_register())
        dialog.bind('<Escape>', lambda e: on_cancel())
        
        # Force update to ensure buttons are visible
        dialog.update()
        
        # Wait for dialog to close
        dialog.wait_window()
    
    def _get_password_dialog(self, title, message):
        """Create a modern password dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("450x250")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Configure dialog background
        dialog.configure(bg='#f0f0f0')
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (250 // 2)
        dialog.geometry(f"450x250+{x}+{y}")
        
        # Variables
        password_var = tk.StringVar()
        result = [None]  # Use list to store result
        
        # Create main container
        main_container = tk.Frame(dialog, bg='#f0f0f0', padx=35, pady=30)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(main_container, text="🔐 Authentication", 
                              font=('Segoe UI', 16, 'bold'), 
                              fg='#2c3e50', bg='#f0f0f0')
        title_label.pack(pady=(0, 10))
        
        # Message
        message_label = tk.Label(main_container, text=message, 
                                font=('Segoe UI', 10), 
                                fg='#7f8c8d', bg='#f0f0f0', wraplength=300)
        message_label.pack(pady=(0, 20))
        
        # Password field
        password_frame = tk.Frame(main_container, bg='#f0f0f0')
        password_frame.pack(fill=tk.X, pady=(0, 25))
        
        password_label = tk.Label(password_frame, text="Password", 
                                 font=('Segoe UI', 10, 'bold'), 
                                 fg='#2c3e50', bg='#f0f0f0', anchor='w')
        password_label.pack(fill=tk.X, pady=(0, 5))
        
        password_entry = tk.Entry(password_frame, textvariable=password_var, show='*',
                                 font=('Segoe UI', 12), 
                                 relief=tk.FLAT, bd=0,
                                 highlightthickness=2, highlightcolor='#3498db',
                                 highlightbackground='#bdc3c7')
        password_entry.pack(fill=tk.X, ipady=12, pady=(0, 5))
        
        # Buttons
        button_container = tk.Frame(main_container, bg='#f0f0f0')
        button_container.pack(fill=tk.X, pady=(10, 0))
        
        def on_ok():
            result[0] = password_var.get().strip()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # OK button
        ok_btn = tk.Button(button_container, text="Start Agent", 
                          command=on_ok,
                          font=('Segoe UI', 11, 'bold'),
                          fg='white', bg='#27ae60',
                          relief=tk.FLAT, bd=0,
                          padx=25, pady=10,
                          cursor='hand2')
        ok_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Cancel button
        cancel_btn = tk.Button(button_container, text="Cancel", 
                              command=on_cancel,
                              font=('Segoe UI', 10),
                              fg='#7f8c8d', bg='#ecf0f1',
                              relief=tk.FLAT, bd=0,
                              padx=20, pady=10,
                              cursor='hand2')
        cancel_btn.pack(side=tk.RIGHT)
        
        # Hover effects
        def on_enter(e):
            e.widget['bg'] = '#229954' if e.widget == ok_btn else '#d5dbdb'
        
        def on_leave(e):
            e.widget['bg'] = '#27ae60' if e.widget == ok_btn else '#ecf0f1'
        
        ok_btn.bind('<Enter>', on_enter)
        ok_btn.bind('<Leave>', on_leave)
        cancel_btn.bind('<Enter>', on_enter)
        cancel_btn.bind('<Leave>', on_leave)
        
        # Focus on password entry
        password_entry.focus()
        
        # Bind Enter key to OK
        dialog.bind('<Return>', lambda e: on_ok())
        dialog.bind('<Escape>', lambda e: on_cancel())
        
        # Wait for dialog to close
        dialog.wait_window()
        
        return result[0]
    
    def _perform_registration(self, email, password, price):
        """Perform the actual registration process"""
        
        # Start registration process
        def register():
            try:
                self.progress.start()
                self.log("Starting GPU registration...")
                
                # Check if agent executable exists
                if not self.agent_exe or not self.agent_exe.exists():
                    error_msg = f"labhya-agent.exe not found!\n\nSearched in:\n"
                    for path in self.possible_paths:
                        error_msg += f"  - {path}\n"
                    
                    # Try to get installation directory from registry
                    try:
                        import winreg
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\Labhya Compute") as key:
                            install_dir, _ = winreg.QueryValueEx(key, "Install_Dir")
                            error_msg += f"\nExpected installation directory: {install_dir}\n"
                    except:
                        error_msg += f"\nExpected installation directory: C:\\Program Files\\Labhya Compute\\\n"
                    
                    error_msg += "\nPlease ensure labhya-agent.exe is installed correctly."
                    self.log(f"Error: {error_msg}")
                    messagebox.showerror("Error", error_msg)
                    return
                
                # Run agent detect command
                cmd = [
                    str(self.agent_exe),
                    "detect",
                    "--api", "http://13.201.2.181/api",
                    "--username", email,
                    "--password", password,
                    "--price", str(price)
                ]
                
                self.log(f"Running: {' '.join(cmd[:3])} *** ***")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    self.log("Registration successful!")
                    self.log(result.stdout)
                    
                    # Update status
                    self.is_registered = True
                    self.current_user = email
                    self.update_ui()
                    
                    messagebox.showinfo("Success", "GPU registered successfully!\nYou can now start the agent.")
                else:
                    self.log("Registration failed!")
                    self.log(f"Error: {result.stderr}")
                    error_msg = result.stderr if result.stderr else "Unknown error occurred"
                    messagebox.showerror("Error", f"Registration failed:\n{error_msg}")
                
            except subprocess.TimeoutExpired:
                self.log("Registration timed out!")
                messagebox.showerror("Error", "Registration timed out. Please try again.")
            except FileNotFoundError:
                error_msg = f"labhya-agent.exe not found at: {self.agent_exe}\n\nPlease ensure the agent executable is in the correct location."
                self.log(f"Error: {error_msg}")
                messagebox.showerror("Error", error_msg)
            except Exception as e:
                self.log(f"Error during registration: {e}")
                messagebox.showerror("Error", f"Registration error: {e}")
            finally:
                self.progress.stop()
        
        threading.Thread(target=register, daemon=True).start()
    
    def start_agent(self):
        """Start the agent"""
        if not self.current_user:
            messagebox.showerror("Error", "Please register first!")
            return
        
        # Create a better password dialog
        password = self._get_password_dialog("Start Agent", "Enter your password to start the agent:")
        if not password:
            return
        
        def start():
            try:
                self.progress.start()
                self.log("Starting agent...")
                
                # Run agent run command
                cmd = [
                    str(self.agent_exe),
                    "run",
                    "--api", "http://13.201.2.181/api",
                    "--username", self.current_user,
                    "--password", password
                ]
                
                self.log(f"Running: {' '.join(cmd[:3])} ***")
                
                # Run agent in subprocess with real-time output
                self.agent_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=False,  # Don't decode as text initially
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW  # Hide console window
                )
                
                self.log("Agent started successfully!")
                self.log("Agent is now running and serving students...")
                self.log("Click 'Stop Agent' to stop the agent")
                
                # Update UI to show stop button and both logs and metrics
                self.start_btn.grid_remove()
                self.stop_btn.grid()
                self.metrics_frame.grid()  # show metrics
                self.start_metrics_stream()
                
                # Read output in real-time with proper encoding handling
                for line in iter(self.agent_process.stdout.readline, b''):
                    if line:
                        try:
                            # Try to decode as UTF-8 first
                            decoded_line = line.decode('utf-8', errors='replace').strip()
                            if decoded_line:
                                self.log(decoded_line)
                        except UnicodeDecodeError:
                            # If UTF-8 fails, try other encodings or skip
                            try:
                                decoded_line = line.decode('latin-1', errors='replace').strip()
                                if decoded_line and not decoded_line.startswith('#'):  # Skip binary data lines
                                    self.log(decoded_line)
                            except:
                                # Skip lines that can't be decoded
                                pass
                    else:
                        break
                
                # Process ended
                self.log("Agent process ended.")
                self.agent_process = None
                self.start_btn.grid()
                self.stop_btn.grid_remove()
                self.stop_metrics_stream()
                
            except Exception as e:
                self.log(f"Error starting agent: {e}")
                messagebox.showerror("Error", f"Failed to start agent: {e}")
                self.agent_process = None
                self.start_btn.grid()
                self.stop_btn.grid_remove()
                # Keep metrics visible even on error
                # self.stop_metrics_stream()
            finally:
                self.progress.stop()
        
        threading.Thread(target=start, daemon=True).start()
    
    def stop_agent(self):
        """Stop the running agent"""
        if self.agent_process:
            try:
                self.log("Stopping agent...")
                self.agent_process.terminate()
                self.agent_process.wait(timeout=5)
                self.log("Agent stopped successfully.")
            except subprocess.TimeoutExpired:
                self.log("Force killing agent...")
                self.agent_process.kill()
                self.log("Agent force killed.")
            except Exception as e:
                self.log(f"Error stopping agent: {e}")
            finally:
                self.agent_process = None
                self.start_btn.grid()
                self.stop_btn.grid_remove()
                self.stop_metrics_stream()
                # Keep log frame visible even when agent stops
    
    def run(self):
        """Start the GUI"""
        self.root.mainloop()

    # ---------------- GPU Metrics (local NVML) ----------------
    def start_metrics_stream(self):
        if self.metrics_thread and self.metrics_thread.is_alive():
            return
        self.metrics_stop_evt = threading.Event()
        self.metrics_thread = threading.Thread(target=self._metrics_loop, args=(self.metrics_stop_evt,), daemon=True)
        self.metrics_thread.start()

    def stop_metrics_stream(self):
        try:
            if self.metrics_stop_evt:
                self.metrics_stop_evt.set()
            self.metrics_stop_evt = None
        except Exception:
            pass
        try:
            if self.metrics_thread and self.metrics_thread.is_alive():
                self.metrics_thread.join(timeout=0.1)
        except Exception:
            pass
        self.metrics_thread = None
        # Don't hide metrics frame - keep it visible for reference
        # self.metrics_frame.grid_remove()

    def _metrics_loop(self, stop_evt: threading.Event):
        nvml_ok = False
        try:
            if pynvml is not None:
                pynvml.nvmlInit()
                nvml_ok = True
        except Exception as e:
            self.log(f"[metrics] NVML init failed: {e}")
            nvml_ok = False
        while not stop_evt.is_set():
            try:
                util = mem_used = mem_total = temp = power = fan = 0.0
                clk_g = clk_m = 0.0
                if nvml_ok:
                    try:
                        count = pynvml.nvmlDeviceGetCount()
                        if count > 0:
                            h = pynvml.nvmlDeviceGetHandleByIndex(0)
                            u = pynvml.nvmlDeviceGetUtilizationRates(h)
                            util = float(u.gpu)
                            m = pynvml.nvmlDeviceGetMemoryInfo(h)
                            mem_used = m.used / (1024*1024*1024)
                            mem_total = m.total / (1024*1024*1024)
                            temp = float(pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU))
                            try:
                                power = pynvml.nvmlDeviceGetPowerUsage(h) / 1000.0
                            except Exception:
                                power = 0.0
                            try:
                                fan = float(pynvml.nvmlDeviceGetFanSpeed(h))
                            except Exception:
                                fan = 0.0
                            try:
                                clk_g = float(pynvml.nvmlDeviceGetClockInfo(h, pynvml.NVML_CLOCK_GRAPHICS))
                                clk_m = float(pynvml.nvmlDeviceGetClockInfo(h, pynvml.NVML_CLOCK_MEM))
                            except Exception:
                                pass
                    except Exception as e:
                        self.log(f"[metrics] NVML read error: {e}")
                # update UI
                self.metrics_vars['util'].set(f"{util:.1f}%")
                if mem_total > 0:
                    self.metrics_vars['mem'].set(f"{mem_used:.2f}/{mem_total:.2f} GB ({(mem_used/mem_total)*100:.0f}%)")
                else:
                    self.metrics_vars['mem'].set("-")
                self.metrics_vars['temp'].set(f"{temp:.0f} °C")
                self.metrics_vars['power'].set(f"{power:.1f} W")
                self.metrics_vars['fan'].set(f"{fan:.0f}%")
                self.metrics_vars['clocks'].set(f"GFX {clk_g:.0f} MHz / MEM {clk_m:.0f} MHz")
            except Exception as e:
                self.log(f"[metrics] update error: {e}")
            finally:
                stop_evt.wait(2.0)
        try:
            if nvml_ok:
                pynvml.nvmlShutdown()
        except Exception:
            pass

def main():
    """Main entry point"""
    try:
        launcher = LabhyaLauncher()
        launcher.run()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start launcher: {e}")

if __name__ == "__main__":
    main() 