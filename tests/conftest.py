"""
Shared test setup. The tests must not depend on whatever keys or provider choices are in the
developer's own .env, so the .env loader is switched off before the package is first imported.
"""

import os

os.environ["DUKAAN_NO_DOTENV"] = "1"
