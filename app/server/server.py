import socket
import threading
import json
import os
from app.server.database import DatabaseManager
import secrets #ספרייה מובנית בפייתון שנועדה ליצור ערכים אקראיים בצורה קריפטוגרפית
import base64

#ספרייה מתקדמת להצפנה בפייתון
from cryptography.hazmat.primitives import serialization #ממיר מפתחות RSA לפורמט שאפשר לשלוח (PEM)
from cryptography.hazmat.primitives.asymmetric import padding #שכבת הגנה נוספת להצפנת RSA
from cryptography.hazmat.primitives import hashes #אלגוריתמים של hash
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes #הצפנה סימטרית AES
from cryptography.hazmat.backends import default_backend #המנוע שמבצע את ההצפנה בפועל
END_MARKER = b"-- End Request --"


class Server:
    """
    טענת כניסה: כתובת השרת ומספר הפורט
    טענת יציאה: מאתחלת את השרת, יוצרת בוקט ומאתחלת גישה למסד הנתונים,
    יוצרת מבנה לניהול סשנים ומוודאת שקיימת תיקיית server_files
    """
    def __init__(self, host="127.0.0.1", port=5000):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.db_manager = DatabaseManager()
        self.active_sessions = {}  # username -> token
        os.makedirs("server_files", exist_ok=True)

    """
    טענת כניסה: אין 
    טענת יציאה: מפעילה את השרת, מאזינה לחיבורים נכנסים, 
    מקבלת מפתח ציבורי מהלקוח, יוצרת מפתח AES וnonce, 
    מצפינה אותם ושולחת ללקוח. לאחר מכן פותחת Thread נפרד לכל לקוח.
    """
    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Server is running on {self.host}:{self.port}")

        while True:
            client_socket, addr = self.server_socket.accept()
            print(f"Accepted connection from {addr}")

            # -- Encryption handshake --
            public_pem = b""
            while True:
                part = client_socket.recv(4048)
                public_pem += part
                if b"-----END PUBLIC KEY-----" in public_pem:
                    break

            client_public_key = serialization.load_pem_public_key(public_pem)

            aes_key = os.urandom(32)
            nonce = os.urandom(16)

            encrypted_aes_key = client_public_key.encrypt(
                aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            client_socket.sendall(encrypted_aes_key)

            confirmation = client_socket.recv(1024).decode('utf-8')
            if confirmation != "AES key received":
                raise Exception("Client didn't receive the AES key.")

            encrypted_nonce = client_public_key.encrypt(
                nonce,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            client_socket.sendall(encrypted_nonce)

            confirmation = client_socket.recv(1024).decode('utf-8')
            if confirmation != "Nonce key received":
                raise Exception("Client didn't receive the nonce.")

            cipher = Cipher(algorithms.AES(aes_key), modes.CFB(nonce), backend=default_backend())
            # -- End Encryption --

            client_thread = threading.Thread(target=self.handle_client, args=(client_socket, cipher))
            client_thread.start()

    """
    טענת כניסה: נתונים להצפנה (data) ואובייקט להצפנה (cipher).
    טענת יציאה: מחזירה את הנתונים לאחר ההצפנה באמצעות AES.
    
    """
    def encrypt(self, data: bytes, cipher) -> bytes:
        aes_encryptor = cipher.encryptor()
        return aes_encryptor.update(data) + aes_encryptor.finalize()

    """
    טענת כניסה: נתונים מוצפנים (data) ואובייקט ההצפנה (cipher).
    טענת יציאה: מפענחת את הנתונים ומחזירה אותם בפורמט קריא.
    """
    def decrypt(self, data: bytes, cipher) -> bytes:
        decryptor = cipher.decryptor()
        return decryptor.update(data) + decryptor.finalize()

    """
    טענת כניסה: סוקט של הלקוח ואובייקט הצפנה.
    טענת יציאה: מטפלת בכל הבקשות שמגיעות מלקוח מסויים: קוראת הודעה מלאה עד END_MARKER, מפענחת אותה, מעבירה לעיבוד, מצפינה את התשובה ושולחת אותה חזרה.
    """
    def handle_client(self, client_socket, cipher):
        try:
            buffer = b""
            while True:
                # receive full encrypted request until END_MARKER
                while END_MARKER not in buffer:
                    chunk = client_socket.recv(65535)
                    if not chunk:
                        return
                    buffer += chunk

                encrypted_request, buffer = buffer.split(END_MARKER, 1)

                request_data = self.decrypt(encrypted_request, cipher)
                if not request_data:
                    break

                request = json.loads(request_data)
                action = request.get("action")
                response = self.process_request(action, request)

                encrypted_response = self.encrypt(json.dumps(response).encode(), cipher)
                client_socket.sendall(encrypted_response + END_MARKER)

        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client_socket.close()
    """
    טענת כניסה: סוג הפעולה שנשלחה (action) ותוכן הבקשה (request).
    טענת יציאה: מנתבת את הבקשה לפונקציה מתאימה לפי סוג הפעולה, כגון הרשמה, התחברות, יצירת קובץ, העלאה, הורדה או פעולות מנהל.
    """
    def process_request(self, action, request):
        if action == "register":
            return self.register_user(request)
        elif action == "login":
            return self.login_user(request)

        # file actions
        elif action == "add_file":
            return self.save_file_on_server(request)
        elif action == "update_file":
            return self.update_file_content(request)
        elif action == "check_file_exists":
            return self.check_file_exists(request)
        elif action == "get_projects":
            return self.get_user_projects(request)
        elif action == "get_file_content":
            return self.get_file_content(request)
        elif action == "delete_file":
            return self.delete_file(request)
        elif action == "upload_binary_file":
            return self.upload_binary_file(request)
        elif action == "get_uploaded_files":
            return self.get_uploaded_files(request)
        elif action == "download_binary_file":
            return self.download_binary_file(request)
        elif action == "delete_uploaded_file":
            return self.delete_uploaded_file(request)




        # admin actions
        elif action == "get_users":
            return self.get_users(request)
        elif action == "set_admin":
            return self.set_admin(request)
        elif action == "delete_user_admin":
            return self.delete_user_admin(request)


        return {"status": "error", "message": "Invalid action."}

    """
    טענת כניסה: request - בקשה הכוללת original_name, token, username וdata.
    טענת יציאה: מפענחת קובץ שהתקבל לbase64, שומרת אותו בתיקיית uploads של המשתמש ומוסיפה מידע על הקבצים לטבלת user_files.
    """
    def upload_binary_file(self, request):
        token_check = self.check_token_validity(request)
        if token_check["status"] != "success":
            return token_check

        username = request.get("username")
        original_name = request.get("original_name")
        b64_data = request.get("data")

        if not username or not original_name or not b64_data:
            return {"status": "error", "message": "Missing username/original_name/data"}

        try:
            raw = base64.b64decode(b64_data.encode("utf-8"))

            user_folder = os.path.join("server_files", username, "uploads")
            os.makedirs(user_folder, exist_ok=True)

            save_path = os.path.join(user_folder, original_name)

            with open(save_path, "wb") as f:
                f.write(raw)

            # שמירת מטא-דאטה במסד הנתונים
            self.db_manager.add_user_file(username, original_name, save_path)

            return {
                "status": "success",
                "message": "File uploaded",
                "saved_as": original_name
            }

        except Exception as e:
            return {"status": "error", "message": f"Upload failed: {e}"}

    """
    טענת כניסה: request - בקשה הכוללת שם משתמש וטוקן.
    טענת יציאה: בודקת האם הטוקן שנשלח תואם לסשן הפעיל של המשתמש ומחזירה תשובת הצלחה או שגיאה.
    """
    def check_token_validity(self, request):
        username = request.get("username")
        token = request.get("token")

        if not username or not token:
            return {"status": "error", "message": "Username or token is missing."}

        if self.active_sessions.get(username) != token:
            return {"status": "error", "message": "Invalid token."}

        return {"status": "success", "message": "Token is valid."}

    """
    טענת כניסה: request - בקשה הכוללת שם משתמש וטוקן.
    טענת יציאה: בודקת שהטוקן תקף ושהמשתמש הוא מנהל מערכת. מחזירה תשובת הצלחה או שגיאה.
    """
    def require_admin(self, request):
        token_check = self.check_token_validity(request)
        if token_check["status"] != "success":
            return token_check

        username = request.get("username")
        if not self.db_manager.is_admin(username):
            return {"status": "error", "message": "Admin permission required."}

        return {"status": "success", "message": "Admin ok."}

    """
    טענת כניסה: אין
    טענת יציאה: יוצרת ומחזירה Token אקראי חדש עבור סשן של משתמש.
    """
    @staticmethod
    def generate_token():
        return secrets.token_hex(16)

    # ---------------- Users ----------------

    """
    טענת כניסה: request- בקשה הכוללת שם משתמש וסיסמה.
    טענת יציאה: רושמת משתמש חדש במסד הנתונים. במקרה של הצלחה נוצרת גם סשן חדשה עם טוקן
    """
    def register_user(self, request):
        username = request.get("username")
        password = request.get("password")

        if self.db_manager.register_user(username, password):
            token = self.generate_token()
            self.active_sessions[username] = token
            return {"status": "success", "message": "Registration successful!", "token": token}
        return {"status": "error", "message": "Username already exists."}

    """
    טענת כניסה: request- בקשה הכוללת שם משתמש וסיסמה.
    טענת יציאה: מאמתת את פרטי ההתחברות מול מסד הנתונים. אם ההתחברות מצליחה, נוצר Token חדש ונשלח ללקוח.
    """
    def login_user(self, request):
        username = request.get("username")
        password = request.get("password")

        if self.db_manager.authenticate_user(username, password):
            token = self.generate_token()
            self.active_sessions[username] = token
            return {"status": "success", "message": "Login successful!", "token": token}
        return {"status": "error", "message": "Invalid username or password."}

    # ---------------- File operations ----------------

    """
    טענת כניסה: request – בקשה הכוללת שם משתמש, טוקן ושם קובץ.
    טענת יציאה: מוחק את הקובץ מהשרת וגם מסיר את הרשומה שלו ממסד הנתונים.
    """
    def delete_file(self, request):
        token_check = self.check_token_validity(request)
        if token_check["status"] != "success":
            return token_check

        username = request.get("username")
        filename = request.get("filename")

        if username and filename:
            user_folder = os.path.join("server_files", username)
            file_path = os.path.join(user_folder, filename + ".json")
            try:
                os.remove(file_path)

                # מחיקת המטא-דאטה מה-DB
                self.db_manager.delete_user_file_record(username, filename + ".json")

                return {"status": "success", "message": "File Deleted."}
            except Exception:
                return {"status": "error", "message": "Failed to delete file."}

        return {"status": "error", "message": "Username or filename is missing."}

    """
    טענת כניסה: request – בקשה הכוללת שם משתמש, טוקן ושם קובץ.
    טענת יציאה: מחזיר את תוכן הקובץ מהשרת בפורמט JSON.
    """
    def get_file_content(self, request):
        token_check = self.check_token_validity(request)
        if token_check["status"] != "success":
            return token_check

        username = request.get("username")
        filename = request.get("project_name") or request.get("filename")

        if username and filename:
            user_folder = os.path.join("server_files", username)
            file_path = os.path.join(user_folder, filename + ".json")

            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read()
                return {"status": "success", "content": content}

            return {"status": "error", "message": f"File '{filename}' does not exist."}

        return {"status": "error", "message": "Username or filename is missing."}


    def save_file_on_server(self, request):
        token_check = self.check_token_validity(request)
        if token_check["status"] != "success":
            return token_check

        username = request.get("username")
        filename = request.get("filename")

        if username and filename:
            user_folder = os.path.join("server_files", username)
            os.makedirs(user_folder, exist_ok=True)

            file_path = os.path.join(user_folder, filename + ".json")
            with open(file_path, "w", encoding="utf-8") as file:
                file.write("")

            # שמירת מטא-דאטה במסד הנתונים
            self.db_manager.add_user_file(username, filename + ".json", file_path)

            return {
                "status": "success",
                "message": f"File '{filename}' created successfully for user '{username}'."
            }

        return {"status": "error", "message": "Username or filename is missing."}

    """
    טענת כניסה: request – בקשה הכוללת שם משתמש, טוקן, שם קובץ ותוכן.
    טענת יציאה: מעדכן את תוכן הקובץ הקיים בשרת לפי הנתונים שנשלחו.
    """
    def update_file_content(self, request):
        token_check = self.check_token_validity(request)
        if token_check["status"] != "success":
            return token_check

        username = request.get("username")
        filename = request.get("filename")
        content = request.get("content")

        if username and filename:
            user_folder = os.path.join("server_files", username)
            file_path = os.path.join(user_folder, filename + ".json")

            with open(file_path, "w", encoding="utf-8") as file:
                file.write(json.dumps(content))

            return {"status": "success", "message": "File content updated successfully."}

        return {"status": "error", "message": "Username or filename is missing."}

    """
    טענת כניסה: request – בקשה הכוללת שם משתמש, טוקן ושם קובץ.
    טענת יציאה: בודק אם הקובץ קיים ומחזיר תשובה בהתאם.
    """
    def check_file_exists(self, request):
        token_check = self.check_token_validity(request)
        if token_check["status"] != "success":
            return token_check

        username = request.get("username")
        filename = request.get("filename")

        if username and filename:
            user_folder = os.path.join("server_files", username)
            file_path = os.path.join(user_folder, filename + ".json")

            if os.path.exists(file_path):
                return {"status": "exists", "message": f"The file {filename} exists."}
            return {"status": "success", "message": "File does not exist."}

        return {"status": "error", "message": "Username or filename is missing."}

    """
    טענת כניסה: request – בקשה הכוללת שם משתמש וטוקן.
    טענת יציאה: מחזיר רשימת כל הקבצים של המשתמש.
    """
    def get_user_projects(self, request):
        token_check = self.check_token_validity(request)
        if token_check["status"] != "success":
            return token_check

        username = request.get("username")
        if not username:
            return {"status": "error", "message": "Username is missing."}

        user_folder = os.path.join("server_files", username)
        if os.path.exists(user_folder):
            projects = [
                fn.split(".")[0]
                for fn in os.listdir(user_folder)
                if fn.endswith(".json")
            ]

            return {"status": "success", "projects": projects}

        return {"status": "success", "projects": []}

    """
    טענת כניסה: request – בקשה הכוללת שם משתמש וטוקן.
    טענת יציאה: מחזיר רשימת קבצים שהמשתמש העלה.
    """
    def get_uploaded_files(self, request):
        token_check = self.check_token_validity(request)
        if token_check["status"] != "success":
            return token_check

        username = request.get("username")
        uploads_folder = os.path.join("server_files", username, "uploads")

        if os.path.exists(uploads_folder):
            files = os.listdir(uploads_folder)
            return {"status": "success", "files": files}

        return {"status": "success", "files": []}

    """
    טענת כניסה: request – בקשה הכוללת שם משתמש, טוקן ושם קובץ.
    טענת יציאה: מחזיר את הקובץ כשהוא מקודד ב־Base64.
    """
    def download_binary_file(self, request):
        token_check = self.check_token_validity(request)
        if token_check["status"] != "success":
            return token_check

        username = request.get("username")
        filename = request.get("filename")  # שם הקובץ כמו שמופיע ב-[UPLOAD]
        if not username or not filename:
            return {"status": "error", "message": "Missing username/filename"}

        uploads_folder = os.path.join("server_files", username, "uploads")
        file_path = os.path.join(uploads_folder, filename)

        if not os.path.exists(file_path):
            return {"status": "error", "message": "File not found"}

        try:
            with open(file_path, "rb") as f:
                raw = f.read()

            return {
                "status": "success",
                "filename": filename,
                "data": base64.b64encode(raw).decode("utf-8")
            }
        except Exception as e:
            return {"status": "error", "message": f"Download failed: {e}"}

    """
    טענת כניסה: request – בקשה הכוללת שם משתמש, טוקן ושם קובץ.
    טענת יציאה: מוחק קובץ שהועלה וגם את הרשומה שלו מהמסד.
    """
    def delete_uploaded_file(self, request):
        token_check = self.check_token_validity(request)
        if token_check["status"] != "success":
            return token_check

        username = request.get("username")
        filename = request.get("filename")

        if not username or not filename:
            return {"status": "error", "message": "Username or filename is missing."}

        uploads_folder = os.path.join("server_files", username, "uploads")
        file_path = os.path.join(uploads_folder, filename)

        if not os.path.exists(file_path):
            return {"status": "error", "message": "File not found."}

        try:
            os.remove(file_path)

            # מחיקת המטא-דאטה מה-DB
            self.db_manager.delete_user_file_record(username, filename)

            return {"status": "success", "message": "Uploaded file deleted."}
        except Exception as e:
            return {"status": "error", "message": f"Failed to delete file: {e}"}


    # ---------------- Admin operations ----------------

    """
    טענת כניסה: request – בקשה הכוללת שם משתמש וטוקן.
    טענת יציאה: מחזיר רשימת כל המשתמשים במערכת (למנהל בלבד)
    """
    def get_users(self, request):
        admin_check = self.require_admin(request)
        if admin_check["status"] != "success":
            return admin_check

        users = self.db_manager.get_all_users()
        # users is list of tuples (username, is_admin)
        payload = [{"username": u, "is_admin": bool(a)} for (u, a) in users]
        return {"status": "success", "users": payload}

    """
    טענת כניסה: request – בקשה הכוללת שם משתמש, טוקן, משתמש יעד והרשאה.
    טענת יציאה: מעדכן הרשאות מנהל למשתמש.
    """
    def set_admin(self, request):
        admin_check = self.require_admin(request)
        if admin_check["status"] != "success":
            return admin_check

        target_username = request.get("target_username")
        is_admin = request.get("is_admin")

        if target_username is None or is_admin is None:
            return {"status": "error", "message": "target_username or is_admin missing."}

        ok = self.db_manager.set_admin(target_username, 1 if is_admin else 0)
        if ok:
            return {"status": "success", "message": "Admin updated."}
        return {"status": "error", "message": "User not found."}

    """
    טענת כניסה: request – בקשה הכוללת שם משתמש, טוקן ומשתמש יעד.
    טענת יציאה: מוחק משתמש מהמערכת (לא ניתן למחוק את המשתמש עצמו).
    """
    def delete_user_admin(self, request):
        admin_check = self.require_admin(request)
        if admin_check["status"] != "success":
            return admin_check

        target_username = request.get("target_username")
        if not target_username:
            return {"status": "error", "message": "target_username missing."}

        # לא לתת לאדמין למחוק את עצמו
        if target_username == request.get("username"):
            return {"status": "error", "message": "You can't delete yourself."}

        ok = self.db_manager.delete_user(target_username)
        if ok:
            self.active_sessions.pop(target_username, None)
            return {"status": "success", "message": "User deleted."}
        return {"status": "error", "message": "User not found."}

    """
    טענת כניסה: אין.
    טענת יציאה: סוגר את השרת ומפסיק את פעולתו.
    """
    def stop(self):
        self.server_socket.close()
        print("Server has been stopped.")


if __name__ == "__main__":
    server = Server()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
