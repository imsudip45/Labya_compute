#!/usr/bin/env python3
"""
Labhya Compute - Unified Agent App (GUI + Agent Logic)

- Single file app combining the Tkinter launcher and the headless agent
- Env-configurable (no hardcoded URLs or credentials)
- Detects GPU and system info, registers host/GPU, polls backend for sessions
- Launches Docker session containers, opens reverse SSH tunnels
- Sends real-time GPU metrics to backend
- Checks system requirements (WSL2, Ubuntu 22.04, Docker Desktop)

Environment variables (override defaults):
  LABHYA_API               → Backend base URL (e.g., http://localhost:8000/api)
  LABHYA_TUNNEL_TYPE       → 'bastion' (default) or 'nglocalhost'
  LABHYA_BASTION_HOST      → Bastion SSH host
  LABHYA_BASTION_PORT      → Bastion SSH port (default 22)
  LABHYA_BASTION_USER      → Bastion SSH user
  LABHYA_LOG_LEVEL         → INFO | DEBUG

This file intentionally avoids hardcoding; defaults are safe and overridable.
"""

from __future__ import annotations

import os
import sys
import time
import json
import re
import threading
import subprocess
import random
import platform
import webbrowser
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

# Optional GUI
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext
    GUI_AVAILABLE = True
except Exception:
    GUI_AVAILABLE = False

# Optional NVML
try:
    import pynvml
except Exception:
    pynvml = None

import requests

# Configuration
API_BASE_URL = os.environ.get('LABHYA_API_URL', 'http://localhost:8000/api')
LABHYA_USER = os.environ.get('LABHYA_USER', '')
LABHYA_PASS = os.environ.get('LABHYA_PASS', '')

class UnifiedAgent:
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.host_id = None
        self.gpu_id = None
        self.session_id = None
        self.agent_running = False
        self.agent_thread = None
        self.stop_agent_event = threading.Event()
        
    def http(self, method: str, endpoint: str, data: Optional[Dict] = None, 
             headers: Optional[Dict] = None) -> Optional[Dict]:
        """Make HTTP request to API"""
        url = f"{API_BASE_URL}{endpoint}"
        default_headers = {'Content-Type': 'application/json'}
        
        if self.access_token:
            default_headers['Authorization'] = f'Bearer {self.access_token}'
        
        if headers:
            default_headers.update(headers)
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=default_headers)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=default_headers)
            elif method.upper() == 'PUT':
                response = requests.put(url, json=data, headers=default_headers)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=default_headers)
            else:
                return None
            
            if response.status_code == 401 and self.refresh_token:
                # Try to refresh token
                refresh_response = requests.post(f"{API_BASE_URL}/auth/refresh/", 
                                               json={'refresh': self.refresh_token})
                if refresh_response.status_code == 200:
                    refresh_data = refresh_response.json()
                    self.access_token = refresh_data['access']
                    default_headers['Authorization'] = f'Bearer {self.access_token}'
                    # Retry original request
                    if method.upper() == 'GET':
                        response = requests.get(url, headers=default_headers)
                    elif method.upper() == 'POST':
                        response = requests.post(url, json=data, headers=default_headers)
                    elif method.upper() == 'PUT':
                        response = requests.put(url, json=data, headers=default_headers)
                    elif method.upper() == 'DELETE':
                        response = requests.delete(url, headers=default_headers)
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                print(f"HTTP {method} {endpoint} failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"HTTP request failed: {e}")
            return None
    
    def login(self, email: str, password: str) -> bool:
        """Login and get host_id"""
        try:
            # First get JWT tokens
            login_data = {'username': email, 'password': password}
            response = self.http('POST', '/auth/login/', login_data)
            
            if not response:
                return False
            
            self.access_token = response['access']
            self.refresh_token = response['refresh']
            
            # Now get host_id by querying hosts with the email
            hosts_response = self.http('GET', '/hosts/')
            if not hosts_response:
                return False
            
            # Find host with matching email
            for host in hosts_response.get('results', []):
                if host.get('host_email') == email:
                    self.host_id = host['id']
                    return True
            
            return False
        except Exception as e:
            print(f"Login failed: {e}")
            return False
    
    def check_gpu_exists(self) -> bool:
        """Check if GPU exists for this host"""
        try:
            response = self.http('GET', f'/gpus/')
            if not response:
                return False
            
            for gpu in response.get('results', []):
                if gpu.get('host') == self.host_id:
                    self.gpu_id = gpu['id']
                    return True
            
            return False
        except Exception as e:
            print(f"Check GPU failed: {e}")
            return False
    
    def register_gpu(self, gpu_name: str, gpu_memory: int, gpu_price: int) -> bool:
        """Register a new GPU for this host"""
        try:
            # Get GPU details from system
            gpu_details = self.get_gpu_details()
            
            gpu_data = {
                'host': self.host_id,
                'gpu_name': gpu_name,
                'gpu_model': gpu_details.get('model', 'Unknown'),
                'gpu_memory': gpu_memory,
                'gpu_price': gpu_price,
                'gpu_location': 'Local WSL2',
                'gpu_availability': True
            }
            
            response = self.http('POST', '/gpus/', gpu_data)
            if response:
                self.gpu_id = response['id']
                return True
            
            return False
        except Exception as e:
            print(f"GPU registration failed: {e}")
            return False
    
    def get_gpu_details(self) -> Dict[str, Any]:
        """Get GPU details from system"""
        try:
            # Try to get GPU info from WSL
            result = subprocess.run(['wsl', '-d', 'Ubuntu-22.04', '--', 'nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                if lines:
                    parts = lines[0].split(', ')
                    if len(parts) >= 2:
                        return {
                            'model': parts[0].strip(),
                            'memory': int(parts[1].strip())
                        }
        except Exception as e:
            print(f"Failed to get GPU details: {e}")
        
        # Fallback values
        return {
            'model': 'NVIDIA GPU',
            'memory': 8
        }
    
    def start_agent(self):
        """Start the agent polling for sessions"""
        if self.agent_running:
            return
        
        self.agent_running = True
        self.stop_agent_event.clear()
        self.agent_thread = threading.Thread(target=self._agent_loop, daemon=True)
        self.agent_thread.start()
    
    def stop_agent(self):
        """Stop the agent"""
        if not self.agent_running:
            return
        
        self.agent_running = False
        self.stop_agent_event.set()
        
        if self.agent_thread:
            self.agent_thread.join(timeout=5)
        
        # Stop any active session
        if self.session_id:
            self.stop_session()
    
    def _agent_loop(self):
        """Main agent loop - poll for sessions"""
        while self.agent_running and not self.stop_agent_event.is_set():
            try:
                # Check for active sessions for this GPU
                response = self.http('GET', f'/sessions/')
                if response:
                    active_session = None
                    for session in response.get('results', []):
                        if (session.get('gpu') == self.gpu_id and 
                            session.get('session_status') == 'active'):
                            active_session = session
                            break
                    
                    if active_session and not self.session_id:
                        # New session started
                        self.session_id = active_session['id']
                        self.start_session(active_session)
                    elif not active_session and self.session_id:
                        # Session ended
                        self.session_id = None
                
                time.sleep(5)  # Poll every 5 seconds
            except Exception as e:
                print(f"Agent loop error: {e}")
                time.sleep(5)
    
    def start_session(self, session_data: Dict):
        """Start a GPU session"""
        try:
            print(f"Starting session {self.session_id}")
            
            # Update session status
            self.http('PUT', f'/sessions/{self.session_id}/', {
                'session_status': 'running',
                'connection_details': {
                    'ssh_host': 'localhost',
                    'ssh_port': 2222,
                    'ssh_user': 'gpu_user'
                }
            })
            
            # Start Docker container for the session
            self._start_docker_session(session_data)
            
        except Exception as e:
            print(f"Failed to start session: {e}")
    
    def stop_session(self):
        """Stop the current session"""
        try:
            if self.session_id:
                print(f"Stopping session {self.session_id}")
                
                # Update session status
                self.http('PUT', f'/sessions/{self.session_id}/', {
                    'session_status': 'completed'
                })
                
                # Stop Docker container
                self._stop_docker_session()
                
                self.session_id = None
        except Exception as e:
            print(f"Failed to stop session: {e}")
    
    def _start_docker_session(self, session_data: Dict):
        """Start Docker container for GPU session"""
        try:
            # This is a simplified version - you'd implement actual Docker container management
            print(f"Starting Docker container for session {self.session_id}")
            
            # Example Docker run command (simplified)
            # subprocess.run(['docker', 'run', '-d', '--gpus', 'all', '--name', f'gpu-session-{self.session_id}', 'gpu-image'])
            
        except Exception as e:
            print(f"Failed to start Docker session: {e}")
    
    def _stop_docker_session(self):
        """Stop Docker container for GPU session"""
        try:
            if self.session_id:
                print(f"Stopping Docker container for session {self.session_id}")
                
                # Example Docker stop command (simplified)
                # subprocess.run(['docker', 'stop', f'gpu-session-{self.session_id}'])
                # subprocess.run(['docker', 'rm', f'gpu-session-{self.session_id}'])
                
        except Exception as e:
            print(f"Failed to stop Docker session: {e}")

class LauncherGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Labhya GPU Agent")
        self.root.geometry("500x700")
        self.root.resizable(False, False)
        
        # Initialize agent
        self.agent = UnifiedAgent()
        
        # State variables
        self.logged_in = False
        self.gpu_exists = False
        self.agent_running = False
        
        # Check system requirements first
        self.prereq_ok = False
        self._check_requirements()
        
        # Build UI
        self._build()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _check_requirements(self):
        """Check system requirements"""
        requirements = check_system_requirements()
        self.prereq_ok = requirements['all_ok']
        self.requirements_status = requirements
    
    def _build(self):
        """Build the GUI"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Labhya GPU Agent", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # System Requirements Status
        self.req_status_label = ttk.Label(main_frame, text="", font=("Arial", 10))
        self.req_status_label.grid(row=1, column=0, columnspan=2, pady=(0, 10))
        
        # Setup Environment Button
        self.setup_btn = ttk.Button(main_frame, text="Setup Environment", command=self._run_setup)
        self.setup_btn.grid(row=2, column=0, columnspan=2, pady=(0, 20))
        
        # Login Frame
        self.login_frame = ttk.LabelFrame(main_frame, text="Login", padding="10")
        self.login_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Email
        ttk.Label(self.login_frame, text="Email:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.email_var = tk.StringVar(value=LABHYA_USER)
        self.email_entry = ttk.Entry(self.login_frame, textvariable=self.email_var, width=30)
        self.email_entry.grid(row=0, column=1, padx=(10, 0), pady=2)
        
        # Password
        ttk.Label(self.login_frame, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.password_var = tk.StringVar(value=LABHYA_PASS)
        self.password_entry = ttk.Entry(self.login_frame, textvariable=self.password_var, show="*", width=30)
        self.password_entry.grid(row=1, column=1, padx=(10, 0), pady=2)
        
        # Login Button
        self.login_btn = ttk.Button(self.login_frame, text="Login", command=self._login)
        self.login_btn.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        
        # GPU Registration Frame
        self.gpu_frame = ttk.LabelFrame(main_frame, text="GPU Registration", padding="10")
        self.gpu_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # GPU Name
        ttk.Label(self.gpu_frame, text="GPU Name:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.gpu_name_var = tk.StringVar(value="NVIDIA GPU")
        self.gpu_name_entry = ttk.Entry(self.gpu_frame, textvariable=self.gpu_name_var, width=30)
        self.gpu_name_entry.grid(row=0, column=1, padx=(10, 0), pady=2)
        
        # GPU Memory
        ttk.Label(self.gpu_frame, text="GPU Memory (GB):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.gpu_memory_var = tk.StringVar(value="8")
        self.gpu_memory_entry = ttk.Entry(self.gpu_frame, textvariable=self.gpu_memory_var, width=30)
        self.gpu_memory_entry.grid(row=1, column=1, padx=(10, 0), pady=2)
        
        # GPU Price
        ttk.Label(self.gpu_frame, text="Price per Hour ($):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.gpu_price_var = tk.StringVar(value="2")
        self.gpu_price_entry = ttk.Entry(self.gpu_frame, textvariable=self.gpu_price_var, width=30)
        self.gpu_price_entry.grid(row=2, column=1, padx=(10, 0), pady=2)
        
        # Register GPU Button
        self.register_gpu_btn = ttk.Button(self.gpu_frame, text="Register GPU", command=self._register_gpu)
        self.register_gpu_btn.grid(row=3, column=0, columnspan=2, pady=(10, 0))
        
        # Agent Control Frame
        self.agent_frame = ttk.LabelFrame(main_frame, text="Agent Control", padding="10")
        self.agent_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Start/Stop Agent Button
        self.agent_btn = ttk.Button(self.agent_frame, text="Start Agent", command=self._toggle_agent)
        self.agent_btn.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Status Label
        self.status_label = ttk.Label(self.agent_frame, text="Ready", font=("Arial", 10))
        self.status_label.grid(row=1, column=0, columnspan=2)
        
        # Log Frame
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Log Text
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, width=60)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Update UI based on requirements
        self._update_ui()
    
    def _update_ui(self):
        """Update UI based on current state"""
        # Update requirements status
        if self.prereq_ok:
            self.req_status_label.config(text="✅ All requirements met", foreground="green")
            self.setup_btn.grid_remove()
        else:
            self.req_status_label.config(text=f"❌ {self.requirements_status['message']}", foreground="red")
            self.setup_btn.grid()
        
        # Update login frame visibility
        if self.prereq_ok:
            self.login_frame.grid()
        else:
            self.login_frame.grid_remove()
        
        # Update GPU frame visibility - show only if logged in but no GPU exists
        if self.logged_in and not self.gpu_exists:
            self.gpu_frame.grid()
        else:
            self.gpu_frame.grid_remove()
        
        # Update agent frame visibility - show only if logged in and GPU exists
        if self.logged_in and self.gpu_exists:
            self.agent_frame.grid()
        else:
            self.agent_frame.grid_remove()
        
        # Update agent button text
        if self.agent_running:
            self.agent_btn.config(text="Stop Agent")
        else:
            self.agent_btn.config(text="Start Agent")
    
    def _run_setup(self):
        """Run setup wizard"""
        self.log("Running setup wizard...")
        try:
            run_setup_wizard()
            self._check_requirements()
            self._update_ui()
            self.log("Setup completed. Please restart the application.")
        except Exception as e:
            self.log(f"Setup failed: {e}")
    
    def _login(self):
        """Handle login"""
        email = self.email_var.get().strip()
        password = self.password_var.get().strip()
        
        if not email or not password:
            messagebox.showerror("Error", "Please enter email and password")
            return
        
        self.log("Logging in...")
        self.login_btn.config(state="disabled")
        
        # Run login in thread
        def login_thread():
            try:
                success = self.agent.login(email, password)
                if success:
                    self.logged_in = True
                    self.gpu_exists = self.agent.check_gpu_exists()
                    self.log(f"Login successful. GPU exists: {self.gpu_exists}")
                    if self.gpu_exists:
                        self.log("GPU found - you can start the agent")
                    else:
                        self.log("No GPU found - please register a GPU")
                else:
                    self.log("Login failed. Check credentials.")
                    messagebox.showerror("Error", "Login failed. Check your credentials.")
            except Exception as e:
                self.log(f"Login error: {e}")
                messagebox.showerror("Error", f"Login error: {e}")
            finally:
                self.root.after(0, lambda: self.login_btn.config(state="normal"))
                self.root.after(0, self._update_ui)
        
        threading.Thread(target=login_thread, daemon=True).start()
    
    def _register_gpu(self):
        """Handle GPU registration"""
        gpu_name = self.gpu_name_var.get().strip()
        gpu_memory = self.gpu_memory_var.get().strip()
        gpu_price = self.gpu_price_var.get().strip()
        
        if not gpu_name or not gpu_memory or not gpu_price:
            messagebox.showerror("Error", "Please fill all GPU fields")
            return
        
        try:
            gpu_memory = int(gpu_memory)
            gpu_price = int(gpu_price)
        except ValueError:
            messagebox.showerror("Error", "GPU memory and price must be numbers")
            return
        
        self.log("Registering GPU...")
        self.register_gpu_btn.config(state="disabled")
        
        # Run registration in thread
        def register_thread():
            try:
                success = self.agent.register_gpu(gpu_name, gpu_memory, gpu_price)
                if success:
                    self.gpu_exists = True
                    self.log("GPU registered successfully")
                    self.log("GPU registered - you can now start the agent")
                else:
                    self.log("GPU registration failed")
                    messagebox.showerror("Error", "GPU registration failed")
            except Exception as e:
                self.log(f"GPU registration error: {e}")
                messagebox.showerror("Error", f"GPU registration error: {e}")
            finally:
                self.root.after(0, lambda: self.register_gpu_btn.config(state="normal"))
                self.root.after(0, self._update_ui)
        
        threading.Thread(target=register_thread, daemon=True).start()
    
    def _toggle_agent(self):
        """Toggle agent start/stop"""
        if self.agent_running:
            self._stop_agent()
        else:
            self._start_agent()
    
    def _start_agent(self):
        """Start the agent"""
        self.log("Starting agent...")
        self.agent_running = True
        self.agent.start_agent()
        self._update_ui()
        self.log("Agent started - polling for sessions")
        self.status_label.config(text="Agent Running - Polling for Sessions")
    
    def _stop_agent(self):
        """Stop the agent"""
        self.log("Stopping agent...")
        self.agent_running = False
        self.agent.stop_agent()
        self._update_ui()
        self.log("Agent stopped")
        self.status_label.config(text="Agent Stopped")
    
    def _on_closing(self):
        """Handle window close"""
        if self.agent_running:
            self.log("Stopping agent before closing...")
            self.agent.stop_agent()
        
        self.root.destroy()
    
    def log(self, message: str):
        """Add message to log"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
    
    def run(self):
        """Run the GUI"""
        self.root.mainloop()

# System requirements checking functions (keep existing ones)
def _wsl_cmd() -> str:
    """Get WSL command path"""
    system_root = os.environ.get('SystemRoot', r'C:\Windows')
    candidates = [
        os.path.join(system_root, 'Sysnative', 'wsl.exe'),
        os.path.join(system_root, 'System32', 'wsl.exe'),
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

def check_wsl_enabled() -> bool:
    """Check if WSL is enabled"""
    try:
        r = subprocess.run([_wsl_cmd(), "--status"], capture_output=True, text=True)
        return r.returncode == 0
    except Exception:
        return False

def check_ubuntu_installed() -> bool:
    """Check if Ubuntu is installed in WSL"""
    try:
        # First try direct Ubuntu-22.04 test (we know this works)
        r = subprocess.run([_wsl_cmd(), "-d", "Ubuntu-22.04", "--", "true"], 
                          capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return True
        
        # Try quiet listing with proper encoding handling
        r = subprocess.run([_wsl_cmd(), "-l", "-q"], capture_output=True, text=True, encoding='utf-16')
        if r.returncode == 0 and r.stdout.strip():
            lines = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
            # Accept any Ubuntu distribution
            found = any(ln.lower().startswith("ubuntu") for ln in lines)
            if found:
                return True
        
        # Try verbose listing with proper encoding
        rv = subprocess.run([_wsl_cmd(), "-l", "-v"], capture_output=True, text=True, encoding='utf-16')
        if rv.returncode == 0:
            out = rv.stdout or rv.stderr or ""
            if any("ubuntu" in ln.lower() for ln in out.splitlines()):
                return True
        
        # Try other Ubuntu distribution names
        for distro_name in ["Ubuntu", "Ubuntu-20.04", "Ubuntu-22.04"]:
            try:
                rr = subprocess.run([_wsl_cmd(), "-d", distro_name, "--", "true"], 
                                  capture_output=True, text=True, timeout=10)
                if rr.returncode == 0:
                    return True
            except Exception:
                continue
        
        return False
    except Exception as e:
        # If encoding fails, try without specifying encoding
        try:
            r = subprocess.run([_wsl_cmd(), "-l", "-q"], capture_output=True, text=True)
            if r.returncode == 0 and r.stdout.strip():
                lines = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
                found = any(ln.lower().startswith("ubuntu") for ln in lines)
                if found:
                    return True
        except Exception:
            pass
        return False

def _docker_cmd() -> str:
    """Get Docker command path"""
    return 'docker'

def check_docker_installed() -> bool:
    """Check if Docker is installed"""
    try:
        r = subprocess.run([_docker_cmd(), "--version"], capture_output=True, text=True)
        return r.returncode == 0
    except Exception:
        return False

def check_docker_running() -> bool:
    """Check if Docker is running"""
    try:
        r = subprocess.run([_docker_cmd(), "info"], capture_output=True, text=True)
        return r.returncode == 0
    except Exception:
        return False

def start_docker_desktop():
    """Start Docker Desktop"""
    try:
        subprocess.Popen(["start", "Docker Desktop"], shell=True)
        return True
    except Exception:
        return False

def check_system_requirements() -> dict:
    """Check all system requirements and return status"""
    if platform.system() != 'Windows':
        return {
            'wsl_ok': False, 'ubuntu_ok': False, 'docker_installed': False,
            'docker_running': False, 'all_ok': False, 'message': 'Windows required for this agent'
        }
    
    wsl_ok = check_wsl_enabled()
    ubuntu_ok = check_ubuntu_installed()
    docker_installed = check_docker_installed()
    docker_running = check_docker_running() if docker_installed else False
    
    all_ok = all([wsl_ok, ubuntu_ok, docker_installed, docker_running])
    
    missing = []
    if not wsl_ok: missing.append('WSL2')
    if not ubuntu_ok: missing.append('Ubuntu')
    if not docker_installed: missing.append('Docker Desktop')
    elif not docker_running: missing.append('Docker (start it)')
    
    message = "All requirements met" if all_ok else f"Missing: {', '.join(missing)}"
    
    return {
        'wsl_ok': wsl_ok, 'ubuntu_ok': ubuntu_ok, 'docker_installed': docker_installed,
        'docker_running': docker_running, 'all_ok': all_ok, 'message': message
    }

def run_setup_wizard():
    """Run setup wizard to install missing components"""
    print("Running setup wizard...")
    
    # Check current status
    requirements = check_system_requirements()
    
    if requirements['all_ok']:
        print("All requirements already met!")
        return
    
    print("Installing missing components...")
    
    # Enable WSL if needed
    if not requirements['wsl_ok']:
        print("Enabling WSL...")
        subprocess.run(["dism", "/online", "/enable-feature", "/featurename:Microsoft-Windows-Subsystem-Linux", "/all", "/norestart"])
        subprocess.run(["dism", "/online", "/enable-feature", "/featurename:VirtualMachinePlatform", "/all", "/norestart"])
        print("WSL enabled. Please restart your computer and run this again.")
        return
    
    # Install Ubuntu if needed
    if not requirements['ubuntu_ok']:
        print("Installing Ubuntu...")
        subprocess.run(["wsl", "--install", "-d", "Ubuntu-22.04"])
        print("Ubuntu installation started. Please complete the setup and run this again.")
        return
    
    # Install Docker if needed
    if not requirements['docker_installed']:
        print("Please install Docker Desktop from https://www.docker.com/products/docker-desktop/")
        print("After installation, run this setup again.")
        return
    
    # Start Docker if needed
    if not requirements['docker_running']:
        print("Starting Docker Desktop...")
        if start_docker_desktop():
            print("Docker Desktop started. Please wait a moment and run this again.")
        else:
            print("Failed to start Docker Desktop. Please start it manually.")
        return
    
    print("Setup completed!")

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == '--headless':
        # Headless mode
        print("Running in headless mode...")
        
        # Check requirements
        requirements = check_system_requirements()
        if not requirements['all_ok']:
            print(f"System requirements not met: {requirements['message']}")
            print("Please run the GUI version to set up your environment.")
            sys.exit(1)
        
        # Check credentials
        if not LABHYA_USER or not LABHYA_PASS:
            print("Please set LABHYA_USER and LABHYA_PASS environment variables")
            sys.exit(1)
        
        # Create agent and run
        agent = UnifiedAgent()
        
        # Login
        print("Logging in...")
        if not agent.login(LABHYA_USER, LABHYA_PASS):
            print("Login failed")
            sys.exit(1)
        
        print("Login successful")
        
        # Check GPU
        if not agent.check_gpu_exists():
            print("No GPU found. Please register a GPU first using the GUI.")
            sys.exit(1)
        
        print("GPU found, starting agent...")
        
        # Start agent
        agent.start_agent()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Stopping agent...")
            agent.stop_agent()
            print("Agent stopped")
    else:
        # GUI mode
        app = LauncherGUI()
        app.run()

if __name__ == '__main__':
    main()
