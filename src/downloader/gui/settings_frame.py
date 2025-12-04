import customtkinter

class SettingsFrame(customtkinter.CTkScrollableFrame):
    """Frame for all user-configurable settings."""

    def __init__(self, master, controller, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)

        self._create_header()
        
        self.current_row = 1
        self._create_output_dir_widgets()
        self._create_email_widgets()
        self._create_core_api_widgets()
        self._create_ssl_widget()
        self._create_parallel_downloads_widget()
        self._create_completion_popup_widget()
        self._create_action_buttons()

        self.lockable_widgets = [
            self.output_dir_entry,
            self.browse_button,
            self.email_entry,
            self.show_email_checkbox,
            self.core_api_key_entry,
            self.ssl_checkbox,
            self.parallel_downloads_slider,
            self.save_settings_button,
            self.clear_settings_button,
            self.show_completion_popup_checkbox,
        ]

    def _create_header(self):
        self.settings_label = customtkinter.CTkLabel(
            self, text="Settings", font=("Roboto", 16)
        )
        self.settings_label.grid(
            row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w"
        )

    def _create_output_dir_widgets(self):
        self.output_dir_label = customtkinter.CTkLabel(self, text="Output Directory")
        self.output_dir_label.grid(
            row=self.current_row, column=0, columnspan=2, padx=10, pady=(5, 0), sticky="w"
        )
        self.current_row += 1
        self.output_dir_entry = customtkinter.CTkEntry(self)
        self.output_dir_entry.grid(row=self.current_row, column=0, padx=10, pady=(0, 5), sticky="we")
        self.browse_button = customtkinter.CTkButton(
            self, text="Browse", command=self.controller.browse_output_dir, width=80
        )
        self.browse_button.grid(row=self.current_row, column=1, padx=(0, 10), pady=(0, 5))
        self.current_row += 1

    def _create_email_widgets(self):
        self.email_label = customtkinter.CTkLabel(self, text="Unpaywall Email")
        self.email_label.grid(
            row=self.current_row, column=0, columnspan=2, padx=10, pady=(5, 0), sticky="w"
        )
        self.current_row += 1
        self.email_entry = customtkinter.CTkEntry(self, show="*")
        self.email_entry.grid(row=self.current_row, column=0, padx=10, pady=(0, 5), sticky="we")
        self.show_email_checkbox = customtkinter.CTkCheckBox(
            self,
            text="Show",
            checkbox_width=18,
            checkbox_height=18,
            command=self.controller.toggle_email_visibility,
            text_color=("gray10", "#DCE4EE"),
        )
        self.show_email_checkbox.grid(row=self.current_row, column=1, padx=(0, 10), pady=(0, 5))
        self.current_row += 1

    def _create_core_api_widgets(self):
        self.core_api_key_label = customtkinter.CTkLabel(self, text="CORE API Key")
        self.core_api_key_label.grid(
            row=self.current_row, column=0, columnspan=2, padx=10, pady=(5, 0), sticky="w"
        )
        self.current_row += 1
        self.core_api_key_entry = customtkinter.CTkEntry(self, show="*")
        self.core_api_key_entry.grid(
            row=self.current_row, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="we"
        )
        self.current_row += 1

    def _create_ssl_widget(self):
        self.ssl_checkbox = customtkinter.CTkCheckBox(
            self, text="Bypass SSL verification", checkbox_width=18, checkbox_height=18
        )
        self.ssl_checkbox.grid(
            row=self.current_row, column=0, columnspan=2, padx=10, pady=5, sticky="w"
        )
        self.current_row += 1

    def _create_parallel_downloads_widget(self):
        self.parallel_downloads_label = customtkinter.CTkLabel(
            self, text="Parallel Downloads: 10"
        )
        self.parallel_downloads_label.grid(
            row=self.current_row, column=0, columnspan=2, padx=10, pady=(5, 0), sticky="w"
        )
        self.current_row += 1
        self.parallel_downloads_slider = customtkinter.CTkSlider(
            self,
            from_=1,
            to=20,
            number_of_steps=19,
            command=self.controller.update_parallel_downloads_label,
        )
        self.parallel_downloads_slider.grid(
            row=self.current_row, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="we"
        )
        self.parallel_downloads_slider.set(10)
        self.current_row += 1

    def _create_completion_popup_widget(self):
        self.show_completion_popup_checkbox = customtkinter.CTkCheckBox(
            self, text="Show popup on completion", checkbox_width=18, checkbox_height=18
        )
        self.show_completion_popup_checkbox.grid(
            row=self.current_row, column=0, columnspan=2, padx=10, pady=5, sticky="w"
        )
        self.current_row += 1

    def _create_action_buttons(self):
        self.save_settings_button = customtkinter.CTkButton(
            self, text="Save Settings", command=self.controller.save_settings
        )
        self.save_settings_button.grid(
            row=self.current_row, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="we"
        )
        self.current_row += 1
        self.clear_settings_button = customtkinter.CTkButton(
            self,
            text="Clear Settings",
            command=self.controller.clear_settings,
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE"),
        )
        self.clear_settings_button.grid(
            row=self.current_row, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="we"
        )

    def set_locked(self, locked: bool):
        new_state = "disabled" if locked else "normal"
        for widget in self.lockable_widgets:
            widget.configure(state=new_state)
