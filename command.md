## frontend
cd d:\TerraSim\frontend
npm run dev

## backend
cd d:\TerraSim
uvicorn backend.main:app --reload --port 8010

## native
cd d:\TerraSim\nativeApp
.\venv\Scripts\activate
python dev_runner.py

## rust compiler
cd d:\TerraSim\nativeApp\engine\rust_core
maturin build --release --out /build/wheels

## build .exe
cd d:\TerraSim\nativeApp
.\venv\Scripts\activate
pip install -r requirements.txt
python build_exe.py

## serial number
HKEY_CURRENT_USER\Software\DaharEngineer\TerraSim


