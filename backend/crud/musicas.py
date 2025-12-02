from database import (
    get_conn,
    USE_MEMORY_DB,
    listar_musicas as mem_listar,
    listar_por_genero as mem_listar_genero,
    listar_por_artista as mem_listar_artista,
    rows_to_dicts,
)


def listar_musicas(nome: str | None = None, id_album: int | None = None):
    if USE_MEMORY_DB:
        rows = mem_listar()
        if nome:
            rows = [
                r for r in rows
                if nome.lower() in (r.get("nome") or "").lower()
            ]
        if id_album is not None:
            rows = [r for r in rows if r.get("id_album") == id_album]
        return rows

    conn = get_conn()
    cur = conn.cursor()
    try:
        clauses = []
        params = []
        if nome:
            clauses.append("LOWER(nome) LIKE %s")
            params.append(f"%{nome.lower()}%")
        if id_album is not None:
            clauses.append("id_album = %s")
            params.append(id_album)

        sql = "SELECT * FROM musicas"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        return rows_to_dicts(rows)
    finally:
        cur.close()
        conn.close()


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
