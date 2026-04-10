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

cd d:\TerraSim\nativeApp\engine\rust_core
maturin build --release --out /build/wheels


## serial number
TS-ABCDE-0640D