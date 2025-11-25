from database import (
    get_conn,
    USE_MEMORY_DB,
    create_playlist as mem_create_playlist,
    add_musica_playlist as mem_add,
    rows_to_dicts,
)


def criar_playlist(nome, id_dono):
    if USE_MEMORY_DB:
        row = mem_create_playlist(nome, id_dono)
        return {"id_playlist": row["id_playlist"], "nome": row["nome"], "id_dono": id_dono}

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO playlists (nome, id_dono)
        VALUES (%s, %s)
        RETURNING id_playlist, nome;
    """,
        (nome, id_dono),
    )

    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return dict(row) if row else None


def adicionar_musica(id_playlist, id_musica):
    if USE_MEMORY_DB:
        mem_add(id_playlist, id_musica)
        return

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO musica_playlist (id_playlist, id_musica)
        VALUES (%s, %s)
    """,
        (id_playlist, id_musica),
    )

    conn.commit()
    cur.close()
    conn.close()
