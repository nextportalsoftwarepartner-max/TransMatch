# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files

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
    ['ocrmypdf', 'pytesseract', 'pdf2image', 'fitz', 'pdfplumber', 'opencv_python_headless']
)

# Note: External folders (ml_libraries, tesseract, poppler) are NOT included in datas
# because we want them as separate folders next to the exe, not bundled inside.
# The build_and_package.py script will copy them.

a = Analysis(
    ['login_screen.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('LoadingIcon.gif', '.'),
        ('.env', '.'),
        ('TransMatch_Logo.png', '.'),
    ] + collect_data_files('ocrmypdf', include_py_files=True),
    hiddenimports=hiddenimports,
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
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
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
