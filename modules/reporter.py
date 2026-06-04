"""
Módulo 3: Análisis estadístico del sistema de archivos
Comando: somonger report <ruta> [--output archivo.csv|archivo.txt]

Genera informe con:
  - Número total de archivos por tipo
  - Porcentaje de espacio utilizado del directorio
  - Porcentaje de espacio en disco/partición
  - Estimación del espacio libre en la partición
  - Exportable a .txt o .csv (separado por ";" con dobles comillas)
"""

import os
import stat
import sys
import shutil
import datetime


# ─── Colores ─────────────────────────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    BLUE    = "\033[94m"
    CYAN    = "\033[96m"
    YELLOW  = "\033[93m"
    GREEN   = "\033[92m"
    RED     = "\033[91m"
    MAGENTA = "\033[95m"
    WHITE   = "\033[97m"
    GRAY    = "\033[90m"

def cprint(text, color="", bold=False):
    if sys.stdout.isatty():
        b = C.BOLD if bold else ""
        return f"{b}{color}{text}{C.RESET}"
    return text

def separator(char="─", width=65):
    print(cprint(char * width, C.GRAY))


# ─── Clase Reporter ───────────────────────────────────────────────────────────

class Reporter:
    """
    Genera informe estadístico de un directorio.
    Incluye conteos por tipo, porcentajes de uso y espacio libre.
    """

    # Tipos Unix y sus descripciones
    TYPE_LABELS = {
        '-': 'Archivos regulares',
        'd': 'Directorios',
        'l': 'Enlaces simbólicos',
        'c': 'Dispositivos carácter',
        'b': 'Dispositivos bloque',
        'p': 'FIFOs / Named pipes',
        's': 'Sockets',
        '?': 'Desconocidos / inaccesibles',
    }

    def __init__(self, path: str):
        self.path = os.path.abspath(path)
        self.report_data = {}

    def run(self, output_path: str = None):
        """Punto de entrada: analiza y muestra (y opcionalmente exporta)."""
        if not os.path.exists(self.path):
            print(cprint(f"[ERROR] Ruta no existe: {self.path}", C.RED))
            sys.exit(1)

        self._analyze()
        self._print_report()

        if output_path:
            self._export(output_path)

    # ── Análisis ──────────────────────────────────────────────────────────────

    def _analyze(self):
        """Recorre el directorio y recopila estadísticas."""
        counts   = {k: 0 for k in self.TYPE_LABELS}
        sizes    = {k: 0 for k in self.TYPE_LABELS}
        ext_map  = {}          # extensión → (count, total_bytes)
        total_entries = 0
        total_bytes   = 0
        errors        = 0

        for dirpath, dirnames, filenames in os.walk(self.path, followlinks=False):
            all_entries = [(d, True) for d in dirnames] + [(f, False) for f in filenames]
            for name, is_dir_hint in all_entries:
                full = os.path.join(dirpath, name)
                total_entries += 1
                try:
                    st = os.lstat(full)
                    mode = st.st_mode
                    sz   = st.st_size

                    if stat.S_ISREG(mode):    t = '-'
                    elif stat.S_ISDIR(mode):  t = 'd'
                    elif stat.S_ISLNK(mode):  t = 'l'
                    elif stat.S_ISCHR(mode):  t = 'c'
                    elif stat.S_ISBLK(mode):  t = 'b'
                    elif stat.S_ISFIFO(mode): t = 'p'
                    elif stat.S_ISSOCK(mode): t = 's'
                    else:                     t = '?'

                    counts[t] += 1
                    sizes[t]  += sz
                    total_bytes += sz

                    # Extensión (solo archivos regulares)
                    if t == '-':
                        _, ext = os.path.splitext(name)
                        ext = ext.lower() if ext else '(sin extensión)'
                        if ext not in ext_map:
                            ext_map[ext] = [0, 0]
                        ext_map[ext][0] += 1
                        ext_map[ext][1] += sz

                except (PermissionError, FileNotFoundError, OSError):
                    counts['?'] += 1
                    errors += 1

        # Información de disco/partición
        try:
            disk = shutil.disk_usage(self.path)
            disk_total = disk.total
            disk_used  = disk.used
            disk_free  = disk.free
        except Exception:
            disk_total = disk_used = disk_free = 0

        # Porcentajes
        pct_dir_of_disk = (total_bytes / disk_total * 100) if disk_total > 0 else 0
        pct_disk_used   = (disk_used   / disk_total * 100) if disk_total > 0 else 0
        pct_disk_free   = (disk_free   / disk_total * 100) if disk_total > 0 else 0

        self.report_data = {
            'path':          self.path,
            'timestamp':     datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'counts':        counts,
            'sizes':         sizes,
            'total_entries': total_entries,
            'total_bytes':   total_bytes,
            'total_kb':      total_bytes / 1024,
            'total_mb':      total_bytes / 1024 / 1024,
            'errors':        errors,
            'ext_map':       ext_map,
            'disk_total':    disk_total,
            'disk_used':     disk_used,
            'disk_free':     disk_free,
            'disk_total_gb': disk_total / 1024**3,
            'disk_used_gb':  disk_used  / 1024**3,
            'disk_free_gb':  disk_free  / 1024**3,
            'pct_dir_of_disk': pct_dir_of_disk,
            'pct_disk_used':   pct_disk_used,
            'pct_disk_free':   pct_disk_free,
        }

    # ── Imprimir informe ──────────────────────────────────────────────────────

    def _print_report(self):
        d = self.report_data
        print()
        print(cprint("=" * 65, C.CYAN, bold=True))
        print(cprint("  SOMONGER — Informe Estadístico del Sistema de Archivos", C.BOLD))
        print(cprint("=" * 65, C.CYAN, bold=True))
        print(f"  Directorio analizado : {cprint(d['path'], C.WHITE)}")
        print(f"  Fecha del informe    : {cprint(d['timestamp'], C.WHITE)}")
        print()

        # ── Tabla por tipo ────────────────────────────────────────────────────
        separator()
        print(cprint("  DISTRIBUCIÓN POR TIPO DE ARCHIVO", C.CYAN, bold=True))
        separator()

        total_e = d['total_entries']
        header = f"  {'TIPO':<5} {'DESCRIPCIÓN':<28} {'CANTIDAD':>8} {'% COUNT':>8} {'TAMAÑO (KB)':>12}"
        print(cprint(header, C.GRAY))
        separator("-", 65)

        for t, label in self.TYPE_LABELS.items():
            cnt  = d['counts'][t]
            if cnt == 0:
                continue
            sz   = d['sizes'][t]
            pct  = (cnt / total_e * 100) if total_e > 0 else 0
            sz_kb = sz / 1024
            bar  = self._bar(pct, 15)
            line = (f"  [{t}]  {label:<28} {cnt:>8}   "
                    f"{pct:>5.1f}%  {sz_kb:>12.2f}")
            print(cprint(line, C.WHITE))

        separator("-", 65)
        total_kb = d['total_kb']
        print(f"  {'TOTAL':<34} {total_e:>8}  {'100.0%':>7}  {total_kb:>12.2f} KB")
        print(f"  {'':34} {'':9} {'':8}  {d['total_mb']:>12.3f} MB")

        # ── Espacio en disco ──────────────────────────────────────────────────
        print()
        separator()
        print(cprint("  INFORMACIÓN DE PARTICIÓN / DISCO", C.CYAN, bold=True))
        separator()

        rows_disk = [
            ("Espacio total en disco",
             f"{d['disk_total_gb']:.2f} GB  ({d['disk_total']:,} bytes)"),
            ("Espacio usado en disco",
             f"{d['disk_used_gb']:.2f} GB  "
             f"({d['pct_disk_used']:.1f}%)  {self._bar(d['pct_disk_used'], 20)}"),
            ("Espacio libre en disco",
             f"{d['disk_free_gb']:.2f} GB  "
             f"({d['pct_disk_free']:.1f}%)  {self._bar(d['pct_disk_free'], 20)}"),
            ("Este directorio ocupa",
             f"{d['total_mb']:.3f} MB  "
             f"({d['pct_dir_of_disk']:.3f}% del disco total)"),
        ]
        max_k = max(len(r[0]) for r in rows_disk)
        for key, val in rows_disk:
            print(f"  {cprint(key.ljust(max_k + 2), C.CYAN)}: {val}")

        # ── Top 10 extensiones ─────────────────────────────────────────────────
        print()
        separator()
        print(cprint("  TOP 10 EXTENSIONES (archivos regulares)", C.CYAN, bold=True))
        separator()
        ext_sorted = sorted(d['ext_map'].items(),
                            key=lambda x: x[1][0], reverse=True)[:10]
        if ext_sorted:
            hdr = f"  {'EXTENSIÓN':<20} {'ARCHIVOS':>8} {'TAMAÑO (KB)':>12}"
            print(cprint(hdr, C.GRAY))
            separator("-", 45)
            for ext, (cnt, sz) in ext_sorted:
                print(f"  {cprint(ext, C.YELLOW):<20} {cnt:>8} {sz/1024:>12.2f}")
        else:
            print(cprint("  (no hay archivos regulares)", C.GRAY))

        print()
        if d['errors'] > 0:
            print(cprint(f"  ⚠ Entradas con error de acceso: {d['errors']}", C.YELLOW))
        separator("=", 65)
        print()

    def _bar(self, pct, width=20):
        """Barra de progreso ASCII."""
        filled = int(pct / 100 * width)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}]"

    # ── Exportación ───────────────────────────────────────────────────────────

    def _export(self, output_path: str):
        """Exporta a .csv o .txt según extensión."""
        ext = os.path.splitext(output_path)[1].lower()
        if ext == '.csv':
            self._export_csv(output_path)
        else:
            self._export_txt(output_path)

    def _quote(self, val):
        """Envuelve en dobles comillas para CSV."""
        return f'"{val}"'

    def _export_csv(self, path: str):
        """CSV separado por ; con dobles comillas en cada campo."""
        d = self.report_data
        lines = []

        # Encabezado del informe
        lines.append(";".join([self._quote("SOMONGER - Informe Estadístico"),
                                self._quote(d['timestamp'])]))
        lines.append(";".join([self._quote("Directorio"), self._quote(d['path'])]))
        lines.append("")

        # Sección 1: conteo por tipo
        lines.append(";".join([self._quote("TIPO"),
                                self._quote("DESCRIPCION"),
                                self._quote("CANTIDAD"),
                                self._quote("PORCENTAJE"),
                                self._quote("TAMANO_KB")]))
        total_e = d['total_entries']
        for t, label in self.TYPE_LABELS.items():
            cnt = d['counts'][t]
            if cnt == 0:
                continue
            pct = (cnt / total_e * 100) if total_e > 0 else 0
            sz_kb = d['sizes'][t] / 1024
            lines.append(";".join([
                self._quote(t),
                self._quote(label),
                self._quote(str(cnt)),
                self._quote(f"{pct:.2f}%"),
                self._quote(f"{sz_kb:.2f}"),
            ]))
        lines.append(";".join([self._quote("TOTAL"), self._quote(""),
                                self._quote(str(total_e)),
                                self._quote("100.00%"),
                                self._quote(f"{d['total_kb']:.2f}")]))
        lines.append("")

        # Sección 2: partición
        lines.append(";".join([self._quote("PARTICION"), self._quote("VALOR_GB"),
                                self._quote("PORCENTAJE")]))
        lines.append(";".join([self._quote("Espacio total"),
                                self._quote(f"{d['disk_total_gb']:.2f}"),
                                self._quote("100.00%")]))
        lines.append(";".join([self._quote("Espacio usado"),
                                self._quote(f"{d['disk_used_gb']:.2f}"),
                                self._quote(f"{d['pct_disk_used']:.2f}%")]))
        lines.append(";".join([self._quote("Espacio libre"),
                                self._quote(f"{d['disk_free_gb']:.2f}"),
                                self._quote(f"{d['pct_disk_free']:.2f}%")]))
        lines.append(";".join([self._quote("Este directorio"),
                                self._quote(f"{d['total_mb']:.3f} MB"),
                                self._quote(f"{d['pct_dir_of_disk']:.4f}%")]))
        lines.append("")

        # Sección 3: extensiones
        lines.append(";".join([self._quote("EXTENSION"),
                                self._quote("CANTIDAD"),
                                self._quote("TAMANO_KB")]))
        ext_sorted = sorted(d['ext_map'].items(),
                            key=lambda x: x[1][0], reverse=True)
        for ext, (cnt, sz) in ext_sorted:
            lines.append(";".join([
                self._quote(ext),
                self._quote(str(cnt)),
                self._quote(f"{sz/1024:.2f}"),
            ]))

        content = "\n".join(lines)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(cprint(f"[✓] Informe CSV exportado: {path}", C.GREEN))
        except Exception as e:
            print(cprint(f"[ERROR] No se pudo escribir CSV: {e}", C.RED))

    def _export_txt(self, path: str):
        """TXT formateado con separadores de ;"""
        d = self.report_data
        lines = []
        lines.append("SOMONGER - Informe Estadístico del Sistema de Archivos")
        lines.append(f"Fecha: {d['timestamp']}")
        lines.append(f"Directorio: {d['path']}")
        lines.append("=" * 65)
        lines.append("")
        lines.append("TIPO;DESCRIPCION;CANTIDAD;PORCENTAJE;TAMANO_KB")
        total_e = d['total_entries']
        for t, label in self.TYPE_LABELS.items():
            cnt = d['counts'][t]
            if cnt == 0:
                continue
            pct = (cnt / total_e * 100) if total_e > 0 else 0
            sz_kb = d['sizes'][t] / 1024
            lines.append(f'"{t}";"{label}";"{cnt}";"{pct:.2f}%";"{sz_kb:.2f}"')
        lines.append("")
        lines.append("PARTICION;VALOR_GB;PORCENTAJE")
        lines.append(f'"Total";"{d["disk_total_gb"]:.2f}";"100.00%"')
        lines.append(f'"Usado";"{d["disk_used_gb"]:.2f}";"{d["pct_disk_used"]:.2f}%"')
        lines.append(f'"Libre";"{d["disk_free_gb"]:.2f}";"{d["pct_disk_free"]:.2f}%"')
        lines.append(f'"Directorio";"{d["total_mb"]:.3f} MB";"{d["pct_dir_of_disk"]:.4f}%"')

        content = "\n".join(lines)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(cprint(f"[✓] Informe TXT exportado: {path}", C.GREEN))
        except Exception as e:
            print(cprint(f"[ERROR] No se pudo escribir TXT: {e}", C.RED))

    def get_data(self):
        """Devuelve datos del informe (para GUI)."""
        if not self.report_data:
            self._analyze()
        return self.report_data
