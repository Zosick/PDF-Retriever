import sys
import os
# Ensure src is in path so collect_all can find the package
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('downloader')
