"""Re-export the bible store (which uses Firestore under the hood)."""
from ..bible import store as _bible_store

# Backwards-compatible alias: storage.firestore is the same client as bible.store
get_client = _bible_store._get_firestore
