# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('D:\\TerraSim\\nativeApp\\assets', 'assets')]
binaries = [('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\ifdlg100.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\impi.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\libfabric.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\libhwloc-15.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\libicaf.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\libifcoremd.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\libifcoremdd.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\libifcorert.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\libifcorertd.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\libifportmd.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\libimalloc.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\libiomp5md.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\libiomp5md_db.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\libiompstubs5md.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\libircmd.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\libirngmd.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\libmmd.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\libmmdd.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\libmpi_ilp64.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_avx2.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_avx512.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_blacs_ilp64.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_blacs_intelmpi_ilp64.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_blacs_intelmpi_lp64.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_blacs_lp64.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_blacs_msmpi_ilp64.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_blacs_msmpi_lp64.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_cdft_core.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_core.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_def.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_intel_thread.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_mc3.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_rt.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_scalapack_ilp64.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_scalapack_lp64.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_sequential.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_tbb_thread.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_vml_avx2.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_vml_avx512.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_vml_cmpt.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_vml_def.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\mkl_vml_mc3.2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\omptarget.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\omptarget.rtl.level0.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\omptarget.rtl.opencl.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\omptarget.rtl.unified_runtime.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\omptarget.sycl.wrap.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\onnxruntime.1.12.22.721.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\qkmalloc.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\svml_dispmd.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\tbb12.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\tbbbind.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\tbbbind_2_0.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\tbbbind_2_5.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\tbbmalloc.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\tbbmalloc_proxy.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\tcm.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\tcm_debug.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\umf.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\umfd.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\ur_adapter_level_zero.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\ur_adapter_level_zero_v2.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\ur_adapter_opencl.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\ur_loader.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\ur_win_proxy_loader.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\ur_win_proxy_loaderd.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\xptifw.dll', '.'), ('D:\\TerraSim\\nativeApp\\venv\\Library\\bin\\xptifwd.dll', '.')]
hiddenimports = ['pypardiso', 'terrasim_core', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'matplotlib.backends.backend_qtagg', 'numpy', 'scipy.spatial.transform._rotation_groups']
hiddenimports += collect_submodules('pypardiso')
tmp_ret = collect_all('pypardiso')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TerraSim',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:\\TerraSim\\nativeApp\\assets\\Logo.png'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TerraSim',
)
