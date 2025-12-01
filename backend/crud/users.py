# backend/crud/users.py
from passlib.hash import argon2
from database import get_conn, USE_MEMORY_DB, add_user

def create_user(nome, email, senha):
    """
    Usa Argon2 para hashear a senha (não há limite de 72 bytes como no bcrypt).
    """
    hashed = argon2.hash(senha)

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
    # Normaliza para o mesmo formato que a versão em memória:
    return user["id_usuario"], user["nome"], user["email"]