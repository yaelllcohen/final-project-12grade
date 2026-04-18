import sqlite3
from app.server.settings import DATABASE_FILE
import bcrypt
from app.server.Hashing import Hashing


class DatabaseManager:
    """
    טענת כניסה: אין.
טענת יציאה: מאתחלת את המחלקה, שומרת את מיקום מסד הנתונים וקוראת לפונקציה היוצרת את הטבלאות הדרושות.
    """
    def __init__(self):
        self.database_file = DATABASE_FILE #הנתיב לקובץ מסד הנתונים
        self.create_tables()

    """
    טענת כניסה: אין.
טענת יציאה: פותחת ומחזירה חיבור למסד הנתונים מסוג SQLite.
"""
    def get_connection(self):
        return sqlite3.connect(self.database_file)

    """
    טענת כניסה: אין.
טענת יציאה: יוצרת את הטבלאות users ו־user_files אם הן אינן קיימות,
 ובודקת אם יש צורך להוסיף את השדה is_admin למסד ישן.
"""
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

            cursor.execute("PRAGMA table_info(users)")
            cols = [row[1] for row in cursor.fetchall()]
            if "is_admin" not in cols:
                cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")

            conn.commit()
        finally:
            conn.close()

    """
    טענת כניסה: username – שם משתמש, password – סיסמה.
טענת יציאה: יוצר משתמש חדש במסד הנתונים לאחר ביצוע Hash לסיסמה באמצעות bcrypt. 
אם שם המשתמש כבר קיים, מוחזרת תשובת כישלון.
"""
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

    """
    טענת כניסה: username – שם המשתמש המבוקש.
טענת יציאה: מחזיר את נתוני המשתמש מתוך מסד הנתונים, כולל הסיסמה וההרשאה, אם המשתמש קיים.
"""
    def get_user(self, username):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT username, password, is_admin FROM users WHERE username=?", (username,))
            return cursor.fetchone()
        finally:
            conn.close()

    """
    טענת כניסה: username – שם משתמש, password – סיסמה.
טענת יציאה: בודק אם המשתמש קיים ואם הסיסמה שהוזנה תואמת לסיסמה השמורה במסד הנתונים.
"""
    def authenticate_user(self, username, password):
        user = self.get_user(username)
        if user is None:
            return False
        return Hashing.check_password(user[1], password)

    """
    טענת כניסה: username – שם המשתמש.
טענת יציאה: בודק האם למשתמש יש הרשאות מנהל ומחזיר ערך בוליאני בהתאם.
"""
    def is_admin(self, username) -> bool:
        user = self.get_user(username)
        if not user:
            return False
        return bool(user[2])

    # -------- Admin operations --------

    """
    טענת כניסה: אין.
טענת יציאה: מחזיר רשימה של כל המשתמשים במערכת יחד עם מצב ההרשאה שלהם (is_admin).
"""
    def get_all_users(self):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT username, is_admin FROM users ORDER BY username")
            return cursor.fetchall()
        finally:
            conn.close()

    """
    טענת כניסה: username – שם המשתמש, is_admin – ערך הרשאה (0 או 1).
טענת יציאה: מעדכן את הרשאת המנהל של המשתמש במסד הנתונים.
"""
    def set_admin(self, username, is_admin: int) -> bool:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_admin=? WHERE username=?", (1 if is_admin else 0, username))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    """
    טענת כניסה: username – שם המשתמש למחיקה.
    טענת יציאה: מוחק משתמש ממסד הנתונים ומחזיר האם הפעולה הצליחה.
    """
    def delete_user(self, username) -> bool:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE username=?", (username,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    """
    טענת כניסה: username - שם המשתמש, filename - שם הקובץ, file_path – נתיב הקובץ בשרת.
טענת יציאה: מוסיף רשומת מטא־דאטה חדשה לטבלת user_files.
 אם כבר קיימת רשומה לאותו קובץ, היא נמחקת קודם כדי למנוע כפילות.
"""
    def add_user_file(self, username, filename, file_path):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            # אם כבר קיימת רשומה לאותו משתמש+קובץ, זה יימחק כדי לא ליצור כפילות
            cursor.execute(
                "DELETE FROM user_files WHERE username=? AND filename=?",
                (username, filename)
            )

            cursor.execute(
                """
                INSERT INTO user_files (username, filename, file_path)
                VALUES (?, ?, ?)
                """,
                (username, filename, file_path)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding user file: {e}")
            return False
        finally:
            conn.close()

    """
    טענת כניסה: username – שם המשתמש, filename – שם הקובץ.
טענת יציאה: מוחק את רשומת המטא־דאטה של הקובץ מטבלת user_files.
"""
    def delete_user_file_record(self, username, filename):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM user_files WHERE username=? AND filename=?",
                (username, filename)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting user file record: {e}")
            return False
        finally:
            conn.close()

    """
    טענת כניסה: username – שם המשתמש.
טענת יציאה: מחזיר את כל רשומות הקבצים של המשתמש מטבלת user_files, ממוינות לפי תאריך העלאה.
"""
    def get_user_files(self, username):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, filename, file_path, upload_date
                FROM user_files
                WHERE username=?
                ORDER BY upload_date DESC
                """,
                (username,)
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"Error getting user files: {e}")
            return []
        finally:
            conn.close()

    """
    טענת כניסה: username – שם המשתמש, filename – שם הקובץ.
טענת יציאה: בודק האם קיימת רשומה של הקובץ עבור המשתמש במסד הנתונים ומחזיר ערך בוליאני בהתאם.
"""
    def file_record_exists(self, username, filename):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 1 FROM user_files
                WHERE username=? AND filename=?
                LIMIT 1
                """,
                (username, filename)
            )
            return cursor.fetchone() is not None
        except Exception as e:
            print(f"Error checking file record exists: {e}")
            return False
        finally:
            conn.close()
