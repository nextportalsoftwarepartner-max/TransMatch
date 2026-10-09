# Extraction parity check

Compares this package's output with the original Python desktop application,
statement by statement.

1. Produce the reference output with the Python application's virtualenv
   (needs Tesseract and Poppler, as the desktop app does). Edit `SRC` and
   `PDF_DIR` at the top of the script if your paths differ:

   ```
   <venv>/Scripts/python -I parity/make_groundtruth.py .parity/reference
   ```

2. Run the comparison (add `--ml` to use the embedding model for UOB names):

   ```
   pnpm parity .parity/reference <folder-with-the-same-PDFs> --ml
   ```

`.parity/` is git-ignored because the reference output contains statement data.

Known, accepted differences:

- Hong Leong: the notice text that the template appends to the last row has
  single instead of double spaces between some words.
- UOB target names: the Python implementation iterates unordered sets, so its
  own output changes on about 12% of rows from run to run. This port is
  deterministic.
- Image-only PDFs (no text layer) yield zero rows here; Python raised an error.
