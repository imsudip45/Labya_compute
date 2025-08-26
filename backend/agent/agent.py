#!/usr/bin/env python3
"""Labhya Compute Host Agent

Usage:
  labhya-agent register --api <url> --token <jwt> [--hostname <name>]
  labhya-agent detect --api <url> --username <email> --password <pwd> [--price <npr>]
  labhya-agent templates [--format json|text]
  labhya-agent run [--config <path>]

register   → obtains a nodeId from the backend and writes config.json.
detect     → detects GPU/system info and registers node with backend.
templates  → lists available Docker templates (ML-ready vs Ubuntu).
run        → polls the backend for sessions, builds/runs SSH containers,
             opens ngLocalhost tunnel, patches session & job records.

Docker Templates:
  - ml: ML-Ready Environment (PyTorch, TensorFlow, Jupyter, 50+ libraries)
  - ubuntu: Clean Ubuntu Environment (minimal setup, fast startup)
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import random
import re
import subprocess
import sys
import time
import uuid
import platform
from pathlib import Path
from typing import Tuple, Optional
import threading

import requests
try:
    import pynvml
except Exception:
    pynvml = None

import secrets
import string

# ------------ constants -------------
DEFAULT_API = "http://13.201.2.181/api"
LOGIN_PATH = "/login"
POLL_INTERVAL = 5  # seconds
BASE_IMAGE = "labhya-gpu-base"
SESSION_IMAGE_PREFIX = "labhya-session-"
BASE_DOCKERFILE = Path(__file__).parent / "gpu_ssh_image" / "labhya-base.dockerfile"
SESSION_DOCKERFILE = Path(__file__).parent / "gpu_ssh_image" / "session.Dockerfile"
SSH_PORT = 22

# Base images for different templates
BASE_UBUNTU_IMAGE = "ubuntu:22.04"
BASE_IMAGE_ML = "labhya-ml-base"      # ML-ready image with all libraries
BASE_IMAGE_UBUNTU = "labhya-ubuntu-base"  # Clean Ubuntu image

# Reverse SSH tunneling configuration
TUNNEL_TYPE = os.getenv("LABHYA_TUNNEL_TYPE", "bastion")
BASTION_HOST = os.getenv("LABHYA_BASTION_HOST", "13.201.2.181")
BASTION_PORT = int(os.getenv("LABHYA_BASTION_PORT", "22"))
BASTION_USER = os.getenv("LABHYA_BASTION_USER", "ubuntu")

# ------------ helpers -------------

def http(api_base: str, method: str, path: str, **kwargs):
    url = f"{api_base.rstrip('/')}/{path.lstrip('/')}"
    if os.getenv("AGENT_DEBUG"):
        print(f"[http] {method.upper()} {path}")
    return requests.request(method, url, timeout=30, **kwargs)


def fetch_tokens(api_base: str, username: str, password: str) -> tuple[str, str]:
    """Authenticate with the backend and return (access, refresh) JWT pair."""
    resp = http(api_base, "post", LOGIN_PATH, json={"username": username, "password": password})
    resp.raise_for_status()
    data = resp.json()
    return data["access"], data.get("refresh", "")


def refresh_access(api_base: str, refresh_token: str) -> str:
    resp = http(api_base, "post", "/token/refresh", json={"refresh": refresh_token})
    resp.raise_for_status()
    return resp.json()["access"]


def ensure_dockerfiles() -> None:
    BASE_DOCKERFILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Create ML-ready base image Dockerfile
    ml_base_content = f"""FROM {BASE_UBUNTU_IMAGE}

# Set up environment
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    python3 python3-pip python3-dev python3-venv \\
    git curl wget vim nano \\
    openssh-server openssh-client \\
    build-essential cmake \\
    libgl1-mesa-glx libglib2.0-0 \\
    libsm6 libxext6 libxrender-dev \\
    libgomp1 libgcc-s1 \\
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install wheel
RUN python3 -m pip install --upgrade pip setuptools wheel

# Install CUDA runtime libraries (without full CUDA toolkit)
RUN apt-get update && apt-get install -y \\
    nvidia-cuda-toolkit-gcc \\
    && rm -rf /var/lib/apt/lists/*

# Install comprehensive ML/data science libraries
RUN pip install \\
    torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 \\
    numpy pandas matplotlib seaborn \\
    scikit-learn scipy \\
    jupyter jupyterlab ipykernel \\
    tqdm requests pillow \\
    opencv-python \\
    transformers datasets \\
    tensorflow tensorflow-gpu \\
    keras \\
    xgboost lightgbm \\
    plotly bokeh \\
    nltk spacy \\
    beautifulsoup4 lxml \\
    sqlalchemy psycopg2-binary \\
    flask fastapi uvicorn \\
    pytest pytest-cov \\
    black flake8 isort \\
    && rm -rf ~/.cache/pip

# Create non-root user for security
RUN useradd -m -s /bin/bash -G sudo labhya && \\
    mkdir -p /home/labhya/.jupyter && \\
    chown -R labhya:labhya /home/labhya

# Set up SSH with non-root access
RUN mkdir /var/run/sshd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config && \\
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Set up Jupyter Notebook config for non-root user
RUN mkdir -p /workspace && chown labhya:labhya /workspace
WORKDIR /workspace

# Create Jupyter config
RUN mkdir -p /home/labhya/.jupyter && \\
    echo 'c.NotebookApp.ip = "0.0.0.0"' > /home/labhya/.jupyter/jupyter_notebook_config.py && \\
    echo 'c.NotebookApp.port = 8888' >> /home/labhya/.jupyter/jupyter_notebook_config.py && \\
    echo 'c.NotebookApp.open_browser = False' >> /home/labhya/.jupyter/jupyter_notebook_config.py && \\
    echo 'c.NotebookApp.allow_root = True' >> /home/labhya/.jupyter/jupyter_notebook_config.py && \\
    echo 'c.NotebookApp.token = ""' >> /home/labhya/.jupyter/jupyter_notebook_config.py && \\
    echo 'c.NotebookApp.password = ""' >> /home/labhya/.jupyter/jupyter_notebook_config.py && \\
    chown -R labhya:labhya /home/labhya/.jupyter

# Expose both SSH and Jupyter ports
EXPOSE {SSH_PORT} 8888

# Start both SSH and Jupyter services (set user password from LABHYA_PASS)
CMD ["/bin/bash", "-c", "echo 'labhya:'\"${{LABHYA_PASS:-labhyapass}}\" | chpasswd && service ssh start && su -c 'jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token=\\\"\\\" --NotebookApp.password=\\\"\\\" --notebook-dir=/workspace' labhya & wait"]
"""
    
    # Create clean Ubuntu base image Dockerfile
    ubuntu_base_content = f"""FROM {BASE_UBUNTU_IMAGE}

# Set up environment
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install basic system dependencies
RUN apt-get update && apt-get install -y \\
    python3 python3-pip python3-dev \\
    git curl wget vim nano \\
    openssh-server openssh-client \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN python3 -m pip install --upgrade pip setuptools wheel

# Create non-root user for security
RUN useradd -m -s /bin/bash -G sudo labhya && \\
    mkdir -p /home/labhya/.jupyter && \\
    chown -R labhya:labhya /home/labhya

# Set up SSH with non-root access
RUN mkdir /var/run/sshd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config && \\
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Set up workspace
RUN mkdir -p /workspace && chown labhya:labhya /workspace
WORKDIR /workspace

# Create Jupyter config
RUN mkdir -p /home/labhya/.jupyter && \\
    echo 'c.NotebookApp.ip = "0.0.0.0"' > /home/labhya/.jupyter/jupyter_notebook_config.py && \\
    echo 'c.NotebookApp.port = 8888' >> /home/labhya/.jupyter/jupyter_notebook_config.py && \\
    echo 'c.NotebookApp.open_browser = False' >> /home/labhya/.jupyter/jupyter_notebook_config.py && \\
    echo 'c.NotebookApp.allow_root = True' >> /home/labhya/.jupyter/jupyter_notebook_config.py && \\
    echo 'c.NotebookApp.token = ""' >> /home/labhya/.jupyter/jupyter_notebook_config.py && \\
    echo 'c.NotebookApp.password = ""' >> /home/labhya/.jupyter/jupyter_notebook_config.py && \\
    chown -R labhya:labhya /home/labhya/.jupyter

# Expose both SSH and Jupyter ports
EXPOSE {SSH_PORT} 8888

# Start both SSH and Jupyter services (set user password from LABHYA_PASS)
CMD ["/bin/bash", "-c", "echo 'labhya:'\"${{LABHYA_PASS:-labhyapass}}\" | chpasswd && service ssh start && su -c 'jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token=\\\"\\\" --NotebookApp.password=\\\"\\\" --notebook-dir=/workspace' labhya & wait"]
"""
    
    # Write ML base Dockerfile
    ml_dockerfile = BASE_DOCKERFILE.parent / "labhya-ml-base.dockerfile"
    ml_dockerfile.write_text(ml_base_content)
    
    # Write Ubuntu base Dockerfile
    ubuntu_dockerfile = BASE_DOCKERFILE.parent / "labhya-ubuntu-base.dockerfile"
    ubuntu_dockerfile.write_text(ubuntu_base_content)
    
    # Create session Dockerfile (uses ARG to specify base image)
    session_content = f"""ARG BASE_IMAGE
FROM ${{BASE_IMAGE}}
WORKDIR /workspace

# Optionally install user requirements if provided
ARG REQUIREMENTS
RUN if [ -f "$REQUIREMENTS" ]; then pip install --no-cache-dir -r $REQUIREMENTS; fi

# Optionally copy user code if provided
ARG USER_CODE_PATH
COPY ${{USER_CODE_PATH:-.}} /workspace

# Ensure proper ownership
RUN chown -R labhya:labhya /workspace

EXPOSE {SSH_PORT} 8888
CMD ["/bin/bash", "-c", "echo 'labhya:'\"${{LABHYA_PASS:-labhyapass}}\" | chpasswd && service ssh start && su -c 'jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token=\\\"\\\" --NotebookApp.password=\\\"\\\" --notebook-dir=/workspace' labhya & wait"]
"""
    SESSION_DOCKERFILE.write_text(session_content)


def _docker_image_exists(image: str) -> bool:
    result = subprocess.run(["docker", "images", "-q", image], capture_output=True, text=True)
    return bool(result.stdout.strip())


def _docker_pull(image: str) -> bool:
    try:
        subprocess.check_call(["docker", "pull", image])
        return True
    except subprocess.CalledProcessError:
        return False


def ensure_ubuntu_base_image() -> str:
    """Ensure Ubuntu base image is available locally"""
    if not _docker_image_exists(BASE_UBUNTU_IMAGE):
        print(f"[agent] Pulling Ubuntu base image: {BASE_UBUNTU_IMAGE}")
        if not _docker_pull(BASE_UBUNTU_IMAGE):
            raise RuntimeError(f"Failed to pull Ubuntu base image: {BASE_UBUNTU_IMAGE}")
        print(f"[agent] Successfully pulled Ubuntu base image: {BASE_UBUNTU_IMAGE}")
    else:
        print(f"[agent] Ubuntu base image already available: {BASE_UBUNTU_IMAGE}")
    return BASE_UBUNTU_IMAGE


def ensure_base_image_exists(image_name: str):
    """Build a specific base image only if it doesn't exist"""
    # Ensure Ubuntu base image is present
    ensure_ubuntu_base_image()
    
    # Check if the requested base image already exists
    result = subprocess.run(["docker", "images", "-q", image_name], capture_output=True, text=True)
    if result.stdout.strip():
        print(f"[agent] Base image {image_name} already exists, skipping build")
        return
    
    # Build the specific base image
    if image_name == BASE_IMAGE_ML:
        print("[agent] Building ML-ready base image…")
        ml_dockerfile = BASE_DOCKERFILE.parent / "labhya-ml-base.dockerfile"
        try:
            result = subprocess.run([
                "docker", "build", "--progress=plain", "-t", BASE_IMAGE_ML, "-f", str(ml_dockerfile), str(BASE_DOCKERFILE.parent)
            ], capture_output=True, text=True, timeout=1800)  # 30 minute timeout for comprehensive build
            
            if result.returncode != 0:
                print(f"[agent] ML base image build failed!")
                print(f"[agent] Error output: {result.stderr}")
                print(f"[agent] Standard output: {result.stdout}")
                raise RuntimeError(f"ML base image build failed with return code {result.returncode}")
            
            print("[agent] ML-ready base image built successfully!")
            
        except subprocess.TimeoutExpired:
            print("[agent] ML base image build timed out after 30 minutes!")
            raise RuntimeError("ML base image build timed out")
        except Exception as e:
            print(f"[agent] Error during ML base image build: {e}")
            raise
            
    elif image_name == BASE_IMAGE_UBUNTU:
        print("[agent] Building clean Ubuntu base image…")
        ubuntu_dockerfile = BASE_DOCKERFILE.parent / "labhya-ubuntu-base.dockerfile"
        try:
            result = subprocess.run([
                "docker", "build", "--progress=plain", "-t", BASE_IMAGE_UBUNTU, "-f", str(ubuntu_dockerfile), str(BASE_DOCKERFILE.parent)
            ], capture_output=True, text=True, timeout=600)  # 10 minute timeout for Ubuntu build
            
            if result.returncode != 0:
                print(f"[agent] Ubuntu base image build failed!")
                print(f"[agent] Error output: {result.stderr}")
                print(f"[agent] Standard output: {result.stdout}")
                raise RuntimeError(f"Ubuntu base image build failed with return code {result.returncode}")
            
            print("[agent] Clean Ubuntu base image built successfully!")
            
        except subprocess.TimeoutExpired:
            print("[agent] Ubuntu base image build timed out after 10 minutes!")
            raise RuntimeError("Ubuntu base image build timed out")
        except Exception as e:
            print(f"[agent] Error during Ubuntu base image build: {e}")
            raise
    else:
        raise ValueError(f"Unknown base image: {image_name}")


def build_session_image(session_id: str, base_image: str = BASE_IMAGE_ML) -> str:
    """
    Build session image with specified base image
    base_image: 'ml' for ML-ready image, 'ubuntu' for clean Ubuntu image
    """
    tag = f"{SESSION_IMAGE_PREFIX}{session_id}"
    
    # Map base image choice to actual image name
    base_image_map = {
        'ml': BASE_IMAGE_ML,
        'ubuntu': BASE_IMAGE_UBUNTU
    }
    
    actual_base_image = base_image_map.get(base_image, BASE_IMAGE_ML)
    print(f"[agent] Using base image: {actual_base_image}")
    
    # Check if session image already exists
    if _docker_image_exists(tag):
        print(f"[agent] Session image {tag} already exists, skipping build")
        return tag
    
    # Ensure the required base image exists before building session image
    ensure_base_image_exists(actual_base_image)
    
    print(f"[agent] Building session image {tag} with base {actual_base_image}...")
    try:
        # Run docker build with base image argument
        result = subprocess.run([
            "docker", "build", 
            "--progress=plain", 
            "--build-arg", f"BASE_IMAGE={actual_base_image}",
            "-t", tag, 
            "-f", str(SESSION_DOCKERFILE), 
            str(SESSION_DOCKERFILE.parent)
        ], capture_output=True, text=True, timeout=300)  # 5 minute timeout for session images
        
        if result.returncode != 0:
            print(f"[agent] Session image build failed!")
            print(f"[agent] Error output: {result.stderr}")
            print(f"[agent] Standard output: {result.stdout}")
            raise RuntimeError(f"Session image build failed with return code {result.returncode}")
        
        print(f"[agent] Session image {tag} built successfully!")
        return tag
        
    except subprocess.TimeoutExpired:
        print(f"[agent] Session image build timed out after 5 minutes!")
        raise RuntimeError("Session image build timed out")
    except Exception as e:
        print(f"[agent] Error during session image build: {e}")
        raise


def launch_container(image_tag: str, host_port: int, password: str, session_id: str = None) -> str:
    print(f"[agent] Launching container with image {image_tag} on port {host_port}")
    jupyter_port = host_port + 1  # Jupyter on next port
    cmd = [
        "docker", "run", "-d", "--gpus", "all", 
        "-p", f"{host_port}:{SSH_PORT}",
        "-p", f"{jupyter_port}:8888",
        "--env", f"LABHYA_PASS={password}",
    ]
    
    # Add session ID label if provided
    if session_id:
        cmd.extend(["--label", f"session_id={session_id}"])
    
    cmd.append(image_tag)
    print(f"[agent] Docker command: {' '.join(cmd)}")
    cid = subprocess.check_output(cmd, text=True).strip()
    print(f"[agent] Container launched successfully: {cid}")
    return cid, jupyter_port


# ngLocalhost helpers ------------------------------------------------

def start_nglocalhost_tunnel(local_port: int, session_id=None, password=None):
    """Open a reverse SSH tunnel via nglocalhost.com.

    Returns (proc, public_host, public_port, ssh_command)
    """
    print(f"[agent] Starting ngLocalhost tunnel for port {local_port}")
    cmd = [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-R",
        f"0:localhost:{local_port}",
        "nglocalhost.com",
    ]
    print(f"[agent] SSH command: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    public_host = "nglocalhost.com"
    public_port = None
    pattern_banner = re.compile(r'\*+ nglocalhost.com:(\d+)')
    pattern_1 = re.compile(r"Forwarding TCP port (\d+).*->")
    pattern_2 = re.compile(r"Forwarding TCP connections from (\S+):(\d+)")

    print(f"[agent] Waiting for tunnel to establish...")
    # Wait up to 30 s for tunnel details
    for i in range(60):
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.5)
            continue
        print(f"[ngLocalhost] {line.strip()}")
        match_banner = pattern_banner.search(line)
        if match_banner:
            public_port = int(match_banner.group(1))
            print(f"[agent] Found port via ngLocalhost banner: {public_port}")
            break
        m1 = pattern_1.search(line)
        if m1:
            public_port = int(m1.group(1))
            print(f"[agent] Found port via pattern 1: {public_port}")
            break
        m2 = pattern_2.search(line)
        if m2:
            public_host = m2.group(1)
            public_port = int(m2.group(2))
            print(f"[agent] Found host/port via pattern 2: {public_host}:{public_port}")
            break

    if public_port:
        ssh_command = f"ssh root@{public_host} -p {public_port}"
        print(f"[agent] SSH command: {ssh_command}")
        if session_id and password:
            print(f"SESSION_CREDENTIALS::{{'session_id': {session_id}, 'ssh_command': '{ssh_command}', 'password': '{password}', 'public_host': '{public_host}', 'public_port': {public_port}}}")
        print(f"[agent] Tunnel established successfully: {ssh_command}")
        return proc, public_host, public_port, ssh_command
    else:
        print(f"[agent] Tunnel failed - no port found after 60 attempts")
        proc.terminate()
        raise RuntimeError("ngLocalhost tunnel did not provide a port")


def start_bastion_tunnel(local_port: int, session_id=None, password=None):
    """Open a reverse SSH tunnel via self-hosted bastion host.
    
    Returns (proc, public_host, public_port, ssh_command)
    """
    if not BASTION_HOST:
        raise RuntimeError("Bastion host not configured")
    
    print(f"[agent] Starting bastion tunnel for port {local_port}")
    
    # Generate a random tunnel port on bastion (20000-40000 range)
    tunnel_port = random.randint(20000, 40000)
    
    # Use SSH key if available, otherwise use password
    # Check if running as executable (PyInstaller)
    if getattr(sys, 'frozen', False):
        # Running as executable
        base_path = sys._MEIPASS
    else:
        # Running as script
        base_path = os.path.dirname(__file__)
    
    # Try multiple possible SSH key locations
    possible_ssh_key_paths = [
        os.path.join(base_path, "labhya_agent_key"),
        os.path.join(os.getcwd(), "labhya_agent_key"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "labhya_agent_key"),
        "labhya_agent_key"  # Current directory
    ]
    
    ssh_key_path = None
    for path in possible_ssh_key_paths:
        if os.path.exists(path):
            ssh_key_path = path
            break
    print(f"[agent] SSH key path: {ssh_key_path}")
    print(f"[agent] SSH key exists: {os.path.exists(ssh_key_path)}")
    if os.path.exists(ssh_key_path):
        cmd = [
            "ssh",
            "-i", ssh_key_path,
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ServerAliveInterval=60",
            "-o", "ServerAliveCountMax=3",
            "-R", f"{tunnel_port}:localhost:{local_port}",
            f"{BASTION_USER}@{BASTION_HOST}",
            "-p", str(BASTION_PORT)
        ]
    else:
        cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ServerAliveInterval=60",
            "-o", "ServerAliveCountMax=3",
            "-R", f"{tunnel_port}:localhost:{local_port}",
            f"{BASTION_USER}@{BASTION_HOST}",
            "-p", str(BASTION_PORT)
        ]
    
    print(f"[agent] SSH command: {' '.join(cmd)}")
    print(f"[agent] Using SSH key: {'Yes' if os.path.exists(ssh_key_path) else 'No'}")
    print(f"[agent] SSH key path: {ssh_key_path}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # Wait a moment for tunnel to establish
    time.sleep(2)
    
    # Check if process is still running
    if proc.poll() is not None:
        raise RuntimeError("Bastion tunnel failed to establish")
    
    public_host = BASTION_HOST
    public_port = tunnel_port
    ssh_command = f"ssh labhya@{public_host} -p {public_port}"
    
    print(f"[agent] Bastion tunnel established: {ssh_command}")
    if session_id and password:
        print(f"SESSION_CREDENTIALS::{{'session_id': {session_id}, 'ssh_command': '{ssh_command}', 'password': '{password}', 'public_host': '{public_host}', 'public_port': {public_port}}}")
    
    return proc, public_host, public_port, ssh_command

def start_reverse_ssh_tunnel(local_port: int, session_id=None, password=None, token=None):
    """Start reverse SSH tunnel using direct bastion tunneling.
    
    Returns (proc, public_host, public_port, ssh_command)
    """
    # Skip tunnel API and use direct bastion tunneling
    print(f"[agent] Using direct bastion tunneling (tunnel API not available)")
    return start_bastion_tunnel(local_port, session_id, password)

# ------------------- polling loop (simplified) -------------------

def run_poll_loop(api_base: str, cfg: dict):
    # Ensure Dockerfiles are created (but don't build images yet)
    ensure_dockerfiles()

    node_id = cfg["id"]
    token = cfg["token"]
    refresh = cfg.get("refresh")

    active_tunnels = {}
    metrics_threads: dict[str, tuple[threading.Thread, threading.Event]] = {}
    last_heartbeat = 0
    heartbeat_interval = 30  # Send heartbeat every 30 seconds

    print("[agent] Polling for sessions… ctrl+c to stop")
    while True:
        try:
            current_time = time.time()
            
            # Send heartbeat to update online status
            if current_time - last_heartbeat >= heartbeat_interval:
                try:
                    def request(method: str, path: str, **kwargs):
                        nonlocal token, refresh
                        headers = kwargs.pop("headers", {}) or {}
                        headers["Authorization"] = f"Bearer {token}"
                        try:
                            resp = http(api_base, method, path, headers=headers, **kwargs)
                            if resp.status_code == 401 and refresh:
                                # try refresh once
                                try:
                                    token = refresh_access(api_base, refresh)
                                except Exception as e:
                                    print("[agent] token refresh failed", e)
                                    raise
                                headers["Authorization"] = f"Bearer {token}"
                                resp = http(api_base, method, path, headers=headers, **kwargs)
                            return resp
                        except Exception as e:
                            raise

                    # Send heartbeat to update host online status
                    heartbeat_resp = request("patch", f"/agent/nodes/{node_id}", json={"online": True})
                    if heartbeat_resp.ok:
                        print("[agent] Heartbeat sent - host marked as online")
                    else:
                        print(f"[agent] Heartbeat failed: {heartbeat_resp.status_code}")
                    
                    last_heartbeat = current_time
                except Exception as e:
                    print(f"[agent] Heartbeat error: {e}")

            # fetch active sessions without container_id
            def request(method: str, path: str, **kwargs):
                nonlocal token, refresh
                headers = kwargs.pop("headers", {}) or {}
                headers["Authorization"] = f"Bearer {token}"
                try:
                    resp = http(api_base, method, path, headers=headers, **kwargs)
                    if resp.status_code == 401 and refresh:
                        # try refresh once
                        try:
                            token = refresh_access(api_base, refresh)
                        except Exception as e:
                            print("[agent] token refresh failed", e)
                            raise
                        headers["Authorization"] = f"Bearer {token}"
                        resp = http(api_base, method, path, headers=headers, **kwargs)
                    return resp
                except Exception as e:
                    raise

            resp = request("get", "/agent/sessions/active", params={"node": node_id})
            resp.raise_for_status()
            sessions = resp.json()

            for s in sessions:
                sid = s["id"]
                print(f"[agent] Processing session {sid}")
                
                # Skip if this session already has a container_id or we've processed it
                if s.get("container_id") or sid in active_tunnels:
                    print(f"[agent] Skipping session {sid} - already processed")
                    continue
                
                # Check if we already have a container for this session (even if not in active_tunnels)
                existing_containers = subprocess.run(
                    ["docker", "ps", "-a", "--filter", f"label=session_id={sid}", "--format", "{{.ID}}"],
                    capture_output=True, text=True
                )
                if existing_containers.stdout.strip():
                    print(f"[agent] Session {sid} already has container, skipping")
                    continue

                print(f"[agent] Starting session {sid} setup...")
                host_port = random.randint(20000, 30000)
                password = generate_password()
                
                # Get image template from session (default to ML if not specified)
                image_template = s.get("image_template", "ml")
                print(f"[agent] Session {sid} requested image template: {image_template}")
                
                print(f"[agent] Building session image for {sid}...")
                img_tag = build_session_image(str(sid), image_template)
                print(f"[agent] Launching container for {sid} on port {host_port}...")
                cid, jupyter_port = launch_container(img_tag, host_port, password, str(sid))
                print(f"[agent] Container launched: {cid}")
                print(f"[agent] Jupyter available on port: {jupyter_port}")
                
                # When starting tunnel, use the new function
                print(f"[agent] Starting reverse SSH tunnel for {sid}...")
                try:
                    proc, pub_host, pub_port, ssh_cmd = start_reverse_ssh_tunnel(host_port, sid, password, token)
                except Exception as e:
                    print(f"[agent] Failed to create tunnel for session {sid}: {e}")
                    # Clean up the container we just created
                    subprocess.run(["docker", "rm", "-f", cid])
                    continue
                
                print(f"[agent] Updating backend for session {sid}...")
                # Create Jupyter URL
                jupyter_url = f"http://{pub_host}:{jupyter_port}"
                jupyter_ssh_cmd = f"ssh labhya@{pub_host} -p {pub_port}"
                
                patch = {
                    "container_id": cid,
                    "public_host": pub_host,
                    "public_port": pub_port,
                    "ssh_command": jupyter_ssh_cmd,
                    "ssh_password": password,
                    "ssh_host": pub_host,
                    "ssh_port": pub_port,
                    "jupyter_url": jupyter_url,
                    "jupyter_port": jupyter_port,
                    "image_template": image_template,  # Include which template was used
                    "tunnel_type": TUNNEL_TYPE,
                    "bastion_host": BASTION_HOST if TUNNEL_TYPE == "bastion" else None,
                    "bastion_port": BASTION_PORT if TUNNEL_TYPE == "bastion" else None,
                    "tunnel_port": pub_port if TUNNEL_TYPE == "bastion" else None,
                }
                resp_p = request("patch", f"/agent/sessions/{sid}", json=patch)

                if resp_p.ok:
                    active_tunnels[sid] = (proc, cid)
                    print(f"[agent] Session {sid} ready  →  {ssh_cmd}")
                    print(f"[agent] SSH Password: {password}")
                    # Start metrics reporter thread for this session
                    stop_evt = threading.Event()
                    t = threading.Thread(target=report_metrics_loop, args=(api_base, token, sid, stop_evt), daemon=True)
                    metrics_threads[sid] = (t, stop_evt)
                    t.start()
                else:
                    print(f"[agent] PATCH failed for session {sid}: {resp_p.status_code} {resp_p.text}")

            # Check for ended sessions and clean them up
            resp = request("get", "/agent/sessions/ended", params={"node": node_id})
            resp.raise_for_status()
            ended = resp.json()
            for s in ended:
                sid = s["id"]
                proc_cid = active_tunnels.pop(sid, None)
                if proc_cid:
                    proc, cid = proc_cid
                    print(f"[agent] Cleaning up ended session {sid}")
                    if proc:
                        print(f"[agent] Terminating tunnel process for session {sid}")
                    proc.terminate()
                    if cid:
                        print(f"[agent] Removing container {cid} for session {sid}")
                    subprocess.run(["docker", "rm", "-f", cid])
                    # Mark session as cleaned
                    request("patch", f"/agent/sessions/{sid}", json={"status": "cleaned"})
                    print(f"[agent] Cleaned session {sid}")
                # Stop metrics reporter
                mt = metrics_threads.pop(sid, None)
                if mt:
                    t, stop_evt = mt
                    stop_evt.set()

        except KeyboardInterrupt:
            print("\n[agent] Shutting down...")
            break
        except Exception as e:
            print(f"[agent] Error in polling loop: {e}")
            time.sleep(POLL_INTERVAL)

    # Cleanup: mark host as offline when agent stops
    try:
        def request(method: str, path: str, **kwargs):
            nonlocal token, refresh
            headers = kwargs.pop("headers", {}) or {}
            headers["Authorization"] = f"Bearer {token}"
            try:
                resp = http(api_base, method, path, headers=headers, **kwargs)
                if resp.status_code == 401 and refresh:
                    # try refresh once
                    try:
                        token = refresh_access(api_base, refresh)
                    except Exception as e:
                        print("[agent] token refresh failed", e)
                        raise
                    headers["Authorization"] = f"Bearer {token}"
                    resp = http(api_base, method, path, headers=headers, **kwargs)
                return resp
            except Exception as e:
                raise

        # Mark host as offline
        offline_resp = request("patch", f"/agent/nodes/{node_id}", json={"online": False})
        if offline_resp.ok:
            print("[agent] Host marked as offline")
        else:
            print(f"[agent] Failed to mark host as offline: {offline_resp.status_code}")
    except Exception as e:
        print(f"[agent] Error marking host as offline: {e}")

    # Stop all metrics threads
    for sid, (thread, stop_evt) in metrics_threads.items():
        stop_evt.set()
        thread.join(timeout=1)
        print(f"[agent] Stopped metrics thread for session {sid}")

    # Clean up tunnels
    for sid, (proc, cid) in active_tunnels.items():
        if proc:
            proc.terminate()
            print(f"[agent] Terminated tunnel for session {sid}")
        # Note: containers will be cleaned up by the backend when sessions end


# ------------- config helpers -------------

def generate_password(length=12):
    # Cryptographically secure per-session password
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def get_available_templates():
    """Return available Docker templates for frontend"""
    return {
        "ml": {
            "name": "ML-Ready Environment",
            "description": "Pre-installed with PyTorch, TensorFlow, scikit-learn, Jupyter, and 50+ ML libraries",
            "features": [
                "PyTorch 2.1.0 with CUDA support",
                "TensorFlow & Keras",
                "scikit-learn, pandas, numpy",
                "Jupyter Notebook & JupyterLab",
                "OpenCV, Transformers, spaCy",
                "Flask, FastAPI, uvicorn",
                "Development tools (git, vim, nano)",
                "GPU acceleration ready"
            ],
            "size": "~8GB",
            "startup_time": "30-60 seconds"
        },
        "ubuntu": {
            "name": "Clean Ubuntu Environment",
            "description": "Minimal Ubuntu setup with basic Python and development tools",
            "features": [
                "Ubuntu 22.04 LTS",
                "Python 3 with pip",
                "Basic development tools",
                "SSH and Jupyter access",
                "Clean slate for custom setup",
                "Fast startup time"
            ],
            "size": "~2GB",
            "startup_time": "10-20 seconds"
        }
    }


def detect_gpu_info() -> dict:
    """Detect GPU information using nvidia-smi or other methods."""
    gpu_info = {
        "name": "Unknown GPU",
        "vram_gb": 0,
        "cuda_cores": 0,
        "driver_version": "Unknown",
        "cuda_version": "Unknown"
    }
    
    try:
        # Try nvidia-smi first
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if lines and lines[0]:
                parts = lines[0].split(', ')
                if len(parts) >= 3:
                    gpu_info["name"] = parts[0].strip()
                    # Convert memory from MB to GB
                    memory_mb = int(parts[1].strip())
                    gpu_info["vram_gb"] = memory_mb // 1024
                    gpu_info["driver_version"] = parts[2].strip()
                    
                    # Try to get CUDA version
                    try:
                        cuda_result = subprocess.run(["nvcc", "--version"], capture_output=True, text=True, timeout=5)
                        if cuda_result.returncode == 0:
                            cuda_match = re.search(r'release (\d+\.\d+)', cuda_result.stdout)
                            if cuda_match:
                                gpu_info["cuda_version"] = cuda_match.group(1)
                    except:
                        pass
                    
                    # Estimate CUDA cores based on GPU name (rough estimates)
                    name_lower = gpu_info["name"].lower()
                    if "rtx 4090" in name_lower:
                        gpu_info["cuda_cores"] = 16384
                    elif "rtx 4080" in name_lower:
                        gpu_info["cuda_cores"] = 9728
                    elif "rtx 3090" in name_lower:
                        gpu_info["cuda_cores"] = 10496
                    elif "rtx 3080" in name_lower:
                        gpu_info["cuda_cores"] = 8704
                    elif "rtx 3070" in name_lower:
                        gpu_info["cuda_cores"] = 5888
                    elif "rtx 3060" in name_lower:
                        gpu_info["cuda_cores"] = 3584
                    elif "gtx 1650" in name_lower:
                        gpu_info["cuda_cores"] = 1024  # GTX 1650 Ti has 1024 CUDA cores
                    elif "gtx 1660" in name_lower:
                        gpu_info["cuda_cores"] = 1408
                    elif "gtx 1080" in name_lower:
                        gpu_info["cuda_cores"] = 2560
                    elif "gtx 1070" in name_lower:
                        gpu_info["cuda_cores"] = 1920
                    else:
                        gpu_info["cuda_cores"] = 1024  # Default estimate
    except Exception as e:
        print(f"[agent] GPU detection failed: {e}")
    
    return gpu_info

def detect_system_info() -> dict:
    """Detect system information."""
    system_info = {
        "hostname": platform.node(),
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor()
    }
    
    # Try to get more detailed system info
    try:
        if platform.system() == "Linux":
            # Get CPU info on Linux
            with open("/proc/cpuinfo", "r") as f:
                cpu_info = f.read()
                model_match = re.search(r'model name\s+:\s+(.+)', cpu_info)
                if model_match:
                    system_info["processor"] = model_match.group(1).strip()
        elif platform.system() == "Windows":
            # Get CPU info on Windows
            try:
                result = subprocess.run(["wmic", "cpu", "get", "name"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        system_info["processor"] = lines[1].strip()
            except:
                pass
    except Exception as e:
        print(f"[agent] System info detection failed: {e}")
    
    return system_info


def report_metrics_loop(api_base: str, token: str, session_id: str, stop_evt: threading.Event, interval_seconds: float = 2.0) -> None:
    """Report GPU metrics similar to nvtop every few seconds to backend.

    Attempts to use NVML if available; falls back to nvidia-smi parsing if NVML missing.
    """
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    nvml_inited = False
    try:
        if pynvml is not None:
            pynvml.nvmlInit()
            nvml_inited = True
    except Exception as e:
        print(f"[metrics] NVML init failed: {e}")

    def collect_via_nvml() -> dict:
        data = {"metrics": {}}
        try:
            count = pynvml.nvmlDeviceGetCount()
            # For now, summarize device 0 (extend to per-device if needed)
            if count == 0:
                return data
            h = pynvml.nvmlDeviceGetHandleByIndex(0)
            util = pynvml.nvmlDeviceGetUtilizationRates(h)
            mem = pynvml.nvmlDeviceGetMemoryInfo(h)
            temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
            power = None
            fan = None
            clocks = {}
            try:
                power = pynvml.nvmlDeviceGetPowerUsage(h) / 1000.0
            except Exception:
                power = 0.0
            try:
                fan = pynvml.nvmlDeviceGetFanSpeed(h)
            except Exception:
                fan = 0.0
            try:
                clocks["graphics"] = pynvml.nvmlDeviceGetClockInfo(h, pynvml.NVML_CLOCK_GRAPHICS)
                clocks["memory"] = pynvml.nvmlDeviceGetClockInfo(h, pynvml.NVML_CLOCK_MEM)
            except Exception:
                pass
            procs = []
            try:
                for p in pynvml.nvmlDeviceGetComputeRunningProcesses_v3(h):
                    procs.append({
                        "pid": int(getattr(p, 'pid', 0)),
                        "gpu_mem": float(getattr(p, 'usedGpuMemory', 0) / (1024*1024)),
                    })
            except Exception:
                pass
            data["metrics"] = {
                "gpu_index": 0,
                "utilization": float(util.gpu),
                "memory_used": float(mem.used / (1024*1024*1024)),
                "memory_total": float(mem.total / (1024*1024*1024)),
                "temperature": float(temp),
                "power_draw": float(power),
                "fan_speed": float(fan),
                "clocks": clocks,
                "processes": procs,
            }
        except Exception as e:
            print(f"[metrics] NVML collection error: {e}")
        return data

    def collect_via_nvidia_smi() -> dict:
        try:
            q = [
                'nvidia-smi',
                '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,fan.speed,clocks.gr,clocks.mem',
                '--format=csv,noheader,nounits'
            ]
            r = subprocess.run(q, capture_output=True, text=True, timeout=5)
            if r.returncode != 0:
                return {"metrics": {}}
            parts = r.stdout.strip().split(', ')
            if len(parts) < 8:
                return {"metrics": {}}
            util, mem_used, mem_total, temp, power, fan, clk_gr, clk_mem = [p.strip() for p in parts[:8]]
            return {
                "metrics": {
                    "gpu_index": 0,
                    "utilization": float(util or 0.0),
                    "memory_used": float(mem_used) / 1024.0 if float(mem_used or 0) > 32 else float(mem_used),
                    "memory_total": float(mem_total) / 1024.0 if float(mem_total or 0) > 32 else float(mem_total),
                    "temperature": float(temp or 0.0),
                    "power_draw": float(power or 0.0),
                    "fan_speed": float(fan or 0.0),
                    "clocks": {"graphics": float(clk_gr or 0.0), "memory": float(clk_mem or 0.0)},
                }
            }
        except Exception as e:
            print(f"[metrics] nvidia-smi error: {e}")
            return {"metrics": {}}

    try:
        while not stop_evt.is_set():
            payload = collect_via_nvml() if nvml_inited else collect_via_nvidia_smi()
            if payload.get("metrics"):
                try:
                    url = f"{api_base.rstrip('/')}/agent/sessions/{session_id}/metrics"
                    resp = requests.post(url, headers=headers, json=payload, timeout=5)
                    if not resp.ok:
                        print(f"[metrics] post failed {resp.status_code}: {resp.text[:120]}")
                except Exception as e:
                    print(f"[metrics] post exception: {e}")
            stop_evt.wait(interval_seconds)
    finally:
        if nvml_inited:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass

def main():
    parser = argparse.ArgumentParser(description="Labhya Compute Agent (prototype)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    reg = sub.add_parser("register")
    reg.add_argument("--api", default=DEFAULT_API)
    token_group = reg.add_mutually_exclusive_group(required=False)
    token_group.add_argument("--token", help="JWT access token")
    token_group.add_argument("--username")
    reg.add_argument("--password")
    reg.add_argument("--hostname", default=os.uname().nodename if hasattr(os, "uname") else "host")

    detect = sub.add_parser("detect")
    detect.add_argument("--api", default=DEFAULT_API)
    token_group_detect = detect.add_mutually_exclusive_group(required=False)
    token_group_detect.add_argument("--token", help="JWT access token")
    token_group_detect.add_argument("--username")
    detect.add_argument("--password")
    detect.add_argument("--hostname", default=os.uname().nodename if hasattr(os, "uname") else "host")
    detect.add_argument("--price", type=int, default=100, help="Price per hour in NPR")

    templates = sub.add_parser("templates")
    templates.add_argument("--format", choices=["json", "text"], default="text", help="Output format")

    run_p = sub.add_parser("run")
    run_p.add_argument("--api", default=DEFAULT_API)
    run_p.add_argument("--node", help="host UUID returned by register (optional)")
    token_group2 = run_p.add_mutually_exclusive_group(required=False)
    token_group2.add_argument("--token", help="JWT access token")
    token_group2.add_argument("--username")
    run_p.add_argument("--password")
    run_p.add_argument("--refresh", help="JWT refresh token")

    args = parser.parse_args()

    if args.cmd == "register":
        token = args.token
        if not token:
            username = args.username or input("Host email: ").strip()
            pwd = args.password or getpass.getpass(f"Password for {username}: ")
            token, _ = fetch_tokens(args.api, username, pwd)
        headers = {"Authorization": f"Bearer {token}"}
        resp = http(args.api, "post", "/agent/nodes", json={"hostname": args.hostname}, headers=headers)
        resp.raise_for_status()
        node_id = resp.json()["nodeId"]
        print(f"Registered node {node_id}  (save this ID for --node when running)")

    elif args.cmd == "detect":
        print("[agent] Detecting GPU and system information...")
        
        # Detect GPU and system info
        gpu_info = detect_gpu_info()
        system_info = detect_system_info()
        
        print(f"[agent] GPU detected: {gpu_info['name']}")
        print(f"[agent] VRAM: {gpu_info['vram_gb']} GB")
        print(f"[agent] CUDA cores: {gpu_info['cuda_cores']}")
        print(f"[agent] System: {system_info['os']} on {system_info['hostname']}")
        
        # Get authentication
        token = args.token
        if not token:
            username = args.username or input("Host email: ").strip()
            pwd = args.password or getpass.getpass(f"Password for {username}: ")
            token, _ = fetch_tokens(args.api, username, pwd)
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Register node with detected info
        node_data = {
            "hostname": args.hostname,
            "gpu_name": gpu_info["name"],
            "vram_gb": gpu_info["vram_gb"],
            "cuda_cores": gpu_info["cuda_cores"],
            "driver_version": gpu_info["driver_version"],
            "cuda_version": gpu_info["cuda_version"],
            "system_info": system_info
        }
        
        resp = http(args.api, "post", "/agent/nodes", json=node_data, headers=headers)
        resp.raise_for_status()
        node_id = resp.json()["nodeId"]
        print(f"[agent] Node registered: {node_id}")
        
        # Create GPU with detected specs, but only if not already present
        gpu_data = {
            "gpuName": gpu_info["name"],
            "vramGB": gpu_info["vram_gb"],
            "cudaCores": gpu_info["cuda_cores"],
            "priceNpr": args.price
        }

        # Enhanced deduplication: fetch existing GPUs and check for a match
        print(f"[agent] Checking for existing GPUs with specs: {gpu_data['gpuName']}, {gpu_data['vramGB']}GB, {gpu_data['cudaCores']} cores")
        gpus_resp = http(args.api, "get", "/host/gpus", headers=headers)
        gpus_resp.raise_for_status()
        gpus = gpus_resp.json()
        
        print(f"[agent] Found {len(gpus)} existing GPUs")
        match = None
        for g in gpus:
            print(f"[agent] Checking GPU {g.get('id')}: {g.get('gpuName')}, {g.get('vramGB')}GB, {g.get('cudaCores')} cores")
            if (
                g.get("gpuName") == gpu_data["gpuName"] and
                g.get("vramGB") == gpu_data["vramGB"] and
                g.get("cudaCores") == gpu_data["cudaCores"]
            ):
                match = g
                print(f"[agent] Found matching GPU: {match['id']}")
                break
        
        if match:
            print(f"[agent] GPU already registered: {match['id']} ({match['gpuName']})")
            # Optionally update price if different
            if match.get("priceNpr") != args.price:
                print(f"[agent] Updating price from {match.get('priceNpr')} to {args.price} NPR/hour")
                patch_resp = http(args.api, "patch", f"/host/gpus/{match['id']}", json={"priceNpr": args.price}, headers=headers)
                if patch_resp.ok:
                    print(f"[agent] Updated GPU price to: {args.price} NPR/hour")
                else:
                    print(f"[agent] Failed to update GPU price: {patch_resp.status_code} {patch_resp.text}")
            else:
                print(f"[agent] Price already set to {args.price} NPR/hour")
            print(f"[agent] You can now run: labhya-agent run")
        else:
            print(f"[agent] No matching GPU found, creating new GPU entry")
            resp = http(args.api, "post", "/host/gpus", json=gpu_data, headers=headers)
            resp.raise_for_status()
            gpu_id = resp.json()["id"]
            print(f"[agent] GPU registered: {gpu_id}")
            print(f"[agent] Price set to: {args.price} NPR/hour")
            print(f"[agent] You can now run: labhya-agent run")

    elif args.cmd == "templates":
        templates = get_available_templates()
        if args.format == "json":
            print(json.dumps(templates, indent=2))
        else:
            print("🚀 Available Docker Templates:")
            print("=" * 50)
            for template_id, template in templates.items():
                print(f"\n📦 {template['name']} ({template_id})")
                print(f"   {template['description']}")
                print(f"   📏 Size: {template['size']}")
                print(f"   ⏱️  Startup: {template['startup_time']}")
                print("   ✨ Features:")
                for feature in template['features']:
                    print(f"      • {feature}")
            print(f"\n💡 Usage: Students can choose template when creating sessions")
            print(f"   Default: 'ml' (ML-Ready Environment)")

    elif args.cmd == "run":
        token = args.token
        refresh_tok = None
        if not token:
            username = args.username or input("Host email: ").strip()
            pwd = args.password or getpass.getpass(f"Password for {username}: ")
            token, refresh_tok = fetch_tokens(args.api, username, pwd)

        node_id = args.node

        if not node_id:
                # auto-register a new node
                hostname = os.uname().nodename if hasattr(os, "uname") else "host"
                headers = {"Authorization": f"Bearer {token}"}
                resp = http(args.api, "post", "/agent/nodes", json={"hostname": hostname}, headers=headers)
                resp.raise_for_status()
                node_id = resp.json()["nodeId"]
                print(f"[agent] Auto-registered node {node_id}")

        cfg = {"id": node_id, "token": token}
        if refresh_tok:
            cfg["refresh"] = refresh_tok
        run_poll_loop(args.api, cfg)


if __name__ == "__main__":
    main() 