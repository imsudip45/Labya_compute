#!/usr/bin/env python3
"""
Labhya Compute Agent - Tkinter GUI Version
Combines agent launcher and agent functionality in a modern GUI
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import threading
import time
import json
import os
import sys
import subprocess
import platform
import requests
import webbrowser
from datetime import datetime
import queue
import uuid

        # Import agent functionality
try:
    from agent import (
        http, fetch_tokens, refresh_access, detect_gpu_info, detect_system_info,
        ensure_dockerfiles, build_session_image, launch_container, start_relay_tunnel,
        generate_password, get_available_templates
    )
except ImportError:
    # Agent helper module not available; provide built-in implementations
    def http(*args, **kwargs):
        raise NotImplementedError("HTTP helper not wired here")
    def fetch_tokens(*args, **kwargs):
        raise NotImplementedError("Token helper not wired here")
    def refresh_access(*args, **kwargs):
        raise NotImplementedError("Refresh helper not wired here")
    def detect_gpu_info(*args, **kwargs):
        """Best-effort GPU detection on Windows/WSL without the external agent module.
        Tries nvidia-smi, then PowerShell/WMI fallbacks.
        """
        import shutil
        import re
        from math import floor

        # Helper to safely run a command
        def run_cmd(cmd, timeout=8):
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                if r.returncode == 0:
                    return r.stdout.strip()
            except Exception:
                pass
            return ""

        # Attempt 1: nvidia-smi on Windows host
        if shutil.which('nvidia-smi'):
            out = run_cmd(['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader'])
            if out:
                # Take first GPU line
                first = out.splitlines()[0]
                parts = [p.strip() for p in first.split(',')]
                if len(parts) >= 3:
                    name, mem_str, drv = parts[0], parts[1], parts[2]
                    m = re.search(r"(\d+)\s*MiB", mem_str, re.IGNORECASE)
                    vram_gb = 0
                    if m:
                        vram_mb = int(m.group(1))
                        vram_gb = max(1, floor(vram_mb / 1024))
                    return {"name": name, "vram_gb": vram_gb, "cuda_cores": 0, "driver_version": drv}

        # Attempt 2: PowerShell CIM query for video controller
        ps_cmd = [
            'powershell', '-NoProfile', '-Command',
            "Get-CimInstance Win32_VideoController | Select-Object -First 1 Name,AdapterRAM,DriverVersion | ConvertTo-Json -Compress"
        ]
        out = run_cmd(ps_cmd)
        if out:
            try:
                data = json.loads(out)
                name = data.get('Name') or 'Unknown GPU'
                drv = data.get('DriverVersion') or 'Unknown'
                ram = int(data.get('AdapterRAM') or 0)
                vram_gb = max(0, floor(ram / (1024**3)))
                return {"name": name, "vram_gb": vram_gb, "cuda_cores": 0, "driver_version": drv}
            except Exception:
                pass

        # Attempt 3: WMIC fallback (older systems)
        out = run_cmd(['wmic', 'path', 'win32_VideoController', 'get', 'Name,AdapterRAM,DriverVersion', '/value'])
        if out:
            try:
                name = 'Unknown GPU'
                drv = 'Unknown'
                ram = 0
                for line in out.splitlines():
                    if line.startswith('Name='):
                        name = line.split('=',1)[1].strip()
                    elif line.startswith('AdapterRAM='):
                        try:
                            ram = int(line.split('=',1)[1].strip())
                        except Exception:
                            pass
                    elif line.startswith('DriverVersion='):
                        drv = line.split('=',1)[1].strip()
                from math import floor
                vram_gb = max(0, floor(ram / (1024**3)))
                return {"name": name, "vram_gb": vram_gb, "cuda_cores": 0, "driver_version": drv}
            except Exception:
                pass

        # Last resort
        return {"name": "Unknown GPU", "vram_gb": 0, "cuda_cores": 0, "driver_version": "Unknown"}

    def detect_system_info(*args, **kwargs):
        try:
            import socket
            return {"os": platform.platform(), "hostname": socket.gethostname()}
        except Exception:
            return {"os": sys.platform, "hostname": "Unknown"}
    def ensure_dockerfiles() -> str:
        """Create a minimal Dockerfile for an SSH-enabled Ubuntu image and return its directory."""
        base_dir = os.path.join(os.path.dirname(__file__), 'docker', 'session')
        os.makedirs(base_dir, exist_ok=True)
        dockerfile = os.path.join(base_dir, 'Dockerfile')
        content = r"""
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y openssh-server sudo python3 \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/run/sshd
# Create user
RUN useradd -m -s /bin/bash labuser && echo 'labuser:changeme' | chpasswd && adduser labuser sudo
# Enable password auth
RUN sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
EXPOSE 22
CMD ["/usr/sbin/sshd","-D"]
""".strip()
        try:
            with open(dockerfile, 'w', encoding='utf-8') as f:
                f.write(content + "\n")
        except Exception:
            pass
        return base_dir

    def build_session_image(session_tag: str, image_template: str = 'default') -> str:
        """Build (or reuse) the session image and return the image tag."""
        workdir = ensure_dockerfiles()
        image_tag = 'labhya/session:latest'
        try:
            subprocess.run(["docker", "image", "inspect", image_tag], capture_output=True, text=True, timeout=20)
            # If inspect fails, build will run anyway
            subprocess.run(["docker", "build", "-t", image_tag, workdir], check=True)
        except subprocess.CalledProcessError:
            subprocess.run(["docker", "build", "-t", image_tag, workdir], check=False)
        except Exception:
            pass
        return image_tag

    def _choose_free_port(start: int = 20000, end: int = 30000) -> int:
        import socket
        for port in range(start, end):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except Exception:
                    continue
        # Fallback
        return 22222

    def launch_container(image_tag: str, host_port: int, password: str, session_id: str):
        """Run the SSH container mapping host_port:22, set labuser password, return (cid, host_port)."""
        try:
            # If host_port not specified, choose one
            if not host_port:
                host_port = _choose_free_port()
            name = f"sess-{session_id[:8]}"
            # Remove container with same name if exists to prevent conflicts
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, text=True)
            # Run container
            run = subprocess.run([
                "docker", "run", "-d", "-p", f"{host_port}:22", "--name", name, image_tag
            ], capture_output=True, text=True)
            cid = (run.stdout or "").strip()
            if run.returncode != 0 or not cid:
                raise RuntimeError(f"docker run failed: {run.stderr}")
            # Set password for labuser
            subprocess.run(["docker", "exec", cid, "bash", "-lc", f"echo 'labuser:{password}' | chpasswd"],
                           capture_output=True, text=True)
            return cid, host_port
        except Exception as e:
            raise RuntimeError(f"launch_container error: {e}")

    def start_relay_tunnel(host_port: int, relay_host: str, relay_port: int, ssh_username: str, password: str):
        """Start reverse SSH tunnel: relay_port -> host_port (container's 22). Returns Popen or None.
        Requires OpenSSH client available on PATH. Auth strategy may vary in real deployment.
        """
        try:
            # Note: This assumes keyless or agent-based auth on relay for demo/testing purposes.
            cmd = [
                "ssh", "-N", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
                "-R", f"{relay_port}:127.0.0.1:{host_port}", f"{ssh_username}@{relay_host}"
            ]
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return proc
        except Exception:
            return None
    def generate_password(*args, **kwargs):
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(12))
    def get_available_templates(*args, **kwargs):
        return {}

class AgentGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Labhya Compute Agent")
        self.root.geometry("1000x700")
        self.root.configure(bg='#f0f0f0')
        
        # Configuration
        self.api_base = "http://localhost:8000/api"
        self.token = None
        self.refresh_token = None
        self.host_id = None
        self.active_sessions = {}
        self.metrics_threads = {}
        self.log_queue = queue.Queue()
        self.is_agent_running = False
        self.prereq_ok = False
        
        # Create GUI
        self._create_widgets()
        self._setup_logging()
        
        # Check prerequisites
        self._check_prerequisites()
        
        # Start log consumer
        self._consume_logs()
    
    def _create_widgets(self):
        """Create the main GUI widgets"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Labhya Compute Agent", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="System Status", padding="10")
        status_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Status indicators
        self.wsl_status = ttk.Label(status_frame, text="WSL2: Checking...", foreground="orange")
        self.wsl_status.grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        
        self.ubuntu_status = ttk.Label(status_frame, text="Ubuntu: Checking...", foreground="orange")
        self.ubuntu_status.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        self.docker_status = ttk.Label(status_frame, text="Docker: Checking...", foreground="orange")
        self.docker_status.grid(row=0, column=2, sticky=tk.W, padx=(0, 20))
        
        # Refresh button
        self.refresh_prereq_button = ttk.Button(status_frame, text="Refresh", command=self._refresh_prerequisites)
        self.refresh_prereq_button.grid(row=0, column=3, sticky=tk.W)
        
        # Login frame
        login_frame = ttk.LabelFrame(main_frame, text="Authentication", padding="10")
        login_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Login fields
        ttk.Label(login_frame, text="Email:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.email_var = tk.StringVar()
        self.email_entry = ttk.Entry(login_frame, textvariable=self.email_var, width=30)
        self.email_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        
        ttk.Label(login_frame, text="Password:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(login_frame, textvariable=self.password_var, 
                                       show="*", width=20)
        self.password_entry.grid(row=0, column=3, sticky=tk.W, padx=(0, 10))
        
        self.login_button = ttk.Button(login_frame, text="Login", command=self._login)
        self.login_button.grid(row=0, column=4, padx=(0, 10))
        
        self.logout_button = ttk.Button(login_frame, text="Logout", command=self._logout, 
                                       state="disabled")
        self.logout_button.grid(row=0, column=5)
        
        # Main content area
        content_frame = ttk.Frame(main_frame)
        content_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # Left panel - GPU Management
        gpu_frame = ttk.LabelFrame(content_frame, text="GPU Management", padding="10")
        gpu_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        gpu_frame.columnconfigure(0, weight=1)
        gpu_frame.rowconfigure(1, weight=1)
        
        # GPU info
        self.gpu_info_text = scrolledtext.ScrolledText(gpu_frame, height=8, width=40)
        self.gpu_info_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # GPU actions
        gpu_actions_frame = ttk.Frame(gpu_frame)
        gpu_actions_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        self.detect_gpu_button = ttk.Button(gpu_actions_frame, text="Detect GPU", 
                                           command=self._detect_gpu, state="disabled")
        self.detect_gpu_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.register_gpu_button = ttk.Button(gpu_actions_frame, text="Register GPU", 
                                             command=self._register_gpu, state="disabled")
        self.register_gpu_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Right panel - Session Management
        session_frame = ttk.LabelFrame(content_frame, text="Session Management", padding="10")
        session_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        session_frame.columnconfigure(0, weight=1)
        # Make the tree (row 0) expand, keep action buttons visible without fullscreen
        session_frame.rowconfigure(0, weight=1)
        
        # Session list
        self.session_tree = ttk.Treeview(session_frame, columns=("Status", "GPU", "Renter"), 
                                        show="tree headings", height=8)
        self.session_tree.heading("#0", text="Session ID")
        self.session_tree.heading("Status", text="Status")
        self.session_tree.heading("GPU", text="GPU")
        self.session_tree.heading("Renter", text="Renter")
        self.session_tree.column("#0", width=150)
        self.session_tree.column("Status", width=80)
        self.session_tree.column("GPU", width=100)
        self.session_tree.column("Renter", width=100)
        self.session_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Session actions
        session_actions_frame = ttk.Frame(session_frame)
        session_actions_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        self.start_agent_button = ttk.Button(session_actions_frame, text="Start Agent", 
                                            command=self._start_agent, state="disabled")
        self.start_agent_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_agent_button = ttk.Button(session_actions_frame, text="Stop Agent", 
                                           command=self._stop_agent, state="disabled")
        self.stop_agent_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Bottom panel - Logs
        log_frame = ttk.LabelFrame(main_frame, text="Agent Logs", padding="10")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, width=100)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Log controls
        log_controls_frame = ttk.Frame(log_frame)
        log_controls_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        self.clear_log_button = ttk.Button(log_controls_frame, text="Clear Logs", 
                                          command=self._clear_logs)
        self.clear_log_button.pack(side=tk.LEFT)
        
        # Progress bar
        self.progress_var = tk.StringVar(value="Ready")
        self.progress_label = ttk.Label(main_frame, textvariable=self.progress_var)
        self.progress_label.grid(row=5, column=0, columnspan=3, pady=(10, 0))
    
    def _setup_logging(self):
        """Setup logging to GUI"""
        def log_to_gui(message):
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_message = f"[{timestamp}] {message}\n"
            self.log_queue.put(log_message)
        
        # Store original print function
        self.original_print = print
        
        # Override print to log to GUI
        def gui_print(*args, **kwargs):
            message = " ".join(str(arg) for arg in args)
            log_to_gui(message)
        
        # Replace print function
        import builtins
        builtins.print = gui_print
    
    def _consume_logs(self):
        """Consume logs from queue and display in GUI"""
        try:
            # Process multiple log messages at once to improve performance
            messages = []
            for _ in range(20):  # Process up to 20 messages at once
                try:
                    log_message = self.log_queue.get_nowait()
                    messages.append(log_message)
                except queue.Empty:
                    break
            
            if messages:
                # Batch insert messages
                combined_message = ''.join(messages)
                self.log_text.insert(tk.END, combined_message)
                
                # Only scroll to end if we're near the bottom
                if self.log_text.yview()[1] > 0.9:
                    self.log_text.see(tk.END)
                
                # Limit log size to prevent memory issues
                try:
                    line_count = int(self.log_text.index(tk.END).split('.')[0])
                    if line_count > 1000:
                        self.log_text.delete('1.0', '500.0')
                except (ValueError, IndexError):
                    pass
                    
        except Exception as e:
            # Log error but don't crash
            try:
                print(f"Log consumption error: {e}")
            except:
                pass
        
        # Schedule next check with longer interval for better performance
        self.root.after(300, self._consume_logs)
    
    def _check_prerequisites(self):
        """Check system prerequisites"""
        def check_in_thread():
            try:
                self._log("Checking system prerequisites...")
                
                # Check WSL2
                wsl_ok = self._check_wsl()
                self.root.after(0, lambda: self._update_status(self.wsl_status, "WSL2", wsl_ok))
                
                # Check Ubuntu
                ubuntu_ok = self._check_ubuntu()
                self.root.after(0, lambda: self._update_status(self.ubuntu_status, "Ubuntu", ubuntu_ok))
                
                # Check Docker installation and running status
                docker_installed = self._check_docker_installed()
                docker_running = self._check_docker() if docker_installed else False
                
                # Try to start Docker if installed but not running
                if docker_installed and not docker_running:
                    self._log("Docker installed but not running. Attempting to start...")
                    if self._start_docker_desktop():
                        # Wait longer for Docker Desktop to fully start
                        self._log("Waiting for Docker Desktop to fully start...")
                        for i in range(6):  # Wait up to 30 seconds
                            time.sleep(5)
                            self._log(f"Checking Docker status... ({i+1}/6)")
                            docker_running = self._check_docker()
                            if docker_running:
                                self._log("[SUCCESS] Docker Desktop is now running")
                                break
                        else:
                            self._log("[WARNING] Docker Desktop may still be starting up")
                
                self.root.after(0, lambda: self._update_status(self.docker_status, "Docker", docker_running))
                
                self.prereq_ok = wsl_ok and ubuntu_ok and docker_installed and docker_running
                
                if self.prereq_ok:
                    self._log("[SUCCESS] All prerequisites satisfied")
                    self.root.after(0, self._enable_login)
                else:
                    self._log("[ERROR] Some prerequisites are missing")
                    missing = []
                    if not wsl_ok:
                        missing.append('WSL2')
                    if not ubuntu_ok:
                        missing.append('Ubuntu')
                    if not docker_installed:
                        missing.append('Docker Desktop')
                    elif not docker_running:
                        missing.append('Docker (start it)')
                    
                    self._log(f"[WARNING] Missing: {', '.join(missing)}")
                    
                    # Add debug info for Ubuntu detection
                    if wsl_ok and not ubuntu_ok:
                        self._log("[WARNING] WSL2 detected but Ubuntu not found. Debug info:")
                        self._debug_wsl_installations()
                    
                    # Show setup button if prerequisites are missing
                    self.root.after(0, self._show_setup_button)
                    
            except Exception as e:
                self._log(f"Error checking prerequisites: {e}")
        
        # Run in thread to prevent GUI freezing
        threading.Thread(target=check_in_thread, daemon=True).start()
    
    def _check_wsl(self):
        """Check if WSL2 is available"""
        try:
            result = subprocess.run(['wsl', '--list', '--verbose'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def _check_ubuntu(self):
        """Check if Ubuntu is installed in WSL"""
        try:
            # Try multiple detection methods
            detection_methods = [
                # Method 1: Quiet list
                lambda: self._check_ubuntu_quiet_list(),
                # Method 2: Verbose list
                lambda: self._check_ubuntu_verbose_list(),
                # Method 3: Try to run Ubuntu command
                lambda: self._check_ubuntu_command(),
                # Method 4: Check for specific Ubuntu distributions
                lambda: self._check_ubuntu_specific()
            ]
            
            for i, method in enumerate(detection_methods, 1):
                try:
                    if method():
                        self._log(f"[SUCCESS] Ubuntu detected using method {i}")
                        return True
                except Exception as e:
                    self._log(f"Method {i} failed: {e}")
                    continue
            
            self._log("[ERROR] Ubuntu distribution not found with any method")
            return False
            
        except Exception as e:
            self._log(f"[ERROR] Unable to query WSL distributions: {e}")
            return False
    
    def _check_ubuntu_quiet_list(self):
        """Check Ubuntu using quiet list"""
        r = subprocess.run([self._wsl_cmd(), "-l", "-q"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            lines = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
            found = any("ubuntu" in ln.lower() for ln in lines)
            if found:
                self._log(f"Ubuntu found in quiet list: {lines}")
                return True
        return False
    
    def _check_ubuntu_verbose_list(self):
        """Check Ubuntu using verbose list"""
        r = subprocess.run([self._wsl_cmd(), "-l", "-v"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            output = (r.stdout or r.stderr or "").lower()
            if "ubuntu" in output:
                self._log(f"Ubuntu found in verbose list")
                return True
            # Also check for specific Ubuntu patterns
            lines = output.splitlines()
            for line in lines:
                if "ubuntu" in line and ("running" in line or "stopped" in line):
                    self._log(f"Ubuntu found in verbose list: {line.strip()}")
                    return True
        return False
    
    def _check_ubuntu_command(self):
        """Check Ubuntu by trying to run a command"""
        # Try different Ubuntu distribution names
        ubuntu_names = ["Ubuntu", "Ubuntu-22.04", "Ubuntu-20.04", "ubuntu", "ubuntu-22.04", "ubuntu-20.04"]
        
        for name in ubuntu_names:
            try:
                r = subprocess.run([self._wsl_cmd(), "-d", name, "--", "lsb_release", "-a"], 
                                 capture_output=True, text=True, timeout=8)
                if r.returncode == 0 and "ubuntu" in r.stdout.lower():
                    self._log(f"Ubuntu command check successful for {name}")
                    return True
            except Exception:
                continue
        return False
    
    def _check_ubuntu_specific(self):
        """Check for specific Ubuntu distributions"""
        try:
            # Try to get WSL status
            r = subprocess.run([self._wsl_cmd(), "--status"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                output = r.stdout.lower()
                if "ubuntu" in output:
                    self._log("Ubuntu found in WSL status")
                    return True
            
            # Try to list distributions with different flags
            for flag in ["--list", "-l"]:
                try:
                    r = subprocess.run([self._wsl_cmd(), flag], capture_output=True, text=True, timeout=10)
                    if r.returncode == 0 and "ubuntu" in r.stdout.lower():
                        self._log(f"Ubuntu found with flag {flag}")
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False
    
    def _check_docker(self):
        """Check if Docker Desktop is running"""
        try:
            # Try multiple Docker commands to check if it's running
            docker_commands = [
                ['version'],
                ['info'],
                ['ps']
            ]
            
            for cmd in docker_commands:
                try:
                    result = subprocess.run([self._docker_cmd()] + cmd, 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        # For 'version' command, check if server info is present
                        if cmd == ['version']:
                            if 'Server:' in result.stdout:
                                self._log("[SUCCESS] Docker Desktop is fully running")
                                return True
                            else:
                                self._log("[WARNING] Docker client available but server not ready")
                                continue
                        else:
                            self._log("[SUCCESS] Docker Desktop is running")
                            return True
                except Exception as e:
                    self._log(f"Docker command {' '.join(cmd)} failed: {e}")
                    continue
            
            return False
        except Exception as e:
            self._log(f"Docker check failed: {e}")
            return False
    
    def _wsl_cmd(self):
        """Get the WSL command path"""
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
    
    def _docker_cmd(self):
        """Get the Docker command path"""
        # Try PATH first
        import shutil
        path = shutil.which('docker')
        if path:
            return path
        # Fallback common Docker Desktop path
        candidate = r"C:\\Program Files\\Docker\\Docker\\resources\\bin\\docker.exe"
        return candidate if os.path.exists(candidate) else 'docker'
    
    def _check_docker_installed(self):
        """Check if Docker is installed"""
        try:
            r = subprocess.run([self._docker_cmd(), "--version"], capture_output=True, text=True)
            if r.returncode == 0:
                self._log(f"[SUCCESS] Docker installed: {r.stdout.strip()}")
                return True
            self._log("[ERROR] Docker not installed")
            return False
        except FileNotFoundError:
            self._log("[ERROR] Docker not installed")
            return False
    
    def _start_docker_desktop(self):
        """Attempt to launch Docker Desktop on Windows."""
        try:
            candidates = [
                r"C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe",
                os.path.expandvars(r"%LocalAppData%\\Docker\\Docker\\Docker Desktop.exe"),
                r"C:\\Program Files (x86)\\Docker\\Docker\\Docker Desktop.exe",
            ]
            
            for exe in candidates:
                if exe and os.path.exists(exe):
                    self._log(f"Starting Docker Desktop: {exe}")
                    try:
                        # Use subprocess.Popen with shell=True for better compatibility
                        subprocess.Popen([exe], 
                                       stdout=subprocess.DEVNULL, 
                                       stderr=subprocess.DEVNULL, 
                                       shell=True,
                                       creationflags=subprocess.CREATE_NEW_CONSOLE)
                        self._log("[SUCCESS] Docker Desktop startup initiated")
                        return True
                    except Exception as e:
                        self._log(f"Failed to start Docker Desktop at {exe}: {e}")
                        continue
            
            # If no executable found, try using the service
            try:
                self._log("Trying to start Docker service...")
                result = subprocess.run(["net", "start", "com.docker.service"], 
                             capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    self._log("[SUCCESS] Docker service started")
                    return True
                else:
                    self._log(f"Failed to start Docker service: {result.stderr}")
            except Exception as e:
                self._log(f"Failed to start Docker service: {e}")
            
            self._log("[ERROR] Could not start Docker Desktop automatically")
            return False
        except Exception as e:
            self._log(f"Unable to auto-start Docker Desktop: {e}")
            return False
    
    def _debug_wsl_installations(self):
        """Debug WSL installations to help troubleshoot Ubuntu detection"""
        try:
            # Try different WSL commands and log their output
            commands = [
                ['wsl', '--list', '--verbose'],
                ['wsl', '--list'],
                ['wsl', '-l', '-v']
            ]
            
            for i, cmd in enumerate(commands):
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, encoding='utf-8')
                    self._log(f"WSL command {i+1} ({' '.join(cmd)}):")
                    self._log(f"  Return code: {result.returncode}")
                    self._log(f"  Output: {result.stdout.strip()}")
                    if result.stderr:
                        self._log(f"  Error: {result.stderr.strip()}")
                except Exception as e:
                    self._log(f"  Exception: {str(e)}")
                    
        except Exception as e:
            self._log(f"Debug failed: {str(e)}")
    
    def _refresh_prerequisites(self):
        """Refresh prerequisites check"""
        # Disable refresh button to prevent multiple simultaneous checks
        self.refresh_prereq_button.config(state="disabled")
        
        def refresh_in_thread():
            try:
                self._log("Refreshing prerequisites check...")
                self._check_prerequisites()
            finally:
                # Re-enable refresh button after a delay
                self.root.after(2000, lambda: self.refresh_prereq_button.config(state="normal"))
        
        # Run in thread to prevent GUI freezing
        threading.Thread(target=refresh_in_thread, daemon=True).start()
    
    def _update_status(self, label, name, status):
        """Update status label"""
        if status:
            label.config(text=f"{name}: [SUCCESS] Available", foreground="green")
        else:
            label.config(text=f"{name}: [ERROR] Not Available", foreground="red")
    
    def _enable_login(self):
        """Enable login controls"""
        self.email_entry.config(state="normal")
        self.password_entry.config(state="normal")
        self.login_button.config(state="normal")
    
    def _show_setup_button(self):
        """Show setup button when prerequisites are missing"""
        # Add a setup button to the status frame if not already present
        if not hasattr(self, 'setup_button'):
            self.setup_button = ttk.Button(
                self.wsl_status.master, 
                text="Setup Environment", 
                command=self._run_setup_wizard
            )
            self.setup_button.grid(row=0, column=4, sticky=tk.W, padx=(10, 0))
    
    def _run_setup_wizard(self):
        """Guide user through WSL2, Ubuntu 22.04 and Docker setup. Attempts automation where possible."""
        def run():
            try:
                self.progress_var.set("Setting up environment...")
                self._log("=== Environment Setup Wizard ===")

                # 1) Enable WSL and Virtual Machine Platform (requires admin)
                self._log("Enabling WSL and Virtual Machine Platform features (requires Administrator)…")
                try:
                    # Launch elevated PowerShell to enable features
                    ps_cmd = (
                        'Start-Process PowerShell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass '
                        'dism /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart; '
                        'dism /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart; '
                        'wsl --set-default-version 2"'
                    )
                    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=60)
                    self._log("Requested WSL feature enable. A reboot may be required.")
                except Exception as e:
                    self._log(f"Could not auto-enable WSL features: {e}")

                # 2) Install Ubuntu 22.04
                if not self._check_ubuntu():
                    self._log("Installing Ubuntu 22.04… (this may open a system window)")
                    try:
                        subprocess.run([self._wsl_cmd(), "--install", "-d", "Ubuntu-22.04"], timeout=180)
                        self._log("Ubuntu 22.04 installation initiated. Complete initialization on first launch if prompted.")
                    except Exception as e:
                        self._log(f"Could not auto-install Ubuntu 22.04: {e}")
                        self._log("Open Microsoft Store and install 'Ubuntu 22.04 LTS' manually.")
                        # Try direct product link for Ubuntu 22.04 LTS, fallback to search
                        if sys.platform.startswith('win'):
                            import webbrowser
                            webbrowser.open("ms-windows-store://pdp/?productid=9PN20MSR04DW")
                        webbrowser.open("https://apps.microsoft.com/store/detail/ubuntu-2204-lts/9PN20MSR04DW")

                # 3) Install Docker Desktop
                if not self._check_docker_installed():
                    self._log("Opening Docker Desktop download page…")
                    webbrowser.open("https://www.docker.com/products/docker-desktop/")
                    self._log("Download and install Docker Desktop. When finished, start Docker Desktop.")

                # 4) Ensure Docker is running and using WSL2 engine
                self._log("Ensuring Docker Desktop is running…")
                # Try a simple docker info to trigger autostart if available
                self._check_docker()
                self._log("Make sure Docker Desktop is set to use WSL 2 backend and Ubuntu-22.04 is enabled under Resources > WSL Integration.")

                # Final re-check
                self._log("Re-checking prerequisites…")
                self._check_prerequisites()
                self._log("Setup wizard finished.")
                self.progress_var.set("Setup completed")
            except Exception as e:
                self._log(f"Setup wizard error: {e}")
                self.progress_var.set("Setup failed")
        
        threading.Thread(target=run, daemon=True).start()
    
    def _login(self):
        """Handle user login"""
        email = self.email_var.get().strip()
        password = self.password_var.get().strip()
        
        if not email or not password:
            messagebox.showerror("Error", "Please enter both email and password")
            return
        
        self._log(f"Logging in as {email}...")
        self.progress_var.set("Logging in...")
        
        try:
            # Prefer direct HTTP call to backend to avoid mismatched helper logic
            url = f"{self.api_base}/auth/login/"
            resp = requests.post(url, json={"email": email, "password": password}, timeout=15)
            try:
                resp.raise_for_status()
            except Exception as http_err:
                # Include server message if available
                msg = resp.text
                raise RuntimeError(f"{http_err}: {msg}")
            data = resp.json()
            self.token = data.get("access")
            self.refresh_token = data.get("refresh")
            if not self.token:
                raise RuntimeError("No access token in response")
            self._log("[SUCCESS] Login successful")
            
            # Get host info
            self._get_host_info()
            
            # Enable post-login features
            self._enable_post_login()
            
        except Exception as e:
            self._log(f"[ERROR] Login failed: {str(e)}")
            messagebox.showerror("Login Failed", f"Login failed: {str(e)}")
            self.progress_var.set("Login failed")
    
    def _get_host_info(self):
        """Get host information for the logged-in user"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{self.api_base}/hosts/", headers=headers, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            # Our API returns the current host profile object (not a list)
            if isinstance(data, dict) and data.get("id"):
                self.host_id = data["id"]
                self._log(f"[SUCCESS] Host ID: {self.host_id}")
                # Load GPU info
                self._load_gpu_info()
            else:
                self._log("[WARNING] No host profile found for this user")
        except Exception as e:
            self._log(f"[ERROR] Failed to get host info: {str(e)}")
    
    def _load_gpu_info(self):
        """Load GPU information"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{self.api_base}/gpus/", 
                                  params={"host": self.host_id}, headers=headers)
            response.raise_for_status()
            
            gpus_data = response.json()
            gpus = gpus_data.get("results", gpus_data)
            
            if gpus:
                gpu = gpus[0]
                gpu_info = f"GPU: {gpu['gpu_name']}\n"
                gpu_info += f"Memory: {gpu['gpu_memory']}GB\n"
                gpu_info += f"Price: {gpu['gpu_price']} NPR/hour\n"
                gpu_info += f"Status: {'Available' if gpu['gpu_availability'] else 'In Use'}"
                
                self.gpu_info_text.delete(1.0, tk.END)
                self.gpu_info_text.insert(1.0, gpu_info)
                
                self._log(f"[SUCCESS] GPU loaded: {gpu['gpu_name']}")
            else:
                self.gpu_info_text.delete(1.0, tk.END)
                self.gpu_info_text.insert(1.0, "No GPU registered")
                self._log("[WARNING] No GPU registered")
                
        except Exception as e:
            self._log(f"[ERROR] Failed to load GPU info: {str(e)}")
    
    def _enable_post_login(self):
        """Enable features after login"""
        self.login_button.config(state="disabled")
        self.logout_button.config(state="normal")
        self.detect_gpu_button.config(state="normal")
        self.register_gpu_button.config(state="normal")
        self.start_agent_button.config(state="normal")
        
        self.progress_var.set("Ready")
    
    def _logout(self):
        """Handle user logout"""
        self._stop_agent()
        
        self.token = None
        self.refresh_token = None
        self.host_id = None
        
        # Reset UI
        self.login_button.config(state="normal")
        self.logout_button.config(state="disabled")
        self.detect_gpu_button.config(state="disabled")
        self.register_gpu_button.config(state="disabled")
        self.start_agent_button.config(state="disabled")
        self.stop_agent_button.config(state="disabled")
        
        self.gpu_info_text.delete(1.0, tk.END)
        self.session_tree.delete(*self.session_tree.get_children())
        
        self._log("[SUCCESS] Logged out")
        self.progress_var.set("Logged out")
    
    def _detect_gpu(self):
        """Detect GPU information"""
        self._log("Detecting GPU information...")
        self.progress_var.set("Detecting GPU...")
        
        try:
            gpu_info = detect_gpu_info()
            system_info = detect_system_info()
            
            info_text = f"GPU: {gpu_info['name']}\n"
            info_text += f"VRAM: {gpu_info['vram_gb']}GB\n"
            info_text += f"CUDA Cores: {gpu_info['cuda_cores']}\n"
            info_text += f"Driver: {gpu_info['driver_version']}\n"
            info_text += f"System: {system_info['os']} on {system_info['hostname']}"
            
            self.gpu_info_text.delete(1.0, tk.END)
            self.gpu_info_text.insert(1.0, info_text)
            
            self._log(f"[SUCCESS] GPU detected: {gpu_info['name']}")
            self.progress_var.set("GPU detected")
            
        except Exception as e:
            self._log(f"[ERROR] GPU detection failed: {str(e)}")
            messagebox.showerror("GPU Detection Failed", f"Failed to detect GPU: {str(e)}")
            self.progress_var.set("GPU detection failed")
    
    def _register_gpu(self):
        """Register GPU with backend"""
        if not self.token:
            messagebox.showerror("Error", "Please login first")
            return
        
        # Get price from user
        price = simpledialog.askinteger("GPU Price", 
                                       "Enter price per hour (NPR):", 
                                       minvalue=1, maxvalue=10000)
        if not price:
            return
        
        self._log(f"Registering GPU with price {price} NPR/hour...")
        self.progress_var.set("Registering GPU...")
        
        try:
            gpu_info = detect_gpu_info()
            sys_info = detect_system_info()
            # Try to resolve geo location using public IP geolocation services
            def get_geo_location():
                try:
                    # Provider 1: ipapi.co
                    r = requests.get("https://ipapi.co/json/", timeout=6)
                    if r.status_code == 200:
                        j = r.json()
                        lat = j.get("latitude") or j.get("lat")
                        lon = j.get("longitude") or j.get("lon")
                        city = j.get("city")
                        country = j.get("country_name") or j.get("country")
                        if lat and lon:
                            return {"lat": lat, "lon": lon, "label": f"{city}, {country}" if city and country else None}
                except Exception:
                    pass
                try:
                    # Provider 2: ipinfo.io
                    r = requests.get("https://ipinfo.io/json", timeout=6)
                    if r.status_code == 200:
                        j = r.json()
                        loc = j.get("loc")  # "lat,lon"
                        if loc:
                            lat, lon = loc.split(",")
                            city = j.get("city")
                            country = j.get("country")
                            return {"lat": lat, "lon": lon, "label": f"{city}, {country}" if city and country else None}
                except Exception:
                    pass
                try:
                    # Provider 3: ipwho.is
                    r = requests.get("https://ipwho.is/", timeout=6)
                    if r.status_code == 200:
                        j = r.json()
                        lat = j.get("latitude")
                        lon = j.get("longitude")
                        city = j.get("city")
                        country = j.get("country")
                        if lat and lon:
                            return {"lat": lat, "lon": lon, "label": f"{city}, {country}" if city and country else None}
                except Exception:
                    pass
                return None
            geo = get_geo_location()
            
            # Map to backend serializer fields
            gpu_data = {
                "host": self.host_id,
                "gpu_name": gpu_info.get("name") or "Unknown GPU",
                "gpu_model": gpu_info.get("name") or "Unknown",
                "gpu_memory": int(gpu_info.get("vram_gb") or 0),
                "gpu_price": int(price),
                "gpu_availability": True,
                # Prefer human-readable place label; fallback to lat,lon; then hostname
                "gpu_location": (
                    (geo.get('label') if geo and geo.get('label') else None)
                    or (f"{geo['lat']},{geo['lon']}" if geo and geo.get('lat') and geo.get('lon') else None)
                    or (sys_info.get("hostname") or "Unknown")
                ),
            }
            
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(f"{self.api_base}/gpus/", 
                                   json=gpu_data, headers=headers, timeout=20)
            try:
                response.raise_for_status()
            except Exception as http_err:
                raise RuntimeError(f"{http_err}: {response.text}")
            
            gpu = response.json()
            self._log(f"[SUCCESS] GPU registered: {gpu.get('id')}")
            
            # Reload GPU info
            self._load_gpu_info()
            
            self.progress_var.set("GPU registered")
            
        except Exception as e:
            self._log(f"[ERROR] GPU registration failed: {str(e)}")
            messagebox.showerror("GPU Registration Failed", f"Failed to register GPU: {str(e)}")
            self.progress_var.set("GPU registration failed")
    
    def _start_agent(self):
        """Start the agent polling loop"""
        if not self.token:
            messagebox.showerror("Error", "Please login first")
            return
        
        if self.is_agent_running:
            messagebox.showwarning("Warning", "Agent is already running")
            return
        
        self.is_agent_running = True
        self.start_agent_button.config(state="disabled")
        self.stop_agent_button.config(state="normal")
        
        self._log("Starting agent...")
        self.progress_var.set("Agent starting...")
        
        # Start agent thread
        agent_thread = threading.Thread(target=self._agent_loop, daemon=True)
        agent_thread.start()
    
    def _stop_agent(self):
        """Stop the agent polling loop"""
        if not self.is_agent_running:
            return
        
        self.is_agent_running = False
        self.start_agent_button.config(state="normal")
        self.stop_agent_button.config(state="disabled")
        
        self._log("Stopping agent...")
        self.progress_var.set("Agent stopping...")
        
        # Clean up active sessions
        for session_id, (proc, cid) in self.active_sessions.items():
            if proc:
                proc.terminate()
                self._log(f"Terminated tunnel for session {session_id}")
        
        self.active_sessions.clear()
        
        # Stop metrics threads
        for session_id, (thread, stop_evt) in self.metrics_threads.items():
            stop_evt.set()
            thread.join(timeout=1)
        
        self.metrics_threads.clear()
        
        self._log("[SUCCESS] Agent stopped")
        self.progress_var.set("Agent stopped")
    
    def _agent_loop(self):
        """Main agent polling loop"""
        self._log("Agent started - polling for sessions...")
        
        while self.is_agent_running:
            try:
                # Poll pending sessions assigned to this host
                headers = {"Authorization": f"Bearer {self.token}"}
                response = requests.get(f"{self.api_base}/sessions/pending_for_host/",
                                      headers=headers, timeout=20)
                response.raise_for_status()
                
                sessions_data = response.json()
                if isinstance(sessions_data, list):
                    sessions = sessions_data
                else:
                    sessions = sessions_data.get("results", sessions_data)
                
                # Process new sessions
                for session in sessions:
                    session_id = session["id"]
                    if session_id not in self.active_sessions:
                        self._process_new_session(session)
                
                # Update session tree
                self._update_session_tree(sessions)
                
                # Check for ended sessions
                self._check_ended_sessions()
                
                time.sleep(5)  # Poll every 5 seconds
                
            except Exception as e:
                self._log(f"[ERROR] Agent loop error: {str(e)}")
                time.sleep(10)  # Wait longer on error
    
    def _process_new_session(self, session):
        """Process a new session"""
        session_id = session["id"]
        self._log(f"Processing new session: {session_id}")
        
        try:
            # Build session image
            image_template = session.get("image_template", "ml")
            img_tag = build_session_image(str(session_id), image_template)
            
            # Launch container
            host_port = self._get_free_port()
            password = generate_password()
            cid, jupyter_port = launch_container(img_tag, host_port, password, str(session_id))
            
            # Start relay tunnel
            relay_host = session.get("ssh_host")
            relay_port = session.get("ssh_port")
            ssh_username = session.get("ssh_username")
            
            proc = None
            if relay_host and relay_port:
                proc = start_relay_tunnel(host_port, relay_host, relay_port, ssh_username, password)

            # Store session info
            self.active_sessions[session_id] = (proc, cid)

            # Require relay tunnel to be up; otherwise, mark error and clean up
            tunnel_ok = proc is not None and getattr(proc, 'poll', lambda: None)() is None
            if not tunnel_ok:
                try:
                    # Inform backend the connection failed
                    headers = {"Authorization": f"Bearer {self.token}"}
                    requests.post(f"{self.api_base}/sessions/{session_id}/update_connection_status/", json={
                        "status": "ERROR",
                        "error_message": "Reverse SSH tunnel failed to start"
                    }, headers=headers, timeout=10)
                except Exception:
                    pass
                # Stop container if tunnel can't be established
                try:
                    subprocess.run(["docker", "rm", "-f", cid], capture_output=True, text=True)
                except Exception:
                    pass
                self._log(f"[ERROR] Tunnel failed for session {session_id}; container removed")
                return

            # Relay OK: publish relay details and mark started
            self._mark_session_started(session_id, password)

            # Start metrics thread
            self._start_metrics_thread(session_id)

            self._log(f"[SUCCESS] Session {session_id} ready")
                
        except Exception as e:
            self._log(f"[ERROR] Failed to process session {session_id}: {str(e)}")
    
    def _get_free_port(self):
        """Get a free port for container"""
        return _choose_free_port()
    
    def _update_session_status(self, session_id, status, password=None):
        """Update session status in backend"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            data = {"connection_status": status}
            if password:
                data["ssh_password"] = password
            
            response = requests.patch(f"{self.api_base}/sessions/{session_id}/", 
                                    json=data, headers=headers)
            response.raise_for_status()
            
        except Exception as e:
            self._log(f"[ERROR] Failed to update session status: {str(e)}")

    def _mark_session_started(self, session_id, password=None, override_host=None, override_port=None, override_user=None):
        """Call backend mark_started to set start_time and mark ACTIVE"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            payload = {}
            if password:
                payload["ssh_password"] = password
            if override_host:
                payload["ssh_host"] = override_host
            if override_port:
                payload["ssh_port"] = override_port
            if override_user:
                payload["ssh_username"] = override_user
            r = requests.post(f"{self.api_base}/sessions/{session_id}/mark_started/",
                              json=payload, headers=headers, timeout=15)
            r.raise_for_status()
        except Exception as e:
            self._log(f"[ERROR] Failed to mark session started: {str(e)}")
    
    def _start_metrics_thread(self, session_id):
        """Start metrics reporting thread for session"""
        stop_evt = threading.Event()
        
        def metrics_loop():
            while not stop_evt.is_set():
                try:
                    # Collect GPU metrics
                    gpu_info = detect_gpu_info()
                    
                    # Update session metrics
                    headers = {"Authorization": f"Bearer {self.token}"}
                    metrics_data = {
                        "gpu_utilization": 50,  # Placeholder
                        "memory_utilization": 30,  # Placeholder
                        "temperature": 60  # Placeholder
                    }
                    
                    response = requests.post(f"{self.api_base}/sessions/{session_id}/update_gpu_metrics/", 
                                           json=metrics_data, headers=headers)
                    
                    time.sleep(2)
                    
                except Exception as e:
                    self._log(f"[ERROR] Metrics error for session {session_id}: {str(e)}")
                    break
        
        thread = threading.Thread(target=metrics_loop, daemon=True)
        thread.start()
        
        self.metrics_threads[session_id] = (thread, stop_evt)
    
    def _update_session_tree(self, sessions):
        """Update session tree view"""
        # Clear existing items
        for item in self.session_tree.get_children():
            self.session_tree.delete(item)
        
        # Add sessions
        for session in sessions:
            session_id = session["id"]
            status = session.get("connection_status", "UNKNOWN")
            # Handle both list serializer (flat fields) and detail serializer (nested objects)
            gpu_field = session.get("gpu")
            if isinstance(gpu_field, dict):
                gpu_name = gpu_field.get("gpu_name", "Unknown")
            else:
                gpu_name = session.get("gpu_name", "Unknown")

            renter_field = session.get("renter")
            if isinstance(renter_field, dict):
                renter_user = renter_field.get("user") or {}
                if isinstance(renter_user, dict):
                    renter_name = renter_user.get("first_name") or renter_user.get("username") or "Unknown"
                else:
                    renter_name = session.get("renter_name", "Unknown")
            else:
                renter_name = session.get("renter_name", "Unknown")
            
            self.session_tree.insert("", "end", text=session_id[:8], 
                                   values=(status, gpu_name, renter_name))
    
    def _check_ended_sessions(self):
        """Check for ended sessions and clean up"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{self.api_base}/sessions/", 
                                  params={"host": self.host_id, "status": "COMPLETED"}, 
                                  headers=headers)
            response.raise_for_status()
            
            sessions_data = response.json()
            sessions = sessions_data.get("results", sessions_data)
            
            for session in sessions:
                session_id = session["id"]
                if session_id in self.active_sessions:
                    self._cleanup_session(session_id)
                    
        except Exception as e:
            self._log(f"[ERROR] Failed to check ended sessions: {str(e)}")
    
    def _cleanup_session(self, session_id):
        """Clean up a session"""
        if session_id in self.active_sessions:
            proc, cid = self.active_sessions.pop(session_id)
            
            if proc:
                proc.terminate()
                self._log(f"Terminated tunnel for session {session_id}")
            
            if cid:
                subprocess.run(["docker", "rm", "-f", cid])
                self._log(f"Removed container for session {session_id}")
        
        # Stop metrics thread
        if session_id in self.metrics_threads:
            thread, stop_evt = self.metrics_threads.pop(session_id)
            stop_evt.set()
            thread.join(timeout=1)
        
        self._log(f"[SUCCESS] Cleaned up session {session_id}")
    
    def _clear_logs(self):
        """Clear log display"""
        self.log_text.delete(1.0, tk.END)
    
    def _log(self, message):
        """Log message to GUI"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.log_queue.put(log_message)
    
    def run(self):
        """Start the GUI"""
        self.root.mainloop()

def main():
    """Main entry point"""
    app = AgentGUI()
    app.run()

if __name__ == "__main__":
    main()
