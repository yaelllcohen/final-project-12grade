import tkinter as tk
from tkinter import messagebox, simpledialog
from tkinter import filedialog
import os
import base64
import tempfile
import subprocess
import sys


from app.client.editor import Editor


class FirstScreenAfterLoginPink:
    def __init__(self, client_socket, username):
        self.client_socket = client_socket
        self.username = username

        self.root = tk.Tk()
        self.root.title("main")
        self.root.geometry("650x520")
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=1)
        self.root.rowconfigure(3, weight=1)
        self.root.config(bg="pink")

        self.welcome_label = tk.Label(
            self.root, text=f"welcome, {self.username}!",
            font=("David", 30, "bold"), bg="lightblue"
        )
        self.welcome_label.grid(row=0, column=0, columnspan=3, pady=10, sticky="ew")

        self.buttons = tk.Frame(self.root, bg="pink")
        self.buttons.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10)

        self.logout_button = tk.Button(
            self.buttons, bg="orange", fg="white", text="log out",
            width=17, height=2, font=("David", 13, "bold"), command=self.logout
        )
        self.logout_button.pack(side="right", padx=5, pady=5)

        self.create_file_button = tk.Button(
            self.buttons, bg="orange", fg="white", text="create file",
            width=17, height=2, font=("David", 13, "bold"), command=self.create_project
        )
        self.create_file_button.pack(side="right", padx=5, pady=5)

        self.admin_button = tk.Button(
            self.buttons, bg="orange", fg="white", text="administor",
            width=17, height=2, font=("David", 13, "bold"), command=self.admin_ready
        )
        self.admin_button.pack(side="right", padx=5, pady=5)

        self.files_frame = tk.Frame(self.root, bg="pink")
        self.files_frame.grid(row=3, column=0, columnspan=3, padx=12, pady=10, sticky="nsew")
        self.files_frame.rowconfigure(0, weight=1)
        self.files_frame.columnconfigure(0, weight=1)

        self.files_listbox = tk.Listbox(self.files_frame, width=100, height=17)
        self.files_listbox.grid(row=0, column=0, sticky="nsew")
        self.files_listbox.bind("<Double-Button-1>", self.open_selected_project)

        self.refresh_button = tk.Button(
            self.root, bg="orange", fg="white", text="upload file",
            width=20, height=2, font=("David", 13, "bold"), command=self.upload_file
        )
        self.refresh_button.grid(row=4, column=0, columnspan=3, padx=12, pady=10, sticky="sew")
        self.files_listbox.bind("<Button-3>", self.show_file_menu)

        self.file_menu = tk.Menu(self.root, tearoff=0)
        self.file_menu.add_command(label="Delete", command=self.delete_selected)

        self.load_projects()
        self.root.mainloop()

    def load_projects(self):
        self.files_listbox.delete(0, tk.END)

        # 1) פרויקטים (json)
        resp_projects = self.client_socket.send_request("get_projects", {"username": self.username})
        if resp_projects.get("status") == "success":
            projects = resp_projects.get("projects", [])
            for p in projects:
                # p בלי סיומת (לפי השרת שלך)
                self.files_listbox.insert(tk.END, p)
        else:
            messagebox.showerror("Error", resp_projects.get("message", "Failed to load projects."))

        # 2) קבצים שהועלו (uploads)
        resp_uploads = self.client_socket.send_request("get_uploaded_files", {"username": self.username})
        if resp_uploads.get("status") == "success":
            files = resp_uploads.get("files", [])
            if files:
                self.files_listbox.insert(tk.END, "----- UPLOADS -----")
                for fn in files:
                    # נשמור אותם עם תגית כדי שנדע שזה לא פרויקט json
                    self.files_listbox.insert(tk.END, f"[UPLOAD] {fn}")
        else:
            messagebox.showerror("Error", resp_uploads.get("message", "Failed to load uploads."))

    def create_project(self):
        filename = simpledialog.askstring("File Name", "Enter file name:")
        if not filename:
            return

        resp = self.client_socket.send_request("add_file", {"username": self.username, "filename": filename})
        if resp.get("status") != "success":
            messagebox.showerror("Error", resp.get("message", "Failed to create file."))
            return

        self.load_projects()
        Editor(self.client_socket, self.username, filename)

    def open_selected_project(self, event=None):
        selection = self.files_listbox.curselection()
        if not selection:
            return

        item = self.files_listbox.get(selection[0])

        # לא עושים כלום על כותרת
        if item.startswith("-----"):
            return

        # אם זה Upload – מורידים ופותחים מקומית
        if item.startswith("[UPLOAD] "):
            filename = item.replace("[UPLOAD] ", "", 1)

            resp = self.client_socket.send_request("download_binary_file", {
                "username": self.username,
                "filename": filename
            })

            if resp.get("status") != "success":
                messagebox.showerror("Error", resp.get("message", "Download failed"))
                return

            try:
                raw = base64.b64decode(resp["data"].encode("utf-8"))

                # שמירה לקובץ זמני עם אותה סיומת
                suffix = os.path.splitext(filename)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(raw)
                    tmp_path = tmp.name

                # לפתוח עם ברירת מחדל של המחשב
                if sys.platform.startswith("win"):
                    os.startfile(tmp_path)
                elif sys.platform.startswith("darwin"):
                    subprocess.call(["open", tmp_path])
                else:
                    subprocess.call(["xdg-open", tmp_path])

            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file: {e}")

            return

        # אחרת זה פרויקט JSON רגיל
        project_name = item
        Editor(self.client_socket, self.username, project_name)

    def logout(self):
        self.client_socket.data.pop("username", None)
        self.client_socket.data.pop("token", None)
        self.root.destroy()
        from app.client.login_pink import LoginPink
        LoginPink(self.client_socket)

    def admin_ready(self):
        from app.client.admin_screen_pink import AdminScreenPink
        self.root.withdraw()
        AdminScreenPink(self.client_socket, self.username, self.root)

    def upload_file(self):
        path = filedialog.askopenfilename(title="Select a file")
        if not path:
            return

        try:
            with open(path, "rb") as f:
                raw = f.read()

            payload = {
                # חשוב! השרת צריך לדעת למי לשמור + token לבדיקה
                "username": self.username,
                "token": self.client_socket.data.get("token"),

                "original_name": os.path.basename(path),
                "data": base64.b64encode(raw).decode("utf-8")
            }

            resp = self.client_socket.send_request("upload_binary_file", payload)

            if resp.get("status") == "success":
                messagebox.showinfo("Uploaded", f"Uploaded: {resp.get('saved_as')}")
                # חשוב! לרענן רשימה אחרי העלאה
                self.load_projects()
            else:
                messagebox.showerror("Error", resp.get("message", "Upload failed"))


        except Exception as e:
            messagebox.showerror("Error", str(e))

    def show_file_menu(self, event):
        try:
            # מזהה על איזה שורה לחצו
            index = self.files_listbox.nearest(event.y)
            if index < 0:
                return

            self.files_listbox.selection_clear(0, tk.END)
            self.files_listbox.selection_set(index)

            item = self.files_listbox.get(index)

            # לא לאפשר מחיקה של כותרת
            if item.startswith("-----"):
                return

            self.file_menu.tk_popup(event.x_root, event.y_root)

        finally:
            self.file_menu.grab_release()

    def delete_selected(self):
        selection = self.files_listbox.curselection()
        if not selection:
            return

        item = self.files_listbox.get(selection[0])

        # Upload
        if item.startswith("[UPLOAD] "):
            filename = item.replace("[UPLOAD] ", "", 1)

            ok = messagebox.askyesno("Confirm delete", f"Delete uploaded file '{filename}'?")
            if not ok:
                return

            resp = self.client_socket.send_request("delete_uploaded_file", {
                "username": self.username,
                "filename": filename
            })

            if resp.get("status") == "success":
                self.load_projects()
            else:
                messagebox.showerror("Error", resp.get("message", "Delete failed"))
            return

        # פרויקט רגיל
        project_name = item

        ok = messagebox.askyesno("Confirm delete", f"Delete project '{project_name}'?")
        if not ok:
            return

        resp = self.client_socket.send_request("delete_file", {
            "username": self.username,
            "filename": project_name
        })

        if resp.get("status") == "success":
            self.load_projects()
        else:
            messagebox.showerror("Error", resp.get("message", "Delete failed"))

