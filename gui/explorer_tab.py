"""
GUI — Tab Módulo 1: Explorador de directorios
Árbol interactivo expandible con iconos por tipo de archivo.
"""

import os
import stat
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from modules.explorer import get_file_type, format_permissions, Explorer


class ExplorerTab(tk.Frame):

    # Iconos de texto por tipo
    ICONS = {
        'd': '📁',
        '-': '📄',
        'l': '🔗',
        'c': '⚙️',
        'b': '💾',
        'p': '📡',
        's': '🔌',
        '?': '❓',
    }

    # Colores del Treeview por tipo
    TAG_COLORS = {
        'd': '#4fc3f7',   # azul claro — directorios
        '-': '#e0e0e0',   # blanco grisáceo — archivos regulares
        'l': '#80cbc4',   # teal — enlaces
        'c': '#ffcc02',   # amarillo — dispositivo carácter
        'b': '#ff9800',   # naranja — dispositivo bloque
        'p': '#ce93d8',   # violeta — FIFO
        's': '#f48fb1',   # rosa — socket
        '?': '#ef5350',   # rojo — desconocido
    }

    def __init__(self, parent, theme):
        super().__init__(parent, bg=theme['bg'])
        self.theme = theme
        self.current_path = None
        self._node_paths = {}   # iid -> full_path
        self._build_ui()

    def _build_ui(self):
        t = self.theme

        # ── Barra superior ────────────────────────────────────────────────────
        top = tk.Frame(self, bg=t['panel'], pady=8, padx=10)
        top.pack(fill='x', side='top')

        tk.Label(top, text="📁  Explorador de Directorios",
                 bg=t['panel'], fg=t['accent'], font=t['font_title']).pack(side='left')

        btn_frame = tk.Frame(top, bg=t['panel'])
        btn_frame.pack(side='right')

        tk.Button(btn_frame, text="📂 Abrir ruta", command=self._browse,
                  bg=t['accent'], fg='white', font=t['font_btn'],
                  relief='flat', padx=12, pady=4, cursor='hand2'
                  ).pack(side='left', padx=4)

        tk.Button(btn_frame, text="🔄 Actualizar", command=self._refresh,
                  bg=t['btn2'], fg='white', font=t['font_btn'],
                  relief='flat', padx=12, pady=4, cursor='hand2'
                  ).pack(side='left', padx=4)

        # ── Ruta actual ───────────────────────────────────────────────────────
        path_frame = tk.Frame(self, bg=t['bg'], pady=4, padx=10)
        path_frame.pack(fill='x')

        tk.Label(path_frame, text="Ruta:", bg=t['bg'],
                 fg=t['fg_dim'], font=t['font_small']).pack(side='left')

        self.path_var = tk.StringVar(value="(ninguna ruta seleccionada)")
        tk.Label(path_frame, textvariable=self.path_var,
                 bg=t['bg'], fg=t['fg'], font=t['font_small']).pack(side='left', padx=6)

        # ── Panel principal (árbol + detalle) ─────────────────────────────────
        main = tk.Frame(self, bg=t['bg'])
        main.pack(fill='both', expand=True, padx=10, pady=6)

        # Árbol izquierda
        tree_frame = tk.Frame(main, bg=t['bg'])
        tree_frame.pack(side='left', fill='both', expand=True)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient='vertical')
        hsb = ttk.Scrollbar(tree_frame, orient='horizontal')

        self.tree = ttk.Treeview(
            tree_frame,
            columns=('type', 'perms', 'inode', 'size', 'desc'),
            displaycolumns=('type', 'perms', 'inode', 'size'),
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            selectmode='browse'
        )
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        self.tree.heading('#0',     text='Nombre')
        self.tree.heading('type',   text='Tipo')
        self.tree.heading('perms',  text='Permisos')
        self.tree.heading('inode',  text='Inodo')
        self.tree.heading('size',   text='Tamaño (KB)')

        self.tree.column('#0',    width=300, minwidth=150)
        self.tree.column('type',  width=50,  minwidth=40,  anchor='center')
        self.tree.column('perms', width=100, minwidth=80,  anchor='center')
        self.tree.column('inode', width=90,  minwidth=70,  anchor='center')
        self.tree.column('size',  width=100, minwidth=80,  anchor='e')

        # Configurar colores por tipo
        for type_char, color in self.TAG_COLORS.items():
            self.tree.tag_configure(type_char, foreground=color)

        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # Evento: expandir directorio lazy
        self.tree.bind('<<TreeviewOpen>>', self._on_expand)
        self.tree.bind('<<TreeviewSelect>>', self._on_select)

        # Panel derecho: detalle del elemento seleccionado
        detail_frame = tk.Frame(main, bg=t['panel'], width=280)
        detail_frame.pack(side='right', fill='y', padx=(8, 0))
        detail_frame.pack_propagate(False)

        tk.Label(detail_frame, text="Detalle", bg=t['panel'],
                 fg=t['accent'], font=t['font_subtitle']).pack(pady=(12, 6))

        self.detail_text = tk.Text(
            detail_frame, bg=t['card'], fg=t['fg'],
            font=('Courier', 10), relief='flat',
            state='disabled', wrap='word', padx=8, pady=8
        )
        self.detail_text.pack(fill='both', expand=True, padx=8, pady=(0, 8))

        # ── Barra de estado ───────────────────────────────────────────────────
        status_bar = tk.Frame(self, bg=t['panel'], pady=4)
        status_bar.pack(fill='x', side='bottom')

        self.status_var = tk.StringVar(value="Listo")
        tk.Label(status_bar, textvariable=self.status_var,
                 bg=t['panel'], fg=t['fg_dim'],
                 font=t['font_small']).pack(side='left', padx=10)

        # Leyenda
        legend = tk.Frame(status_bar, bg=t['panel'])
        legend.pack(side='right', padx=10)
        for tc, desc in [('d', 'Dir'), ('-', 'Archivo'), ('l', 'Enlace'),
                         ('c', 'Carácter'), ('b', 'Bloque')]:
            color = self.TAG_COLORS.get(tc, '#fff')
            tk.Label(legend, text=f"{self.ICONS.get(tc,'')} {desc}",
                     bg=t['panel'], fg=color,
                     font=t['font_small']).pack(side='left', padx=4)

    # ── Callbacks ──────────────────────────────────────────────────────────────

    def _browse(self):
        path = filedialog.askdirectory(title="Seleccionar directorio")
        if path:
            self.load_path(path)

    def _refresh(self):
        if self.current_path:
            self.load_path(self.current_path)

    def load_path(self, path: str):
        self.current_path = path
        self.path_var.set(path)
        self.status_var.set(f"Cargando {path}...")
        self.tree.delete(*self.tree.get_children())
        self._node_paths.clear()

        # Insertar raíz
        try:
            st = os.lstat(path)
            tc, desc, _ = get_file_type(path, st)
            icon = self.ICONS.get(tc, '?')
            perms = format_permissions(st.st_mode)
            node = self.tree.insert('', 'end',
                                    iid=path,
                                    text=f" {icon} {os.path.basename(path)}/",
                                    values=(tc, f"{tc}{perms}", st.st_ino, '—'),
                                    tags=(tc,), open=False)
            self._node_paths[node] = path
            # Placeholder para lazy load
            if os.path.isdir(path):
                self.tree.insert(node, 'end', text='   ⏳ Cargando...', tags=('loading',))
        except Exception as e:
            import tkinter.messagebox as mb
            mb.showerror("Error", str(e))
            return

        self.status_var.set(f"Listo — {path}")

    def _on_expand(self, event):
        """Carga hijos de un nodo cuando se expande (lazy load)."""
        node = self.tree.focus()
        children = self.tree.get_children(node)
        # Si solo tiene el placeholder, cargar hijos reales
        if len(children) == 1:
            first = children[0]
            if 'Cargando' in self.tree.item(first, 'text'):
                self.tree.delete(first)
                path = self._node_paths.get(node)
                if path and os.path.isdir(path):
                    self._populate_children(node, path)

    def _on_double_click(self, event):
        """Doble clic en directorio: expandir y navegar."""
        node = self.tree.focus()
        path = self._node_paths.get(node)
        if path and os.path.isdir(path):
            self.tree.item(node, open=True)
            self._on_expand(event)

    def _get_node_path(self, node):
        """Reconstruye la ruta del nodo desde el árbol."""
        parts = []
        cur = node
        while cur:
            label = self.tree.item(cur, 'text').strip()
            # Quitar icono (primer caracter emoji)
            label = label.split(' ', 2)[-1].rstrip('/')
            parts.append(label)
            cur = self.tree.parent(cur)
        parts.reverse()
        if self.current_path:
            base = os.path.dirname(self.current_path)
            return os.path.join(base, *parts)
        return os.path.join(*parts) if parts else '/'

    def _populate_children(self, parent_node, parent_path):
        """Inserta hijos de un directorio en el árbol."""
        try:
            entries = sorted(os.listdir(parent_path))
        except PermissionError:
            self.tree.insert(parent_node, 'end',
                             text=' 🔒 [Permiso denegado]', tags=('?',))
            return

        for entry in entries:
            full = os.path.join(parent_path, entry)
            # Usar el full path como iid para evitar duplicados
            safe_iid = full.replace(' ', '_SPACE_')
            try:
                st = os.lstat(full)
                tc, desc, _ = get_file_type(full, st)
                perms = format_permissions(st.st_mode)
                icon  = self.ICONS.get(tc, '?')
                size_kb = st.st_size / 1024
                is_dir = os.path.isdir(full) and not os.path.islink(full)

                label = f" {icon} {entry}" + ("/" if is_dir else "")

                try:
                    child = self.tree.insert(
                        parent_node, 'end',
                        iid=safe_iid,
                        text=label,
                        values=(tc, f"{tc}{perms}", st.st_ino, f"{size_kb:.1f}"),
                        tags=(tc,),
                        open=False
                    )
                    self._node_paths[child] = full
                except Exception:
                    # iid duplicado: intentar sin iid fijo
                    child = self.tree.insert(
                        parent_node, 'end',
                        text=label,
                        values=(tc, f"{tc}{perms}", st.st_ino, f"{size_kb:.1f}"),
                        tags=(tc,),
                        open=False
                    )
                    self._node_paths[child] = full

                # Placeholder si es directorio
                if is_dir:
                    self.tree.insert(child, 'end', text='   ⏳ Cargando...', tags=('loading',))
            except (PermissionError, FileNotFoundError, OSError) as e:
                self.tree.insert(parent_node, 'end',
                                 text=f" ❓ {entry} [{str(e)[:30]}]", tags=('?',))

    def _on_select(self, event):
        """Muestra detalle del elemento seleccionado."""
        node = self.tree.focus()
        if not node:
            return
        path = self._node_paths.get(node)
        if not path:
            return
        self._show_detail(path)

    def _show_detail(self, path: str):
        """Muestra información detallada de un archivo en el panel derecho."""
        try:
            st = os.lstat(path)
            tc, desc, _ = get_file_type(path, st)
            perms = format_permissions(st.st_mode)

            import datetime, pwd as _pwd, grp as _grp
            try:    owner = _pwd.getpwuid(st.st_uid).pw_name
            except: owner = str(st.st_uid)
            try:    group = _grp.getgrgid(st.st_gid).gr_name
            except: group = str(st.st_gid)

            fmt = lambda ts: datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

            info = (
                f"Nombre: {os.path.basename(path)}\n"
                f"Ruta  : {path}\n"
                f"─────────────────────\n"
                f"Tipo  : [{tc}] {desc}\n"
                f"Perms : {tc}{perms}\n"
                f"Octal : {oct(st.st_mode & 0o7777)}\n"
                f"Inodo : {st.st_ino}\n"
                f"Links : {st.st_nlink}\n"
                f"─────────────────────\n"
                f"Dueño : {owner} (uid={st.st_uid})\n"
                f"Grupo : {group} (gid={st.st_gid})\n"
                f"─────────────────────\n"
                f"Tamaño: {st.st_size} B\n"
                f"       {st.st_size/1024:.2f} KB\n"
                f"Bloq. : {st.st_blocks}\n"
                f"─────────────────────\n"
                f"Acceso: {fmt(st.st_atime)}\n"
                f"Modif : {fmt(st.st_mtime)}\n"
                f"Cambio: {fmt(st.st_ctime)}\n"
            )
        except Exception as e:
            info = f"No se pudo obtener info:\n{e}"

        self.detail_text.config(state='normal')
        self.detail_text.delete('1.0', 'end')
        self.detail_text.insert('end', info)
        self.detail_text.config(state='disabled')
