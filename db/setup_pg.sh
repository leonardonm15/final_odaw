#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------
# PostgreSQL setup rápido (instala, cria usuário, DB e GRANT)
# Suporta: Debian/Ubuntu (APT) | Fedora (DNF) | Arch (pacman)
# Uso:
#   ./setup_pg.sh -d <db_name> -u <db_user> -p <db_password>
# ou exporte:
#   DB_NAME=streaming DB_USER=leo DB_PASSWORD='senha' ./setup_pg.sh
# -----------------------------------------------------------

DB_NAME="${DB_NAME:-}"
DB_USER="${DB_USER:-}"
DB_PASSWORD="${DB_PASSWORD:-}"

while getopts ":d:u:p:h" opt; do
  case "$opt" in
    d) DB_NAME="$OPTARG" ;;
    u) DB_USER="$OPTARG" ;;
    p) DB_PASSWORD="$OPTARG" ;;
    h)
      echo "Uso: $0 -d <db_name> -u <db_user> -p <db_password>"
      exit 0
      ;;
    \?)
      echo "Opção inválida: -$OPTARG" >&2; exit 1 ;;
  esac
done

if [[ -z "${DB_NAME}" || -z "${DB_USER}" || -z "${DB_PASSWORD}" ]]; then
  echo "Erro: informe -d, -u e -p (ou DB_NAME/DB_USER/DB_PASSWORD no ambiente)." >&2
  exit 1
fi

echo "==> Detectando gerenciador de pacotes…"
PKG=""
if command -v apt-get >/dev/null 2>&1; then
  PKG="apt"
elif command -v dnf >/dev/null 2>&1; then
  PKG="dnf"
elif command -v pacman >/dev/null 2>&1; then
  PKG="pacman"
else
  echo "Erro: não encontrei apt/dnf/pacman. Instale o PostgreSQL manualmente." >&2
  exit 1
fi

echo "==> Instalando PostgreSQL… (sudo requisitado)"
case "$PKG" in
  apt)
    sudo apt-get update -y
    sudo apt-get install -y postgresql postgresql-contrib
    # Em Debian/Ubuntu o cluster já vem inicializado
    sudo systemctl enable postgresql
    sudo systemctl start postgresql
    ;;
  dnf)
    sudo dnf install -y postgresql-server postgresql-contrib
    # Inicializa se ainda não houver data dir
    if [ ! -d /var/lib/pgsql/data/base ]; then
      sudo postgresql-setup --initdb
    fi
    sudo systemctl enable postgresql
    sudo systemctl start postgresql
    ;;
  pacman)
    sudo pacman -Sy --noconfirm postgresql
    # Inicializa se necessário
    if [ ! -d /var/lib/postgres/data/base ]; then
      sudo -u postgres initdb -D /var/lib/postgres/data
    fi
    sudo systemctl enable postgresql
    sudo systemctl start postgresql
    ;;
esac

echo "==> Criando ROLE (usuário da aplicação) de forma idempotente…"
# Cria usuário se não existir
if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1; then
  echo "   - Usuário '${DB_USER}' já existe; atualizando senha…"
  sudo -u postgres psql -v ON_ERROR_STOP=1 -c "ALTER ROLE \"${DB_USER}\" WITH LOGIN ENCRYPTED PASSWORD '${DB_PASSWORD}';"
else
  echo "   - Criando usuário '${DB_USER}'…"
  sudo -u postgres psql -v ON_ERROR_STOP=1 -c "CREATE ROLE \"${DB_USER}\" WITH LOGIN ENCRYPTED PASSWORD '${DB_PASSWORD}';"
fi

echo "==> Criando DATABASE de forma idempotente…"
# Cria DB se não existir
if sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
  echo "   - Banco '${DB_NAME}' já existe."
else
  echo "   - Criando banco '${DB_NAME}'…"
  sudo -u postgres createdb "${DB_NAME}"
fi

echo "==> Concedendo privilégios ao usuário…"
sudo -u postgres psql -v ON_ERROR_STOP=1 -c "GRANT ALL PRIVILEGES ON DATABASE \"${DB_NAME}\" TO \"${DB_USER}\";"

# Opcional: definir como dono do DB (evita problemas de migração/criação de schema)
echo "==> (Opcional) Transferindo ownership do DB para '${DB_USER}'…"
sudo -u postgres psql -v ON_ERROR_STOP=1 -c "ALTER DATABASE \"${DB_NAME}\" OWNER TO \"${DB_USER}\";"

# Importante para novas tabelas post-13: garantir que o usuário terá privilégios em objetos futuros.
# Você pode ajustar depois por schema, mas aqui deixamos a dica:
cat <<'TIP'
[INFO] Dica pós-setup:
- Após criar o schema/tabelas, rode:
  ALTER SCHEMA public OWNER TO "<USER>";
  GRANT ALL ON SCHEMA public TO "<USER>";
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "<USER>";
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "<USER>";

- Se for usar hashing no SQL (crypt/pgcrypto), habilite dentro do DB:
  sudo -u postgres psql -d <DB> -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"
TIP

echo "✅ Pronto! DB='${DB_NAME}', USER='${DB_USER}' configurados."

