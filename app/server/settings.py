import os

# Create a relative path to a folder named "data"
DATABASE_FILE = os.path.join("data", "database.db")
# Ensure that the folder exists
os.makedirs(os.path.dirname(DATABASE_FILE), exist_ok=True)