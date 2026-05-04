import os
import pickle
from azure.storage.blob import BlobServiceClient

CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER = os.getenv("BLOB_CONTAINER_NAME", "nemoclaw-state")
SESSION_BLOB = os.getenv("SESSION_BLOB_NAME", "insta-session.pkl")

def _blob_client():
    service = BlobServiceClient.from_connection_string(CONN_STR)
    container = service.get_container_client(CONTAINER)
    return container.get_blob_client(SESSION_BLOB)

def load_session() -> dict | None:
    try:
        blob = _blob_client()
        if blob.exists():
            stream = blob.download_blob()
            return pickle.loads(stream.readall())
    except Exception:
        pass
    return None

def save_session(session: dict):
    blob = _blob_client()
    blob.upload_blob(pickle.dumps(session), overwrite=True)
