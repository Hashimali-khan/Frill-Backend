from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

# Backed by Redis so limits are enforced correctly even if you later run
# more than one backend instance — an in-memory limiter would let each
# instance count separately, defeating the point under real load.
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)