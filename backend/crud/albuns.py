from database import (
    get_conn,
    USE_MEMORY_DB,
    create_album as mem_create_album,
    renomear_album as mem_renomear_album,
)


def criar_album(titulo, ano, id_usuario):
    if USE_MEMORY_DB:
        row = mem_create_album(titulo, ano, id_usuario)
        return {"id_album": row["id_album"], "titulo": row["titulo"], "ano": ano, "id_usuario": id_usuario}

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO albuns (titulo, ano, id_usuario)
        VALUES (%s, %s, %s)
        RETURNING id_album, titulo;
    """,
        (titulo, ano, id_usuario),
    )

    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return dict(row) if row else None


def atualizar_titulo_album(id_album: int, titulo: str):
    if USE_MEMORY_DB:
        return mem_renomear_album(id_album, titulo)

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE albuns
            SET titulo=%s
            WHERE id_album=%s
            RETURNING id_album;
            """,
            (titulo, id_album),
        )
        row = cur.fetchone()
        conn.commit()
        return bool(row)
    finally:
        cur.close()
        conn.close()
