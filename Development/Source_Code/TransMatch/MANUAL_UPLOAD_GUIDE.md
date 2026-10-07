# Manual Upload Guide for TransMatch to GitHub

## Quick Summary
Your repository is too large (3.04 GiB) because it includes:
- `dist/` (12,745 files)
- `build/` (build artifacts)
- `ml_libraries/` (2,424 files)
- `poppler/`, `tesseract/` (external libraries)
- `log/`, `debug/`, `archive/` folders

**These should NOT be uploaded to GitHub!**

---

## Method 1: GitHub Web Interface (Easiest)

### Step 1: Prepare Your Files
1. Create a new folder: `TransMatch_Clean`
2. Copy ONLY these from your project:
   - All `.py` files
   - `administration/` folder
   - `transaction/` folder
   - `report/` folder
   - `ui/` folder
   - `templates/` folder
   - `.gitignore` file
   - `*.spec` files
   - `*.bat` files
   - `*.png`, `*.gif` (images/logos)

3. **DO NOT copy:**
   - `dist/` folder
   - `build/` folder
   - `ml_libraries/` folder
   - `poppler/` folder
   - `tesseract/` folder
   - `log/` folder
   - `debug/` folder
   - `archive/` folder

### Step 2: Upload to GitHub
1. Go to: https://github.com/nextportalsoftwarepartner-max/TransMatch
2. If repository is empty, you'll see "uploading an existing file"
3. Click "uploading an existing file"
4. Drag and drop your `TransMatch_Clean` folder contents
5. Or click "choose your files" and select files
6. Add commit message: "Initial upload - TransMatch source code"
7. Click "Commit changes"

### Step 3: Upload Folders
- For each folder (`administration/`, `transaction/`, etc.):
  1. Click "Add file" → "Upload files"
  2. Drag the entire folder
  3. Commit

---

## Method 2: GitHub Desktop (Recommended for Future)

### Step 1: Download GitHub Desktop
1. Go to: https://desktop.github.com/
2. Download and install
3. Sign in with your GitHub account

### Step 2: Add Your Repository
1. Open GitHub Desktop
2. File → Add Local Repository
3. Click "Choose..."
4. Navigate to: `D:\CHIANWEILON\Software_Dev\TransMatch\Development\Source_Code\TransMatch`
5. Click "Add repository"

### Step 3: Configure .gitignore
Make sure `.gitignore` includes:
```
dist/
build/
ml_libraries/
poppler/
tesseract/
log/
debug/
archive/
*.pyc
__pycache__/
```

### Step 4: Commit and Push
1. In GitHub Desktop, you'll see changed files
2. Uncheck large folders (`dist/`, `build/`, etc.)
3. Check only source code files
4. Write commit message: "Initial commit - TransMatch source code"
5. Click "Commit to main"
6. Click "Publish repository" (first time) or "Push origin"

---

## Method 3: Command Line (Advanced)

### Step 1: Clean Your Repository
```powershell
cd "D:\CHIANWEILON\Software_Dev\TransMatch\Development\Source_Code\TransMatch"

# Remove large directories from Git tracking
git rm -r --cached dist/ build/ ml_libraries/ poppler/ tesseract/ log/ debug/ archive/

# Commit the removal
git commit -m "Remove large directories from tracking"
```

### Step 2: Push (Small Repository)
```powershell
# Push with your token
git push https://YOUR_TOKEN@github.com/nextportalsoftwarepartner-max/TransMatch.git main
```

---

## Important Notes

1. **Never commit large files** - GitHub has a 100MB file limit and 1GB repository warning
2. **Use .gitignore** - Always have a `.gitignore` to exclude build artifacts
3. **External libraries** - Install via `requirements.txt`, don't commit them
4. **Build outputs** - Never commit `dist/`, `build/`, or compiled files

---

## Your .gitignore Should Include:
```
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
dist/
build/
*.egg-info/

# Large directories
ml_libraries/
poppler/
tesseract/
log/
debug/
archive/

# IDE
.vscode/
.idea/

# Environment
*.env
venv/
```

---

## Need Help?
- GitHub Docs: https://docs.github.com/en/get-started
- GitHub Desktop Guide: https://docs.github.com/en/desktop
