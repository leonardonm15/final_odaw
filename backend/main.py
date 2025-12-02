from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
from schemas import UserCreate, UserOut, Login
from auth import login_user
from crud.users import create_user
from crud.musicas import listar_musicas, listar_por_genero, listar_por_artista
from crud.playlists import (
    criar_playlist,
    adicionar_musica,
    listar_musicas_da_playlist,
    atualizar_nome_playlist,
)
from crud.albuns import criar_album, atualizar_titulo_album
import os
from pathlib import Path
from database import (
    get_conn,
    USE_MEMORY_DB,
    add_musica,
    update_musica,
    update_musica_metadata,
    delete_musica,
    get_user_by_id,
    delete_album,
    add_musica_playlist,
    remove_musica_playlist,
    playlists_by_user,
    musicas_por_album,
    deletar_playlist,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse


app = FastAPI(title="Streaming Musical - Backend")

# ====================== CORS ======================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ou restrinja para ["http://localhost:5500"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Pastas de arquivos: tenta usar APP_MEDIA_DIR (env) ou backend/media; se não conseguir, cai para /tmp
def _ensure_dir(path: Path):
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except PermissionError:
        return None


media_root = os.getenv("APP_MEDIA_DIR")
MEDIA_ROOT = None
if media_root:
    MEDIA_ROOT = _ensure_dir(Path(media_root))

if MEDIA_ROOT is None:
    MEDIA_ROOT = _ensure_dir(Path(__file__).resolve().parent / "media")

if MEDIA_ROOT is None:
    MEDIA_ROOT = _ensure_dir(Path("/tmp/backend_media"))

if MEDIA_ROOT is None:
    raise RuntimeError("Não foi possível criar diretório de mídia.")

SONGS_DIR = (MEDIA_ROOT / "songs")
COVERS_DIR = (MEDIA_ROOT / "covers")
SONGS_DIR.mkdir(parents=True, exist_ok=True)
COVERS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 🔵 RF01 — Autenticação (Cadastro e Login)
# ============================================================

@app.post("/register", response_model=UserOut)
def register(user: UserCreate):
    novo = create_user(user.nome, user.email, user.senha)
    return {
        "id_usuario": novo[0],
        "nome": novo[1],
        "email": novo[2]
    }

@app.post("/login")
def login(login: Login):
    user = login_user(login.email, login.senha)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    return user

@app.get("/usuarios/{id_usuario}")
def usuario_por_id(id_usuario: int):
    if USE_MEMORY_DB:
        user = get_user_by_id(id_usuario)
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        return {"id_usuario": user["id_usuario"], "nome": user["nome"], "email": user["email"]}

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id_usuario, nome, email FROM usuarios WHERE id_usuario=%s",
            (id_usuario,),
        )
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    # row pode ser dict ou tuple
    return {
        "id_usuario": row["id_usuario"] if isinstance(row, dict) else row[0],
        "nome": row["nome"] if isinstance(row, dict) else row[1],
        "email": row["email"] if isinstance(row, dict) else row[2],
    }


# ============================================================
# 🟢 RF02 — Catálogo (Listagem e Filtros)
# ============================================================

@app.get("/musicas")
def todas_musicas(nome: Optional[str] = None, id_album: Optional[int] = None):
    return listar_musicas(nome=nome, id_album=id_album)

@app.get("/musicas/genero/{genero}")
def por_genero(genero: str):
    return listar_por_genero(genero)

@app.get("/musicas/autor/{id_usuario}")
def por_artista(id_usuario: int):
    return listar_por_artista(id_usuario)


# ============================================================
# 🟣 RF06 — CRUD de Músicas (Criar, Editar, Deletar, Streaming)
# ============================================================

# Criar música + upload + vincular playlist
@app.post("/musicas/criar")
async def criar_musica(
    nome: str = Form(...),
    genero: str = Form(...),
    duracao_seg: int = Form(...),
    id_album: int = Form(...),
    id_usuario: int = Form(...),
    id_playlist: Optional[int] = Form(None),
    arquivo: UploadFile = File(...)
):
    if not arquivo.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Arquivo enviado não é áudio válido.")

    if USE_MEMORY_DB:
        musica = add_musica(nome, genero, int(duracao_seg), int(id_album), int(id_usuario))
        id_musica = musica["id_musica"]
        if id_playlist is not None:
            add_musica_playlist(int(id_playlist), id_musica)
    else:
        conn = get_conn()
        cur = conn.cursor()

        # 1 — Inserir música
        cur.execute("""
            INSERT INTO musicas (nome, genero, duracao_seg, id_album, id_usuario)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id_musica;
        """, (nome, genero, duracao_seg, id_album, id_usuario))

        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            raise HTTPException(status_code=500, detail="Falha ao criar música.")
        # RealDictCursor retorna dict; tuple fallback se usar cursor default
        id_musica = row["id_musica"] if isinstance(row, dict) else row[0]

        # 2 — Vincular playlist (opcional)
        if id_playlist is not None:
            cur.execute("""
                INSERT INTO musica_playlist (id_playlist, id_musica)
                VALUES (%s, %s)
            """, (id_playlist, id_musica))

        conn.commit()
        cur.close()
        conn.close()

    # 3 — Salvar arquivo (leitura síncrona para evitar uso de threadpool em ambientes restritos)
    ext = Path(arquivo.filename).suffix.lower() or ".mp3"
    destino = SONGS_DIR / f"{id_musica}{ext}"

    with destino.open("wb") as f:
        data = arquivo.file.read()
        f.write(data)

    return {
        "message": "Música criada com sucesso!",
        "id_musica": id_musica,
        "playlist_vinculada": id_playlist
    }


# Stream de áudio
@app.get("/musicas/{id_musica}/stream")
def stream_musica(id_musica: int):
    for file in SONGS_DIR.glob(f"{id_musica}.*"):
        return FileResponse(file, media_type="audio/mpeg")
    raise HTTPException(status_code=404, detail="Arquivo de música não encontrado.")


# Editar música
@app.put("/musicas/{id_musica}/editar")
def editar_musica(id_musica: int, nome: str = Form(...), genero: str = Form(...), duracao_seg: int = Form(...)):
    if USE_MEMORY_DB:
        ok = update_musica(id_musica, nome, genero, int(duracao_seg))
        if not ok:
            raise HTTPException(status_code=404, detail="Música não encontrada.")
        return {"message": "Música atualizada."}

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE musicas
        SET nome=%s, genero=%s, duracao_seg=%s
        WHERE id_musica=%s
        RETURNING id_musica;
    """, (nome, genero, duracao_seg, id_musica))

    updated = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if not updated:
        raise HTTPException(status_code=404, detail="Música não encontrada.")

    return {"message": "Música atualizada."}

# Editar nome/gênero (sem exigir duração)
@app.put("/musicas/{id_musica}/metadata")
def editar_musica_metadata(id_musica: int, nome: str = Form(...), genero: str = Form(...)):
    if USE_MEMORY_DB:
        ok = update_musica_metadata(id_musica, nome, genero)
        if not ok:
            raise HTTPException(status_code=404, detail="Música não encontrada.")
        return {"message": "Música atualizada."}

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE musicas
        SET nome=%s, genero=%s
        WHERE id_musica=%s
        RETURNING id_musica;
        """,
        (nome, genero, id_musica),
    )
    updated = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not updated:
        raise HTTPException(status_code=404, detail="Música não encontrada.")
    return {"message": "Música atualizada."}


# Remover música
@app.delete("/musicas/{id_musica}")
def deletar_musica(id_musica: int):
    if USE_MEMORY_DB:
        ok = delete_musica(id_musica)
        if not ok:
            raise HTTPException(status_code=404, detail="Música não encontrada.")
    else:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("DELETE FROM musica_playlist WHERE id_musica=%s;", (id_musica,))
        cur.execute("DELETE FROM musicas WHERE id_musica=%s RETURNING id_musica;", (id_musica,))
        deleted = cur.fetchone()

        conn.commit()
        cur.close()
        conn.close()

        if not deleted:
            raise HTTPException(status_code=404, detail="Música não encontrada.")

    # Remover arquivo físico
    for f in SONGS_DIR.glob(f"{id_musica}.*"):
        f.unlink(missing_ok=True)

    return {"message": "Música deletada."}


# ============================================================
# 🟡 RF04 / RF05 — Playlists
# ============================================================

@app.post("/playlists/{id_dono}")
def criar_playlist_route(id_dono: int, nome: str):
    return criar_playlist(nome, id_dono)

@app.post("/playlists/{id_playlist}/add/{id_musica}")
def add_music(id_playlist: int, id_musica: int):
    if USE_MEMORY_DB:
        add_musica_playlist(id_playlist, id_musica)
    else:
        adicionar_musica(id_playlist, id_musica)
    return {"message": "Música adicionada à playlist."}

@app.delete("/playlists/{id_playlist}/musicas/{id_musica}")
def remover_musica_playlist(id_playlist: int, id_musica: int):
    if USE_MEMORY_DB:
        ok = remove_musica_playlist(id_playlist, id_musica)
        if not ok:
            raise HTTPException(status_code=404, detail="Relação não encontrada.")
    else:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            DELETE FROM musica_playlist
            WHERE id_playlist=%s AND id_musica=%s
            RETURNING id_playlist;
        """, (id_playlist, id_musica))

        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Relação não encontrada.")

    return {"message": "Música removida da playlist."}

@app.delete("/playlists/{id_playlist}")
def excluir_playlist(id_playlist: int):
    if USE_MEMORY_DB:
        ok = deletar_playlist(id_playlist)
        if not ok:
            raise HTTPException(status_code=404, detail="Playlist não encontrada.")
    else:
        conn = get_conn()
        cur = conn.cursor()
        # apaga relações e a playlist
        cur.execute("DELETE FROM musica_playlist WHERE id_playlist=%s;", (id_playlist,))
        cur.execute("DELETE FROM playlists WHERE id_playlist=%s RETURNING id_playlist;", (id_playlist,))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="Playlist não encontrada.")
    return {"message": "Playlist deletada."}


@app.get("/usuarios/{id_usuario}/playlists")
def playlists_usuario(id_usuario: int):
    if USE_MEMORY_DB:
        return playlists_by_user(id_usuario)

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM playlists WHERE id_dono=%s;", (id_usuario,))
    rows = cur.fetchall()

    cur.close()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/playlists/{id_playlist}/musicas")
def musicas_da_playlist_route(id_playlist: int):
    return listar_musicas_da_playlist(id_playlist)


@app.put("/playlists/{id_playlist}")
def renomear_playlist_route(id_playlist: int, nome: str = Form(...)):
    ok = atualizar_nome_playlist(id_playlist, nome)
    if not ok:
        raise HTTPException(status_code=404, detail="Playlist não encontrada.")
    return {"message": "Playlist atualizada.", "id_playlist": id_playlist, "nome": nome}


# ============================================================
# 🟠 RF06 — Álbuns (CRUD básico)
# ============================================================

@app.post("/albuns")
def criar_album_route(titulo: str, ano: int, id_usuario: int):
    return criar_album(titulo, ano, id_usuario)

@app.get("/albuns/{id_album}/musicas")
def musicas_do_album(id_album: int):
    if USE_MEMORY_DB:
        return musicas_por_album(id_album)

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM musicas WHERE id_album=%s", (id_album,))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [dict(r) for r in rows]


@app.delete("/albuns/{id_album}")
def excluir_album(id_album: int):
    removed_files = []
    if USE_MEMORY_DB:
        ok = delete_album(id_album)
        if not ok:
            raise HTTPException(status_code=404, detail="Álbum não encontrado.")
    else:
        conn = get_conn()
        cur = conn.cursor()
        # pega ids das músicas para remover arquivos depois
        cur.execute("SELECT id_musica FROM musicas WHERE id_album=%s;", (id_album,))
        ids = [r[0] if not isinstance(r, dict) else r["id_musica"] for r in cur.fetchall()]
        cur.execute("DELETE FROM albuns WHERE id_album=%s RETURNING id_album;", (id_album,))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="Álbum não encontrado.")
        removed_files = ids

    # remove arquivos físicos das músicas do álbum (se existirem)
    for mid in removed_files:
        for f in SONGS_DIR.glob(f"{mid}.*"):
            f.unlink(missing_ok=True)

    return {"message": "Álbum deletado."}


@app.put("/albuns/{id_album}")
def renomear_album_route(id_album: int, titulo: str = Form(...)):
    ok = atualizar_titulo_album(id_album, titulo)
    if not ok:
        raise HTTPException(status_code=404, detail="Álbum não encontrado.")
    return {"message": "Álbum atualizado.", "id_album": id_album, "titulo": titulo}


# Upload da capa
@app.post("/albuns/{id_album}/upload_capa")
async def upload_capa(id_album: int, arquivo: UploadFile = File(...)):
    if not arquivo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Arquivo enviado não é imagem.")

    ext = Path(arquivo.filename).suffix.lower() or ".jpg"
    destino = COVERS_DIR / f"{id_album}{ext}"

    with destino.open("wb") as f:
        data = arquivo.file.read()
        f.write(data)

    return {"message": "Capa enviada."}


@app.get("/albuns/{id_album}/capa")
def get_capa(id_album: int):
    for f in COVERS_DIR.glob(f"{id_album}.*"):
        return FileResponse(f, media_type="image/jpeg")

    raise HTTPException(status_code=404, detail="Capa não encontrada.")

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")
