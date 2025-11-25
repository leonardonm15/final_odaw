import os
import tempfile
from io import BytesIO
from pathlib import Path
import sys
import pytest
from starlette.datastructures import UploadFile

# Force in-memory DB and isolate media writes for tests.
os.environ["USE_MEMORY_DB"] = "1"
_TEST_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="backend_media_tests_"))
os.environ["APP_MEDIA_DIR"] = str(_TEST_MEDIA_ROOT)

# Ensure project root is on path so `main` is importable when pytest runs from test dir.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from schemas import UserCreate, Login  # noqa: E402
from main import (  # noqa: E402
    register,
    login,
    criar_album_route,
    criar_musica,
    stream_musica,
    editar_musica,
    criar_playlist_route,
    add_music,
    remover_musica_playlist,
    upload_capa,
    get_capa,
    por_genero,
    por_artista,
    todas_musicas,
    deletar_musica,
)

# ============================================================
# Helpers / fixtures
# ============================================================

TEST_AUDIO = BytesIO(b"FAKE-MP3-DATA")
TEST_COVER = BytesIO(b"FAKE-IMG-DATA")

user_id = None
album_id = None
musica_id = None
playlist_id = None


# ============================================================
# 🔵 RF01 — Cadastro e Login
# ============================================================

def test_register():
    global user_id
    resp = register(UserCreate(nome="Teste User", email="teste@example.com", senha="123456"))
    user_id = resp["id_usuario"]
    assert user_id is not None


def test_login():
    resp = login(Login(email="teste@example.com", senha="123456"))
    assert resp["id_usuario"] == user_id


# ============================================================
# 🟠 RF06 — Criar álbum
# ============================================================

def test_criar_album():
    global album_id
    resp = criar_album_route(titulo="Album Teste", ano=2024, id_usuario=user_id)
    album_id = resp["id_album"]
    assert album_id is not None


# ============================================================
# 🟣 RF06 — Criar música com upload
# ============================================================

@pytest.mark.asyncio
async def test_criar_musica():
    global musica_id
    upload = UploadFile(file=BytesIO(TEST_AUDIO.getvalue()), filename="audio.mp3", headers={"content-type": "audio/mpeg"})
    resp = await criar_musica(
        nome="Musica Teste",
        genero="Indie",
        duracao_seg=200,
        id_album=album_id,
        id_usuario=user_id,
        id_playlist=1,
        arquivo=upload,
    )
    musica_id = resp["id_musica"]
    assert musica_id is not None


# ============================================================
# 🎶 RF03 — Stream de música
# ============================================================

def test_stream_musica():
    response = stream_musica(musica_id)
    assert response.status_code == 200


# ============================================================
# ✏️ Editar música
# ============================================================

def test_editar_musica():
    response = editar_musica(
        musica_id,
        nome="Musica Editada",
        genero="Rock",
        duracao_seg=250,
    )
    assert response["message"] == "Música atualizada."


# ============================================================
# 📜 RF04 — Criar playlist
# ============================================================

def test_criar_playlist():
    global playlist_id
    resp = criar_playlist_route(user_id, nome="Playlist Teste")
    playlist_id = resp["id_playlist"]
    assert playlist_id is not None


# ============================================================
# ➕ RF05 — Add música à playlist
# ============================================================

def test_add_musica_playlist():
    resp = add_music(playlist_id, musica_id)
    assert resp["message"]


# ============================================================
# 🗑️ RF05 — Remover música da playlist
# ============================================================

def test_remove_musica_playlist():
    resp = remover_musica_playlist(playlist_id, musica_id)
    assert resp["message"]


# ============================================================
# 🖼️ RF06 — Upload capa de álbum
# ============================================================

@pytest.mark.asyncio
async def test_upload_capa():
    upload = UploadFile(file=BytesIO(TEST_COVER.getvalue()), filename="capa.jpg", headers={"content-type": "image/jpeg"})
    resp = await upload_capa(album_id, arquivo=upload)
    assert resp["message"]


# ============================================================
# 🖼️ RF06 — Obter capa do álbum
# ============================================================

def test_get_capa():
    response = get_capa(album_id)
    assert response.status_code == 200


# ============================================================
# 🔍 RF02 — Listar músicas por gênero e autor
# ============================================================

def test_listar_por_genero():
    response = por_genero("Indie")
    assert isinstance(response, list)


def test_listar_por_autor():
    response = por_artista(user_id)
    assert isinstance(response, list)


# ============================================================
# 🟢 RF02 — Listagem geral
# ============================================================

def test_listar_musicas():
    response = todas_musicas()
    assert isinstance(response, list)


# ============================================================
# 🗑️ Remover música
# ============================================================

def test_deletar_musica():
    response = deletar_musica(musica_id)
    assert response["message"]
