"""Launch labsmith_gui on macOS / Linux with the software mock driver installed.

Usage:
    python3 dev_tools/run_gui_mock.py

The mock is registered *before* labsmith_gui is imported, so
`from uProcess_x64 import uProcess_x64` inside LabsmithBoard transparently
resolves to the fake controller. All vendor commands return success and moves
complete after a short interpolated duration.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PYTHON_ROOT = os.path.abspath(os.path.join(HERE, ".."))

if HERE not in sys.path:
    sys.path.insert(0, HERE)
if PYTHON_ROOT not in sys.path:
    sys.path.insert(0, PYTHON_ROOT)

import mock_driver
mock_driver.install()

# sanity: the import path real code will take must now resolve to our mock
from uProcess_x64 import uProcess_x64 as _up
assert getattr(_up, "_is_mock", False), "mock_driver.install() failed"

from labsmith_gui import main
main()
