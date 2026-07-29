from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
import webbrowser
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

from local_llm.agent_core import DEFAULT_MODEL, MODE_INSTRUCTIONS, ask_agent
from local_llm.commerce import check_commerce_connections, format_commerce_checks
from local_llm.memory import append_memory
from local_llm.ollama_client import OllamaClient
from local_llm.patch_ops import apply_patch_with_backup, check_patch
from local_llm.patches import extract_unified_diffs
from local_llm.repo_index import build_repo_index, format_repo_index
from local_llm.session_log import load_agent_sessions
from local_llm.training_presets import TRAINING_PRESETS, ascii_loss_chart, load_metrics, preset_args
from local_llm.web_artifact import create_web_artifact


APP_NAME = "Ares"
BG = "#1f1f1f"
SIDEBAR_BG = "#171717"
PANEL_BG = "#242424"
SURFACE_BG = "#2d2d2d"
TEXT = "#e8e6e3"
MUTED = "#aaa6a0"
BORDER = "#3a3a3a"
ACCENT = "#f97316"
GREEN = "#22c55e"
RED = "#ef4444"


class AresApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1180x720")
        self.minsize(920, 620)
        self.configure(bg=BG)

        self.repo_root = Path.cwd().resolve()
        self.messages: queue.Queue[str] = queue.Queue()
        self.logo_image: tk.PhotoImage | None = None
        self.latest_response = ""
        self.latest_patch = ""
        self.latest_session_id = "manual"
        self.action_buttons: list[tk.Widget] = []
        self.nav_buttons: dict[str, tk.Button] = {}
        self.text_widgets: list[tk.Text] = []
        self.sidebar_session_list: tk.Listbox | None = None

        self.model = tk.StringVar(value=DEFAULT_MODEL)
        self.mode = tk.StringVar(value="answer")
        self.training_preset = tk.StringVar(value="LLM.C CPU Demo")
        self.corpus_path = tk.StringVar(value="data/ares_corpus.txt")
        self.checkpoint_path = tk.StringVar(value="runs/ares/checkpoint.pt")

        self._configure_style()
        self._build_ui()
        self._bind_shortcuts()
        self.after(150, self._drain_messages)
        self.after(300, self.refresh_repo_index)
        self.after(500, self.refresh_sessions)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Header.TFrame", background=BG)
        style.configure("Content.TFrame", background=PANEL_BG)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Content.TLabel", background=PANEL_BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=BG, foreground=TEXT, font=("Segoe UI Semibold", 20))
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("TButton", background=SURFACE_BG, foreground=TEXT, font=("Segoe UI Semibold", 10), padding=(12, 8))
        style.map("TButton", background=[("active", "#3a3a3a"), ("disabled", "#292929")], foreground=[("disabled", "#777777")])
        style.configure("Accent.TButton", background="#3a3a3a", foreground=TEXT)
        style.map("Accent.TButton", background=[("active", "#4a4a4a")])
        style.configure("TNotebook", background=PANEL_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background="#333333", foreground=MUTED, padding=(14, 8), font=("Segoe UI Semibold", 10))
        style.map("TNotebook.Tab", background=[("selected", PANEL_BG), ("active", "#3a3a3a")], foreground=[("selected", TEXT)])
        style.layout("TNotebook.Tab", [])
        style.configure("TCombobox", fieldbackground=SURFACE_BG, background=SURFACE_BG, foreground=TEXT, arrowcolor=MUTED)
        style.configure("TEntry", fieldbackground=SURFACE_BG, foreground=TEXT, insertcolor=TEXT)

    def _build_ui(self) -> None:
        workspace = ttk.Frame(self, style="TFrame")
        workspace.pack(fill=tk.BOTH, expand=True)
        self.sidebar = tk.Frame(workspace, bg=SIDEBAR_BG, width=260, highlightbackground=BORDER, highlightthickness=1)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        content = ttk.Frame(workspace, style="TFrame")
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(14, 18), pady=14)

        topbar = ttk.Frame(content, style="TFrame")
        topbar.pack(fill=tk.X, pady=(0, 10))
        self.status = ttk.Label(topbar, text="Ready", style="Muted.TLabel")
        self.status.pack(side=tk.RIGHT)

        self.notebook = ttk.Notebook(content)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.chat_tab = ttk.Frame(self.notebook, padding=14)
        self.files_tab = ttk.Frame(self.notebook, padding=14)
        self.diff_tab = ttk.Frame(self.notebook, padding=14)
        self.training_tab = ttk.Frame(self.notebook, padding=14)
        self.commerce_tab = ttk.Frame(self.notebook, padding=14)
        self.sessions_tab = ttk.Frame(self.notebook, padding=14)
        self.settings_tab = ttk.Frame(self.notebook, padding=14)

        self.notebook.add(self.chat_tab, text="Chat")
        self.notebook.add(self.files_tab, text="Files")
        self.notebook.add(self.diff_tab, text="Diff")
        self.notebook.add(self.training_tab, text="Training")
        self.notebook.add(self.commerce_tab, text="Commerce")
        self.notebook.add(self.sessions_tab, text="Sessions")
        self.notebook.add(self.settings_tab, text="Settings")

        self._build_sidebar()
        self._build_chat_tab()
        self._build_files_tab()
        self._build_diff_tab()
        self._build_training_tab()
        self._build_commerce_tab()
        self._build_sessions_tab()
        self._build_settings_tab()
        self._style_text_widgets()

    def _build_header(self) -> None:
        header = ttk.Frame(self, style="Header.TFrame", padding=(20, 14))
        header.pack(fill=tk.X)

        logo_path = asset_path("ares_logo.png")
        if logo_path.exists():
            self.logo_image = tk.PhotoImage(file=logo_path)
            ttk.Label(header, image=self.logo_image, background=BG).pack(side=tk.LEFT, padx=(0, 18))

        title_box = ttk.Frame(header, style="Header.TFrame")
        title_box.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(title_box, text="Ares", style="Header.TLabel").pack(anchor=tk.W)
        ttk.Label(title_box, text="Local coding workspace powered by Ollama", style="Muted.TLabel").pack(anchor=tk.W)

        self.status = ttk.Label(header, text="Ready", style="Muted.TLabel")
        self.status.pack(side=tk.RIGHT)

    def _build_sidebar(self) -> None:
        logo_path = asset_path("ares_logo.png")
        if logo_path.exists():
            self.logo_image = tk.PhotoImage(file=logo_path)
            tk.Label(self.sidebar, image=self.logo_image, bg=SIDEBAR_BG).pack(fill=tk.X, pady=(14, 10))

        tk.Label(
            self.sidebar,
            text="ARES",
            bg=SIDEBAR_BG,
            fg=TEXT,
            font=("Segoe UI Semibold", 13),
            anchor="w",
            padx=18,
            pady=14,
        ).pack(fill=tk.X)
        nav_items = [
            ("New Chat", self.chat_tab),
            ("Files", self.files_tab),
            ("Diff", self.diff_tab),
            ("Training", self.training_tab),
            ("Commerce", self.commerce_tab),
        ]
        for label, tab in nav_items:
            command = self.new_chat if label == "New Chat" else lambda target=tab, name=label: self._select_tab(target, name)
            button = tk.Button(
                self.sidebar,
                text=label,
                command=command,
                bg=SIDEBAR_BG,
                fg=MUTED,
                activebackground="#333333",
                activeforeground=TEXT,
                bd=0,
                anchor="w",
                padx=18,
                pady=10,
                font=("Segoe UI Semibold", 10),
            )
            button.pack(fill=tk.X, padx=10, pady=2)
            self.nav_buttons[label] = button

        sessions_label = tk.Label(
            self.sidebar,
            text="Sessions",
            bg=SIDEBAR_BG,
            fg=TEXT,
            anchor="w",
            padx=18,
            font=("Segoe UI Semibold", 10),
        )
        sessions_label.pack(fill=tk.X, pady=(18, 6))
        bottom = tk.Frame(self.sidebar, bg=SIDEBAR_BG)
        bottom.pack(fill=tk.X, side=tk.BOTTOM, pady=(0, 8))
        settings_button = tk.Button(
            bottom,
            text="Settings",
            command=lambda: self._select_tab(self.settings_tab, "Settings"),
            bg="#242424",
            fg=TEXT,
            activebackground="#333333",
            activeforeground=TEXT,
            bd=0,
            anchor="w",
            padx=18,
            pady=10,
            font=("Segoe UI Semibold", 10),
        )
        settings_button.pack(fill=tk.X, padx=10, pady=(4, 8))
        self.nav_buttons["Settings"] = settings_button

        self.sidebar_session_list = tk.Listbox(
            self.sidebar,
            bg="#111111",
            fg=MUTED,
            selectbackground="#333333",
            selectforeground=TEXT,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=BORDER,
            font=("Segoe UI", 9),
            height=8,
        )
        self.sidebar_session_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))
        self.sidebar_session_list.bind("<<ListboxSelect>>", self.show_selected_sidebar_session)
        self._select_tab(self.chat_tab, "New Chat")

    def _select_tab(self, tab: ttk.Frame, name: str) -> None:
        self.notebook.select(tab)
        for label, button in self.nav_buttons.items():
            selected = label == name
            button.configure(bg="#333333" if selected else SIDEBAR_BG, fg=TEXT if selected else MUTED)

    def _style_text_widgets(self) -> None:
        def walk(widget: tk.Widget) -> None:
            if isinstance(widget, tk.Text):
                widget.configure(
                    bg="#151515",
                    fg=TEXT,
                    insertbackground=TEXT,
                    selectbackground="#3a3a3a",
                    selectforeground=TEXT,
                    relief=tk.FLAT,
                    borderwidth=1,
                    highlightthickness=1,
                    highlightbackground=BORDER,
                    highlightcolor=ACCENT,
                )
            elif isinstance(widget, tk.Listbox):
                widget.configure(
                    bg="#151515",
                    fg=TEXT,
                    selectbackground="#333333",
                    selectforeground=TEXT,
                    relief=tk.FLAT,
                    highlightthickness=1,
                    highlightbackground=BORDER,
                )
            for child in widget.winfo_children():
                walk(child)

        walk(self)

    def _build_chat_tab(self) -> None:
        ttk.Label(self.chat_tab, text="Task").pack(anchor=tk.W)
        self.prompt = scrolledtext.ScrolledText(self.chat_tab, height=9, wrap=tk.WORD, font=("Consolas", 10))
        self.prompt.pack(fill=tk.X, pady=(6, 14))
        self.prompt.bind("<Return>", self._submit_prompt_from_keyboard)
        self.prompt.bind("<Control-Return>", self._insert_prompt_newline)

        ttk.Label(self.chat_tab, text="Output").pack(anchor=tk.W)
        self.output = scrolledtext.ScrolledText(self.chat_tab, wrap=tk.WORD, font=("Consolas", 10))
        self.output.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    def _build_files_tab(self) -> None:
        toolbar = ttk.Frame(self.files_tab)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        self.refresh_files_button = self._button(toolbar, "Refresh Index", self.refresh_repo_index)
        self.refresh_git_button = self._button(toolbar, "Refresh Git", self.refresh_git)

        panes = ttk.PanedWindow(self.files_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=3)
        panes.add(right, weight=2)

        ttk.Label(left, text="Repo Index And Python Symbols").pack(anchor=tk.W)
        self.file_index_text = scrolledtext.ScrolledText(left, wrap=tk.NONE, font=("Consolas", 9))
        self.file_index_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        ttk.Label(right, text="Git Status").pack(anchor=tk.W)
        self.git_status_text = scrolledtext.ScrolledText(right, height=12, wrap=tk.WORD, font=("Consolas", 9))
        self.git_status_text.pack(fill=tk.BOTH, expand=True, pady=(6, 10))
        ttk.Label(right, text="Git Diff Stat").pack(anchor=tk.W)
        self.git_diff_text = scrolledtext.ScrolledText(right, height=12, wrap=tk.WORD, font=("Consolas", 9))
        self.git_diff_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    def _build_diff_tab(self) -> None:
        toolbar = ttk.Frame(self.diff_tab)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        self.preview_patch_button = self._button(toolbar, "Preview Latest Patch", self.preview_latest_patch)
        self.apply_patch_button = self._button(toolbar, "Apply Patch", self.apply_latest_patch, style="Accent.TButton")
        self.check_patch_button = self._button(toolbar, "Check Patch", self.check_latest_patch)
        self.diff_tests_button = self._button(toolbar, "Run Tests", self.run_tests)

        ttk.Label(self.diff_tab, text="Patch Preview").pack(anchor=tk.W)
        self.patch_text = scrolledtext.ScrolledText(self.diff_tab, wrap=tk.NONE, font=("Consolas", 9))
        self.patch_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.patch_text.insert(tk.END, "Ask Ares in patch mode, then preview and apply the diff here.\n")

    def _build_training_tab(self) -> None:
        controls = ttk.Frame(self.training_tab)
        controls.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(controls, text="Preset").pack(side=tk.LEFT, padx=(0, 6))
        self.preset_box = ttk.Combobox(
            controls,
            textvariable=self.training_preset,
            values=sorted(TRAINING_PRESETS),
            width=18,
            state="readonly",
        )
        self.preset_box.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(controls, text="Corpus").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Entry(controls, textvariable=self.corpus_path, width=28).pack(side=tk.LEFT, padx=(0, 10))
        self.train_button = self._button(controls, "Train Scratch LLM", self.train_scratch_llm, style="Accent.TButton")
        self.metrics_button = self._button(controls, "Refresh Loss Chart", self.refresh_loss_chart)

        generate_box = ttk.Frame(self.training_tab)
        generate_box.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(generate_box, text="Checkpoint").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Entry(generate_box, textvariable=self.checkpoint_path, width=30).pack(side=tk.LEFT, padx=(0, 10))
        self.scratch_prompt = tk.StringVar(value="Ares can")
        ttk.Label(generate_box, text="Prompt").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Entry(generate_box, textvariable=self.scratch_prompt, width=24).pack(side=tk.LEFT, padx=(0, 10))
        self.generate_button = self._button(generate_box, "Generate From Scratch Model", self.generate_from_scratch)

        panes = ttk.PanedWindow(self.training_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True)
        train_left = ttk.Frame(panes)
        train_right = ttk.Frame(panes)
        panes.add(train_left, weight=3)
        panes.add(train_right, weight=2)

        ttk.Label(train_left, text="Training Log").pack(anchor=tk.W)
        self.training_log = scrolledtext.ScrolledText(train_left, wrap=tk.WORD, font=("Consolas", 9))
        self.training_log.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        ttk.Label(train_right, text="Loss Chart").pack(anchor=tk.W)
        self.loss_chart = scrolledtext.ScrolledText(train_right, wrap=tk.NONE, font=("Consolas", 9))
        self.loss_chart.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    def _build_commerce_tab(self) -> None:
        toolbar = ttk.Frame(self.commerce_tab)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        self.commerce_check_button = self._button(toolbar, "Check Shopify/Etsy", self.check_commerce)
        self.shopify_login_button = self._button(toolbar, "Open Shopify Sign In", self.open_shopify_sign_in)
        self.etsy_login_button = self._button(toolbar, "Open Etsy Sign In", self.open_etsy_sign_in)
        self.etsy_apps_button = self._button(toolbar, "Open Etsy Apps", self.open_etsy_apps)
        self.commerce_learn_button = self._button(toolbar, "Learn From Snapshot", self.learn_from_commerce_snapshot)

        ttk.Label(
            self.commerce_tab,
            text="Read-only shop connector. Write actions will be added only with previews and approvals.",
        ).pack(anchor=tk.W, pady=(0, 8))
        self.commerce_output = scrolledtext.ScrolledText(self.commerce_tab, wrap=tk.WORD, font=("Consolas", 9))
        self.commerce_output.pack(fill=tk.BOTH, expand=True)
        self.commerce_output.insert(
            tk.END,
            "Ares can open the official Shopify and Etsy sign-in pages for you.\n"
            "For shop management, their APIs still require an approved app/OAuth token or admin token.\n\n"
            "Environment variables:\n"
            "Shopify: ARES_SHOPIFY_SHOP, ARES_SHOPIFY_ADMIN_TOKEN, optional ARES_SHOPIFY_API_VERSION\n"
            "Etsy: ARES_ETSY_API_KEY, ARES_ETSY_ACCESS_TOKEN, ARES_ETSY_SHOP_ID\n\n"
            "Click Check Shopify/Etsy to test connections and fetch a shop snapshot.\n",
        )

    def _build_sessions_tab(self) -> None:
        toolbar = ttk.Frame(self.sessions_tab)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        self.refresh_sessions_button = self._button(toolbar, "Refresh Sessions", self.refresh_sessions)

        panes = ttk.PanedWindow(self.sessions_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True)
        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=3)

        self.session_list = tk.Listbox(left, font=("Consolas", 9), activestyle="dotbox")
        self.session_list.pack(fill=tk.BOTH, expand=True)
        self.session_list.bind("<<ListboxSelect>>", self.show_selected_session)
        self.sessions: list[dict[str, object]] = []

        ttk.Label(right, text="Session Detail").pack(anchor=tk.W)
        self.session_detail = scrolledtext.ScrolledText(right, wrap=tk.WORD, font=("Consolas", 9))
        self.session_detail.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    def _build_settings_tab(self) -> None:
        ttk.Label(self.settings_tab, text="Local Model").pack(anchor=tk.W)
        ttk.Entry(self.settings_tab, textvariable=self.model, width=36).pack(anchor=tk.W, pady=(6, 14))
        ttk.Label(self.settings_tab, text="Agent Mode").pack(anchor=tk.W)
        self.mode_box = ttk.Combobox(
            self.settings_tab,
            textvariable=self.mode,
            values=sorted(MODE_INSTRUCTIONS),
            width=18,
            state="readonly",
        )
        self.mode_box.pack(anchor=tk.W, pady=(6, 14))
        info = (
            "Ares is configured for local-first coding through Ollama.\n\n"
            "Implemented panels:\n"
            "- New Chat: ask the local model; website/app tasks are routed automatically.\n"
            "- Files: repo index, Python symbols, git status, and diff stat.\n"
            "- Diff: preview/check/apply patch suggestions with backups.\n"
            "- Training: pretraining/SFT presets, progress log, loss chart, and scratch generation.\n"
            "- Commerce: read-only Shopify/Etsy connection checks and shop snapshots.\n"
            "- Sessions: local history viewer from runs/agent/sessions.jsonl.\n"
            "\nKeyboard shortcuts:\n"
            "- Enter in Task: send to Ares.\n"
            "- Ctrl+Enter in Task: insert a new paragraph.\n"
            "- Ctrl+R: Run tests.\n"
            "- Ctrl+L: Refresh repo index.\n"
            "- Ctrl+T: Start scratch training.\n"
            "\nTraining note:\n"
            "The scratch model is a learning/experiment model. Ares uses Ollama for real coding-agent work.\n"
            "The LLM.C CPU Demo preset is inspired by karpathy/llm.c's short CPU demo style: small batch,\n"
            "short context, visible loss, timing, and token-throughput logs.\n"
            "BPE presets add learned pair-token merges. Ares SFT presets add chat formatting and assistant-only masked loss.\n"
            "Training runs save metrics.json, training_log.csv, validation_curve.svg, and runs/experiments.jsonl.\n"
            "\nSelf-learning note:\n"
            "Ares learns safely through local memory in data/ares_memory.md, not by silently retraining itself.\n"
            "Long unattended retraining can overfit, break behavior, or learn bad data unless it is evaluated.\n"
            "\nCommerce note:\n"
            "Shopify and Etsy credentials are read from environment variables so secrets are not saved in this repo.\n"
        )
        text = scrolledtext.ScrolledText(self.settings_tab, wrap=tk.WORD, font=("Consolas", 10))
        text.pack(fill=tk.BOTH, expand=True)
        text.insert(tk.END, info)
        text.configure(state=tk.DISABLED)

    def _bind_shortcuts(self) -> None:
        self.bind("<Control-r>", lambda _event: self.run_tests())
        self.bind("<Control-l>", lambda _event: self.refresh_repo_index())
        self.bind("<Control-t>", lambda _event: self.train_scratch_llm())

    def _submit_prompt_from_keyboard(self, _event=None) -> str:
        self.ask_ares()
        return "break"

    def _insert_prompt_newline(self, _event=None) -> str:
        self.prompt.insert(tk.INSERT, "\n")
        return "break"

    def _button(self, parent: tk.Widget, text: str, command, style: str | None = None) -> ttk.Button:
        button = ttk.Button(parent, text=text, command=command, style=style)
        button.pack(side=tk.LEFT, padx=(0, 10))
        self.action_buttons.append(button)
        return button

    def ask_ares(self) -> None:
        task = self.prompt.get("1.0", tk.END).strip()
        if not task:
            messagebox.showinfo(APP_NAME, "Enter a task for Ares first.")
            return

        if should_create_web_artifact(task):
            self.create_website_app()
            return

        self._set_busy(True, "Asking local model...")
        self._append_output(f"\n[Ares] {task}\n\n")
        thread = threading.Thread(target=self._ask_ares_worker, args=(task,), daemon=True)
        thread.start()

    def new_chat(self) -> None:
        self._select_tab(self.chat_tab, "New Chat")
        self.prompt.delete("1.0", tk.END)
        self.output.delete("1.0", tk.END)
        self.latest_response = ""
        self.latest_patch = ""
        self.latest_session_id = "manual"
        self.status.configure(text="Ready")

    def _ask_ares_worker(self, task: str) -> None:
        try:
            client = ensure_ollama_client()
            result = ask_agent(
                task=task,
                repo=self.repo_root,
                model=self.model.get().strip() or DEFAULT_MODEL,
                mode=self.mode.get(),
                max_files=24,
                max_chars_per_file=3500,
                max_total_chars=22000,
                temperature=0.2,
                num_ctx=8192,
                client=client,
            )
            self.latest_response = result.response
            self.latest_session_id = result.session.id
            self.messages.put(result.response + "\n")
            self.messages.put(
                f"\n[Ares session {result.session.id}] "
                f"context files: {result.included_files}/{result.total_files}; "
                f"estimated tokens: prompt {result.session.estimated_prompt_tokens}, "
                f"response {result.session.estimated_response_tokens}\n"
            )
            self.messages.put("__PATCH_PREVIEW__")
            self.messages.put("__REFRESH_SESSIONS__")
        except Exception as exc:
            self.messages.put(f"Error: {exc}\n")
        finally:
            self.messages.put("__READY__")

    def create_website_app(self) -> None:
        brief = self.prompt.get("1.0", tk.END).strip()
        if not brief:
            messagebox.showinfo(APP_NAME, "Enter a website or app brief first.")
            return

        self._set_busy(True, "Creating website/app...")
        self._append_output(f"\n[Ares Builder] {brief}\n\n")
        thread = threading.Thread(target=self._create_website_app_worker, args=(brief,), daemon=True)
        thread.start()

    def _create_website_app_worker(self, brief: str) -> None:
        try:
            client = ensure_ollama_client()
            result = create_web_artifact(
                brief=brief,
                repo=self.repo_root,
                model=self.model.get().strip() or DEFAULT_MODEL,
                client=client,
            )
            self.messages.put(f"Created website/app artifact:\n{result.root}\n")
            self.messages.put(f"Open file:\n{result.entry_file}\n")
            self.messages.put(f"Files: {', '.join(file.path for file in result.files)}\n")
            if result.used_fallback:
                self.messages.put(
                    "Ares used the built-in polished template because the model output did not pass the artifact gate.\n"
                )
            try:
                os.startfile(result.entry_file)
            except OSError as exc:
                self.messages.put(f"Could not auto-open browser: {exc}\n")
        except Exception as exc:
            self.messages.put(f"Error: {exc}\n")
        finally:
            self.messages.put("__READY__")

    def run_tests(self) -> None:
        python_exe = self.python_exe()
        command = [str(python_exe), "-m", "pytest", "-q"]
        self._set_busy(True, "Running tests...")
        self._append_output("\n[Tests] Running pytest\n\n")
        thread = threading.Thread(target=self._run_process_worker, args=(command, "[Tests]"), daemon=True)
        thread.start()

    def train_scratch_llm(self) -> None:
        preset = TRAINING_PRESETS[self.training_preset.get()]
        python_exe = self.python_exe()
        corpus = self.corpus_path.get().strip() or "data/ares_corpus.txt"
        mask_path = "data/ares_sft_mask.json"
        if preset.stage == "sft" and corpus == "data/ares_corpus.txt":
            corpus = "data/ares_sft_corpus.txt"

        if preset.stage == "sft":
            command = [
                str(python_exe),
                "-m",
                "local_llm.prepare_sft_corpus",
                "--repo",
                str(self.repo_root),
                "--output",
                corpus,
                "--mask-output",
                mask_path,
            ]
        else:
            command = [
                str(python_exe),
                "-m",
                "local_llm.prepare_corpus",
                "--repo",
                str(self.repo_root),
                "--output",
                corpus,
            ]
        train_command = [
            str(python_exe),
            "-m",
            "local_llm.train",
            "--input",
            corpus,
            "--out-dir",
            "runs/ares",
            "--device",
            "cpu",
            *preset_args(preset),
        ]
        if preset.stage == "sft":
            train_command.extend(["--sft-mask", mask_path])

        self._set_busy(True, f"Training: {preset.name}...")
        self._append_training(f"\n[Training] Preparing corpus and running {preset.name}\n\n")
        thread = threading.Thread(
            target=self._run_process_chain_worker,
            args=([command, train_command], "[Training]", "__REFRESH_LOSS__"),
            daemon=True,
        )
        thread.start()

    def generate_from_scratch(self) -> None:
        checkpoint = self.checkpoint_path.get().strip() or "runs/ares/checkpoint.pt"
        command = [
            str(self.python_exe()),
            "-m",
            "local_llm.generate",
            "--checkpoint",
            checkpoint,
            "--prompt",
            self.scratch_prompt.get(),
            "--max-new-tokens",
            "120",
            "--device",
            "cpu",
        ]
        self._set_busy(True, "Generating from scratch model...")
        self._append_training("\n[Generate] Running scratch checkpoint\n\n")
        thread = threading.Thread(target=self._run_process_worker, args=(command, "[Generate]"), daemon=True)
        thread.start()

    def check_commerce(self) -> None:
        self._set_busy(True, "Checking Shopify/Etsy...")
        self.commerce_output.delete("1.0", tk.END)
        self.commerce_output.insert(tk.END, "Checking connections...\n")
        thread = threading.Thread(target=self._check_commerce_worker, daemon=True)
        thread.start()

    def _check_commerce_worker(self) -> None:
        try:
            checks = check_commerce_connections()
            self.messages.put("__COMMERCE__" + format_commerce_checks(checks))
        except Exception as exc:
            self.messages.put("__COMMERCE__" + f"Commerce check failed: {exc}")
        finally:
            self.messages.put("__READY__")

    def learn_from_commerce_snapshot(self) -> None:
        snapshot = self.commerce_output.get("1.0", tk.END).strip()
        if not snapshot:
            messagebox.showinfo(APP_NAME, "Run a commerce check first.")
            return
        entry = append_memory(self.repo_root, "Commerce snapshot", snapshot[:4000])
        self.commerce_output.insert(tk.END, f"\n\nSaved to Ares memory: {entry.created_at} - {entry.title}\n")

    def open_shopify_sign_in(self) -> None:
        webbrowser.open("https://admin.shopify.com/")
        self.commerce_output.insert(tk.END, "\nOpened Shopify Admin sign-in in your browser.\n")

    def open_etsy_sign_in(self) -> None:
        webbrowser.open("https://www.etsy.com/signin")
        self.commerce_output.insert(tk.END, "\nOpened Etsy sign-in in your browser.\n")

    def open_etsy_apps(self) -> None:
        webbrowser.open("https://www.etsy.com/developers/your-apps")
        self.commerce_output.insert(tk.END, "\nOpened Etsy developer apps page in your browser.\n")

    def preview_latest_patch(self) -> None:
        bundle = extract_unified_diffs(self.latest_response)
        self.latest_patch = "\n".join(bundle.patches)
        self.patch_text.delete("1.0", tk.END)
        if self.latest_patch:
            self.patch_text.insert(tk.END, self.latest_patch)
            self.notebook.select(self.diff_tab)
        else:
            self.patch_text.insert(tk.END, "No unified diff found in the latest Ares response.\n")

    def current_patch_text(self) -> str:
        text = self.patch_text.get("1.0", tk.END).strip()
        if text and "Ask Ares in patch mode" not in text:
            return text + "\n"
        return self.latest_patch

    def check_latest_patch(self) -> None:
        patch_text = self.current_patch_text()
        result = check_patch(self.repo_root, patch_text)
        self.patch_text.insert(tk.END, f"\n[Patch check] {result.message}\n")

    def apply_latest_patch(self) -> None:
        patch_text = self.current_patch_text()
        result = check_patch(self.repo_root, patch_text)
        if not result.ok:
            self.patch_text.insert(tk.END, f"\n[Patch check failed] {result.message}\n")
            return

        if not messagebox.askyesno(APP_NAME, "Apply this patch? A backup will be created first."):
            return
        applied = apply_patch_with_backup(self.repo_root, patch_text, label=self.latest_session_id)
        self.patch_text.insert(tk.END, f"\n[Apply patch] {applied.message}\n")
        if applied.backup_dir:
            self.patch_text.insert(tk.END, f"Backup: {applied.backup_dir}\n")
        self.refresh_git()

    def refresh_repo_index(self) -> None:
        try:
            index = build_repo_index(self.repo_root)
            self.file_index_text.delete("1.0", tk.END)
            self.file_index_text.insert(tk.END, format_repo_index(index))
            self.git_status_text.delete("1.0", tk.END)
            self.git_status_text.insert(tk.END, index.git_status)
            self.git_diff_text.delete("1.0", tk.END)
            self.git_diff_text.insert(tk.END, index.git_diff_stat)
        except Exception as exc:
            self.file_index_text.delete("1.0", tk.END)
            self.file_index_text.insert(tk.END, f"Could not build repo index: {exc}")

    def refresh_git(self) -> None:
        index = build_repo_index(self.repo_root, max_files=1)
        self.git_status_text.delete("1.0", tk.END)
        self.git_status_text.insert(tk.END, index.git_status)
        self.git_diff_text.delete("1.0", tk.END)
        self.git_diff_text.insert(tk.END, index.git_diff_stat)

    def refresh_sessions(self) -> None:
        self.sessions = load_agent_sessions(self.repo_root)
        self.session_list.delete(0, tk.END)
        if self.sidebar_session_list is not None:
            self.sidebar_session_list.delete(0, tk.END)
        for session in reversed(self.sessions):
            created = str(session.get("created_at", ""))
            task = str(session.get("task", "")).replace("\n", " ")[:70]
            self.session_list.insert(tk.END, f"{created} | {session.get('mode')} | {task}")
            if self.sidebar_session_list is not None:
                self.sidebar_session_list.insert(tk.END, f"{session.get('mode')} | {task[:42]}")

    def show_selected_session(self, _event=None) -> None:
        selection = self.session_list.curselection()
        if not selection:
            return
        session = list(reversed(self.sessions))[selection[0]]
        lines = [
            f"ID: {session.get('id')}",
            f"Created: {session.get('created_at')}",
            f"Model: {session.get('model')}",
            f"Mode: {session.get('mode')}",
            f"Context files: {session.get('included_files')}/{session.get('total_files')}",
            f"Estimated tokens: prompt {session.get('estimated_prompt_tokens')}, response {session.get('estimated_response_tokens')}",
            "",
            "Task:",
            str(session.get("task", "")),
            "",
            "Response preview:",
            str(session.get("response_preview", "No response preview stored for this older session.")),
        ]
        self.session_detail.delete("1.0", tk.END)
        self.session_detail.insert(tk.END, "\n".join(lines))

    def show_selected_sidebar_session(self, _event=None) -> None:
        if self.sidebar_session_list is None:
            return
        selection = self.sidebar_session_list.curselection()
        if not selection:
            return
        index = selection[0]
        self._select_tab(self.sessions_tab, "Sessions")
        self.session_list.selection_clear(0, tk.END)
        self.session_list.selection_set(index)
        self.session_list.see(index)
        self.show_selected_session()

    def refresh_loss_chart(self) -> None:
        metrics = load_metrics(self.repo_root / "runs" / "ares" / "metrics.json")
        self.loss_chart.delete("1.0", tk.END)
        if not metrics:
            self.loss_chart.insert(tk.END, "No metrics found at runs/ares/metrics.json")
            return
        self.loss_chart.insert(tk.END, ascii_loss_chart(metrics))

    def _run_process_chain_worker(self, commands: list[list[str]], label: str, after_message: str | None = None) -> None:
        try:
            for command in commands:
                return_code = self._run_process(command, label)
                if return_code != 0:
                    self.messages.put(f"\n{label} Stopped after exit code {return_code}\n")
                    return
            self.messages.put(f"\n{label} Complete\n")
            if after_message:
                self.messages.put(after_message)
        except Exception as exc:
            self.messages.put(f"Error: {exc}\n")
        finally:
            self.messages.put("__READY__")

    def _run_process_worker(self, command: list[str], label: str) -> None:
        try:
            return_code = self._run_process(command, label)
            self.messages.put(f"\n{label} Finished with exit code {return_code}\n")
        except Exception as exc:
            self.messages.put(f"Error: {exc}\n")
        finally:
            self.messages.put("__READY__")

    def _run_process(self, command: list[str], label: str) -> int:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process = subprocess.Popen(
            command,
            cwd=self.repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=creationflags,
        )
        assert process.stdout is not None
        for line in process.stdout:
            message = line if label in {"[Training]", "[Generate]"} else f"{line}"
            if label in {"[Training]", "[Generate]"}:
                self.messages.put("__TRAINING__" + message)
            else:
                self.messages.put(message)
        return process.wait()

    def python_exe(self) -> Path:
        python_exe = self.repo_root / ".venv" / "Scripts" / "python.exe"
        return python_exe if python_exe.exists() else Path(sys.executable)

    def clear_output(self) -> None:
        self.output.delete("1.0", tk.END)

    def _append_output(self, text: str) -> None:
        self.output.insert(tk.END, text)
        self.output.see(tk.END)

    def _append_training(self, text: str) -> None:
        self.training_log.insert(tk.END, text)
        self.training_log.see(tk.END)

    def _set_busy(self, busy: bool, status: str) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        for button in self.action_buttons:
            button.configure(state=state)
        self.status.configure(text=status)

    def _drain_messages(self) -> None:
        while True:
            try:
                message = self.messages.get_nowait()
            except queue.Empty:
                break
            if message == "__READY__":
                self._set_busy(False, "Ready")
            elif message == "__PATCH_PREVIEW__":
                self.preview_latest_patch()
            elif message == "__REFRESH_SESSIONS__":
                self.refresh_sessions()
            elif message == "__REFRESH_LOSS__":
                self.refresh_loss_chart()
            elif message.startswith("__TRAINING__"):
                self._append_training(message.removeprefix("__TRAINING__"))
            elif message.startswith("__COMMERCE__"):
                self.commerce_output.delete("1.0", tk.END)
                self.commerce_output.insert(tk.END, message.removeprefix("__COMMERCE__"))
                self.commerce_output.see(tk.END)
            else:
                self._append_output(message)
        self.after(150, self._drain_messages)


def asset_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base / "assets" / name


def ensure_ollama_client() -> OllamaClient:
    client = OllamaClient(timeout=180)
    try:
        client.list_models()
        return client
    except RuntimeError:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        for _ in range(20):
            time.sleep(0.5)
            try:
                client.list_models()
                return client
            except RuntimeError:
                continue
        return client


def should_create_web_artifact(task: str) -> bool:
    text = task.lower()
    build_words = (
        "create",
        "build",
        "make",
        "design",
        "generate",
        "develop",
        "code",
        "implement",
    )
    artifact_words = (
        "website",
        "web site",
        "web app",
        "app",
        "dashboard",
        "landing page",
        "portfolio",
        "storefront",
        "site",
    )
    return any(word in text for word in build_words) and any(word in text for word in artifact_words)


def main() -> None:
    app = AresApp()
    app.mainloop()


if __name__ == "__main__":
    main()
