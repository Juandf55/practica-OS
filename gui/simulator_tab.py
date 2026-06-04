"""
GUI — Tab Módulo 4: Simulador de métodos de asignación
Muestra simulación visual de ext2, ext4 y FAT32.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from modules.simulator import Simulator


class SimulatorTab(tk.Frame):

    FS_COLORS = {
        'ext2':  '#66bb6a',   # verde
        'ext4':  '#4fc3f7',   # azul claro
        'fat32': '#ffcc02',   # amarillo
    }

    FS_METHODS = {
        'ext2':  'Nodos-i (12 directos + simple + doble + triple indirecto)',
        'ext4':  'Nodos-i extendido con extents',
        'fat32': 'FAT — lista enlazada con índice en memoria',
    }

    def __init__(self, parent, theme):
        super().__init__(parent, bg=theme['bg'])
        self.theme = theme
        self.sim = None
        self._build_ui()

    def _build_ui(self):
        t = self.theme

        # ── Barra superior ────────────────────────────────────────────────────
        top = tk.Frame(self, bg=t['panel'], pady=8, padx=10)
        top.pack(fill='x')

        tk.Label(top, text="⚙️  Simulador de Métodos de Asignación",
                 bg=t['panel'], fg=t['accent'],
                 font=t['font_title']).pack(side='left')

        tk.Button(top, text="📂 Seleccionar archivo",
                  command=self._browse,
                  bg=t['accent'], fg='white', font=t['font_btn'],
                  relief='flat', padx=12, pady=4, cursor='hand2'
                  ).pack(side='right', padx=4)

        # ── Info archivo seleccionado ──────────────────────────────────────────
        file_bar = tk.Frame(self, bg=t['card'], pady=6, padx=12)
        file_bar.pack(fill='x')

        tk.Label(file_bar, text="Archivo:", bg=t['card'],
                 fg=t['fg_dim'], font=t['font_small']).pack(side='left')
        self.file_var = tk.StringVar(value="(ningún archivo seleccionado)")
        tk.Label(file_bar, textvariable=self.file_var,
                 bg=t['card'], fg=t['accent'],
                 font=t['font_small']).pack(side='left', padx=6)

        self.size_var = tk.StringVar(value="")
        tk.Label(file_bar, textvariable=self.size_var,
                 bg=t['card'], fg=t['fg_dim'],
                 font=t['font_small']).pack(side='left', padx=10)

        self.run_btn = tk.Button(
            file_bar, text="▶ SIMULAR",
            command=self._run_simulation,
            bg='#66bb6a', fg='white', font=t['font_btn'],
            relief='flat', padx=16, pady=3, cursor='hand2',
            state='disabled'
        )
        self.run_btn.pack(side='right')

        # ── Panel principal ────────────────────────────────────────────────────
        main = tk.Frame(self, bg=t['bg'])
        main.pack(fill='both', expand=True, padx=10, pady=6)

        # Izquierda: cards de particiones
        left = tk.Frame(main, bg=t['bg'])
        left.pack(side='left', fill='both', expand=True)

        tk.Label(left, text="Particiones simuladas",
                 bg=t['bg'], fg=t['accent'],
                 font=t['font_subtitle']).pack(pady=(0, 6), anchor='w')

        self.cards_frame = tk.Frame(left, bg=t['bg'])
        self.cards_frame.pack(fill='both', expand=True)

        # Crear cards vacías
        self.cards = {}
        for i, (fs, color) in enumerate(self.FS_COLORS.items()):
            card = self._make_card(self.cards_frame, fs, color)
            card.grid(row=0, column=i, padx=6, pady=4, sticky='nsew')
            self.cards_frame.columnconfigure(i, weight=1)
        self.cards_frame.rowconfigure(0, weight=1)

        # Derecha: log de salida
        right = tk.Frame(main, bg=t['panel'], width=320)
        right.pack(side='right', fill='y', padx=(8, 0))
        right.pack_propagate(False)

        tk.Label(right, text="📋 Log de ejecución",
                 bg=t['panel'], fg=t['accent'],
                 font=t['font_subtitle']).pack(pady=(10, 4), padx=8, anchor='w')

        self.log = scrolledtext.ScrolledText(
            right, bg=t['card'], fg=t['fg'],
            font=('Courier', 9), relief='flat',
            state='disabled', wrap='word',
            padx=8, pady=6
        )
        self.log.pack(fill='both', expand=True, padx=8, pady=(0, 8))

        # ── Barra estado ──────────────────────────────────────────────────────
        status_bar = tk.Frame(self, bg=t['panel'], pady=4)
        status_bar.pack(fill='x', side='bottom')
        self.status_var = tk.StringVar(value="Listo")
        tk.Label(status_bar, textvariable=self.status_var,
                 bg=t['panel'], fg=t['fg_dim'],
                 font=t['font_small']).pack(side='left', padx=10)

        self.progress = ttk.Progressbar(status_bar, mode='indeterminate', length=200)
        self.progress.pack(side='right', padx=10)

    def _make_card(self, parent, fs_name, color):
        """Crea card para una partición."""
        t = self.theme
        card = tk.Frame(parent, bg=t['card'],
                        highlightbackground=color,
                        highlightthickness=2, pady=10, padx=10)

        # Encabezado
        hdr = tk.Frame(card, bg=t['card'])
        hdr.pack(fill='x')
        tk.Label(hdr, text=fs_name.upper(), bg=t['card'],
                 fg=color, font=t['font_title']).pack(side='left')

        method = self.FS_METHODS.get(fs_name, '')
        tk.Label(card, text=method, bg=t['card'],
                 fg=t['fg_dim'], font=t['font_small'],
                 wraplength=220, justify='left').pack(pady=(2, 8), anchor='w')

        # Métricas
        metrics_frame = tk.Frame(card, bg=t['card'])
        metrics_frame.pack(fill='x')

        labels = {}
        fields = [
            ('tamaño_disco', 'Tamaño en disco:'),
            ('sectores',     'Sectores:'),
            ('libre',        'Espacio libre:'),
            ('total',        'Tamaño partición:'),
            ('modo',         'Modo:'),
        ]
        for key, text in fields:
            row = tk.Frame(metrics_frame, bg=t['card'])
            row.pack(fill='x', pady=1)
            tk.Label(row, text=text, bg=t['card'],
                     fg=t['fg_dim'], font=t['font_small'],
                     width=18, anchor='w').pack(side='left')
            val_lbl = tk.Label(row, text="—", bg=t['card'],
                               fg=color, font=t['font_small'], anchor='w')
            val_lbl.pack(side='left')
            labels[key] = val_lbl

        # Barra de ocupación
        tk.Label(card, text="Ocupación:", bg=t['card'],
                 fg=t['fg_dim'], font=t['font_small']).pack(anchor='w', pady=(8, 1))

        bar_canvas = tk.Canvas(card, height=16, bg=t['bg'],
                               highlightthickness=0)
        bar_canvas.pack(fill='x', pady=(0, 4))

        pct_lbl = tk.Label(card, text="", bg=t['card'],
                           fg=t['fg_dim'], font=t['font_small'])
        pct_lbl.pack(anchor='w')

        # Visualización de bloques (mini mapa)
        tk.Label(card, text="Mapa de bloques (simulado):",
                 bg=t['card'], fg=t['fg_dim'],
                 font=t['font_small']).pack(anchor='w', pady=(8, 2))

        block_canvas = tk.Canvas(card, height=40, bg=t['bg'],
                                  highlightthickness=0)
        block_canvas.pack(fill='x')

        self.cards[fs_name] = {
            'labels':       labels,
            'bar_canvas':   bar_canvas,
            'block_canvas': block_canvas,
            'pct_lbl':      pct_lbl,
            'color':        color,
            'card':         card,
        }
        return card

    # ── Acciones ──────────────────────────────────────────────────────────────

    def _browse(self):
        path = filedialog.askopenfilename(title="Seleccionar archivo para simular")
        if path:
            self.file_var.set(path)
            sz = os.path.getsize(path)
            self.size_var.set(
                f"({sz:,} bytes  /  {sz/1024:.2f} KB  →  "
                f"partición: {sz*3/1024:.2f} KB)"
            )
            self.run_btn.config(state='normal')
            self._reset_cards()

    def _reset_cards(self):
        for fs_name, card_data in self.cards.items():
            for key, lbl in card_data['labels'].items():
                lbl.config(text="—")
            card_data['bar_canvas'].delete('all')
            card_data['block_canvas'].delete('all')
            card_data['pct_lbl'].config(text="")

    def _run_simulation(self):
        path = self.file_var.get()
        if not path or not os.path.isfile(path):
            messagebox.showerror("Error", "Selecciona un archivo válido primero.")
            return

        self.run_btn.config(state='disabled')
        self.progress.start(10)
        self.status_var.set("Simulando...")
        self._log_clear()
        self._log(f"▶ Iniciando simulación para: {path}\n")

        # Ejecutar en hilo separado para no bloquear la GUI
        t = threading.Thread(target=self._simulate_thread, args=(path,), daemon=True)
        t.start()

    def _simulate_thread(self, path: str):
        """Corre la simulación en background y actualiza GUI."""
        import io, sys

        # Capturar stdout del simulador
        old_stdout = sys.stdout
        sys.stdout = buf = io.StringIO()

        try:
            self.sim = Simulator(path)
            self.sim.run()
        except Exception as e:
            self.after(0, lambda: self._log(f"\n[ERROR] {e}\n"))
        finally:
            sys.stdout = old_stdout

        output = buf.getvalue()
        results = self.sim.results if self.sim else []

        # Actualizar GUI en el hilo principal
        self.after(0, lambda: self._on_sim_done(output, results))

    def _on_sim_done(self, output: str, results: list):
        self.progress.stop()
        self.run_btn.config(state='normal')
        self._log(output)
        self.status_var.set("Simulación completada")

        for r in results:
            self._update_card(r)

    def _update_card(self, result: dict):
        name = result.get('name', '').lower()
        if name not in self.cards:
            return

        card_data = self.cards[name]
        labels    = card_data['labels']
        color     = card_data['color']

        ok = result.get('success', False)
        if not ok:
            err = result.get('error', 'Error')
            labels['tamaño_disco'].config(text=f"ERROR: {err[:30]}", fg='#ef5350')
            return

        size_kb  = result.get('size_on_disk_kb', 0)
        sectors  = result.get('size_on_disk_sectors', 0)
        free_kb  = result.get('fs_free_kb', 0)
        total_kb = result.get('fs_total_kb', 1)
        mode     = result.get('mode', 'simulation')

        labels['tamaño_disco'].config(text=f"{size_kb:.2f} KB")
        labels['sectores'].config(     text=f"{sectors:,} sectores")
        labels['libre'].config(        text=f"{free_kb:.2f} KB")
        labels['total'].config(        text=f"{total_kb:.2f} KB")
        labels['modo'].config(         text=mode)

        # Barra de uso
        pct_used = min(100, ((total_kb - free_kb) / total_kb * 100)) if total_kb > 0 else 0
        bc = card_data['bar_canvas']
        w  = bc.winfo_width() or 200
        bc.delete('all')
        filled_w = int(w * pct_used / 100)
        bc.create_rectangle(0, 0, w, 16, fill='#2d2d44', outline='')
        bc.create_rectangle(0, 0, filled_w, 16, fill=color, outline='')
        card_data['pct_lbl'].config(text=f"{pct_used:.1f}% ocupado")

        # Mapa de bloques
        self._draw_block_map(card_data, result, color)

    def _draw_block_map(self, card_data, result, color):
        """Dibuja mapa visual de bloques asignados."""
        canvas = card_data['block_canvas']
        canvas.update_idletasks()
        w = canvas.winfo_width() or 220
        h = 40
        canvas.delete('all')

        # Calcular bloques totales y usados para visualización
        total_kb = result.get('fs_total_kb', 1)
        free_kb  = result.get('fs_free_kb', 0)
        used_kb  = total_kb - free_kb

        block_size_visual = 8  # px por bloque visual
        n_blocks = max(1, w // (block_size_visual + 1))
        blocks_used = int(n_blocks * (used_kb / total_kb)) if total_kb > 0 else 0

        # Colores: reservado (gris), usado (color), libre (oscuro)
        reserved = max(1, int(n_blocks * 0.05))

        for i in range(n_blocks):
            x = i * (block_size_visual + 1)
            if i < reserved:
                fill = '#555577'   # reservado (metadatos)
            elif i < reserved + blocks_used:
                fill = color       # datos del archivo
            else:
                fill = '#2d2d44'   # libre
            canvas.create_rectangle(x, 2, x + block_size_visual, h - 2,
                                     fill=fill, outline='')

        # Leyenda
        canvas.create_rectangle(2, h - 12, 10, h - 4, fill='#555577', outline='')
        canvas.create_text(13, h - 8, text="Metadatos", anchor='w',
                            fill='#aaa', font=('Arial', 6))
        canvas.create_rectangle(70, h - 12, 78, h - 4, fill=color, outline='')
        canvas.create_text(81, h - 8, text="Datos", anchor='w',
                            fill='#aaa', font=('Arial', 6))
        canvas.create_rectangle(115, h - 12, 123, h - 4, fill='#2d2d44', outline='')
        canvas.create_text(126, h - 8, text="Libre", anchor='w',
                            fill='#aaa', font=('Arial', 6))

    # ── Log ───────────────────────────────────────────────────────────────────

    def _log(self, msg: str):
        self.log.config(state='normal')
        self.log.insert('end', msg)
        self.log.see('end')
        self.log.config(state='disabled')

    def _log_clear(self):
        self.log.config(state='normal')
        self.log.delete('1.0', 'end')
        self.log.config(state='disabled')
