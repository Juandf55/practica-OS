"""
GUI — Tab Módulo 3: Análisis estadístico
Tablas y gráficas de distribución de archivos y uso de disco.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from modules.reporter import Reporter

# matplotlib opcional
try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


class ReporterTab(tk.Frame):

    def __init__(self, parent, theme):
        super().__init__(parent, bg=theme['bg'])
        self.theme = theme
        self.reporter = None
        self.data     = None
        self._build_ui()

    def _build_ui(self):
        t = self.theme

        # ── Barra superior ────────────────────────────────────────────────────
        top = tk.Frame(self, bg=t['panel'], pady=8, padx=10)
        top.pack(fill='x')

        tk.Label(top, text="📊  Análisis Estadístico del Sistema de Archivos",
                 bg=t['panel'], fg=t['accent'],
                 font=t['font_title']).pack(side='left')

        btn_frame = tk.Frame(top, bg=t['panel'])
        btn_frame.pack(side='right')

        tk.Button(btn_frame, text="📂 Seleccionar directorio",
                  command=self._browse,
                  bg=t['accent'], fg='white', font=t['font_btn'],
                  relief='flat', padx=10, pady=4, cursor='hand2'
                  ).pack(side='left', padx=3)

        tk.Button(btn_frame, text="💾 Exportar CSV",
                  command=lambda: self._export('.csv'),
                  bg=t['btn2'], fg='white', font=t['font_btn'],
                  relief='flat', padx=10, pady=4, cursor='hand2'
                  ).pack(side='left', padx=3)

        tk.Button(btn_frame, text="📄 Exportar TXT",
                  command=lambda: self._export('.txt'),
                  bg=t['btn2'], fg='white', font=t['font_btn'],
                  relief='flat', padx=10, pady=4, cursor='hand2'
                  ).pack(side='left', padx=3)

        # ── Ruta ──────────────────────────────────────────────────────────────
        path_bar = tk.Frame(self, bg=t['card'], pady=5, padx=10)
        path_bar.pack(fill='x')
        self.path_var = tk.StringVar(value="Ninguna ruta analizada")
        tk.Label(path_bar, textvariable=self.path_var,
                 bg=t['card'], fg=t['accent'],
                 font=t['font_small']).pack(side='left')

        # ── Notebook interno (tablas / gráficas) ──────────────────────────────
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill='both', expand=True, padx=10, pady=6)

        # Tab 1: Tabla resumen
        self.tab_table = tk.Frame(self.nb, bg=t['bg'])
        self.nb.add(self.tab_table, text="  📋 Tabla de tipos  ")

        # Tab 2: Info de partición
        self.tab_disk = tk.Frame(self.nb, bg=t['bg'])
        self.nb.add(self.tab_disk, text="  💽 Partición / Disco  ")

        # Tab 3: Gráficas
        self.tab_chart = tk.Frame(self.nb, bg=t['bg'])
        self.nb.add(self.tab_chart, text="  📈 Gráficas  ")

        # Tab 4: Top extensiones
        self.tab_ext = tk.Frame(self.nb, bg=t['bg'])
        self.nb.add(self.tab_ext, text="  📂 Extensiones  ")

        self._build_table_tab()
        self._build_disk_tab()
        self._build_chart_tab()
        self._build_ext_tab()

        # ── Barra de estado ───────────────────────────────────────────────────
        status_bar = tk.Frame(self, bg=t['panel'], pady=4)
        status_bar.pack(fill='x', side='bottom')
        self.status_var = tk.StringVar(value="Listo")
        tk.Label(status_bar, textvariable=self.status_var,
                 bg=t['panel'], fg=t['fg_dim'],
                 font=t['font_small']).pack(side='left', padx=10)

    # ── Construcción de tabs ──────────────────────────────────────────────────

    def _build_table_tab(self):
        t = self.theme
        frame = self.tab_table

        cols = ('tipo', 'descripcion', 'cantidad', 'porcentaje', 'tamano_kb')
        self.type_table = ttk.Treeview(frame, columns=cols,
                                        show='headings', height=10)
        self.type_table.heading('tipo',        text='T')
        self.type_table.heading('descripcion', text='Descripción')
        self.type_table.heading('cantidad',    text='Cantidad')
        self.type_table.heading('porcentaje',  text='% Count')
        self.type_table.heading('tamano_kb',   text='Tamaño (KB)')

        self.type_table.column('tipo',        width=40,  anchor='center')
        self.type_table.column('descripcion', width=220)
        self.type_table.column('cantidad',    width=90,  anchor='e')
        self.type_table.column('porcentaje',  width=90,  anchor='e')
        self.type_table.column('tamano_kb',   width=120, anchor='e')

        vsb = ttk.Scrollbar(frame, orient='vertical',
                             command=self.type_table.yview)
        self.type_table.configure(yscrollcommand=vsb.set)
        self.type_table.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        vsb.pack(side='left', fill='y', pady=10)

        # Totales
        self.total_lbl = tk.Label(frame, text="",
                                   bg=t['bg'], fg=t['accent'],
                                   font=t['font_subtitle'])
        self.total_lbl.pack(pady=4)

    def _build_disk_tab(self):
        t = self.theme
        frame = self.tab_disk
        self.disk_text = tk.Text(frame, bg=t['card'], fg=t['fg'],
                                  font=('Courier', 11), relief='flat',
                                  state='disabled', padx=16, pady=12)
        self.disk_text.pack(fill='both', expand=True, padx=10, pady=10)

    def _build_chart_tab(self):
        t = self.theme
        frame = self.tab_chart
        if not HAS_MPL:
            tk.Label(frame,
                     text="⚠  matplotlib no instalado.\n\n"
                          "Instala con:\n  pip install matplotlib",
                     bg=t['bg'], fg=t['yellow'] if 'yellow' in t else '#ffcc02',
                     font=t['font_subtitle'],
                     justify='center').pack(expand=True)
            return

        self.fig = Figure(figsize=(10, 4), dpi=90,
                          facecolor=t['bg'])
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, padx=6, pady=6)

    def _build_ext_tab(self):
        t = self.theme
        frame = self.tab_ext

        cols = ('extension', 'cantidad', 'tamano_kb')
        self.ext_table = ttk.Treeview(frame, columns=cols,
                                       show='headings', height=15)
        self.ext_table.heading('extension', text='Extensión')
        self.ext_table.heading('cantidad',  text='Archivos')
        self.ext_table.heading('tamano_kb', text='Tamaño (KB)')

        self.ext_table.column('extension', width=180)
        self.ext_table.column('cantidad',  width=100, anchor='e')
        self.ext_table.column('tamano_kb', width=140, anchor='e')

        vsb = ttk.Scrollbar(frame, orient='vertical',
                             command=self.ext_table.yview)
        self.ext_table.configure(yscrollcommand=vsb.set)
        self.ext_table.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        vsb.pack(side='left', fill='y', pady=10)

    # ── Lógica ────────────────────────────────────────────────────────────────

    def _browse(self):
        path = filedialog.askdirectory(title="Seleccionar directorio a analizar")
        if path:
            self.analyze(path)

    def analyze(self, path: str):
        self.path_var.set(f"Analizando: {path}...")
        self.status_var.set("Analizando...")
        self.update()

        self.reporter = Reporter(path)
        self.reporter._analyze()
        self.data = self.reporter.get_data()

        self.path_var.set(path)
        self._populate_table()
        self._populate_disk()
        self._populate_charts()
        self._populate_ext()
        self.status_var.set(
            f"Listo — {self.data['total_entries']} entradas analizadas"
        )

    def _populate_table(self):
        d = self.data
        self.type_table.delete(*self.type_table.get_children())
        total_e = d['total_entries']

        for tc, label in Reporter.TYPE_LABELS.items():
            cnt = d['counts'][tc]
            if cnt == 0:
                continue
            pct = (cnt / total_e * 100) if total_e > 0 else 0
            sz_kb = d['sizes'][tc] / 1024
            self.type_table.insert('', 'end', values=(
                f"[{tc}]", label, cnt, f"{pct:.1f}%", f"{sz_kb:.2f}"
            ))

        self.total_lbl.config(
            text=f"Total: {total_e} entradas  |  {d['total_kb']:.2f} KB  "
                 f"({d['total_mb']:.3f} MB)"
        )

    def _populate_disk(self):
        d = self.data
        info = (
            f"{'INFORMACIÓN DE PARTICIÓN / DISCO':^60}\n"
            f"{'─'*60}\n\n"
            f"  Espacio total en disco : {d['disk_total_gb']:.2f} GB"
            f"  ({d['disk_total']:,} bytes)\n"
            f"  Espacio usado          : {d['disk_used_gb']:.2f} GB"
            f"  ({d['pct_disk_used']:.1f}%)\n"
            f"  Espacio libre          : {d['disk_free_gb']:.2f} GB"
            f"  ({d['pct_disk_free']:.1f}%)\n\n"
            f"  Este directorio ocupa  : {d['total_mb']:.3f} MB\n"
            f"  % del disco total      : {d['pct_dir_of_disk']:.4f}%\n\n"
            f"{'─'*60}\n"
            f"  Barra de uso del disco:\n"
            f"  {self._bar(d['pct_disk_used'], 50)}\n"
            f"  {d['pct_disk_used']:.1f}% usado / {d['pct_disk_free']:.1f}% libre\n\n"
            f"  Barra de uso por directorio:\n"
            f"  {self._bar(d['pct_dir_of_disk'], 50)}\n"
            f"  {d['pct_dir_of_disk']:.4f}% del disco total\n"
        )
        self.disk_text.config(state='normal')
        self.disk_text.delete('1.0', 'end')
        self.disk_text.insert('end', info)
        self.disk_text.config(state='disabled')

    def _populate_charts(self):
        if not HAS_MPL or not self.data:
            return
        d = self.data
        self.fig.clf()

        # Preparar datos
        labels, sizes = [], []
        for tc, label in Reporter.TYPE_LABELS.items():
            cnt = d['counts'][tc]
            if cnt > 0:
                labels.append(f"[{tc}] {label}\n({cnt})")
                sizes.append(cnt)

        colors = ['#4fc3f7','#80cbc4','#66bb6a','#ffcc02',
                  '#ff9800','#ce93d8','#f48fb1','#ef5350']

        # Gráfica de tarta (izquierda)
        ax1 = self.fig.add_subplot(1, 2, 1)
        ax1.set_facecolor('#1e1e2e')
        ax1.pie(sizes, labels=labels, colors=colors[:len(sizes)],
                autopct='%1.1f%%', pctdistance=0.8,
                textprops={'color': '#e0e0e0', 'fontsize': 7},
                wedgeprops={'linewidth': 0.5, 'edgecolor': '#2d2d44'})
        ax1.set_title('Distribución por tipo', color='#e0e0e0', fontsize=10)

        # Gráfica de barras uso disco (derecha)
        ax2 = self.fig.add_subplot(1, 2, 2)
        ax2.set_facecolor('#1e1e2e')
        categories = ['Usado', 'Libre', 'Este dir']
        values     = [
            d['disk_used_gb'],
            d['disk_free_gb'],
            d['total_mb'] / 1024,
        ]
        bar_colors = ['#ef5350', '#66bb6a', '#4fc3f7']
        bars = ax2.bar(categories, values, color=bar_colors,
                       edgecolor='#2d2d44', linewidth=0.5)
        ax2.set_ylabel('Gigabytes', color='#e0e0e0')
        ax2.set_title('Uso del disco', color='#e0e0e0', fontsize=10)
        ax2.tick_params(colors='#e0e0e0')
        for spine in ax2.spines.values():
            spine.set_edgecolor('#444466')

        # Etiquetas en barras
        for bar, val in zip(bars, values):
            ax2.text(bar.get_x() + bar.get_width() / 2,
                     bar.get_height() + 0.01,
                     f'{val:.2f}GB', ha='center', va='bottom',
                     color='#e0e0e0', fontsize=7)

        self.fig.tight_layout(pad=1.5)
        self.canvas.draw()

    def _populate_ext(self):
        d = self.data
        self.ext_table.delete(*self.ext_table.get_children())
        ext_sorted = sorted(d['ext_map'].items(),
                            key=lambda x: x[1][0], reverse=True)
        for ext, (cnt, sz) in ext_sorted:
            self.ext_table.insert('', 'end', values=(
                ext, cnt, f"{sz/1024:.2f}"
            ))

    def _export(self, ext: str):
        if not self.data:
            messagebox.showwarning("Aviso",
                                   "Primero selecciona y analiza un directorio.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[("CSV", "*.csv"), ("TXT", "*.txt"), ("Todos", "*")],
            title="Exportar informe"
        )
        if not path:
            return
        self.reporter._export(path)
        messagebox.showinfo("Exportado", f"Informe guardado en:\n{path}")

    @staticmethod
    def _bar(pct, width=50):
        filled = int(min(pct, 100) / 100 * width)
        return "[" + "█" * filled + "░" * (width - filled) + "]"
