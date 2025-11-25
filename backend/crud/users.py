from passlib.hash import bcrypt
from database import get_conn, USE_MEMORY_DB, add_user


def create_user(nome, email, senha):
    hashed = bcrypt.hash(senha)

    if USE_MEMORY_DB:
        user = add_user(nome, email, hashed)
        return user["id_usuario"], user["nome"], user["email"]

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO usuarios (nome, email, senha_hash)
        VALUES (%s, %s, %s)
        RETURNING id_usuario, nome, email;
    """,
        (nome, email, hashed),
    )

    user = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return user
