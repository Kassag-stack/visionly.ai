import os
from dotenv import load_dotenv
from colorama import Fore
from supabase import create_client

# ─── Supabase Client Setup ─────────────────────────────────────
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_API_KEY")
SUPA = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None

# ─── Supabase Upload Function ──────────────────────────────────
def upload_supabase(data: bytes|str, fname: str, bucket: str):
    """
    Uploads data to a Supabase storage bucket.
    - data: bytes or str to upload
    - fname: filename in the bucket
    - bucket: Supabase storage bucket name
    """
    if not SUPA:
        print("Supabase creds missing – skipping upload.")
        return
    # Convert string data to bytes if needed
    if isinstance(data, str):
        data = data.encode("utf-8")
    # Upload to Supabase
    SUPA.storage.from_(bucket).upload(
        path=fname,
        file=data,
        file_options={"content-type": "text/csv" if fname.endswith(".csv") else "image/png"}
    )
    # Print public URL for debugging
    url = SUPA.storage.from_(bucket).get_public_url(fname)
    print(Fore.GREEN + f"Supabase upload → {url}") 