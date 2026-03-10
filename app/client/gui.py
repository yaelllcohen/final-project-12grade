# gui.py
from app.client.login_pink import LoginPink


def start_gui(client_socket):
    LoginPink(client_socket)
