import tkinter as tk
from tkinter import ttk


class LoginPink:
    def __init__(self, client_socket):
        self.client_socket = client_socket

        self.root = tk.Tk()
        self.root.title("login screen")
        self.root.geometry("400x300")
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=1)
        self.root.config(bg="pink")

        self.label_login = tk.Label(self.root, text="LOGIN", font=('david', 30, 'bold'), bg="lightblue")
        self.label_login.grid(row=0, column=1, pady=20)

        tk.Label(self.root, text="enter your username", font=("David", 15, "bold"), bg="pink")\
            .grid(row=1, column=1, pady=5, sticky="ew")
        self.username = ttk.Entry(self.root)
        self.username.grid(row=2, column=1, padx=5, pady=5, sticky="nsew")

        tk.Label(self.root, text="enter your password", font=("David", 15, "bold"), bg="pink")\
            .grid(row=3, column=1, pady=5, sticky="ew")
        self.password = ttk.Entry(self.root, show="*")
        self.password.grid(row=4, column=1, padx=5, pady=5, sticky="nsew")
        self.password.bind("<Return>", self.do_login)

        self.button_frame = tk.Frame(self.root, bg="pink")
        self.button_frame.grid(row=6, column=1, pady=10)

        ttk.Button(self.button_frame, text="register", command=self.open_register)\
            .grid(row=0, column=0, pady=3, padx=10)
        ttk.Button(self.button_frame, text="login", command=self.do_login)\
            .grid(row=0, column=1, pady=3, padx=10)

        self.message_label = tk.Label(self.root, text="", fg="red", bg="pink", font=("Arial", 10, "bold"))
        self.message_label.grid(row=5, column=1, pady=5)

        self.root.mainloop()

    def show_message(self, text, color=None):
        self.message_label.config(text=text, fg=color)

    def do_login(self, event=None):
        username = self.username.get().strip()
        password = self.password.get()

        if not username or not password:
            self.show_message("enter username and password", "orange")
            return

        resp = self.client_socket.send_request("login", {"username": username, "password": password})
        if resp.get("status") == "success":
            self.client_socket.data["username"] = username
            self.root.destroy()
            from app.client.first_screen_after_login_pink import FirstScreenAfterLoginPink
            FirstScreenAfterLoginPink(self.client_socket, username)
        else:
            self.show_message(resp.get("message", "login failed"), "red")

    def open_register(self):
        self.root.destroy()
        from app.client.register_pink import RegisterPink
        RegisterPink(self.client_socket)
