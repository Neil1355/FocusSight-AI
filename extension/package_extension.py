"""Package the FocusSight browser extension into distributable archives.

Run from the repository root:
    python extension/package_extension.py

Produces:
    dist/focussight-extension.zip  – Chrome Web Store ready
    dist/focussight-extension.xpi  – Firefox unsigned add-on (same format)
"""

import os
import zipfile


# Files / directories to exclude from the package.
EXCLUDE = {".DS_Store", "Thumbs.db", "__pycache__", "package_extension.py", "generate_icons.py"}


def package():
    ext_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(os.path.dirname(ext_dir), "dist")
    os.makedirs(dist_dir, exist_ok=True)

    zip_path = os.path.join(dist_dir, "focussight-extension.zip")
    xpi_path = os.path.join(dist_dir, "focussight-extension.xpi")

    def _add_to_zip(zf: zipfile.ZipFile):
        for root, dirs, files in os.walk(ext_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDE]
            for fname in files:
                if fname in EXCLUDE:
                    continue
                abs_path = os.path.join(root, fname)
                arcname = os.path.relpath(abs_path, ext_dir)
                zf.write(abs_path, arcname)
                print(f"  + {arcname}")

    print(f"Building {zip_path}…")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        _add_to_zip(zf)
    print(f"  → {zip_path}")

    print(f"Building {xpi_path}…")
    with zipfile.ZipFile(xpi_path, "w", zipfile.ZIP_DEFLATED) as zf:
        _add_to_zip(zf)
    print(f"  → {xpi_path}")

    print("\nDone.  Load unpacked from extension/ for local development.")


if __name__ == "__main__":
    package()
