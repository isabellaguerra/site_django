import os

from dotenv import load_dotenv

load_dotenv()

_client = None


def get_supabase():
    """Cria o cliente do Supabase só na primeira vez que for usado.

    Assim o site abre mesmo se o .env estiver faltando; só as telas
    que dependem do Supabase mostram um aviso.
    """
    global _client
    if _client is None:
        from supabase import create_client

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("Configure SUPABASE_URL e SUPABASE_KEY no arquivo .env")
        _client = create_client(url, key)
    return _client
