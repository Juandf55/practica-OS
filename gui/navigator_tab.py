"""
GUI — Tab Módulo 2: Navegador de archivos
Panel con tabla de atributos y botones de operación.
"""

import os
import stat
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from modules.navigator import Navigator, get_type_char, format_permissions, get_owner, fmt_date


class NavigatorTab(tk.Frame):

    ICONS = {
        'd': '📁', '-': '📄', 'l': '🔗',
        'c': '⚙️', 'b': '💾', 'p': '📡', 's': '🔌', '?': '❓'
    }
    COL_COLORS = {
        'd': '#4fc3f7', '-': '#e0e0e0', 'l': '#80cbc4',
        'c': '#ffcc02', 'b': '#ff9800', 'p': '#ce93d8',
        's': '#f48fb1', '?': '#ef5350',
    }

    def __init__(self, parent, theme):
        super().__init__(parent, bg=theme['bg'])
        self.theme = theme
        self.current_path = None
        self.history = []
        self._build_ui()

    def _build_ui(self):
        t = self.theme

        # ── Barra superior ────────────────────────────────────────────────────
        top = tk.Frame(self, bg=t['panel'], pady=8, padx=10)
        top.pack(fill='x')

        tk.Label(top, text="🗂  Navegador de Archivos",
                 bg=t['panel'], fg=t['accent'],
                 font=t['font_title']).pack(side='left')

        nav_btns = tk.Frame(top, bg=t['panel'])
        nav_btns.pack(side='right')

        tk.Button(nav_btns, text="📂 Abrir", command=self._browse,
                  bg=t['accent'], fg='white', font=t['font_btn'],
                  relief='flat', padx=10, pady=4, cursor='hand2'
                  ).pack(side='left', padx=3)
        tk.Button(nav_btns, text="⬆ Subir", command=self._go_up,
                  bg=t['btn2'], fg='white', font=t['font_btn'],
                  relief='flat', padx=10, pady=4, cursor='hand2'
                  ).pack(side='left', padx=3)
        tk.Button(nav_btns, text="🔄 Refrescar", command=self._refresh,
                  bg=t['btn2'], fg='white', font=t['font_btn'],
                  relief='flat', padx=10, pady=4, cursor='hand2'
                  ).pack(side='left', padx=3)

        # ── Barra de ruta ─────────────────────────────────────────────────────
        path_bar = tk.Frame(self, bg=t['card'], pady=5, padx=10)
        path_bar.pack(fill='x')

        tk.Label(path_bar, text="📍", bg=t['card'], fg=t['fg'],
                 font=t['font_small']).pack(side='left')
        self.path_var = tk.StringVar(value="Ninguna ruta seleccionada")
        tk.Label(path_bar, textvariable=self.path_var,
                 bg=t['card'], fg=t['accent'],
                 font=t['font_small']).pack(side='left', padx=4)

        # ── Panel principal ────────────────────────────────────────────────────
        paned = tk.PanedWindow(self, orient='horizontal',
                               bg=t['bg'], sashwidth=4)
        paned.pack(fill='both', expand=True, padx=10, pady=6)

        # ── Lista de archivos (izquierda) ──────────────────────────────────────
        list_frame = tk.Frame(paned, bg=t['bg'])

        columns = ('tipo', 'perms', 'inodo', 'tamaño_kb', 'links',
                   'propietario', 'modificado')
        self.table = ttk.Treeview(list_frame, columns=columns,
                                  show='headings tree', selectmode='browse')

        # Columnas
        self.table.heading('#0',         text='Nombre')
        self.table.heading('tipo',       text='T')
        self.table.heading('perms',      text='Permisos')
        self.table.heading('inodo',      text='Inodo')
        self.table.heading('tamaño_kb',  text='Tamaño KB')
        self.table.heading('links',      text='Links')
        self.table.heading('propietario',text='Propietario')
        self.table.heading('modificado', text='Modificado')

        self.table.column('#0',          width=220, minwidth=120)
        self.table.column('tipo',        width=35,  minwidth=30,  anchor='center')
        self.table.column('perms',       width=110, minwidth=90,  anchor='center')
        self.table.column('inodo',       width=90,  minwidth=70,  anchor='center')
        self.table.column('tamaño_kb',   width=90,  minwidth=70,  anchor='e')
        self.table.column('links',       width=50,  minwidth=40,  anchor='center')
        self.table.column('propietario', width=110, minwidth=80)
        self.table.column('modificado',  width=160, minwidth=130)

        for tc, color in self.COL_COLORS.items():
            self.table.tag_configure(tc, foreground=color)

        vsb = ttk.Scrollbar(list_frame, orient='vertical',
                             command=self.table.yview)
        hsb = ttk.Scrollbar(list_frame, orient='horizontal',
                             command=self.table.xview)
        self.table.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.table.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.table.bind('<Double-Button-1>', self._on_double_click)
        self.table.bind('<<TreeviewSelect>>', self._on_select)

        paned.add(list_frame, minsize=400)

        # ── Panel derecho: atributos + operaciones ─────────────────────────────
        right = tk.Frame(paned, bg=t['panel'])
        paned.add(right, minsize=280)

        # Atributos
        tk.Label(right, text="📋 Atributos",
                 bg=t['panel'], fg=t['accent'],
                 font=t['font_subtitle']).pack(pady=(12, 4), padx=10, anchor='w')

        self.attr_text = tk.Text(right, bg=t['card'], fg=t['fg'],
                                  font=('Courier', 9), relief='flat',
                                  state='disabled', height=18,
                                  padx=8, pady=6)
        self.attr_text.pack(fill='x', padx=8)

        # ── Operaciones ────────────────────────────────────────────────────────
        tk.Label(right, text="⚙️ Operaciones",
                 bg=t['panel'], fg=t['accent'],
                 font=t['font_subtitle']).pack(pady=(10, 4), padx=10, anchor='w')

        ops = tk.Frame(right, bg=t['panel'], padx=8)
        ops.pack(fill='x')

        btn_style = dict(bg=t['card'], fg=t['fg'], font=t['font_btn'],
                         relief='flat', pady=5, cursor='hand2',
                         activebackground=t['accent'], activeforeground='white')

        operations = [
            ("📄 Crear archivo  (--rm)",    self._op_create_file),
            ("📁 Crear directorio (--touchDir)", self._op_create_dir),
            ("🗑 Borrar          (--mk)",   self._op_delete),
            ("📋 Copiar          (--cc)",   self._op_copy),
            ("✂️  Cortar          (--cx)",   self._op_cut),
            ("📌 Pegar           (--cv)",   self._op_paste),
        ]
        for label, cmd in operations:
            tk.Button(ops, text=label, command=cmd,
                      width=32, anchor='w', **btn_style
                      ).pack(fill='x', pady=2)

        # ── Estado ────────────────────────────────────────────────────────────
        status_bar = tk.Frame(self, bg=t['panel'], pady=4)
        status_bar.pack(fill='x', side='bottom')
        self.status_var = tk.StringVar(value="Listo")
        tk.Label(status_bar, textvariable=self.status_var,
                 bg=t['panel'], fg=t['fg_dim'],
                 font=t['font_small']).pack(side='left', padx=10)

    # ── Carga ─────────────────────────────────────────────────────────────────

    def _browse(self):
        path = filedialog.askdirectory(title="Seleccionar directorio")
        if path:
            self.load_path(path)

    def load_path(self, path: str):
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            messagebox.showerror("Error", f"No es un directorio:\n{path}")
            return
        if self.current_path and self.current_path != path:
            self.history.append(self.current_path)
        self.current_path = path
        self.path_var.set(path)
        self._refresh()

    def _refresh(self):
        if not self.current_path:
            return
        self.table.delete(*self.table.get_children())
        nav = Navigator(self.current_path)
        entries = nav.get_entries_data(self.current_path)
        for e in entries:
            tc   = e['type']
            icon = self.ICONS.get(tc, '?')
            name = e['name'] + ('/' if e['is_dir'] else '')
            self.table.insert(
                '', 'end',
                text=f" {icon} {name}",
                values=(
                    tc,
                    f"{tc}{e['perms']}",
                    e['inode'],
                    f"{e['size_kb']:.2f}",
                    e['links'],
                    f"{e['owner']}:{e['group']}",
                    e['mtime'],
                ),
                tags=(tc,),
                iid=e['path'],
            )
        self.status_var.set(f"{len(entries)} entradas — {self.current_path}")

    def _go_up(self):
        if self.current_path:
            parent = os.path.dirname(self.current_path)
            if parent != self.current_path:
                self.load_path(parent)

    # ── Eventos tabla ─────────────────────────────────────────────────────────

    def _on_double_click(self, event):
        sel = self.table.focus()
        if sel and os.path.isdir(sel):
            self.load_path(sel)

    def _on_select(self, event):
        sel = self.table.focus()
        if not sel:
            return
        self._show_attrs(sel)

    def _show_attrs(self, path: str):
        try:
            st = os.lstat(path)
            tc, _ = get_type_char(st.st_mode)
            perms  = format_permissions(st.st_mode)
            owner, group = get_owner(st)
            info = (
                f"Nombre : {os.path.basename(path)}\n"
                f"Tipo   : [{tc}]\n"
                f"─────────────────────\n"
                f"Permisos: {tc}{perms}\n"
                f"Octal  : {oct(st.st_mode & 0o7777)}\n"
                f"Inodo  : {st.st_ino}\n"
                f"Links  : {st.st_nlink}\n"
                f"─────────────────────\n"
                f"Dueño  : {owner} (uid={st.st_uid})\n"
                f"Grupo  : {group} (gid={st.st_gid})\n"
                f"─────────────────────\n"
                f"Tamaño : {st.st_size} B\n"
                f"         {st.st_size/1024:.3f} KB\n"
                f"Bloques: {st.st_blocks}\n"
                f"─────────────────────\n"
                f"Acceso : {fmt_date(st.st_atime)}\n"
                f"Modif  : {fmt_date(st.st_mtime)}\n"
                f"Cambio : {fmt_date(st.st_ctime)}\n"
                f"─────────────────────\n"
                f"Ruta   :\n{path}"
            )
        except Exception as e:
            info = f"Error: {e}"

        self.attr_text.config(state='normal')
        self.attr_text.delete('1.0', 'end')
        self.attr_text.insert('end', info)
        self.attr_text.config(state='disabled')

    # ── Operaciones ───────────────────────────────────────────────────────────

    def _get_selected_path(self):
        return self.table.focus() or None

    def _op_create_file(self):
        if not self.current_path:
            messagebox.showwarning("Aviso", "Selecciona una ruta primero.")
            return
        name = simpledialog.askstring("Crear archivo",
                                      "Nombre del nuevo archivo:",
                                      parent=self)
        if not name:
            return
        target = os.path.join(self.current_path, name)
        nav = Navigator(self.current_path)

        class FakeArgs:
            dir = touchDir = mk = cc = cx = cv = None
            rm = target
        nav.run(FakeArgs())
        self._refresh()

    def _op_create_dir(self):
        if not self.current_path:
            messagebox.showwarning("Aviso", "Selecciona una ruta primero.")
            return
        name = simpledialog.askstring("Crear directorio",
                                      "Nombre del nuevo directorio:",
                                      parent=self)
        if not name:
            return
        target = os.path.join(self.current_path, name)
        nav = Navigator(self.current_path)

        class FakeArgs:
            dir = rm = mk = cc = cx = cv = None
            touchDir = target
        nav.run(FakeArgs())
        self._refresh()

    def _op_delete(self):
        sel = self._get_selected_path()
        if not sel:
            messagebox.showwarning("Aviso", "Selecciona un elemento primero.")
            return
        if not messagebox.askyesno("Confirmar",
                                   f"¿Eliminar?\n{sel}"):
            return
        nav = Navigator(self.current_path or '/')

        class FakeArgs:
            dir = rm = touchDir = cc = cx = cv = None
            mk = sel
        nav.run(FakeArgs())
        self._refresh()

    def _op_copy(self):
        sel = self._get_selected_path()
        if not sel:
            messagebox.showwarning("Aviso", "Selecciona un elemento primero.")
            return
        nav = Navigator(self.current_path or '/')

        class FakeArgs:
            dir = rm = touchDir = mk = cx = cv = None
            cc = sel
        nav.run(FakeArgs())
        self.status_var.set(f"Copiado: {os.path.basename(sel)}")

    def _op_cut(self):
        sel = self._get_selected_path()
        if not sel:
            messagebox.showwarning("Aviso", "Selecciona un elemento primero.")
            return
        nav = Navigator(self.current_path or '/')

        class FakeArgs:
            dir = rm = touchDir = mk = cc = cv = None
            cx = sel
        nav.run(FakeArgs())
        self.status_var.set(f"Cortado: {os.path.basename(sel)}")

    def _op_paste(self):
        if not self.current_path:
            messagebox.showwarning("Aviso", "Navega a un directorio destino primero.")
            return
        nav = Navigator(self.current_path)

        class FakeArgs:
            dir = rm = touchDir = mk = cc = cx = None
            cv = self.current_path
        nav.run(FakeArgs())
        self._refresh()

    # ── API para carga desde CLI ──────────────────────────────────────────────

    def _op_from_arg(self, op: str, target: str):
        """
        Ejecuta una operación (rm, touchDir, mk, cc, cx, cv)
        con un path dado directamente desde argumentos CLI.
        Muestra el resultado en la interfaz.
        """
        import io, sys as _sys
        old_out = _sys.stdout
        _sys.stdout = buf = io.StringIO()

        nav = Navigator(self.current_path or os.path.dirname(target) or '/')

        class FakeArgs:
            dir      = None
            rm       = target if op == 'rm'       else None
            touchDir = target if op == 'touchDir'  else None
            mk       = target if op == 'mk'        else None
            cc       = target if op == 'cc'        else None
            cx       = target if op == 'cx'        else None
            cv       = target if op == 'cv'        else None

        nav.run(FakeArgs())
        _sys.stdout = old_out
        output = buf.getvalue()

        # Mostrar resultado en panel de atributos
        self.attr_text.config(state='normal')
        self.attr_text.delete('1.0', 'end')
        self.attr_text.insert('end',
            f"Operación: --{op}\n"
            f"Destino  : {target}\n"
            f"{'─'*40}\n"
            f"{output if output else '(sin salida)'}\n"
        )
        self.attr_text.config(state='disabled')
        self.status_var.set(f"Operación --{op} ejecutada: {target}")

        # Refrescar tabla si aplica
        if op in ('rm', 'touchDir', 'mk', 'cv') and self.current_path:
            self._refresh()

    # ── Pantalla de bienvenida / menú ─────────────────────────────────────────

    def show_welcome_menu(self):
        """
        Muestra una pantalla de menú cuando se llama 'somonger nav' sin argumentos.
        Presenta todos los subcomandos disponibles con botones que ejecutan
        la misma interfaz de navegación.
        """
        t = self.theme

        # Overlay encima del contenido actual
        overlay = tk.Toplevel(self)
        overlay.title("somonger nav — Selecciona comando")
        overlay.geometry("620x500")
        overlay.configure(bg=t['bg'])
        overlay.resizable(False, False)
        overlay.grab_set()   # Modal

        # Centrar sobre la ventana padre
        overlay.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width()  - 620) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 500) // 2
        overlay.geometry(f"+{x}+{y}")

        # ── Encabezado ────────────────────────────────────────────────────────
        hdr = tk.Frame(overlay, bg=t['panel'], pady=16)
        hdr.pack(fill='x')
        tk.Label(hdr, text="🗂  somonger nav",
                 bg=t['panel'], fg=t['accent'],
                 font=('Inter', 16, 'bold')).pack()
        tk.Label(hdr,
                 text="Selecciona una operación o escribe la ruta manualmente",
                 bg=t['panel'], fg=t['fg_dim'],
                 font=('Inter', 10)).pack(pady=(4, 0))

        # ── Comandos disponibles ──────────────────────────────────────────────
        body = tk.Frame(overlay, bg=t['bg'], padx=30, pady=16)
        body.pack(fill='both', expand=True)

        tk.Label(body, text="Comandos disponibles:",
                 bg=t['bg'], fg=t['fg'],
                 font=('Inter', 11, 'bold')).pack(anchor='w', pady=(0, 10))

        commands = [
            ("📂  --dir  <ruta>",
             "Navegar a un directorio y ver su contenido",
             '#4fc3f7', 'dir_arg'),
            ("📄  --rm   <ruta>",
             "Crear un nuevo fichero en la ruta indicada",
             '#66bb6a', 'rm'),
            ("📁  --touchDir <ruta>",
             "Crear un nuevo directorio en la ruta indicada",
             '#ffcc02', 'touchDir'),
            ("🗑  --mk   <ruta>",
             "Borrar un archivo o directorio",
             '#ef5350', 'mk'),
            ("📋  --cc   <ruta>",
             "Copiar archivo/directorio al portapapeles",
             '#a06cd5', 'cc'),
            ("✂️   --cx   <ruta>",
             "Cortar archivo/directorio al portapapeles",
             '#ff9800', 'cx'),
            ("📌  --cv   <ruta>",
             "Pegar el elemento copiado/cortado en la ruta",
             '#80cbc4', 'cv'),
        ]

        def make_cmd_handler(flag, op_key, overlay_ref):
            def handler():
                overlay_ref.destroy()
                path = simpledialog.askstring(
                    f"somonger nav {flag}",
                    f"Introduce la ruta para {flag}:\n\n"
                    f"Ejemplo: /home/usuario/archivo",
                    parent=self
                )
                if path:
                    path = path.strip()
                    if op_key == 'dir_arg':
                        self.load_path(path)
                    else:
                        if not self.current_path:
                            self.current_path = os.path.dirname(path) or '/'
                        self._op_from_arg(op_key, path)
            return handler

        for cmd_text, desc, color, op_key in commands:
            flag = cmd_text.split()[0].strip()
            row = tk.Frame(body, bg=t['card'], pady=8, padx=12,
                           highlightbackground=color,
                           highlightthickness=1)
            row.pack(fill='x', pady=3)

            left_col = tk.Frame(row, bg=t['card'])
            left_col.pack(side='left', fill='y')

            tk.Label(left_col, text=cmd_text,
                     bg=t['card'], fg=color,
                     font=('Courier', 11, 'bold'),
                     width=26, anchor='w').pack(anchor='w')
            tk.Label(left_col, text=desc,
                     bg=t['card'], fg=t['fg_dim'],
                     font=('Inter', 9), anchor='w').pack(anchor='w')

            tk.Button(row, text="Usar →",
                      command=make_cmd_handler(flag, op_key, overlay),
                      bg=color, fg='#111122',
                      font=('Inter', 9, 'bold'),
                      relief='flat', padx=10, pady=4,
                      cursor='hand2'
                      ).pack(side='right', padx=6)

        # ── Acceso rápido por ruta ─────────────────────────────────────────────
        sep = tk.Frame(body, bg='#2d2d44', height=1)
        sep.pack(fill='x', pady=12)

        quick = tk.Frame(body, bg=t['bg'])
        quick.pack(fill='x')

        tk.Label(quick, text="O navega directamente a una ruta:",
                 bg=t['bg'], fg=t['fg_dim'],
                 font=('Inter', 9)).pack(side='left', padx=(0, 8))

        self._welcome_path_var = tk.StringVar()
        tk.Entry(quick, textvariable=self._welcome_path_var,
                 bg=t['card'], fg=t['fg'],
                 insertbackground=t['fg'],
                 font=('Courier', 10), relief='flat',
                 width=30).pack(side='left', padx=4)

        def go_direct():
            p = self._welcome_path_var.get().strip()
            if p:
                overlay.destroy()
                self.load_path(p)

        tk.Button(quick, text="Ir →",
                  command=go_direct,
                  bg=t['accent'], fg='white',
                  font=('Inter', 10, 'bold'),
                  relief='flat', padx=10, pady=3,
                  cursor='hand2').pack(side='left', padx=4)

        tk.Button(quick, text="Examinar...",
                  command=lambda: [overlay.destroy(), self._browse()],
                  bg=t['btn2'], fg='white',
                  font=t['font_btn'],
                  relief='flat', padx=10, pady=3,
                  cursor='hand2').pack(side='left', padx=4)
