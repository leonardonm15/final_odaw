import os
from passlib.hash import bcrypt
from dotenv import load_dotenv

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:  # noqa: W0705 - falls back when psycopg2 is absent
    psycopg2 = None

load_dotenv()

# Default to real DB; set USE_MEMORY_DB=1 only for tests/dev fallback.
USE_MEMORY_DB = os.getenv("USE_MEMORY_DB", "0") != "0"

DB_NAME = os.getenv("DB_NAME", "streaming")
DB_USER = os.getenv("DB_USER", "leo")
DB_PASSWORD = os.getenv("DB_PASSWORD", "senha_super_segura")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")


class MemoryDB:
    def __init__(self):
        self.reset()

    def reset(self):
        self.users = {}
        self.albums = {}
        self.musicas = {}
        self.playlists = {}
        self.musica_playlist = set()
        self.user_seq = 1
        self.album_seq = 1
        self.music_seq = 1
        self.playlist_seq = 1


memory_db = MemoryDB()


def get_conn():
    if USE_MEMORY_DB or psycopg2 is None:
        return None

    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        cursor_factory=RealDictCursor,
    )


def rows_to_dicts(rows):
    """
    psycopg2 RealDictCursor already returns dict rows, but keep a helper to
    normalize when needed.
    """
    if rows is None:
        return []
    return [dict(r) for r in rows]


# Memory helpers -----------------------------------------------------------

def add_user(nome: str, email: str, senha_hash: str):
    uid = memory_db.user_seq
    memory_db.user_seq += 1
    memory_db.users[uid] = {
        "id_usuario": uid,
        "nome": nome,
        "email": email,
        "senha_hash": senha_hash,
    }
    return memory_db.users[uid]


def find_user_by_email(email: str):
    return next((u for u in memory_db.users.values() if u["email"] == email), None)


def create_album(titulo: str, ano: int, id_usuario: int):
    aid = memory_db.album_seq
    memory_db.album_seq += 1
    memory_db.albums[aid] = {
        "id_album": aid,
        "titulo": titulo,
        "ano": ano,
        "id_usuario": id_usuario,
    }
    return memory_db.albums[aid]

def renomear_album(aid: int, titulo: str):
    if aid not in memory_db.albums:
        return False
    memory_db.albums[aid]["titulo"] = titulo
    return True


def create_playlist(nome: str, id_dono: int):
    pid = memory_db.playlist_seq
    memory_db.playlist_seq += 1
    memory_db.playlists[pid] = {
        "id_playlist": pid,
        "nome": nome,
        "id_dono": id_dono,
    }
    return memory_db.playlists[pid]


def add_musica(nome: str, genero: str, duracao_seg: int, id_album: int, id_usuario: int):
    mid = memory_db.music_seq
    memory_db.music_seq += 1
    memory_db.musicas[mid] = {
        "id_musica": mid,
        "nome": nome,
        "genero": genero,
        "duracao_seg": duracao_seg,
        "id_album": id_album,
        "id_usuario": id_usuario,
    }
    return memory_db.musicas[mid]


def update_musica(mid: int, nome: str, genero: str, duracao_seg: int):
    musica = memory_db.musicas.get(mid)
    if not musica:
        return False
    musica.update({"nome": nome, "genero": genero, "duracao_seg": duracao_seg})
    return True

def update_musica_metadata(mid: int, nome: str, genero: str):
    musica = memory_db.musicas.get(mid)
    if not musica:
        return False
    musica.update({"nome": nome, "genero": genero})
    return True

def delete_album(aid: int):
    if aid not in memory_db.albums:
        return False
    # remove musicas ligadas ao álbum
    ids_musicas = [mid for mid, m in memory_db.musicas.items() if m["id_album"] == aid]
    for mid in ids_musicas:
        delete_musica(mid)
    del memory_db.albums[aid]
    return True


def delete_musica(mid: int):
    if mid not in memory_db.musicas:
        return False
    del memory_db.musicas[mid]
    memory_db.musica_playlist = {(pid, mid_) for pid, mid_ in memory_db.musica_playlist if mid_ != mid}
    return True

def get_user_by_id(uid: int):
    return memory_db.users.get(uid)


def add_musica_playlist(pid: int, mid: int):
    # Auto-create playlist if it doesn't exist to keep tests simple.
    if pid not in memory_db.playlists:
        create_playlist(f"Playlist {pid}", id_dono=1)
    memory_db.musica_playlist.add((pid, mid))
    return True


def remove_musica_playlist(pid: int, mid: int):
    if (pid, mid) in memory_db.musica_playlist:
        memory_db.musica_playlist.remove((pid, mid))
        return True
    return False


def listar_musicas():
    return list(memory_db.musicas.values())


def listar_por_genero(genero: str):
    return [m for m in memory_db.musicas.values() if m["genero"] == genero]


def listar_por_artista(id_usuario: int):
    return [m for m in memory_db.musicas.values() if m["id_usuario"] == id_usuario]


def playlists_by_user(uid: int):
    return [p for p in memory_db.playlists.values() if p["id_dono"] == uid]


def musicas_por_album(aid: int):
    return [m for m in memory_db.musicas.values() if m["id_album"] == aid]


def musicas_da_playlist(pid: int):
    mids = [mid for (p, mid) in memory_db.musica_playlist if p == pid]
    return [memory_db.musicas[mid] for mid in mids if mid in memory_db.musicas]


def renomear_playlist(pid: int, nome: str):
    pl = memory_db.playlists.get(pid)
    if not pl:
        return False
    pl["nome"] = nome
    return True

def deletar_playlist(pid: int):
    if pid not in memory_db.playlists:
        return False
    # remove relações musica_playlist
    memory_db.musica_playlist = {(p, mid) for (p, mid) in memory_db.musica_playlist if p != pid}
    del memory_db.playlists[pid]
    return True
