from app.client.client import ClientSocket
from app.client.gui import start_gui

if __name__ == "__main__":
    cs = ClientSocket()
    if cs.client:
        start_gui(cs)
    else:
        print("Connection to server failed.")
