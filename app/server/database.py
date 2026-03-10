import sqlite3
from app.server.settings import DATABASE_FILE
import bcrypt
from app.server.Hashing import Hashing


class DatabaseManager:
    def __init__(self):
        self.database_file = DATABASE_FILE
        self.create_tables()

    def get_connection(self):
        return sqlite3.connect(self.database_file)

    def create_tables(self):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password BLOB NOT NULL,
                is_admin INTEGER DEFAULT 0
            )''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS user_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (username) REFERENCES users (username)
            )''')

            # אם יש DB ישן בלי is_admin – נוסיף את העמודה
            cursor.execute("PRAGMA table_info(users)")
            cols = [row[1] for row in cursor.fetchall()]
            if "is_admin" not in cols:
                cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")

            conn.commit()
        finally:
            conn.close()

    def register_user(self, username, password):
        conn = self.get_connection()
        try:
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode(), salt)

            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
                (username, hashed, 0)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_user(self, username):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT username, password, is_admin FROM users WHERE username=?", (username,))
            return cursor.fetchone()
        finally:
            conn.close()

    def authenticate_user(self, username, password):
        user = self.get_user(username)
        if user is None:
            return False
        return Hashing.check_password(user[1], password)

    def is_admin(self, username) -> bool:
        user = self.get_user(username)
        if not user:
            return False
        return bool(user[2])

    # -------- Admin operations --------

    def get_all_users(self):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT username, is_admin FROM users ORDER BY username")
            return cursor.fetchall()
        finally:
            conn.close()

    def set_admin(self, username, is_admin: int) -> bool:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_admin=? WHERE username=?", (1 if is_admin else 0, username))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_user(self, username) -> bool:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE username=?", (username,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
