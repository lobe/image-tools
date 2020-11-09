import os
import sys

ASSETS_PATH = 'assets' if os.path.exists('assets') else os.path.join('app', 'assets')


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = ASSETS_PATH

    return os.path.join(base_path, relative_path)
