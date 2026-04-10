# build_exe.py
import PyInstaller.__main__
import os
import sys

# Get absolute path to assets
current_dir = os.path.dirname(os.path.abspath(__file__))
assets_path = os.path.join(current_dir, 'assets')

print(f"TerraSim Build Script")
print(f"=====================")
print(f"Assets path: {assets_path}")

# PyInstaller parameters
params = [
    'main.py',                      # Entry point
    '--name=TerraSim',              # Name of output EXE
    '--onedir',                     # Package as a directory (faster startup)
    '--noconsole',                  # No command prompt (windowed)
    f'--add-data={assets_path};assets', # Bundle style/icons
    '--icon=' + os.path.join(assets_path, 'Logo.png'), # EXE Icon
    '--clean',                      # Clean cache before build
    
    # Hidden imports often needed for scientific/UI stacks
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
