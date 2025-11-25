# Apenas strings SQL reutilizáveis

CREATE_USER = """
INSERT INTO usuarios (nome, email, senha_hash)
VALUES (%s, %s, crypt(%s, gen_salt('bf')))
RETURNING id_usuario, nome, email;
"""

AUTH_USER = """
SELECT id_usuario, nome, email, senha_hash
FROM usuarios
WHERE email = %s;
"""

LIST_MUSICAS = "SELECT * FROM musicas;"
LIST_MUSICAS_BY_GENERO = "SELECT * FROM musicas WHERE genero = %s;"
LIST_MUSICAS_BY_ARTISTA = "SELECT * FROM musicas WHERE id_usuario = %s;"
