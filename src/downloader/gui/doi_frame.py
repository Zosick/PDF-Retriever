import customtkinter


class DoiFrame(customtkinter.CTkFrame):
    """Frame for DOI input and file loading."""

    def __init__(self, master, controller, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)

        self.doi_input_label = customtkinter.CTkLabel(
            self, text="DOI Input (0)", font=("Roboto", 16)
        )
        self.doi_input_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        self.load_file_button = customtkinter.CTkButton(
            self, text="Load from File", command=self.controller.load_dois_from_file
        )
        self.load_file_button.grid(row=1, column=0, padx=10, pady=5, sticky="we")

        self.doi_textbox = customtkinter.CTkTextbox(self, height=100)
        self.doi_textbox.grid(row=2, column=0, padx=10, pady=5, sticky="new")
        self.doi_textbox.bind("<KeyRelease>", self.controller.update_doi_input_widgets)

        self.lockable_widgets = [self.load_file_button, self.doi_textbox]

    def set_locked(self, locked: bool):
        new_state = "disabled" if locked else "normal"
        for widget in self.lockable_widgets:
            widget.configure(state=new_state)
