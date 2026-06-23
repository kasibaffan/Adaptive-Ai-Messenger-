import os
from slowapi import Limiter
from slowapi.util import get_remote_address

# Disabled under the test suite — every test request shares the same client
# address, so per-IP limits would trip across unrelated tests rather than
# testing anything meaningful. Set by conftest.py before the app is imported.
limiter = Limiter(key_func=get_remote_address, enabled=os.getenv("TESTING") != "1")
