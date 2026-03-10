import tkinter as tk
from tkinter import ttk


class RegisterPink:
    def __init__(self, client_socket):
        self.client_socket = client_socket

        self.root = tk.Tk()
        self.root.title("register screen")
        self.root.geometry("400x300")
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=1)
        self.root.config(bg="pink")

        self.label_register = tk.Label(self.root, text="REGISTER", font=('david', 30, 'bold'), bg="lightblue")
        self.label_register.grid(row=0, column=1, pady=20)

        tk.Label(self.root, text="enter your username", font=("David", 15, "bold"), bg="pink")\
            .grid(row=1, column=1, pady=5, sticky="ew")
        self.username = ttk.Entry(self.root)
        self.username.grid(row=2, column=1, padx=5, pady=5, sticky="nsew")

        tk.Label(self.root, text="enter your password", font=("David", 15, "bold"), bg="pink")\
            .grid(row=3, column=1, pady=5, sticky="ew")
        self.password = ttk.Entry(self.root, show="*")
        self.password.grid(row=4, column=1, padx=5, pady=5, sticky="nsew")
        self.password.bind("<Return>", self.do_register)

        self.button_frame = tk.Frame(self.root, bg="pink")
        self.button_frame.grid(row=6, column=1, pady=10)

        ttk.Button(self.button_frame, text="register", command=self.do_register)\
            .grid(row=0, column=0, pady=3, padx=10)
        ttk.Button(self.button_frame, text="back to login", command=self.back_to_login)\
            .grid(row=0, column=1, pady=3, padx=10)

        self.message_label = tk.Label(self.root, text="", fg="red", bg="pink", font=("Arial", 10, "bold"))
        self.message_label.grid(row=5, column=1, pady=5)

        self.root.mainloop()

    def show_message(self, text, color=None):
        self.message_label.config(text=text, fg=color)

    def do_register(self, event=None):
        username = self.username.get().strip()
        password = self.password.get()

        if not username:
            self.show_message("enter username", "orange")
            return
        if not password:
            self.show_message("enter password", "orange")
            return
        if len(password) < 8:
            self.show_message("password length should be at least 8", "orange")
            return

        resp = self.client_socket.send_request("register", {"username": username, "password": password})
        if resp.get("status") == "success":
            self.client_socket.data["username"] = username
            self.show_message("register!", "green")
            self.root.after(300, self.back_to_login)
        else:
            self.show_message(resp.get("message", "register failed"), "red")

    def back_to_login(self):
        self.root.destroy()
        from app.client.login_pink import LoginPink
        LoginPink(self.client_socket)
