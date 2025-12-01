# backend/auth.py
from passlib.hash import argon2
from database import get_conn, USE_MEMORY_DB, find_user_by_email

def login_user(email: str, senha: str):
    # Modo memória (usando o mesmo argon2 que o create_user)
    if USE_MEMORY_DB:
        row = find_user_by_email(email)
        if row and argon2.verify(senha, row["senha_hash"]):
            return {
                "id_usuario": row["id_usuario"],
                "nome": row["nome"],
                "email": row["email"],
            }
        return None

    # Modo PostgreSQL
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id_usuario, nome, email, senha_hash FROM usuarios WHERE email=%s",
            (email,),
        )
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    # row vem como RealDictRow (mapeamento), então acesse por nomes de coluna
    if row and argon2.verify(senha, row["senha_hash"]):
        return {
            "id_usuario": row["id_usuario"],
            "nome": row["nome"],
            "email": row["email"],
        }

    return None
