## frontend
cd d:\TerraSim\frontend
npm run dev

## backend
cd d:\TerraSim
uvicorn backend.main:app --reload --port 8010

## native
cd d:\Program\TerraSim\nativeApp
.\venv\Scripts\activate
pip install -r requirements.txt
python scripts\ensure_rust_core.py
python dev_runner.py

## rust extension (wajib sekali, atau otomatis lewat dev_runner)
cd d:\Program\TerraSim\nativeApp
.\venv\Scripts\activate
python scripts\ensure_rust_core.py
# manual alternatif:
# cd engine\rust_core
# maturin develop --release

## rust compiler (wheel saja)
cd d:\Program\TerraSim\nativeApp\engine\rust_core
maturin build --release

## build .exe
cd d:\TerraSim\nativeApp
.\venv\Scripts\activate
pip install -r requirements.txt
python build_exe.py

## serial number
HKEY_CURRENT_USER\Software\DaharEngineer\TerraSim


