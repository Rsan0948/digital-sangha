#!/usr/bin/env python3
"""
ZDS-ID: TOOL-501 (Unified Entry Point)
Digital Sangha - Master Orchestrator

This script handles the full lifecycle of the Digital Sangha application:
1. Environment detection & dependency check.
2. Database migrations (alembic upgrade head, unless --skip-migrations).
3. Backend launch (FastAPI).
4. Frontend launch (Vite or Served Build).
5. Desktop launch (Electron).
"""

import os
import sys
import subprocess
import time
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DESKTOP_DIR = PROJECT_ROOT / "desktop"

def get_python():
    """Detect the correct python executable."""
    venv_py = PROJECT_ROOT / ".venv" / "bin" / "python"
    if venv_py.exists():
        return str(venv_py)
    return sys.executable

def run_migrations():
    """Run ``alembic upgrade head`` against the configured DB."""
    print("🗄️  Applying database migrations...")
    py = get_python()
    result = subprocess.run(
        [py, "-m", "alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        check=False,
    )
    if result.returncode != 0:
        print("❌ alembic upgrade failed; aborting startup.", file=sys.stderr)
        sys.exit(result.returncode)

def run_backend(port: int):
    print(f"🧘 Starting Digital Sangha Backend on port {port}...")
    py = get_python()
    return subprocess.Popen(
        [py, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=PROJECT_ROOT
    )

def run_frontend():
    print("⚡ Starting Vite Development Server...")
    return subprocess.Popen(["npm", "run", "dev"], cwd=FRONTEND_DIR)

def run_desktop():
    print("🖥️ Launching Desktop Shell...")
    subprocess.run(["npm", "start"], cwd=DESKTOP_DIR)

def main():
    parser = argparse.ArgumentParser(description="ZDS Digital Sangha Orchestrator")
    parser.add_argument("--mode", choices=["dev", "desktop", "server"], default="desktop")
    parser.add_argument("--port", type=int, default=8000, help="Backend HTTP port")
    parser.add_argument(
        "--skip-migrations",
        action="store_true",
        help="Skip running alembic upgrade head before launch (development convenience).",
    )
    args = parser.parse_args()

    if not args.skip_migrations:
        run_migrations()

    processes = []
    try:
        if args.mode == "dev":
            processes.append(run_backend(args.port))
            processes.append(run_frontend())
            print(f"\n🚀 Dev Environment Ready: http://localhost:5173 (backend on :{args.port})")
            while True: time.sleep(1)

        elif args.mode == "desktop":
            processes.append(run_backend(args.port))
            # Wait for backend health check
            time.sleep(2)
            run_desktop()

        elif args.mode == "server":
            processes.append(run_backend(args.port))
            print(f"\n🚀 Server Mode Active: http://localhost:{args.port}")
            while True: time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Shutting down Digital Sangha...")
    finally:
        for p in processes:
            p.terminate()

if __name__ == "__main__":
    main()
