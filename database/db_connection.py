"""
Camada de conexão com o PostgreSQL.

Este módulo era importado por `app.py` e `scheduler/scheduler_tasks.py`
(`from database.db_connection import db`) mas não existia no projeto.
Foi reconstruído com base na assinatura que o restante do código já espera:

    db.connect()                       -> bool
    db.is_connected()                  -> bool
    db.create_tables()                 -> None
    db.execute_query(query, params)    -> list[dict]
    db.execute_update(query, params)   -> bool

O projeto foi desenhado para funcionar em modo "fallback": se o PostgreSQL
não estiver disponível, os serviços continuam funcionando com os arquivos
CSV (dataset_consolidado.csv e historico_consultas.csv).
"""

import os
import logging

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class Database:
    """Wrapper simples sobre psycopg2 com reconexão e fallback seguro."""

    def __init__(self):
        self._conn = None

    # ------------------------------------------------------------------ #
    # Conexão
    # ------------------------------------------------------------------ #
    def connect(self) -> bool:
        """Abre a conexão usando DATABASE_URL. Retorna True/False."""
        database_url = os.getenv("DATABASE_URL", "").strip()

        if not database_url:
            logger.warning("[AVISO] DATABASE_URL não configurada. Usando fallback em CSV.")
            return False

        try:
            self._conn = psycopg2.connect(database_url, connect_timeout=5)
            self._conn.autocommit = True
            logger.info("[INFO] Conexão com PostgreSQL estabelecida.")
            return True
        except Exception as e:
            logger.error(f"[ERRO] Falha ao conectar ao PostgreSQL: {e}")
            self._conn = None
            return False

    def is_connected(self) -> bool:
        """Verifica se a conexão está ativa, fazendo um ping leve."""
        if self._conn is None or self._conn.closed:
            return False
        try:
            with self._conn.cursor() as cur:
                cur.execute("SELECT 1;")
            return True
        except Exception:
            return False

    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()
            logger.info("[INFO] Conexão com PostgreSQL encerrada.")

    # ------------------------------------------------------------------ #
    # Schema
    # ------------------------------------------------------------------ #
    def create_tables(self):
        """Cria as tabelas usadas pelo restante da aplicação, se não existirem."""
        if not self.is_connected():
            return

        ddl = """
        CREATE TABLE IF NOT EXISTS historico_consultas (
            id          SERIAL PRIMARY KEY,
            data_hora   TIMESTAMP NOT NULL DEFAULT NOW(),
            texto       TEXT NOT NULL,
            fonte       TEXT NOT NULL,
            resultado   TEXT NOT NULL,
            confianca   NUMERIC(5, 2)
        );

        CREATE TABLE IF NOT EXISTS dataset_consolidado (
            id           SERIAL PRIMARY KEY,
            texto        TEXT NOT NULL UNIQUE,
            label        TEXT NOT NULL,
            fonte        TEXT,
            data_coleta  DATE NOT NULL DEFAULT CURRENT_DATE,
            confianca    NUMERIC(5, 2)
        );

        CREATE TABLE IF NOT EXISTS retreinamentos (
            id               SERIAL PRIMARY KEY,
            data_inicio      TIMESTAMP NOT NULL,
            data_fim         TIMESTAMP,
            accuracy         NUMERIC(6, 4),
            precision        NUMERIC(6, 4),
            recall           NUMERIC(6, 4),
            f1_score         NUMERIC(6, 4),
            tamanho_dataset  INTEGER,
            status           TEXT NOT NULL
        );
        """

        try:
            with self._conn.cursor() as cur:
                cur.execute(ddl)
            logger.info("[INFO] Tabelas verificadas/criadas com sucesso.")
        except Exception as e:
            logger.error(f"[ERRO] Falha ao criar tabelas: {e}")

    # ------------------------------------------------------------------ #
    # Operações
    # ------------------------------------------------------------------ #
    def execute_query(self, query: str, params: tuple | None = None):
        """Executa um SELECT e retorna uma lista de dicts (RealDictCursor)."""
        if not self.is_connected():
            return []

        try:
            with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchall()
        except Exception as e:
            logger.error(f"[ERRO] Falha ao executar query: {e}")
            return []

    def execute_update(self, query: str, params: tuple | None = None) -> bool:
        """Executa INSERT/UPDATE/DELETE. Retorna True em caso de sucesso."""
        if not self.is_connected():
            return False

        try:
            with self._conn.cursor() as cur:
                cur.execute(query, params)
            return True
        except Exception as e:
            logger.error(f"[ERRO] Falha ao executar update: {e}")
            return False


# Instância única, importada em todo o projeto via:
#   from database.db_connection import db
db = Database()
