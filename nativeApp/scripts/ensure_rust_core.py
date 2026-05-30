"""
Build/install terrasim_core (Rust extension) into the active venv if missing.

Usage (from nativeApp, with venv activated):
    python scripts/ensure_rust_core.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    try:
        import terrasim_core  # noqa: F401
        print("[OK] terrasim_core sudah terpasang.")
        return 0
    except ImportError:
        pass

    native_app = Path(__file__).resolve().parents[1]
    rust_dir = native_app / "engine" / "rust_core"
    if not (rust_dir / "Cargo.toml").is_file():
        print(f"[ERROR] Cargo.toml tidak ditemukan di {rust_dir}")
        return 1

    venv = os.environ.get("VIRTUAL_ENV")
    if not venv:
        candidate = native_app / "venv"
        if (candidate / "Scripts" / "python.exe").is_file():
            venv = str(candidate)
            os.environ["VIRTUAL_ENV"] = venv

    if not venv:
        print(
            "[ERROR] Aktifkan virtualenv nativeApp terlebih dahulu:\n"
            "  .\\venv\\Scripts\\activate"
        )
        return 1

    print("[BUILD] terrasim_core belum ada — menjalankan maturin develop --release...")
    cmd = [sys.executable, "-m", "maturin", "develop", "--release"]
    result = subprocess.run(cmd, cwd=rust_dir)
    if result.returncode != 0:
        print(
            "[ERROR] Build gagal. Pastikan Rust terpasang: https://rustup.rs\n"
            "Lalu jalankan ulang script ini."
        )
        return result.returncode

    try:
        import terrasim_core  # noqa: F401
        print("[OK] terrasim_core berhasil di-build dan terpasang.")
        return 0
    except ImportError:
        print("[ERROR] Build selesai tetapi import terrasim_core masih gagal.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
