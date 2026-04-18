"""
Manages all hashing operations used by the server.
"""
import bcrypt


class Hashing:

    """
    טענת כניסה: password – סיסמה בטקסט רגיל.
טענת יציאה: מחזיר את הסיסמה לאחר Hash באמצעות bcrypt כולל salt אקראי.

    """
    @staticmethod
    def hash_password(password: str) -> bytes:
        """
        Performs hashing of a password using the bcrypt library.
        :param password: The original password to be hashed.
        :return: The hashed password (in bytes).
        """
        # Generate a salt (random value) to strengthen the encryption
        salt = bcrypt.gensalt()

        # Hash the password using the generated salt
        hashed = bcrypt.hashpw(password.encode(), salt)

        return hashed  # Returns the hashed password

    """
    טענת כניסה: hashed_password – סיסמה מוצפנת מהמסד, password – סיסמה שהוזנה על ידי המשתמש.
טענת יציאה: בודק האם הסיסמה שהוזנה תואמת לסיסמה המוצפנת ומחזיר אמת או שקר בהתאם.
"""
    @staticmethod
    def check_password(hashed_password: bytes, password: str) -> bool:
        """
        Checks if the original password matches the password provided by the user.
        :param hashed_password: The stored password (already hashed).
        :param password: The password entered by the user.
        :return: True if the passwords match, otherwise False.
        """
        # Print the type of the password variable (for debugging/testing only)
        print(type(password))

        # Check if the provided password matches the hashed password
        return bcrypt.checkpw(password.encode(), hashed_password)
