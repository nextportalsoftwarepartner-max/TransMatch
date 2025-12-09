"""
Quick script to copy external folders to dist/TransMatch/
Run this after building if build_and_package.py didn't copy them.
"""

import os
import shutil
import sys
from pathlib import Path

def main():
    project_root = Path(__file__).parent
    target_dir = project_root / "dist" / "TransMatch"
    internal_dir = target_dir / "_internal"
    
    if not target_dir.exists():
        print(f"✗ Target directory not found: {target_dir}", file=sys.stderr)
        print("  Please build the project first using: python build_and_package.py", file=sys.stderr)
        return 1
    
    if not internal_dir.exists():
        print(f"✗ _internal directory not found: {internal_dir}", file=sys.stderr)
        print("  Please build the project first using: python build_and_package.py", file=sys.stderr)
        return 1
    
    print(f"Copying external folders to: {internal_dir}")
    print("-" * 60)
    
    # Copy ml_libraries from project root
    ml_lib_src = project_root / "ml_libraries"
    ml_lib_dst = internal_dir / "ml_libraries"
    if ml_lib_src.exists():
        try:
            if ml_lib_dst.exists():
                shutil.rmtree(ml_lib_dst)
            shutil.copytree(ml_lib_src, ml_lib_dst)
            print(f"  ✓ Copied ml_libraries")
        except Exception as e:
            print(f"  ✗ Failed to copy ml_libraries: {e}")
    else:
        print(f"  ⚠ ml_libraries not found at {ml_lib_src}")
    
    # Copy templates from project root
    templates_src = project_root / "templates"
    templates_dst = internal_dir / "templates"
    if templates_src.exists():
        try:
            if templates_dst.exists():
                shutil.rmtree(templates_dst)
            shutil.copytree(templates_src, templates_dst)
            print(f"  ✓ Copied templates")
        except Exception as e:
            print(f"  ✗ Failed to copy templates: {e}")
    else:
        print(f"  ⚠ templates not found at {templates_src}")
    
    # Copy Poppler from actual location
    poppler_src = Path(r"D:\CHIANWEILON\Software_Dev\TransMatch\Development\libs\poppler-24.08.0")
    poppler_dst = internal_dir / "poppler"
    if poppler_src.exists():
        try:
            if poppler_dst.exists():
                shutil.rmtree(poppler_dst)
            shutil.copytree(poppler_src, poppler_dst)
            print(f"  ✓ Copied poppler from: {poppler_src}")
        except Exception as e:
            print(f"  ✗ Failed to copy poppler: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"  ⚠ Poppler source not found at: {poppler_src}")
        # Fallback to project root poppler if it exists
        poppler_fallback = project_root / "poppler"
        if poppler_fallback.exists():
            try:
                if poppler_dst.exists():
                    shutil.rmtree(poppler_dst)
                shutil.copytree(poppler_fallback, poppler_dst)
                print(f"  ✓ Copied poppler (fallback)")
            except Exception as e:
                print(f"  ✗ Failed to copy poppler (fallback): {e}")
    
    # Copy Tesseract from actual location
    tesseract_src = Path(r"C:\Program Files\Tesseract-OCR")
    tesseract_dst = internal_dir / "tesseract"
    if tesseract_src.exists() and (tesseract_src / "tesseract.exe").exists():
        try:
            if tesseract_dst.exists():
                shutil.rmtree(tesseract_dst)
            os.makedirs(tesseract_dst, exist_ok=True)
            
            # Copy tesseract.exe
            shutil.copy2(tesseract_src / "tesseract.exe", tesseract_dst / "tesseract.exe")
            print(f"  ✓ Copied tesseract.exe")
            
            # Copy all DLL files from Tesseract directory (required for tesseract.exe to run)
            print(f"  Copying Tesseract DLLs...")
            dll_count = 0
            for dll_file in tesseract_src.glob("*.dll"):
                try:
                    shutil.copy2(dll_file, tesseract_dst / dll_file.name)
                    dll_count += 1
                except Exception as e:
                    print(f"    ⚠ Failed to copy {dll_file.name}: {e}")
            if dll_count > 0:
                print(f"  ✓ Copied {dll_count} DLL file(s)")
            else:
                print(f"  ⚠ No DLL files found or copied")
            
            # Copy tessdata folder if it exists
            tessdata_src = tesseract_src / "tessdata"
            tessdata_dst = tesseract_dst / "tessdata"
            if tessdata_src.exists():
                shutil.copytree(tessdata_src, tessdata_dst)
                print(f"  ✓ Copied tessdata folder")
            
            print(f"  ✓ Tesseract copied from: {tesseract_src}")
        except Exception as e:
            print(f"  ✗ Failed to copy Tesseract: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"  ⚠ Tesseract source not found at: {tesseract_src}")
        # Fallback to project root tesseract if it exists
        tesseract_fallback = project_root / "tesseract"
        if tesseract_fallback.exists():
            try:
                if tesseract_dst.exists():
                    shutil.rmtree(tesseract_dst)
                shutil.copytree(tesseract_fallback, tesseract_dst)
                print(f"  ✓ Copied tesseract (fallback)")
            except Exception as e:
                print(f"  ✗ Failed to copy tesseract (fallback): {e}")
    
    print("\n" + "=" * 60)
    print("Copy Complete!")
    print("=" * 60)
    
    # Verify
    print("\n" + "=" * 60)
    print("Verifying copied folders:")
    print("-" * 60)
    
    required_folders = ["ml_libraries", "tesseract", "poppler", "templates"]
    for folder_name in required_folders:
        folder_path = internal_dir / folder_name
        if folder_path.exists():
            print(f"  ✓ {folder_name}/")
            # Check for key files
            if folder_name == "tesseract":
                tesseract_exe = folder_path / "tesseract.exe"
                if tesseract_exe.exists():
                    print(f"    ✓ tesseract.exe found")
                else:
                    print(f"    ✗ tesseract.exe missing")
            elif folder_name == "poppler":
                poppler_bin = folder_path / "Library" / "bin"
                if poppler_bin.exists():
                    if (poppler_bin / "pdftoppm.exe").exists():
                        print(f"    ✓ pdftoppm.exe found")
                    else:
                        print(f"    ✗ pdftoppm.exe missing")
                    if (poppler_bin / "pdfinfo.exe").exists():
                        print(f"    ✓ pdfinfo.exe found")
                    else:
                        print(f"    ✗ pdfinfo.exe missing")
                else:
                    print(f"    ✗ Library/bin folder missing")
        else:
            print(f"  ✗ {folder_name}/ (not found)")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
