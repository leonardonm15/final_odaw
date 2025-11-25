-- Seed data for quick API demos (idempotent)
-- Expects pgcrypto extension enabled (see setup.sql)

DO $$
DECLARE
  u_alice BIGINT;
  u_bob   BIGINT;
  alb1    BIGINT;
  alb2    BIGINT;
  pl1     BIGINT;
  pl2     BIGINT;
BEGIN
  -- Users
  SELECT id_usuario INTO u_alice FROM usuarios WHERE email = 'alice@example.com';
  IF u_alice IS NULL THEN
    INSERT INTO usuarios (nome, email, senha_hash, role)
    VALUES ('Alice Indie', 'alice@example.com', crypt('password123', gen_salt('bf')), 'user')
    RETURNING id_usuario INTO u_alice;
  END IF;

  SELECT id_usuario INTO u_bob FROM usuarios WHERE email = 'bob@example.com';
  IF u_bob IS NULL THEN
    INSERT INTO usuarios (nome, email, senha_hash, role)
    VALUES ('Bob Admin', 'bob@example.com', crypt('adminpass', gen_salt('bf')), 'admin')
    RETURNING id_usuario INTO u_bob;
  END IF;

  -- Albums
  SELECT id_album INTO alb1 FROM albuns WHERE titulo = 'Indie Vibes' AND id_usuario = u_alice;
  IF alb1 IS NULL THEN
    INSERT INTO albuns (titulo, ano, id_usuario)
    VALUES ('Indie Vibes', 2024, u_alice)
    RETURNING id_album INTO alb1;
  END IF;

  SELECT id_album INTO alb2 FROM albuns WHERE titulo = 'Rock Night' AND id_usuario = u_bob;
  IF alb2 IS NULL THEN
    INSERT INTO albuns (titulo, ano, id_usuario)
    VALUES ('Rock Night', 2023, u_bob)
    RETURNING id_album INTO alb2;
  END IF;

  -- Songs
  IF NOT EXISTS (SELECT 1 FROM musicas WHERE nome = 'Skyline Dreams' AND id_album = alb1) THEN
    INSERT INTO musicas (nome, genero, duracao_seg, id_album, id_usuario)
    VALUES ('Skyline Dreams', 'Indie', 210, alb1, u_alice);
  END IF;

  IF NOT EXISTS (SELECT 1 FROM musicas WHERE nome = 'Midnight Echoes' AND id_album = alb1) THEN
    INSERT INTO musicas (nome, genero, duracao_seg, id_album, id_usuario)
    VALUES ('Midnight Echoes', 'Indie', 185, alb1, u_alice);
  END IF;

  IF NOT EXISTS (SELECT 1 FROM musicas WHERE nome = 'Riff Runner' AND id_album = alb2) THEN
    INSERT INTO musicas (nome, genero, duracao_seg, id_album, id_usuario)
    VALUES ('Riff Runner', 'Rock', 200, alb2, u_bob);
  END IF;

  -- Playlists
  SELECT id_playlist INTO pl1 FROM playlists WHERE nome = 'Chill Mix' AND id_dono = u_alice;
  IF pl1 IS NULL THEN
    INSERT INTO playlists (nome, id_dono)
    VALUES ('Chill Mix', u_alice)
    RETURNING id_playlist INTO pl1;
  END IF;

  SELECT id_playlist INTO pl2 FROM playlists WHERE nome = 'Gym Rock' AND id_dono = u_bob;
  IF pl2 IS NULL THEN
    INSERT INTO playlists (nome, id_dono)
    VALUES ('Gym Rock', u_bob)
    RETURNING id_playlist INTO pl2;
  END IF;

  -- Playlist contents
  INSERT INTO musica_playlist (id_playlist, id_musica)
  SELECT pl1, id_musica FROM musicas WHERE nome IN ('Skyline Dreams', 'Midnight Echoes')
  ON CONFLICT DO NOTHING;

  INSERT INTO musica_playlist (id_playlist, id_musica)
  SELECT pl2, id_musica FROM musicas WHERE nome = 'Riff Runner'
  ON CONFLICT DO NOTHING;
END$$;
