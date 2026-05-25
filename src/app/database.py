import json
import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator, Optional

import duckdb


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "document_checker.duckdb"


def database_path() -> Path:
    return Path(os.getenv("DUCKDB_PATH", str(DEFAULT_DATABASE_PATH))).resolve()


@contextmanager
def duckdb_connection() -> Iterator[duckdb.DuckDBPyConnection]:
    db_path = database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(db_path))
    try:
        yield connection
    finally:
        connection.close()


def init_database() -> None:
    UserRepository().init_schema()


@dataclass(frozen=True)
class UserRecord:
    email: str
    redirect: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime


@dataclass(frozen=True)
class SessionRecord:
    token_hash: str
    user_email: str
    created_at: datetime
    expires_at: datetime
    revoked: bool


@dataclass(frozen=True)
class ModelUsageRecord:
    user_email: str
    model_id: str
    used_count: int
    updated_at: datetime


@dataclass(frozen=True)
class CheckHistoryRecord:
    id: str
    user_email: str
    document_name: str
    template_name: Optional[str]
    model_id: str
    result: dict[str, Any]
    compliance_score: int
    errors_count: int
    source_file_path: Optional[str]
    source_content_type: Optional[str]
    created_at: datetime


class UserRepository:
    def init_schema(self) -> None:
        with duckdb_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    email TEXT PRIMARY KEY,
                    redirect TEXT,
                    auth_payload TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_login_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS model_usage (
                    user_email TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    used_count BIGINT NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_email, model_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_email TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    revoked BOOLEAN NOT NULL DEFAULT FALSE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS check_history (
                    id TEXT PRIMARY KEY,
                    user_email TEXT NOT NULL,
                    document_name TEXT NOT NULL,
                    template_name TEXT,
                    model_id TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    compliance_score BIGINT NOT NULL DEFAULT 0,
                    errors_count BIGINT NOT NULL DEFAULT 0,
                    source_file_path TEXT,
                    source_content_type TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def upsert_after_login(self, email: str, redirect: Optional[str], auth_payload: dict[str, Any]) -> UserRecord:
        payload = json.dumps(auth_payload, ensure_ascii=False)
        now = datetime.now()
        with duckdb_connection() as connection:
            connection.execute(
                """
                INSERT INTO users (email, redirect, auth_payload, created_at, updated_at, last_login_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (email) DO UPDATE SET
                    redirect = excluded.redirect,
                    auth_payload = excluded.auth_payload,
                    updated_at = excluded.updated_at,
                    last_login_at = excluded.last_login_at
                """,
                [email, redirect, payload, now, now, now],
            )
            user = self.get_by_email(email, connection=connection)
            if user is None:
                raise RuntimeError("Failed to load user after login")
            return user

    def get_by_email(
        self,
        email: str,
        connection: Optional[duckdb.DuckDBPyConnection] = None,
    ) -> Optional[UserRecord]:
        def fetch(conn: duckdb.DuckDBPyConnection) -> Optional[UserRecord]:
            row = conn.execute(
                """
                SELECT email, redirect, created_at, updated_at, last_login_at
                FROM users
                WHERE email = ?
                """,
                [email],
            ).fetchone()
            if row is None:
                return None
            return UserRecord(
                email=row[0],
                redirect=row[1],
                created_at=row[2],
                updated_at=row[3],
                last_login_at=row[4],
            )

        if connection is not None:
            return fetch(connection)

        with duckdb_connection() as new_connection:
            return fetch(new_connection)

    def list_users_with_check_stats(self) -> list[dict[str, Any]]:
        with duckdb_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    u.email,
                    u.redirect,
                    u.created_at,
                    u.updated_at,
                    u.last_login_at,
                    COUNT(h.id) AS check_count,
                    MAX(h.created_at) AS latest_check_at
                FROM users u
                LEFT JOIN check_history h ON h.user_email = u.email
                GROUP BY u.email, u.redirect, u.created_at, u.updated_at, u.last_login_at
                ORDER BY u.last_login_at DESC
                """
            ).fetchall()
            return [
                {
                    "email": row[0],
                    "redirect": row[1],
                    "created_at": row[2],
                    "updated_at": row[3],
                    "last_login_at": row[4],
                    "check_count": int(row[5] or 0),
                    "latest_check_at": row[6],
                }
                for row in rows
            ]


class SessionRepository:
    def create(self, token_hash: str, user_email: str, ttl: timedelta) -> SessionRecord:
        expires_at = datetime.now() + ttl
        with duckdb_connection() as connection:
            connection.execute(
                """
                INSERT INTO user_sessions (token_hash, user_email, created_at, expires_at, revoked)
                VALUES (?, ?, CURRENT_TIMESTAMP, ?, FALSE)
                """,
                [token_hash, user_email, expires_at],
            )
            session = self.get_active(token_hash, connection=connection)
            if session is None:
                raise RuntimeError("Failed to load session after creation")
            return session

    def get_active(
        self,
        token_hash: str,
        connection: Optional[duckdb.DuckDBPyConnection] = None,
    ) -> Optional[SessionRecord]:
        now = datetime.now()

        def fetch(conn: duckdb.DuckDBPyConnection) -> Optional[SessionRecord]:
            row = conn.execute(
                """
                SELECT token_hash, user_email, created_at, expires_at, revoked
                FROM user_sessions
                WHERE token_hash = ?
                    AND revoked = FALSE
                    AND expires_at > ?
                """,
                [token_hash, now],
            ).fetchone()
            if row is None:
                return None
            return SessionRecord(
                token_hash=row[0],
                user_email=row[1],
                created_at=row[2],
                expires_at=row[3],
                revoked=row[4],
            )

        if connection is not None:
            return fetch(connection)

        with duckdb_connection() as new_connection:
            return fetch(new_connection)

    def revoke(self, token_hash: str) -> None:
        with duckdb_connection() as connection:
            connection.execute(
                """
                UPDATE user_sessions
                SET revoked = TRUE
                WHERE token_hash = ?
                """,
                [token_hash],
            )


class ModelUsageRepository:
    def get_usage(self, user_email: str, model_id: str) -> int:
        with duckdb_connection() as connection:
            row = connection.execute(
                """
                SELECT used_count
                FROM model_usage
                WHERE user_email = ? AND model_id = ?
                """,
                [user_email, model_id],
            ).fetchone()
            return int(row[0]) if row else 0

    def increment_usage(self, user_email: str, model_id: str) -> int:
        used_count = self.consume_usage(user_email, model_id, usage_limit=None)
        return int(used_count or 0)

    def consume_usage(self, user_email: str, model_id: str, usage_limit: Optional[int]) -> Optional[int]:
        with duckdb_connection() as connection:
            connection.execute("BEGIN TRANSACTION")
            try:
                row = connection.execute(
                    """
                    SELECT used_count
                    FROM model_usage
                    WHERE user_email = ? AND model_id = ?
                    """,
                    [user_email, model_id],
                ).fetchone()
                used_count = int(row[0]) if row else 0
                if usage_limit is not None and used_count >= usage_limit:
                    connection.execute("ROLLBACK")
                    return None

                if row:
                    used_count += 1
                    connection.execute(
                        """
                        UPDATE model_usage
                        SET used_count = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE user_email = ? AND model_id = ?
                        """,
                        [used_count, user_email, model_id],
                    )
                else:
                    used_count = 1
                    connection.execute(
                        """
                        INSERT INTO model_usage (user_email, model_id, used_count, updated_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        [user_email, model_id, used_count],
                    )

                connection.execute("COMMIT")
                return used_count
            except Exception:
                connection.execute("ROLLBACK")
                raise

    def reset_usage(
        self,
        user_email: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> int:
        where: list[str] = []
        params: list[str] = []
        if user_email:
            where.append("user_email = ?")
            params.append(user_email)
        if model_id:
            where.append("model_id = ?")
            params.append(model_id)

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        with duckdb_connection() as connection:
            row = connection.execute(
                f"SELECT COUNT(*) FROM model_usage {where_sql}",
                params,
            ).fetchone()
            affected = int(row[0]) if row else 0
            connection.execute(
                f"DELETE FROM model_usage {where_sql}",
                params,
            )
            return affected


class CheckHistoryRepository:
    def create(
        self,
        user_email: str,
        document_name: str,
        template_name: Optional[str],
        model_id: str,
        result: dict[str, Any],
        source_file_path: Optional[str],
        source_content_type: Optional[str],
    ) -> CheckHistoryRecord:
        check_id = str(uuid.uuid4())
        compliance_score = int(result.get("compliance_score") or 0)
        errors_count = len(result.get("errors") or [])
        result_json = json.dumps(result, ensure_ascii=False)

        with duckdb_connection() as connection:
            connection.execute(
                """
                INSERT INTO check_history (
                    id,
                    user_email,
                    document_name,
                    template_name,
                    model_id,
                    result_json,
                    compliance_score,
                    errors_count,
                    source_file_path,
                    source_content_type,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                [
                    check_id,
                    user_email,
                    document_name,
                    template_name,
                    model_id,
                    result_json,
                    compliance_score,
                    errors_count,
                    source_file_path,
                    source_content_type,
                ],
            )
            record = self.get_by_id(check_id, connection=connection)
            if record is None:
                raise RuntimeError("Failed to load check history after creation")
            return record

    def list_for_user(self, user_email: str) -> list[CheckHistoryRecord]:
        return self._list(where_sql="WHERE user_email = ?", params=[user_email])

    def list_all(self, user_email: Optional[str] = None) -> list[CheckHistoryRecord]:
        if user_email:
            return self._list(where_sql="WHERE user_email = ?", params=[user_email])
        return self._list(where_sql="", params=[])

    def get_by_id(
        self,
        check_id: str,
        connection: Optional[duckdb.DuckDBPyConnection] = None,
    ) -> Optional[CheckHistoryRecord]:
        def fetch(conn: duckdb.DuckDBPyConnection) -> Optional[CheckHistoryRecord]:
            row = conn.execute(
                """
                SELECT
                    id,
                    user_email,
                    document_name,
                    template_name,
                    model_id,
                    result_json,
                    compliance_score,
                    errors_count,
                    source_file_path,
                    source_content_type,
                    created_at
                FROM check_history
                WHERE id = ?
                """,
                [check_id],
            ).fetchone()
            return self._record_from_row(row) if row else None

        if connection is not None:
            return fetch(connection)

        with duckdb_connection() as new_connection:
            return fetch(new_connection)

    def _list(self, where_sql: str, params: list[str]) -> list[CheckHistoryRecord]:
        with duckdb_connection() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    id,
                    user_email,
                    document_name,
                    template_name,
                    model_id,
                    result_json,
                    compliance_score,
                    errors_count,
                    source_file_path,
                    source_content_type,
                    created_at
                FROM check_history
                {where_sql}
                ORDER BY created_at DESC
                """,
                params,
            ).fetchall()
            return [self._record_from_row(row) for row in rows]

    @staticmethod
    def _record_from_row(row: tuple) -> CheckHistoryRecord:
        return CheckHistoryRecord(
            id=row[0],
            user_email=row[1],
            document_name=row[2],
            template_name=row[3],
            model_id=row[4],
            result=json.loads(row[5]),
            compliance_score=int(row[6] or 0),
            errors_count=int(row[7] or 0),
            source_file_path=row[8],
            source_content_type=row[9],
            created_at=row[10],
        )
