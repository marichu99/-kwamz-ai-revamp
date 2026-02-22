# mpesa_agent.spec — PyInstaller spec for the Kwamz AI Mpesa scraping agent.
#
# Build:
#   pip install pyinstaller
#   pyinstaller mpesa_agent.spec
#
# The resulting executable is in dist/mpesa_agent/mpesa_agent (Linux/Mac)
# or dist\mpesa_agent\mpesa_agent.exe (Windows).
#
# Playwright browsers are NOT bundled (they are too large).
# On first run the agent auto-installs Chromium via:
#   playwright install chromium
# This happens once in the user's home directory (~/.cache/ms-playwright).

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect Playwright data files (browser definitions, etc.)
playwright_datas = collect_data_files('playwright')

a = Analysis(
    ['mpesa_agent.py'],
    pathex=['.'],
    binaries=[],
    datas=playwright_datas,
    hiddenimports=[
        # Playwright internals
        'playwright',
        'playwright.sync_api',
        'playwright._impl._sync_api',
        # Data processing
        'pandas',
        'numpy',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'bs4',
        'beautifulsoup4',
        # Image handling
        'PIL',
        'PIL.Image',
        # Network
        'requests',
        'urllib3',
        'certifi',
        'charset_normalizer',
        'idna',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude server-side packages to keep the binary lean
        'flask',
        'sqlalchemy',
        'celery',
        'redis',
        'gunicorn',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='mpesa_agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,   # Keep console window so users can see logs
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='mpesa_agent',
)
