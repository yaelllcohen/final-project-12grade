import tkinter as tk
from tkinter import ttk, messagebox


class AdminScreenPink:
    def __init__(self, client_socket, username, first_screen_after_login_root):
        self.client_socket = client_socket
        self.username = username
        self.first_screen_after_login_root = first_screen_after_login_root

        self.root = tk.Toplevel(first_screen_after_login_root)
        self.root.title("admin screen")
        self.root.geometry("600x500")
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=1)
        self.root.rowconfigure(10, weight=1)
        self.root.config(bg="pink")

        self.welcome_label = tk.Label(
            self.root,
            text=f"welcome, Admin {self.username}!",
            font=("David", 30, "bold"),
            bg="lightblue"
        )
        self.welcome_label.grid(row=1, column=0, columnspan=3, pady=5, sticky="ew")

        self.text_label = tk.Label(self.root, text="all the users: ", font=("David", 20, "bold"), bg="pink")
        self.text_label.grid(row=2, column=0, pady=5)

        self.users_table_treeview = ttk.Treeview(
            self.root,
            columns=("username", "IsAdmin"),
            show="headings",
            height=15
        )
        self.users_table_treeview.heading("username", text="Username")
        self.users_table_treeview.heading("IsAdmin", text="IsAdmin")
        self.users_table_treeview.grid(row=3, column=0, columnspan=3, pady=5, sticky="nesw")

        self.scorllbar_for_many_pepole = ttk.Scrollbar(
            self.root, orient="vertical", command=self.users_table_treeview.yview
        )
        self.users_table_treeview.configure(yscrollcommand=self.scorllbar_for_many_pepole.set)

        self.return_button = tk.Button(
            self.root, bg="orange", fg="white", text="return",
            width=17, height=2, font=("David", 13, "bold"),
            command=self.back_to_main
        )
        self.return_button.grid(row=4, column=0, columnspan=3, padx=12, pady=10, sticky="sew")

        self.menu = tk.Menu(self.root, tearoff=0)
        self.users_table_treeview.bind("<Button-3>", self.show_context_menu)

        self.refresh_users()
        self.root.protocol("WM_DELETE_WINDOW", self.back_to_main)

    def refresh_users(self):
        resp = self.client_socket.send_request("get_users", {})
        if resp.get("status") != "success":
            messagebox.showerror("Error", resp.get("message", "Failed to load users (admin required)."))
            return

        users = resp.get("users", [])
        # clear table
        for row in self.users_table_treeview.get_children():
            self.users_table_treeview.delete(row)

        for u in users:
            self.users_table_treeview.insert(
                "", "end",
                values=(u["username"], "Yes" if u["is_admin"] else "No")
            )

    def back_to_main(self):
        self.root.destroy()
        self.first_screen_after_login_root.deiconify()

    def show_context_menu(self, event=None):
        try:
            row_id = self.users_table_treeview.focus()
            if not row_id:
                selected = self.users_table_treeview.selection()
                row_id = selected[0] if selected else None

            if not row_id:
                return

            self.users_table_treeview.selection_set(row_id)

            username = self.users_table_treeview.set(row_id, "username")
            is_admin_text = self.users_table_treeview.set(row_id, "IsAdmin")

            self.menu.delete(0, "end")

            if is_admin_text == "Yes":
                self.menu.add_command(label="Remove admin", command=self.remove_admin)
            else:
                self.menu.add_command(label="Add admin", command=self.add_admin)

            self.menu.add_separator()
            self.menu.add_command(label="Delete user", command=self.delete_user_from_server)


            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def selected_user(self):
        selected = self.users_table_treeview.selection()
        if not selected:
            messagebox.showinfo("No selection", "Please select a user.")
            return None
        return self.users_table_treeview.set(selected[0], "username")

    def add_admin(self):
        target = self.selected_user()
        if not target:
            return

        answer = messagebox.askyesno("Confirm add admin", f"Are you sure you want to add admin to '{target}'?")
        if not answer:
            return

        resp = self.client_socket.send_request("set_admin", {"target_username": target, "is_admin": True})
        if resp.get("status") == "success":
            self.refresh_users()
            messagebox.showinfo("ADD ADMIN", f"User '{target}' is admin.")
        else:
            messagebox.showerror("Error", resp.get("message", "Failed to set admin."))

    def remove_admin(self):
        target = self.selected_user()
        if not target:
            return

        if target == self.username:
            messagebox.showinfo("can't remove admin", "you can't remove your admin")
            return

        answer = messagebox.askyesno("Confirm remove admin", f"Are you sure you want to remove admin to '{target}'?")
        if not answer:
            return

        resp = self.client_socket.send_request("set_admin", {"target_username": target, "is_admin": False})
        if resp.get("status") == "success":
            self.refresh_users()
            messagebox.showinfo("REMOVE ADMIN", f"User '{target}' is not admin anymore")
        else:
            messagebox.showerror("Error", resp.get("message", "Failed to remove admin."))

    def delete_user_from_server(self):
        target = self.selected_user()
        if not target:
            return

        if target == self.username:
            messagebox.showinfo("can't delete", "you can't delete yourself")
            return

        answer = messagebox.askyesno("Confirm delete", f"Are you sure you want to delete '{target}'?")
        if not answer:
            return

        resp = self.client_socket.send_request("delete_user_admin", {"target_username": target})
        if resp.get("status") == "success":
            self.refresh_users()
            messagebox.showinfo("Deleted", f"User '{target}' was deleted successfully.")
        else:
            messagebox.showerror("Error", resp.get("message", "Failed to delete user."))
