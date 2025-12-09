# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
try:
    from PyInstaller.utils.hooks import collect_delvewheel_libs_directory
    HAS_DELVEWHEEL = True
except ImportError:
    HAS_DELVEWHEEL = False

block_cipher = None

# Collect all files inside a folder recursively
def collect_folder(folder_name):
    items = []
    for root, _, files in os.walk(folder_name):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, start='.')
            target_dir = os.path.dirname(rel_path)
            items.append((full_path, target_dir))
    return items

def collect_hiddenimports_from(folder, module_prefix):
    hidden = []
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                rel_path = os.path.relpath(os.path.join(root, file), start=folder)
                modname = rel_path.replace('\\', '.').replace('/', '.').replace('.py', '')
                hidden.append(f"{module_prefix}.{modname}")
    return hidden

# Collect from all key folders
hiddenimports = (
    collect_hiddenimports_from('transaction/pdf_extraction_method', 'transaction.pdf_extraction_method') +
    collect_hiddenimports_from('administration', 'administration') +
    collect_hiddenimports_from('report', 'report') +
    [
        'ocrmypdf', 'pytesseract', 'pdf2image', 'fitz', 'pdfplumber', 'opencv_python_headless',
    ] +
    # Collect all scipy submodules (including compiled extensions)
    list(collect_submodules('scipy')) +
    # Collect all sklearn submodules
    list(collect_submodules('sklearn')) +
    # Collect all transformers submodules (required by sentence_transformers)
    list(collect_submodules('transformers')) +
    # Explicitly include critical compiled extensions
    [
        'scipy._cyutility',
        'scipy.sparse._csparsetools',
        'numpy.core._multiarray_umath',
        # transformers submodules that might be missed
        'transformers.models',
        'transformers.models.auto',
        'transformers.utils',
    ]
)

# Note: External folders (ml_libraries, tesseract, poppler) are NOT included in datas
# because we want them as separate folders next to the exe, not bundled inside.
# The build_and_package.py script will copy them.

# Collect scipy and sklearn binaries (compiled extensions) - required for sentence_transformers
all_binaries = []
all_datas = []

if HAS_DELVEWHEEL:
    # Use delvewheel collection if available (PyInstaller 5.13+)
    try:
        scipy_datas, scipy_binaries = collect_delvewheel_libs_directory('scipy')
        sklearn_datas, sklearn_binaries = collect_delvewheel_libs_directory('sklearn')
        all_binaries = scipy_binaries + sklearn_binaries
        all_datas = scipy_datas + sklearn_datas
    except Exception:
        pass  # Fall back to automatic detection

# Collect transformers data files (required for lazy loading)
transformers_datas = collect_data_files('transformers', include_py_files=True)

a = Analysis(
    ['login_screen.py'],
    pathex=['.'],
    binaries=all_binaries,  # Include scipy and sklearn binaries if collected
    datas=[
        ('LoadingIcon.gif', '.'),
        ('.env', '.'),
        ('TransMatch_Logo.png', '.'),
    ] + collect_data_files('ocrmypdf', include_py_files=True) + all_datas + transformers_datas,
    hiddenimports=hiddenimports,  # Already includes scipy, sklearn, and transformers submodules
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Note: sentence_transformers is now packaged separately, so we exclude it from the main bundle
        # but it will be included via ml_libraries_data if build_ml_libraries.py was run
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Use onedir mode instead of onefile for lighter EXE with external folders
# In onedir mode, EXE only contains the bootloader and scripts
# All other files (binaries, zipfiles, datas) go into COLLECT
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # Binaries go to COLLECT, not EXE
    name='TransMatch',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False
)

# Create COLLECT to bundle everything in a folder (onedir mode)
# This creates dist/TransMatch/ with the exe and all dependencies
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TransMatch'
)

# Note: External folders (ml_libraries, tesseract, poppler) should be copied to 
# dist/TransMatch/ next to TransMatch.exe after build. 
# Use build_and_package.py which handles this automatically.
