# build_exe.py
import PyInstaller.__main__
import os
import sys

# Paths and Assets
current_dir = os.path.dirname(os.path.abspath(__file__))
assets_path = os.path.join(current_dir, 'assets')

# Explicitly collect all DLLs from Intel bin folder (Critical for Pardiso/AMD)
# Our venv is now "Pure" and self-contained with all necessary Intel runtimes.
mkl_bin_path = os.path.join(current_dir, 'venv', 'Library', 'bin')
intel_binaries = []
if os.path.exists(mkl_bin_path):
    print(f"Collecting MKL and Intel binaries from: {mkl_bin_path}")
    for f in os.listdir(mkl_bin_path):
        if f.lower().endswith('.dll'):
            print(f"  + {f}")
            intel_binaries.append(f'--add-binary={os.path.join(mkl_bin_path, f)};.')
else:
    print("WARNING: Intel binaries NOT found in venv/Library/bin. Pardiso will fail.")

# PyInstaller parameters
params = [
    'main.py',                      # Entry point
    '--name=TerraSim',              # Name of output EXE
    '--onedir',                     # Package as a directory (faster startup)
    '--noconsole',                  # No command prompt (windowed)
    f'--add-data={assets_path};assets', # Bundle style/icons
] + intel_binaries + [
    '--icon=' + os.path.join(assets_path, 'Logo.png'), # EXE Icon
    '--clean',                      # Clean cache before build
    
    # Hidden imports often needed for scientific/UI stacks
    '--hidden-import=pypardiso',
    '--collect-all=pypardiso',
    '--collect-submodules=pypardiso',
    '--hidden-import=terrasim_core',
    '--hidden-import=PySide6.QtCore',
    '--hidden-import=PySide6.QtGui',
    '--hidden-import=PySide6.QtWidgets',
    '--hidden-import=matplotlib.backends.backend_qtagg',
    '--hidden-import=numpy',
    '--hidden-import=scipy.spatial.transform._rotation_groups',
    
    # Metadata
    '--version-file=version_info.txt' if os.path.exists('version_info.txt') else None
]

# Filter out None values
params = [p for p in params if p is not None]

if __name__ == "__main__":
    print("Starting build process...")
    try:
        PyInstaller.__main__.run(params)
        print("\nBuild completed successfully!")
        print(f"Executable can be found in: {os.path.join(current_dir, 'dist')}")
    except Exception as e:
        print(f"\nBuild failed: {e}")
        sys.exit(1)
