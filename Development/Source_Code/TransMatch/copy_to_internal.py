"""Copy tesseract and poppler to _internal directory"""
import os
import shutil
from pathlib import Path

# Paths
internal_dir = Path(r"d:\CHIANWEILON\Software_Dev\TransMatch\Development\Source_Code\TransMatch\dist\TransMatch\_internal")
poppler_src = Path(r"D:\CHIANWEILON\Software_Dev\TransMatch\Development\libs\poppler-24.08.0")
tesseract_src = Path(r"C:\Program Files\Tesseract-OCR")

print(f"Internal dir: {internal_dir}")
print(f"Internal dir exists: {internal_dir.exists()}")
print()

# Copy Poppler
poppler_dst = internal_dir / "poppler"
print(f"Copying Poppler...")
print(f"  Source: {poppler_src}")
print(f"  Source exists: {poppler_src.exists()}")
print(f"  Destination: {poppler_dst}")

if poppler_src.exists():
    try:
        if poppler_dst.exists():
            print("  Removing existing poppler...")
            shutil.rmtree(poppler_dst)
        print("  Copying...")
        shutil.copytree(poppler_src, poppler_dst)
        print("  ✓ Poppler copied successfully")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
else:
    print("  ✗ Poppler source not found")
print()

# Copy Tesseract
tesseract_dst = internal_dir / "tesseract"
print(f"Copying Tesseract...")
print(f"  Source: {tesseract_src}")
print(f"  Source exists: {tesseract_src.exists()}")
print(f"  tesseract.exe exists: {(tesseract_src / 'tesseract.exe').exists()}")
print(f"  Destination: {tesseract_dst}")

if tesseract_src.exists() and (tesseract_src / "tesseract.exe").exists():
    try:
        if tesseract_dst.exists():
            print("  Removing existing tesseract...")
            shutil.rmtree(tesseract_dst)
        os.makedirs(tesseract_dst, exist_ok=True)
        print("  Copying tesseract.exe...")
        shutil.copy2(tesseract_src / "tesseract.exe", tesseract_dst / "tesseract.exe")
        print("  ✓ tesseract.exe copied")
        
        tessdata_src = tesseract_src / "tessdata"
        if tessdata_src.exists():
            print("  Copying tessdata...")
            shutil.copytree(tessdata_src, tesseract_dst / "tessdata")
            print("  ✓ tessdata copied")
        
        print("  ✓ Tesseract copied successfully")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
else:
    print("  ✗ Tesseract source not found")
print()

# Verify
print("Verification:")
if (internal_dir / "poppler" / "Library" / "bin" / "pdftoppm.exe").exists():
    print("  ✓ pdftoppm.exe found")
else:
    print("  ✗ pdftoppm.exe missing")

if (internal_dir / "tesseract" / "tesseract.exe").exists():
    print("  ✓ tesseract.exe found")
else:
    print("  ✗ tesseract.exe missing")

print("\nDone!")
