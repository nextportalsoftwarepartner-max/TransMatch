"""
Build script that packages ML libraries and then builds the exe.

This script:
1. Runs build_ml_libraries.py to package ML libraries
2. Runs PyInstaller to build the exe (onedir mode)
3. Copies external folders (ml_libraries, tesseract, poppler, templates) to dist/TransMatch/

Usage:
    python build_and_package.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def copy_folder(src: Path, dst: Path, folder_name: str) -> bool:
    """Copy a folder from source to destination, removing existing if present."""
    if not src.exists():
        print(f"⚠ {folder_name} folder not found at {src}, skipping copy")
        return False
    
    try:
        if dst.exists():
            print(f"  Removing existing {folder_name}...")
            shutil.rmtree(dst)
        print(f"  Copying {folder_name} (this may take a while)...")
        shutil.copytree(src, dst)
        print(f"✓ Copied {folder_name} to {dst}")
        
        # Verify key files were copied
        if folder_name == "poppler":
            pdftoppm = dst / "Library" / "bin" / "pdftoppm.exe"
            if pdftoppm.exists():
                print(f"  ✓ Verified: pdftoppm.exe exists")
            else:
                print(f"  ✗ WARNING: pdftoppm.exe not found after copy!")
        
        return True
    except Exception as e:
        print(f"✗ Failed to copy {folder_name}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("TransMatch Build and Package Script")
    print("=" * 60)
    
    project_root = Path(__file__).parent
    
    # Step 1: Package ML libraries
    print("\n[Step 1/4] Packaging ML libraries...")
    print("-" * 60)
    result = subprocess.run(
        [sys.executable, "build_ml_libraries.py"],
        cwd=project_root
    )
    if result.returncode != 0:
        print("\n✗ Failed to package ML libraries")
        return 1
    print("✓ ML libraries packaged successfully")
    
    # Step 2: Build with PyInstaller
    print("\n[Step 2/4] Building exe with PyInstaller...")
    print("-" * 60)
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "TransMatch.spec", "--clean", "--noconfirm"],
        cwd=project_root
    )
    if result.returncode != 0:
        print("\n✗ PyInstaller build failed")
        return 1
    print("✓ PyInstaller build completed")
    
    # Step 3: Locate the dist directory
    print("\n[Step 3/4] Locating build output...")
    print("-" * 60)
    dist_dir = project_root / "dist"
    exe_in_subdir = dist_dir / "TransMatch" / "TransMatch.exe"
    exe_in_dist = dist_dir / "TransMatch.exe"
    
    # Determine target directory (onedir mode uses dist/TransMatch/)
    if exe_in_subdir.exists():
        target_dir = dist_dir / "TransMatch"
        print(f"✓ Found onedir build at {target_dir}")
    elif exe_in_dist.exists():
        target_dir = dist_dir
        print(f"✓ Found onefile build at {target_dir}")
    else:
        print("✗ Could not find TransMatch.exe in dist folder")
        print("  Expected locations:")
        print(f"    - {exe_in_subdir}")
        print(f"    - {exe_in_dist}")
        return 1
    
    # Step 4: Copy external folders to _internal directory
    print("\n[Step 4/4] Copying external folders to _internal...")
    print("-" * 60)
    
    # In onedir mode, _internal is where PyInstaller puts bundled files
    internal_dir = target_dir / "_internal"
    if not internal_dir.exists():
        print(f"✗ _internal directory not found at: {internal_dir}")
        return 1
    
    # Try to run the batch file first (it's more reliable)
    copy_bat = project_root / "copy_deps.bat"
    if copy_bat.exists():
        print("Running copy_deps.bat to copy dependencies...")
        print("-" * 60)
        result = subprocess.run(
            [str(copy_bat)],
            cwd=project_root,
            shell=True
        )
        if result.returncode == 0:
            print("✓ Dependencies copied via batch file")
            # Verify the files exist
            pdftoppm = internal_dir / "poppler" / "Library" / "bin" / "pdftoppm.exe"
            tesseract_exe = internal_dir / "tesseract" / "tesseract.exe"
            if pdftoppm.exists() and tesseract_exe.exists():
                print("✓ Verified: All dependencies copied successfully")
                return 0
            else:
                print("⚠ Batch file ran but files not found, trying Python copy...")
        else:
            print("⚠ Batch file failed, trying Python copy...")
    
    # Fallback to Python copy if batch file doesn't exist or failed
    copied_count = 0
    
    # Copy ml_libraries from project root
    print(f"\nCopying ml_libraries...")
    print(f"  Source: {project_root / 'ml_libraries'}")
    ml_lib_src = project_root / "ml_libraries"
    ml_lib_dst = internal_dir / "ml_libraries"
    if ml_lib_src.exists():
        if copy_folder(ml_lib_src, ml_lib_dst, "ml_libraries"):
            copied_count += 1
            print(f"  ✓ ML libraries copied from: {ml_lib_src}")
    else:
        print(f"  ⚠ ml_libraries source not found at: {ml_lib_src}")
        print(f"  Note: Run build_ml_libraries.py first to create ml_libraries folder")
    
    # Copy templates from project root
    templates_src = project_root / "templates"
    templates_dst = internal_dir / "templates"
    if copy_folder(templates_src, templates_dst, "templates"):
        copied_count += 1
    
    # Copy Poppler from actual location
    poppler_src = Path(r"D:\CHIANWEILON\Software_Dev\TransMatch\Development\libs\poppler-24.08.0")
    poppler_dst = internal_dir / "poppler"
    print(f"\nCopying Poppler...")
    print(f"  Source: {poppler_src}")
    print(f"  Source exists: {poppler_src.exists()}")
    if poppler_src.exists():
        if copy_folder(poppler_src, poppler_dst, "poppler"):
            copied_count += 1
            print(f"  ✓ Poppler copied from: {poppler_src}")
    else:
        print(f"⚠ Poppler source not found at: {poppler_src}")
        # Fallback to project root poppler if it exists
        poppler_fallback = project_root / "poppler"
        if poppler_fallback.exists():
            if copy_folder(poppler_fallback, poppler_dst, "poppler (fallback)"):
                copied_count += 1
    
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
            
            print(f"✓ Tesseract copied from: {tesseract_src}")
            copied_count += 1
        except Exception as e:
            print(f"✗ Failed to copy Tesseract: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"⚠ Tesseract source not found at: {tesseract_src}")
        # Fallback to project root tesseract if it exists
        tesseract_fallback = project_root / "tesseract"
        if tesseract_fallback.exists():
            if copy_folder(tesseract_fallback, tesseract_dst, "tesseract (fallback)"):
                copied_count += 1
    
    print(f"\n✓ Copied {copied_count} external folders/dependencies")
    
    # Summary
    print("\n" + "=" * 60)
    print("Build Complete!")
    print("=" * 60)
    print(f"\nExecutable location: {target_dir / 'TransMatch.exe'}")
    print(f"\nExternal folders copied to: {internal_dir}")
    
    # Verify all required folders in _internal
    required_folders = ["ml_libraries", "tesseract", "poppler", "templates"]
    for folder_name in required_folders:
        folder_path = internal_dir / folder_name
        if folder_path.exists():
            print(f"  ✓ {folder_name}/")
            # Check for key files
            if folder_name == "tesseract":
                if (folder_path / "tesseract.exe").exists():
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
    sys.exit(main())
