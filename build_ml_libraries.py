# flake8: noqa: E501
"""Build script to download and package ML libraries for TransMatch.

This script should be run on the workstation before building the exe.
It downloads sentence-transformers and the ML model, then packages them
into a folder that will be included with the distribution.

Usage:
    python build_ml_libraries.py
"""

import sys
import subprocess
import sysconfig
import shutil
import time
import stat
import os
from pathlib import Path

# Configuration
ML_LIBRARY_NAME = "sentence-transformers"
ML_MODEL_NAME = "all-MiniLM-L6-v2"
OUTPUT_FOLDER = "ml_libraries"
DIST_FOLDER = "dist"


def get_site_packages():
    """Get the site-packages directory for the current Python environment."""
    return Path(sysconfig.get_paths()["purelib"])


def remove_readonly(func, path, exc_info):
    """Helper function to remove read-only files on Windows."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def safe_rmtree(path, max_retries=3, retry_delay=1):
    """Safely remove a directory tree, handling Windows permission errors.
    
    Args:
        path: Path to the directory to remove
        max_retries: Maximum number of retry attempts
        retry_delay: Delay in seconds between retries
    
    Returns:
        True if successful, False otherwise
    """
    path = Path(path)
    if not path.exists():
        return True
    
    for attempt in range(max_retries):
        try:
            # On Windows, use onerror to handle read-only files
            if sys.platform == 'win32':
                shutil.rmtree(path, onerror=remove_readonly)
            else:
                shutil.rmtree(path)
            return True
        except PermissionError as e:
            if attempt < max_retries - 1:
                print(f"  ⚠ Permission error (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"  → Retrying in {retry_delay} second(s)...")
                time.sleep(retry_delay)
            else:
                print(f"  ✗ Failed to remove directory after {max_retries} attempts: {e}")
                print(f"  → Please close any programs that might be using files in: {path}")
                return False
        except Exception as e:
            print(f"  ✗ Error removing directory: {e}")
            return False
    
    return False


def download_and_package_libraries():
    """Download ML libraries and package them for distribution."""
    print("=" * 60)
    print("TransMatch ML Library Packaging Script")
    print("=" * 60)

    # Get paths
    project_root = Path(__file__).parent
    ml_output_dir = project_root / OUTPUT_FOLDER
    site_packages = get_site_packages()

    print(f"\nProject root: {project_root}")
    print(f"Site-packages: {site_packages}")
    print(f"Output directory: {ml_output_dir}")

    # Clean output directory
    if ml_output_dir.exists():
        print(f"\nCleaning existing {OUTPUT_FOLDER} directory...")
        if not safe_rmtree(ml_output_dir):
            print(f"  ✗ Failed to clean {OUTPUT_FOLDER} directory")
            return False
    ml_output_dir.mkdir(exist_ok=True)

    # Step 1: Install sentence-transformers if not already installed
    print(f"\n[1/5] Checking/Installing {ML_LIBRARY_NAME}...")
    try:
        import sentence_transformers  # noqa: F401  # pyright: ignore[reportMissingImports]
        print(f"  ✓ {ML_LIBRARY_NAME} is already installed")
    except ImportError:
        print(f"  → Installing {ML_LIBRARY_NAME}...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", ML_LIBRARY_NAME],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"  ✗ Failed to install {ML_LIBRARY_NAME}")
            print(f"  Error: {result.stderr}")
            return False
        print(f"  ✓ {ML_LIBRARY_NAME} installed successfully")

    # Step 2: Download and package the ML model
    print(f"\n[2/5] Downloading and packaging ML model '{ML_MODEL_NAME}'...")
    try:
        from sentence_transformers import SentenceTransformer  # pyright: ignore[reportMissingImports]

        # Download the model (this will cache it)
        print("  → Downloading model (this may take a few minutes)...")
        model = SentenceTransformer(ML_MODEL_NAME)

        # Save model directly to our output directory
        model_output = ml_output_dir / "models" / ML_MODEL_NAME
        model_output.parent.mkdir(parents=True, exist_ok=True)

        if model_output.exists():
            shutil.rmtree(model_output)

        print(f"  → Saving model to {model_output}...")
        model.save(str(model_output))
        print(f"  ✓ Model saved to {model_output}")

    except Exception as e:
        print(f"  ✗ Failed to download/package model: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 3: Copy sentence-transformers package
    # (Python code only, no compiled extensions)
    print(f"\n[3/5] Copying {ML_LIBRARY_NAME} package...")
    sentence_transformers_src = site_packages / "sentence_transformers"
    sentence_transformers_dst = ml_output_dir / "sentence_transformers"

    if not sentence_transformers_src.exists():
        print(f"  ✗ {ML_LIBRARY_NAME} not found in site-packages")
        return False

    # Copy the package directory (Python files)
    if sentence_transformers_dst.exists():
        shutil.rmtree(sentence_transformers_dst)

    def should_copy_file(file_path):
        """Determine if a file should be copied."""
        # Skip compiled extensions and large binary files
        skip_extensions = {'.so', '.pyd', '.dll', '.dylib'}
        skip_dirs = {'__pycache__', '.git', 'tests', 'test'}

        if file_path.suffix in skip_extensions:
            return False
        if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
            return False
        return True

    def copy_package(src, dst):
        """Copy package files, filtering out unnecessary files."""
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            if item.is_dir():
                if should_copy_file(item):
                    copy_package(item, dst / item.name)
            elif item.is_file():
                if should_copy_file(item):
                    shutil.copy2(item, dst / item.name)

    copy_package(sentence_transformers_src, sentence_transformers_dst)
    msg = f"  ✓ Copied {ML_LIBRARY_NAME} Python files"
    print(f"{msg} to {sentence_transformers_dst}")

    # Step 3b: Copy transformers package (required by sentence_transformers)
    print(f"\n[3b/5] Copying transformers package (required dependency)...")
    transformers_src = site_packages / "transformers"
    transformers_dst = ml_output_dir / "transformers"
    
    if transformers_src.exists():
        if transformers_dst.exists():
            shutil.rmtree(transformers_dst)
        copy_package(transformers_src, transformers_dst)
        print(f"  ✓ Copied transformers Python files to {transformers_dst}")
    else:
        print(f"  ⚠ transformers not found in site-packages (may cause issues)")

    # Step 5: Create __init__.py files if needed
    print("\n[5/5] Creating package structure...")
    (ml_output_dir / "__init__.py").touch(exist_ok=True)
    (ml_output_dir / "models" / "__init__.py").touch(exist_ok=True)

    # Summary
    print("\n" + "=" * 60)
    print("Packaging Complete!")
    print("=" * 60)
    print(f"\nML libraries packaged to: {ml_output_dir}")
    print("\nContents:")
    total_size = 0
    file_count = 0
    for item in sorted(ml_output_dir.rglob("*")):
        if item.is_file():
            file_count += 1
            rel_path = item.relative_to(ml_output_dir)
            size = item.stat().st_size
            total_size += size
            size_mb = size / (1024 * 1024)
            if size_mb > 0.1:  # Only show files larger than 100KB
                print(f"  {rel_path} ({size_mb:.2f} MB)")

    total_size_mb = total_size / (1024 * 1024)
    print(f"\nTotal: {file_count} files, {total_size_mb:.2f} MB")
    print("\nNext step: Run PyInstaller to build the exe.")
    msg = "  The ml_libraries folder will be included in the dist folder"
    print(f"{msg} next to the exe.")

    return True


if __name__ == "__main__":
    success = download_and_package_libraries()
    sys.exit(0 if success else 1)
