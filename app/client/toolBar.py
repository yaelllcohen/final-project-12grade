import tkinter as tk
from tkinter import font, colorchooser


def create_toolbar(parent, text_widget):
    toolbar = tk.Frame(parent, bg="#f0f4f8")
    toolbar.pack(fill="x", pady=5)

    def apply_tag(tag_name):
        """
        Applies or removes a formatting tag on the selected text in the text widget.
        If the selected text already has the tag, the tag will be removed.
        If the tag is a font size tag, the previous size tag will be removed and replaced with the new one.
        For other tags (bold, italic, underline), similar existing tags will be removed before adding the new tag.
        :param tag_name: The name of the formatting tag to apply or remove (e.g., "bold", "italic",
        "underline", "size_14").
        """
        try:
            start, end = text_widget.index("sel.first"), text_widget.index("sel.last")
        except tk.TclError:
            return  # No selection

        existing_tags = list(text_widget.tag_names("sel.first"))
        if "sel" in existing_tags:
            existing_tags.remove("sel")

        if tag_name in existing_tags:
            print(existing_tags)
            text_widget.tag_remove(tag_name, start, end)

            if len(existing_tags) > 0:
                for tag in existing_tags:
                    if tag.startswith("size_"):
                        text_widget.tag_configure(tag, font=("Delicious", int(tag.split("_")[1])))
            return

        size_tag = ""
        for tag in existing_tags:
            if tag.startswith("size_"):
                size_tag = tag

        if tag_name.startswith("size_"):
            if size_tag:
                text_widget.tag_remove(size_tag, start, end)

            if len(existing_tags) > 0:
                print(("Delicious", int(tag_name.split("_")[1]), " ".join(existing_tags)))
                text_widget.tag_configure(
                    tag_name,
                    font=("Delicious", int(tag_name.split("_")[1]), " ".join(existing_tags))
                )

                # NOTE: זה היה אצלך "existing_tags[0]" — השארתי את אותו רעיון, רק בלי לקרוס אם אין
                text_widget.tag_remove(existing_tags[0], start, end)
            else:
                text_widget.tag_configure(tag_name, font=("Delicious", int(tag_name.split("_")[1])))

            text_widget.tag_add(tag_name, start, end)

        else:
            for tag in existing_tags:
                if tag in ["bold", "underline", "italic"]:
                    text_widget.tag_remove(tag, start, end)

            if size_tag == "":
                text_widget.tag_configure(tag_name, font=("Delicious", 12, tag_name))
                text_widget.tag_add(tag_name, start, end)
            else:
                text_widget.tag_configure(size_tag, font=("Delicious", int(size_tag.split("_")[1]), tag_name))
                text_widget.tag_add(tag_name, start, end)

    # Apply the "bold" tag to the selected text (bold)
    def toggle_bold():
        apply_tag("bold")

    # Apply the "italic" tag to the selected text (italic)
    def toggle_italic():
        apply_tag("italic")

    # Apply the "underline" tag to the selected text (underline)
    def toggle_underline():
        apply_tag("underline")

    # Change the font size of the selected text
    def change_font_size(size):
        tag_name = f"size_{size}"  # Create a tag name based on the selected size
        apply_tag(tag_name)  # Apply the tag to the selected text

    # Open a color picker dialog and change the color of the selected text
    def change_text_color():
        color = colorchooser.askcolor()[1]  # Get the selected color (HEX code)
        if color:
            try:
                # Try to get the selected text range
                start, end = text_widget.index("sel.first"), text_widget.index("sel.last")
            except tk.TclError:
                return  # Do nothing if no text is selected

            tag_name = f"color_{color}"  # Create a tag name based on the color
            text_widget.tag_configure(tag_name, foreground=color)  # Configure a new tag with the chosen color
            text_widget.tag_add(tag_name, start, end)  # Add the tag to the selected text

    # Create a Bold button (B)
    tk.Button(
        toolbar, text="B", command=toggle_bold,
        font=("Delicious", 10, "bold"), width=3,
        bg="#4A90E2", fg="white"
    ).pack(side="left", padx=2)

    # Create an Italic button (I)
    tk.Button(
        toolbar, text="I", command=toggle_italic,
        font=("Delicious", 10, "italic"), width=3,
        bg="#4A90E2", fg="white"
    ).pack(side="left", padx=2)

    # Create an Underline button (U)
    tk.Button(
        toolbar, text="U", command=toggle_underline,
        font=("Delicious", 10, "underline"), width=3,
        bg="#4A90E2", fg="white"
    ).pack(side="left", padx=2)

    # Dropdown menu for selecting font size
    font_sizes = [8, 10, 12, 14, 16, 18, 20]  # List of available sizes
    font_size_var = tk.StringVar(toolbar)  # Variable for selection
    font_size_var.set("Size")  # Initial text in the menu

    # Create the font size dropdown menu
    size_menu = tk.OptionMenu(toolbar, font_size_var, *font_sizes, command=change_font_size)
    size_menu.config(bg="#4A90E2", fg="white", font=("Delicious", 10))
    size_menu.pack(side="left", padx=5)

    # Button to change text color
    color_button = tk.Button(
        toolbar, text="Color", command=change_text_color,
        bg="#4A90E2", fg="white", font=("Delicious", 10)
    )
    color_button.pack(side="left", padx=5)
