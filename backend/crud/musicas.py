from database import (
    get_conn,
    USE_MEMORY_DB,
    listar_musicas as mem_listar,
    listar_por_genero as mem_listar_genero,
    listar_por_artista as mem_listar_artista,
    rows_to_dicts,
)


def listar_musicas():
    if USE_MEMORY_DB:
        return mem_listar()

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM musicas;")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return rows_to_dicts(rows)


def listar_por_genero(genero):
    if USE_MEMORY_DB:
        return mem_listar_genero(genero)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM musicas WHERE genero=%s;", (genero,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows_to_dicts(rows)


def listar_por_artista(id_usuario):
    if USE_MEMORY_DB:
        return mem_listar_artista(id_usuario)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM musicas WHERE id_usuario=%s;", (id_usuario,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows_to_dicts(rows)
