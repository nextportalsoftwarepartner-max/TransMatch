import os
import shutil
from pathlib import Path

project_root = Path(__file__).parent
target_dir = project_root / "dist" / "TransMatch"

print(f"Target: {target_dir}")
print(f"Exists: {target_dir.exists()}")

# Test Poppler copy
poppler_src = Path(r"D:\CHIANWEILON\Software_Dev\TransMatch\Development\libs\poppler-24.08.0")
poppler_dst = target_dir / "poppler"

print(f"\nPoppler source: {poppler_src}")
print(f"Poppler source exists: {poppler_src.exists()}")
print(f"Poppler dest: {poppler_dst}")

if poppler_src.exists():
    try:
        if poppler_dst.exists():
            print("Removing existing poppler...")
            shutil.rmtree(poppler_dst)
        print("Copying poppler...")
        shutil.copytree(poppler_src, poppler_dst)
        print("✓ Poppler copied successfully")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

# Test Tesseract copy
tesseract_src = Path(r"C:\Program Files\Tesseract-OCR")
tesseract_dst = target_dir / "tesseract"

print(f"\nTesseract source: {tesseract_src}")
print(f"Tesseract source exists: {tesseract_src.exists()}")
print(f"Tesseract exe exists: {(tesseract_src / 'tesseract.exe').exists()}")
print(f"Tesseract dest: {tesseract_dst}")

if tesseract_src.exists() and (tesseract_src / "tesseract.exe").exists():
    try:
        if tesseract_dst.exists():
            print("Removing existing tesseract...")
            shutil.rmtree(tesseract_dst)
        os.makedirs(tesseract_dst, exist_ok=True)
        print("Copying tesseract.exe...")
        shutil.copy2(tesseract_src / "tesseract.exe", tesseract_dst / "tesseract.exe")
        print("✓ tesseract.exe copied")
        
        tessdata_src = tesseract_src / "tessdata"
        if tessdata_src.exists():
            print("Copying tessdata...")
            shutil.copytree(tessdata_src, tesseract_dst / "tessdata")
            print("✓ tessdata copied")
        print("✓ Tesseract copied successfully")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

print("\nDone!")
