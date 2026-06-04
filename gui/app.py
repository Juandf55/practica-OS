"""
GUI — Aplicación principal de SOMONGER
Ventana principal con pestañas para cada módulo.
Recibe argumentos del CLI para pre-cargar tabs y rutas.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk

from gui.explorer_tab   import ExplorerTab
from gui.navigator_tab  import NavigatorTab
from gui.reporter_tab   import ReporterTab
from gui.simulator_tab  import SimulatorTab


# ─── Tema oscuro ─────────────────────────────────────────────────────────────
THEME = {
    'bg':           '#12121f',
    'panel':        '#1a1a2e',
    'card':         '#22223b',
    'accent':       '#7c5cbf',
    'accent2':      '#a06cd5',
    'btn2':         '#2d4a6e',
    'fg':           '#e0e0e0',
    'fg_dim':       '#888899',
    'font_title':   ('Inter', 13, 'bold'),
    'font_subtitle':('Inter', 11, 'bold'),
    'font_btn':     ('Inter', 10),
    'font_small':   ('Inter', 9),
    'font_mono':    ('Courier', 10),
}

TAB_INDEX = {
    'explore': 0,
    'nav':     1,
    'report':  2,
    'sim':     3,
}


class SomongerApp(tk.Tk):

    def __init__(self, args=None):
        super().__init__()
        self.args = args

        self.title("SOMONGER — Gestor de Sistema de Archivos")
        self.geometry("1280x780")
        self.minsize(900, 600)
        self.configure(bg=THEME['bg'])

        # Icono / estilo global ttk
        self._apply_styles()
        self._build_ui()

        # Después de que la ventana se dibuje, cargar datos según args
        self.after(150, self._load_from_args)

    # ── Estilos globales ──────────────────────────────────────────────────────

    def _apply_styles(self):
        style = ttk.Style(self)
        style.theme_use('clam')

        bg   = THEME['bg']
        panel= THEME['panel']
        card = THEME['card']
        acc  = THEME['accent']
        fg   = THEME['fg']
        dim  = THEME['fg_dim']

        # Notebook (pestañas)
        style.configure('TNotebook',
                        background=panel, borderwidth=0)
        style.configure('TNotebook.Tab',
                        background=card, foreground=dim,
                        padding=[16, 8], font=('Inter', 10),
                        borderwidth=0)
        style.map('TNotebook.Tab',
                  background=[('selected', acc),
                               ('active',  '#3a2a6e')],
                  foreground=[('selected', 'white'),
                               ('active',  fg)])

        # Treeview
        style.configure('Treeview',
                        background=card, foreground=fg,
                        fieldbackground=card, borderwidth=0,
                        rowheight=24, font=('Inter', 9))
        style.configure('Treeview.Heading',
                        background=panel, foreground=acc,
                        borderwidth=0, font=('Inter', 9, 'bold'))
        style.map('Treeview',
                  background=[('selected', '#3a2a6e')],
                  foreground=[('selected', 'white')])

        # Scrollbar
        style.configure('TScrollbar',
                        background=panel, troughcolor=card,
                        borderwidth=0, arrowcolor=dim)

        # Progressbar
        style.configure('TProgressbar',
                        background=acc, troughcolor=card,
                        borderwidth=0, thickness=6)

        # Separador
        style.configure('TSeparator', background='#2d2d44')

    # ── UI principal ──────────────────────────────────────────────────────────

    def _build_ui(self):
        t = THEME

        # ── Encabezado ───────────────────────────────────────────────────────
        header = tk.Frame(self, bg=t['panel'], pady=10)
        header.pack(fill='x', side='top')

        tk.Label(header,
                 text="  💻  SOMONGER",
                 bg=t['panel'], fg=t['accent'],
                 font=('Inter', 18, 'bold')).pack(side='left', padx=6)

        tk.Label(header,
                 text="Sistema Operativo Monitor-Manager  |  Sistemas Operativos — UE",
                 bg=t['panel'], fg=t['fg_dim'],
                 font=('Inter', 10)).pack(side='left', padx=10)

        # Indicador de comando activo
        self.cmd_var = tk.StringVar(value="")
        tk.Label(header, textvariable=self.cmd_var,
                 bg=t['panel'], fg='#66bb6a',
                 font=('Courier', 10)).pack(side='right', padx=16)

        ttk.Separator(self, orient='horizontal').pack(fill='x')

        # ── Notebook ──────────────────────────────────────────────────────────
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill='both', expand=True)

        self.tab_explore = ExplorerTab(self.nb, t)
        self.tab_nav     = NavigatorTab(self.nb, t)
        self.tab_report  = ReporterTab(self.nb, t)
        self.tab_sim     = SimulatorTab(self.nb, t)

        self.nb.add(self.tab_explore, text="  📁  M1: Explorar  ")
        self.nb.add(self.tab_nav,     text="  🗂   M2: Navegar   ")
        self.nb.add(self.tab_report,  text="  📊  M3: Informe   ")
        self.nb.add(self.tab_sim,     text="  ⚙️   M4: Simular   ")

        # ── Footer ────────────────────────────────────────────────────────────
        footer = tk.Frame(self, bg='#0d0d1a', pady=3)
        footer.pack(fill='x', side='bottom')
        tk.Label(footer,
                 text="  Temas 26, 27, 28 — Archivos · Directorios · Implementación FS  |  "
                      "Python 3 · Linux",
                 bg='#0d0d1a', fg='#444466',
                 font=('Inter', 8)).pack(side='left')

    # ── Carga desde argumentos CLI ────────────────────────────────────────────

    def _load_from_args(self):
        args = self.args
        if not args or not hasattr(args, 'command'):
            return

        cmd = getattr(args, 'command', None)
        if not cmd:
            return

        # Mostrar el comando en el encabezado
        cmd_str = self._reconstruct_cmd(args)
        self.cmd_var.set(f"$ somonger {cmd_str}")

        # Seleccionar la pestaña correcta
        tab_idx = TAB_INDEX.get(cmd, 0)
        self.nb.select(tab_idx)

        # Cargar datos según módulo
        if cmd == 'explore':
            path = getattr(args, 'path', None)
            if path:
                self.tab_explore.load_path(path)

        elif cmd == 'nav':
            path = getattr(args, 'path', None)

            # Mostrar pantalla de menú o cargar ruta directamente
            dir_arg     = getattr(args, 'dir_arg',    None)
            rm_arg      = getattr(args, 'rm',         None)
            touchDir    = getattr(args, 'touchDir',   None)
            mk_arg      = getattr(args, 'mk',         None)
            cc_arg      = getattr(args, 'cc',         None)
            cx_arg      = getattr(args, 'cx',         None)
            cv_arg      = getattr(args, 'cv',         None)

            # Si viene --dir, cargar esa ruta en el navegador
            if dir_arg:
                self.tab_nav.load_path(dir_arg)
            elif path:
                self.tab_nav.load_path(path)

            # Ejecutar operación si se pasó como argumento
            if rm_arg:
                self.tab_nav._op_from_arg('rm', rm_arg)
            if touchDir:
                self.tab_nav._op_from_arg('touchDir', touchDir)
            if mk_arg:
                self.tab_nav._op_from_arg('mk', mk_arg)
            if cc_arg:
                self.tab_nav._op_from_arg('cc', cc_arg)
            if cx_arg:
                self.tab_nav._op_from_arg('cx', cx_arg)
            if cv_arg:
                self.tab_nav._op_from_arg('cv', cv_arg)

            # Si no hay ningún argumento → mostrar menú de comandos
            if not any([path, dir_arg, rm_arg, touchDir, mk_arg,
                        cc_arg, cx_arg, cv_arg]):
                self.tab_nav.show_welcome_menu()

        elif cmd == 'report':
            path = getattr(args, 'path', None)
            if path:
                self.tab_report.analyze(path)

        elif cmd == 'sim':
            file_path = getattr(args, 'file', None)
            if file_path and os.path.isfile(file_path):
                self.tab_sim.file_var.set(file_path)
                sz = os.path.getsize(file_path)
                self.tab_sim.size_var.set(
                    f"({sz:,} bytes  /  {sz/1024:.2f} KB  →  "
                    f"partición: {sz*3/1024:.2f} KB)"
                )
                self.tab_sim.run_btn.config(state='normal')
                # Auto-ejecutar simulación
                self.after(300, self.tab_sim._run_simulation)

    def _reconstruct_cmd(self, args) -> str:
        """Reconstruye la cadena de comando para mostrar en encabezado."""
        parts = []
        cmd = getattr(args, 'command', '')
        parts.append(cmd)

        path = getattr(args, 'path', None)
        if path: parts.append(path)

        file_ = getattr(args, 'file', None)
        if file_: parts.append(file_)

        for flag, attr in [('--dir', 'dir_arg'), ('--rm', 'rm'),
                            ('--touchDir', 'touchDir'), ('--mk', 'mk'),
                            ('--cc', 'cc'), ('--cx', 'cx'), ('--cv', 'cv'),
                            ('--output', 'output')]:
            val = getattr(args, attr, None)
            if val:
                parts.append(f"{flag} {val}")

        return ' '.join(parts)


def launch_gui(args=None):
    """Lanza la aplicación GUI con argumentos opcionales."""
    app = SomongerApp(args=args)
    app.mainloop()
