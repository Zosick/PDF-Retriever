import customtkinter
import threading

class RightFrame(customtkinter.CTkFrame):
    """Frame for logging, progress, and utility buttons."""

    def __init__(self, master, controller, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = controller
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._create_control_buttons()
        self._create_log_textbox()
        self._create_progress_bar()
        self._create_utility_buttons()

        self.lockable_widgets = [
            self.test_status_button,
            self.open_output_button,
            self.view_failed_button,
            self.retry_failed_button,
            self.clear_log_button,
        ]

    def _create_control_buttons(self):
        self.start_download_button = customtkinter.CTkButton(
            self,
            text="Start Download",
            command=self.controller.start_download,
            state="disabled",
        )
        self.start_download_button.grid(row=0, column=0, padx=10, pady=10, sticky="we")

        self.cancel_download_button = customtkinter.CTkButton(
            self,
            text="Cancel",
            command=self.controller.cancel_download,
            fg_color="#D9534F",
            hover_color="#C9302C",
        )
        self.cancel_download_button.grid_forget()

    def _create_log_textbox(self):
        self.log_textbox = customtkinter.CTkTextbox(
            self, state="disabled", font=("Courier", 13)
        )
        self.log_textbox.grid(row=1, column=0, padx=10, pady=10, sticky="nswe")
        self.log_textbox.tag_config("green", foreground="green")
        self.log_textbox.tag_config("red", foreground="red")
        self.log_textbox.tag_config("light_blue", foreground="#56B4E9")
        self.log_textbox.tag_config("orange", foreground="#E69F00")

    def _create_progress_bar(self):
        self.progress_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        self.progress_frame.grid(row=2, column=0, padx=10, pady=0, sticky="we")
        self.progressbar = customtkinter.CTkProgressBar(self.progress_frame)
        self.progressbar.pack(fill="x", expand=True)
        self.progressbar.set(0)
        self.progress_label = customtkinter.CTkLabel(
            self.progress_frame, text="0%", font=("Roboto", 11)
        )
        self.progress_label.place(relx=0.5, rely=0.5, anchor="center")

    def _create_utility_buttons(self):
        self.utility_frame = customtkinter.CTkFrame(self)
        self.utility_frame.grid(row=3, column=0, padx=10, pady=10, sticky="we")
        self.utility_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.retry_failed_button = customtkinter.CTkButton(
            self.utility_frame,
            text="Retry Failed",
            command=self.controller.retry_failed_dois,
            state="disabled",
        )
        self.retry_failed_button.grid(row=0, column=0, padx=5, pady=5)

        self.view_failed_button = customtkinter.CTkButton(
            self.utility_frame,
            text="View Failed",
            command=self.controller.view_failed,
            state="disabled",
        )
        self.view_failed_button.grid(row=0, column=1, padx=5, pady=5)

        self.open_output_button = customtkinter.CTkButton(
            self.utility_frame,
            text="Open Output",
            command=self.controller.open_output_folder,
        )
        self.open_output_button.grid(row=0, column=2, padx=5, pady=5)

        self.clear_log_button = customtkinter.CTkButton(
            self.utility_frame, text="Clear Log", command=self.controller.clear_log
        )
        self.clear_log_button.grid(row=0, column=3, padx=5, pady=5)

        self.test_status_button = customtkinter.CTkButton(
            self.utility_frame, text="Test Status", command=self.controller.test_status
        )
        self.test_status_button.grid(row=0, column=4, padx=5, pady=5)

    def set_locked(self, locked: bool, has_doi_text: bool):
        new_state = "disabled" if locked else "normal"
        for widget in self.lockable_widgets:
            widget.configure(state=new_state)

        if not locked:
            if not has_doi_text:
                self.start_download_button.configure(
                    state="disabled", fg_color=("gray50", "gray50")
                )
            else:
                self.start_download_button.configure(
                    state="normal", fg_color=("#2CC985", "#2CC985")
                )
            self.controller.check_failed_dois_file()
