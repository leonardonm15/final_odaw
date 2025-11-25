-- Habilita hashing seguro (bcrypt) para cadastro e login
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ======================
-- TABELAS
-- ======================

CREATE TABLE usuarios (
  id_usuario     BIGSERIAL PRIMARY KEY,
  nome           VARCHAR(120) NOT NULL,
  email          VARCHAR(255) NOT NULL UNIQUE,
  senha_hash     TEXT NOT NULL,
  role           VARCHAR(20) NOT NULL DEFAULT 'user', -- opcional: 'user' | 'admin'
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE albuns (
  id_album       BIGSERIAL PRIMARY KEY,
  titulo         VARCHAR(160) NOT NULL,
  ano            INTEGER CHECK (ano BETWEEN 1900 AND EXTRACT(YEAR FROM NOW())::INT),
  id_usuario     BIGINT NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE musicas (
  id_musica      BIGSERIAL PRIMARY KEY,
  nome           VARCHAR(160) NOT NULL,
  genero         VARCHAR(60),
  duracao_seg    INTEGER CHECK (duracao_seg IS NULL OR duracao_seg >= 0),
  id_album       BIGINT NOT NULL REFERENCES albuns(id_album) ON DELETE CASCADE,
  id_usuario     BIGINT NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE, -- dono/autor
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE playlists (
  id_playlist    BIGSERIAL PRIMARY KEY,
  nome           VARCHAR(120) NOT NULL,
  id_dono        BIGINT NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- relação N:N entre playlists e músicas
CREATE TABLE musica_playlist (
  id_musica      BIGINT NOT NULL REFERENCES musicas(id_musica) ON DELETE CASCADE,
  id_playlist    BIGINT NOT NULL REFERENCES playlists(id_playlist) ON DELETE CASCADE,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (id_musica, id_playlist)
);

-- ======================
-- ÍNDICES ÚTEIS
-- ======================
CREATE INDEX idx_musicas_album   ON musicas(id_album);
CREATE INDEX idx_musicas_usuario ON musicas(id_usuario);
CREATE INDEX idx_playlists_dono  ON playlists(id_dono);
CREATE INDEX idx_mp_playlist     ON musica_playlist(id_playlist);
