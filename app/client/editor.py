import tkinter as tk
from tkinter import messagebox
import json

from app.client.toolBar import create_toolbar


PINK_BG = "pink"
HEADER_BG = "lightblue"


class Editor:
    def __init__(self, client_socket, username, project_name):
        self.client_socket = client_socket
        self.username = username
        self.project_name = project_name

        self.root = tk.Toplevel()
        self.root.title(f"edit: {project_name}")
        self.root.geometry("700x500")
        self.root.configure(bg=PINK_BG)

        title = tk.Label(
            self.root,
            text=project_name,
            font=("David", 28, "bold"),
            bg=HEADER_BG
        )
        title.pack(fill="x", pady=(0, 10))

        # Text + toolbar
        self.text_area = tk.Text(self.root, wrap="word", font=("Delicious", 12))
        create_toolbar(self.root, self.text_area)
        self.text_area.pack(expand=True, fill="both", padx=12, pady=12)

        btn_frame = tk.Frame(self.root, bg=PINK_BG)
        btn_frame.pack(fill="x", padx=12, pady=(0, 12))

        save_btn = tk.Button(
            btn_frame, text="Save",
            bg="orange", fg="white",
            font=("David", 13, "bold"),
            command=self.save_file
        )
        save_btn.pack(side="left", padx=(0, 10))

        close_btn = tk.Button(
            btn_frame, text="Close",
            bg="orange", fg="white",
            font=("David", 13, "bold"),
            command=self.root.destroy
        )
        close_btn.pack(side="left")

        self.root.bind("<Control-s>", lambda e: self.save_file())

        self.load_file()

    # ---------------- LOAD ----------------

    def load_file(self):
        resp = self.client_socket.send_request(
            "get_file_content",
            {"username": self.username, "project_name": self.project_name}
        )

        if resp.get("status") != "success":
            messagebox.showerror("Error", resp.get("message", "Failed to load file."))
            return

        content = resp.get("content", "")
        self.load_text_safely(content)

    def load_text_safely(self, content):
        self.text_area.delete("1.0", "end")

        if not content:
            return

        s = str(content)

        # נסיון 1 – JSON תקין
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                load_text_with_styles(self.text_area, s)
                return

            # נסיון 2 – JSON שנשמר פעמיים
            if isinstance(parsed, str):
                parsed2 = json.loads(parsed)
                if isinstance(parsed2, list):
                    load_text_with_styles(
                        self.text_area,
                        json.dumps(parsed2, ensure_ascii=False)
                    )
                    return
        except Exception:
            pass

        # נסיון 3 – מצב מקולקל עם \" בתוך הטקסט
        try:
            fixed = s.replace('\\"', '"')
            parsed3 = json.loads(fixed)
            if isinstance(parsed3, list):
                load_text_with_styles(
                    self.text_area,
                    json.dumps(parsed3, ensure_ascii=False)
                )
                return
        except Exception:
            pass

        # אם הכל נכשל – טקסט רגיל
        self.text_area.insert("1.0", s)

    # ---------------- SAVE ----------------

    def save_file(self):
        styled_list = export_text_with_styles(self.text_area)

        content_json = json.dumps(styled_list, ensure_ascii=False)

        resp = self.client_socket.send_request(
            "update_file",
            {
                "username": self.username,
                "filename": self.project_name,
                "content": content_json
            }
        )

        if resp.get("status") == "success":
            messagebox.showinfo("Saved", "File saved successfully.")
        else:
            messagebox.showerror("Error", resp.get("message", "Failed to save file."))


# ---------------- EXPORT ----------------

def export_text_with_styles(text_widget):
    result = []
    index = "1.0"
    end_index = text_widget.index("end-1c")

    while text_widget.compare(index, "<", end_index):
        next_index = text_widget.index(f"{index} +1c")
        char = text_widget.get(index, next_index)
        tags = text_widget.tag_names(index)

        char_data = {
            "text": char,
            "bold": "bold" in tags,
            "italic": "italic" in tags,
            "underline": "underline" in tags,
            "color": None,
            "size": None,
        }

        for tag in tags:
            if tag.startswith("color_"):
                char_data["color"] = tag.split("_", 1)[1]
            elif tag.startswith("size_"):
                try:
                    char_data["size"] = int(tag.split("_", 1)[1])
                except Exception:
                    pass

        result.append(char_data)
        index = next_index

    return result


# ---------------- IMPORT ----------------

def load_text_with_styles(text_widget, styled_data):
    text_widget.delete("1.0", "end")

    data = json.loads(styled_data)

    for item in data:
        start_index = text_widget.index("end-1c")
        text_widget.insert("end", item.get("text", ""))

        tags = []

        if item.get("bold"):
            if "bold" not in text_widget.tag_names():
                text_widget.tag_configure("bold", font=("Delicious", 12, "bold"))
            tags.append("bold")

        if item.get("italic"):
            if "italic" not in text_widget.tag_names():
                text_widget.tag_configure("italic", font=("Delicious", 12, "italic"))
            tags.append("italic")

        if item.get("underline"):
            if "underline" not in text_widget.tag_names():
                text_widget.tag_configure("underline", underline=1)
            tags.append("underline")

        if item.get("color"):
            tag_name = f"color_{item['color']}"
            if tag_name not in text_widget.tag_names():
                text_widget.tag_configure(tag_name, foreground=item["color"])
            tags.append(tag_name)

        if item.get("size"):
            tag_name = f"size_{item['size']}"
            if tag_name not in text_widget.tag_names():
                text_widget.tag_configure(tag_name, font=("Delicious", item["size"]))
            tags.append(tag_name)

        end_index = text_widget.index("end-1c")
        for tag in tags:
            text_widget.tag_add(tag, start_index, end_index)
