import socket
import json

# Encryptions
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5000


class ClientSocket:
    """
    טענת כניסה: אין.
טענת יציאה: יוצר חיבור לשרת, מייצר זוג מפתחות RSA, שולח את המפתח הציבורי לשרת, מקבל מפתח AES ו־nonce כשהם מוצפנים, מפענח אותם ויוצר אובייקט Cipher לצורך הצפנה ופענוח של התקשורת.
    """
    def __init__(self):
        try:
            # RSA keys
            self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            public_key = self.private_key.public_key()

            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )

            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect((SERVER_IP, SERVER_PORT))
            self.data = {} #מילון נתונים מקומי של הלקוח ששומר מידע על המשתמש המחובר

            print("Connected to server successfully.")
            print("Sending public key to the server.")
            self.client.sendall(public_pem)

            aes_key = self.client.recv(1024)
            aes_key = self.private_key.decrypt(
                aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            self.client.send("AES key received".encode('utf-8'))

            nonce = self.client.recv(1024)
            nonce = self.private_key.decrypt(
                nonce,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            self.client.send("Nonce key received".encode('utf-8'))

            #אובייקט הצפנה מסוג AES
            self.cipher = Cipher(
                algorithms.AES(aes_key),
                modes.CFB(nonce),
                backend=default_backend()
            )

        except Exception as e:
            print(f"Error while connecting to the server: {e}")
            self.client = None

    """
    טענת כניסה: data – נתונים להצפנה.
טענת יציאה: מחזיר את הנתונים לאחר הצפנה באמצעות AES.
"""
    def encrypt(self, data: bytes) -> bytes:
        aes_encryptor = self.cipher.encryptor()
        return aes_encryptor.update(data) + aes_encryptor.finalize()

    """
    טענת כניסה: data – נתונים מוצפנים.
טענת יציאה: מפענח את הנתונים ומחזיר אותם בפורמט קריא.
    """
    def decrypt(self, data: bytes) -> bytes:
        aes_decryptor = self.cipher.decryptor()
        return aes_decryptor.update(data) + aes_decryptor.finalize()

    """
    טענת כניסה: action – סוג הפעולה המבוקשת, data – נתוני הבקשה.
טענת יציאה: יוצר הודעת JSON, מוסיף אליה את ה־token וה־username אם קיימים, מצפין את ההודעה, שולח אותה לשרת, מקבל תשובה מוצפנת, מפענח אותה ומחזיר את הנתונים בפורמט JSON.
"""
    def send_request(self, action, data):
        if self.client is None:
            return {"status": "error", "message": "No connection established."}

        try:
            request = {"action": action, **data}

            if "token" in self.data and "username" in self.data:
                request["token"] = self.data["token"]
                request["username"] = self.data["username"]

            self.client.sendall(self.encrypt(json.dumps(request).encode()) + b"-- End Request --")

            response_buffer = b""
            END_MARKER = b"-- End Request --"

            while END_MARKER not in response_buffer:
                piece = self.client.recv(65535)
                if not piece:
                    return {"status": "error", "message": "Server disconnected."}
                response_buffer += piece

            encrypted_response, _rest = response_buffer.split(END_MARKER, 1)

            response = self.decrypt(encrypted_response)
            response_data = json.loads(response)

            if action in ["login", "register"] and response_data.get("status") == "success":
                self.data["token"] = response_data["token"]

            return response_data

        except Exception as e:
            return {"status": "error", "message": f"Connection error: {e}"}

    """
    טענת כניסה: אין.
טענת יציאה: סוגר את חיבור ה־socket של הלקוח מול השרת.
"""
    def close(self):
        if self.client:
            self.client.close()
