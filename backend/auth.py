from passlib.hash import bcrypt
from database import get_conn, USE_MEMORY_DB, find_user_by_email


def login_user(email: str, senha: str):
    if USE_MEMORY_DB:
        row = find_user_by_email(email)
        if row and bcrypt.verify(senha, row["senha_hash"]):
            return {
                "id_usuario": row["id_usuario"],
                "nome": row["nome"],
                "email": row["email"],
            }
        return None

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT id_usuario, nome, email, senha_hash FROM usuarios WHERE email=%s",
        (email,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row and bcrypt.verify(senha, row[3]):
        return {
            "id_usuario": row[0],
            "nome": row[1],
            "email": row[2],
        }

    return None
