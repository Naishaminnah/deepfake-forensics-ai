# backend/utils/hash_utils.py

import hashlib

def generate_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
