"""Start the GwAu3 bridge worker over stdio, for an AutoIt caller.

A launcher rather than a module: AutoIt's ``Run()`` needs a file to execute, and this puts the worker's
package path in place before handing over to :func:`py4gw.gwa3.bridge.main`. The repository root is
found from this file's own location, so nothing has to be configured.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if __name__ == "__main__":
    from py4gw.gwa3.bridge import main

    raise SystemExit(main())
