"""
Direct script to copy Tesseract and Poppler to _internal directory.
This will show all output and verify the copy was successful.

Run this script directly: python copy_deps_to_internal.py
"""
import os
import shutil
import sys
from pathlib import Path

# Force output to be visible
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# Define paths
project_root = Path(__file__).parent
internal_dir = project_root / "dist" / "TransMatch" / "_internal"

print("=" * 70)
print("Copying Tesseract and Poppler to _internal directory")
print("=" * 70)
print()

# Check if _internal exists
if not internal_dir.exists():
    print(f"ERROR: _internal directory not found at: {internal_dir}")
    print("Please build the project first using: python build_and_package.py")
    sys.exit(1)

print(f"Target directory: {internal_dir}")
print()

# ========== Copy Poppler ==========
print("-" * 70)
print("Copying Poppler...")
print("-" * 70)

poppler_src = Path(r"D:\CHIANWEILON\Software_Dev\TransMatch\Development\libs\poppler-24.08.0")
poppler_dst = internal_dir / "poppler"

print(f"Source: {poppler_src}")
print(f"Source exists: {poppler_src.exists()}")
print(f"Destination: {poppler_dst}")

if not poppler_src.exists():
    print("ERROR: Poppler source directory not found!")
    sys.exit(1)

try:
    if poppler_dst.exists():
        print("Removing existing poppler folder...")
        shutil.rmtree(poppler_dst)
    
    print("Copying poppler folder (this may take a while)...")
    shutil.copytree(poppler_src, poppler_dst)
    print("✓ Poppler copied successfully!")
    
    # Verify
    pdftoppm = poppler_dst / "Library" / "bin" / "pdftoppm.exe"
    pdfinfo = poppler_dst / "Library" / "bin" / "pdfinfo.exe"
    if pdftoppm.exists():
        print(f"  ✓ Verified: {pdftoppm.name} exists")
    else:
        print(f"  ✗ WARNING: {pdftoppm.name} not found after copy!")
    if pdfinfo.exists():
        print(f"  ✓ Verified: {pdfinfo.name} exists")
    else:
        print(f"  ✗ WARNING: {pdfinfo.name} not found after copy!")
        
except Exception as e:
    print(f"ERROR copying Poppler: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# ========== Copy Tesseract ==========
print("-" * 70)
print("Copying Tesseract...")
print("-" * 70)

tesseract_src = Path(r"C:\Program Files\Tesseract-OCR")
tesseract_dst = internal_dir / "tesseract"

print(f"Source: {tesseract_src}")
print(f"Source exists: {tesseract_src.exists()}")
tesseract_exe_src = tesseract_src / "tesseract.exe"
print(f"tesseract.exe exists: {tesseract_exe_src.exists()}")
print(f"Destination: {tesseract_dst}")

if not tesseract_src.exists() or not tesseract_exe_src.exists():
    print("ERROR: Tesseract source directory or tesseract.exe not found!")
    sys.exit(1)

try:
    if tesseract_dst.exists():
        print("Removing existing tesseract folder...")
        shutil.rmtree(tesseract_dst)
    
    os.makedirs(tesseract_dst, exist_ok=True)
    
    print("Copying tesseract.exe...")
    shutil.copy2(tesseract_exe_src, tesseract_dst / "tesseract.exe")
    print("✓ tesseract.exe copied")
    
    # Copy all DLL files from Tesseract directory (required for tesseract.exe to run)
    print("Copying Tesseract DLLs...")
    dll_count = 0
    for dll_file in tesseract_src.glob("*.dll"):
        try:
            shutil.copy2(dll_file, tesseract_dst / dll_file.name)
            dll_count += 1
        except Exception as e:
            print(f"  ⚠ Failed to copy {dll_file.name}: {e}")
    if dll_count > 0:
        print(f"✓ Copied {dll_count} DLL file(s)")
    else:
        print("⚠ WARNING: No DLL files found or copied")
    
    # Copy tessdata
    tessdata_src = tesseract_src / "tessdata"
    if tessdata_src.exists():
        print("Copying tessdata folder (this may take a while)...")
        shutil.copytree(tessdata_src, tesseract_dst / "tessdata")
        print("✓ tessdata folder copied")
    else:
        print("⚠ WARNING: tessdata folder not found in source")
    
    # Verify
    tesseract_exe_dst = tesseract_dst / "tesseract.exe"
    if tesseract_exe_dst.exists():
        print(f"  ✓ Verified: tesseract.exe exists")
    else:
        print(f"  ✗ WARNING: tesseract.exe not found after copy!")
        
except Exception as e:
    print(f"ERROR copying Tesseract: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# ========== Final Verification ==========
print("=" * 70)
print("Final Verification")
print("=" * 70)

required_files = [
    (internal_dir / "poppler" / "Library" / "bin" / "pdftoppm.exe", "pdftoppm.exe"),
    (internal_dir / "poppler" / "Library" / "bin" / "pdfinfo.exe", "pdfinfo.exe"),
    (internal_dir / "tesseract" / "tesseract.exe", "tesseract.exe"),
]

all_ok = True
for file_path, name in required_files:
    if file_path.exists():
        print(f"✓ {name} - OK")
    else:
        print(f"✗ {name} - MISSING at {file_path}")
        all_ok = False

print()
if all_ok:
    print("=" * 70)
    print("SUCCESS! All files copied and verified.")
    print("=" * 70)
    print(f"\nFolders are now in: {internal_dir}")
    print("  - poppler/Library/bin/pdftoppm.exe")
    print("  - poppler/Library/bin/pdfinfo.exe")
    print("  - tesseract/tesseract.exe")
    print("  - tesseract/tessdata/")
else:
    print("=" * 70)
    print("WARNING: Some files are missing. Please check the errors above.")
    print("=" * 70)
    sys.exit(1)
