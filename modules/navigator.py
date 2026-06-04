"""
Módulo 2: Navegador de archivos
Comando: somonger nav <ruta> [opciones]
Muestra atributos completos de archivos/directorios y permite operaciones.

Subcomandos:
  --dir  <ruta>   Moverse a un directorio (listar su contenido)
  --rm   <ruta>   Crear un fichero
  --touchDir <r>  Crear un directorio
  --mk   <ruta>   Borrar un archivo o directorio
  --cc   <ruta>   Copiar (guarda en portapapeles interno)
  --cx   <ruta>   Cortar (guarda en portapapeles interno)
  --cv   <ruta>   Pegar en la ruta dada
"""

import os
import stat
import sys
import json
import shutil
import datetime
try:
    import pwd
    import grp
    _HAS_PWD = True
except ImportError:
    _HAS_PWD = False

# Portapapeles persistente entre llamadas CLI (archivo temporal)
CLIPBOARD_FILE = "/tmp/.somonger_clipboard.json"

# ─── Colores ANSI ────────────────────────────────────────────────────────────
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
    b = C.BOLD if bold else ""
    if sys.stdout.isatty():
        return f"{b}{color}{text}{C.RESET}"
    return text

# ─── Utilidades ───────────────────────────────────────────────────────────────

def format_permissions(mode):
    perms = ''
    for bits in [(stat.S_IRUSR, stat.S_IWUSR, stat.S_IXUSR),
                 (stat.S_IRGRP, stat.S_IWGRP, stat.S_IXGRP),
                 (stat.S_IROTH, stat.S_IWOTH, stat.S_IXOTH)]:
        perms += 'r' if mode & bits[0] else '-'
        perms += 'w' if mode & bits[1] else '-'
        perms += 'x' if mode & bits[2] else '-'
    return perms

def get_type_char(mode):
    if stat.S_ISDIR(mode):   return 'd', C.BLUE
    if stat.S_ISLNK(mode):   return 'l', C.CYAN
    if stat.S_ISCHR(mode):   return 'c', C.YELLOW
    if stat.S_ISBLK(mode):   return 'b', C.YELLOW
    if stat.S_ISFIFO(mode):  return 'p', C.MAGENTA
    if stat.S_ISSOCK(mode):  return 's', C.MAGENTA
    return '-', C.WHITE

def get_owner(st):
    if _HAS_PWD:
        try:
            user = pwd.getpwuid(st.st_uid).pw_name
        except (KeyError, Exception):
            user = str(st.st_uid)
        try:
            group = grp.getgrgid(st.st_gid).gr_name
        except (KeyError, Exception):
            group = str(st.st_gid)
    else:
        user  = str(st.st_uid)
        group = str(st.st_gid)
    return user, group

def fmt_date(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

def print_separator(char="─", width=60):
    print(cprint(char * width, C.GRAY))

def print_header(title):
    print()
    print_separator()
    print(cprint(f"  {title}", C.BOLD))
    print_separator()

# ─── Clase principal ─────────────────────────────────────────────────────────

class Navigator:
    """
    Navegador de archivos: muestra atributos y permite operar sobre
    archivos y directorios en una ruta dada.
    """

    def __init__(self, path: str):
        self.path = os.path.abspath(path)

    def run(self, args):
        """Despacha según los argumentos recibidos."""

        # --dir puede venir como 'dir_arg' (argparse dest) o como 'dir' (FakeArgs)
        dir_target = (getattr(args, 'dir_arg', None) or
                      getattr(args, 'dir',     None))

        all_subcmds = [dir_target,
                       getattr(args, 'rm',       None),
                       getattr(args, 'touchDir', None),
                       getattr(args, 'mk',       None),
                       getattr(args, 'cc',       None),
                       getattr(args, 'cx',       None),
                       getattr(args, 'cv',       None)]

        # Primero, si se pasó ruta principal, mostrar sus atributos/contenido
        if os.path.isdir(self.path):
            self._list_directory(self.path)
        elif os.path.exists(self.path) or os.path.islink(self.path):
            self._show_file_info(self.path)
        else:
            # La ruta no existe: solo es error si no hay subcomando
            if not any(all_subcmds):
                print(cprint(f"[ERROR] Ruta no encontrada: {self.path}", C.RED))
                sys.exit(1)

        # ── Subcomandos ──────────────────────────────────────────────────────
        if dir_target:
            self._cmd_dir(dir_target)

        if getattr(args, 'rm', None):
            self._cmd_rm(args.rm)

        if getattr(args, 'touchDir', None):
            self._cmd_touchDir(args.touchDir)

        if getattr(args, 'mk', None):
            self._cmd_mk(args.mk)

        if getattr(args, 'cc', None):
            self._cmd_cc(args.cc, cut=False)

        if getattr(args, 'cx', None):
            self._cmd_cc(args.cx, cut=True)

        if getattr(args, 'cv', None):
            self._cmd_cv(args.cv)

    # ── Mostrar información completa de un archivo ────────────────────────────

    def _show_file_info(self, path: str):
        print_header(f"SOMONGER — Atributos de: {os.path.basename(path)}")
        try:
            st = os.lstat(path)
        except (PermissionError, FileNotFoundError) as e:
            print(cprint(f"  [ERROR] {e}", C.RED))
            return

        mode = st.st_mode
        type_char, color = get_type_char(mode)
        perms = format_permissions(mode)
        user, group = get_owner(st)

        size_bytes = st.st_size
        size_kb    = size_bytes / 1024

        rows = [
            ("Ruta completa",      path),
            ("Tipo",               f"[{type_char}] {self._type_name(mode)}"),
            ("Permisos (rwx)",     f"{type_char}{perms}"),
            ("Permisos (octal)",   f"{oct(mode & 0o7777)}"),
            ("Inodo",              str(st.st_ino)),
            ("Propietario",        f"{user} (uid={st.st_uid})"),
            ("Grupo",              f"{group} (gid={st.st_gid})"),
            ("Tamaño",             f"{size_bytes} bytes  /  {size_kb:.2f} KB"),
            ("Bloques asignados",  str(st.st_blocks)),
            ("Tamaño de bloque",   str(st.st_blksize) if hasattr(st, 'st_blksize') else "N/A"),
            ("Nº de enlaces duros",str(st.st_nlink)),
            ("Fecha de acceso",    fmt_date(st.st_atime)),
            ("Fecha de modif.",    fmt_date(st.st_mtime)),
            ("Fecha de cambio",    fmt_date(st.st_ctime)),
        ]

        # Mostrar tabla
        max_key = max(len(r[0]) for r in rows)
        for key, val in rows:
            k = cprint(key.ljust(max_key + 2), C.CYAN)
            v = cprint(val, C.WHITE)
            print(f"  {k}: {v}")

        # Si es enlace simbólico, mostrar destino
        if stat.S_ISLNK(mode):
            try:
                target = os.readlink(path)
                exists = "✓ existe" if os.path.exists(target) else "✗ roto"
                print(f"  {cprint('Enlace apunta a'.ljust(max_key + 2), C.CYAN)}: "
                      f"{cprint(target, C.YELLOW)} ({exists})")
            except Exception:
                pass

        print_separator()
        print()

    def _type_name(self, mode):
        if stat.S_ISDIR(mode):  return "Directorio"
        if stat.S_ISLNK(mode):  return "Enlace simbólico"
        if stat.S_ISCHR(mode):  return "Dispositivo de caracteres"
        if stat.S_ISBLK(mode):  return "Dispositivo de bloques"
        if stat.S_ISFIFO(mode): return "FIFO / Named pipe"
        if stat.S_ISSOCK(mode): return "Socket"
        return "Archivo regular"

    # ── Listar contenido de un directorio ─────────────────────────────────────

    def _list_directory(self, path: str):
        print_header(f"SOMONGER — Navegador: {path}")
        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            print(cprint("  [ERROR] Permiso denegado", C.RED))
            return

        # Cabecera de tabla
        header = (
            f"  {'TIPO':<5} {'PERMS':<10} {'INODO':<10} "
            f"{'TAMAÑO (KB)':>11} {'ENLACES':>7} {'PROPIETARIO':<14} "
            f"{'MODIFICADO':<21} NOMBRE"
        )
        print(cprint(header, C.GRAY))
        print_separator()

        total_size = 0
        for entry in entries:
            full = os.path.join(path, entry)
            try:
                st = os.lstat(full)
                mode = st.st_mode
                type_char, color = get_type_char(mode)
                perms = format_permissions(mode)
                user, group = get_owner(st)
                size_kb = st.st_size / 1024
                total_size += st.st_size
                modtime = fmt_date(st.st_mtime)
                inode = st.st_ino

                # Nombre con color por tipo
                if stat.S_ISDIR(mode):
                    name_disp = cprint(entry + "/", C.BLUE)
                elif stat.S_ISLNK(mode):
                    try:
                        tgt = os.readlink(full)
                        name_disp = cprint(f"{entry} -> {tgt}", C.CYAN)
                    except Exception:
                        name_disp = cprint(entry, C.CYAN)
                elif stat.S_ISCHR(mode) or stat.S_ISBLK(mode):
                    name_disp = cprint(entry, C.YELLOW)
                else:
                    name_disp = cprint(entry, C.WHITE)

                line = (
                    f"  [{type_char}]  "
                    f"{type_char}{perms:<9} "
                    f"{inode:<10} "
                    f"{size_kb:>11.2f} "
                    f"{st.st_nlink:>7} "
                    f"{user:<14} "
                    f"{modtime:<21} "
                    f"{name_disp}"
                )
                print(line)
            except (PermissionError, FileNotFoundError, OSError) as e:
                print(f"  [?]   {cprint(entry, C.RED)} — {str(e)}")

        print_separator()
        print(f"  Total entradas: {len(entries)} | "
              f"Tamaño total: {total_size/1024:.2f} KB  "
              f"({total_size/1024/1024:.3f} MB)")
        print()

    # ── Subcomandos de operación ──────────────────────────────────────────────

    def _cmd_dir(self, target: str):
        """--dir: moverse a un directorio (listar su contenido)."""
        target = os.path.abspath(target)
        if not os.path.isdir(target):
            print(cprint(f"[ERROR] No es un directorio: {target}", C.RED))
            return
        print(cprint(f"\n[--dir] Navegando a: {target}", C.GREEN, bold=True))
        self._list_directory(target)

    def _cmd_rm(self, target: str):
        """--rm: crear un fichero (nombre contraintuitivo según enunciado)."""
        target = os.path.abspath(target)
        if os.path.exists(target):
            print(cprint(f"[AVISO] El archivo ya existe: {target}", C.YELLOW))
            return
        try:
            # Crear directorios padre si no existen
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'w') as f:
                f.write("")
            st = os.stat(target)
            print(cprint(f"[--rm] Fichero creado: {target}", C.GREEN))
            print(f"       Inodo: {st.st_ino} | Permisos: {format_permissions(st.st_mode)}")
        except Exception as e:
            print(cprint(f"[ERROR] No se pudo crear el fichero: {e}", C.RED))

    def _cmd_touchDir(self, target: str):
        """--touchDir: crear un directorio."""
        target = os.path.abspath(target)
        if os.path.exists(target):
            print(cprint(f"[AVISO] El directorio ya existe: {target}", C.YELLOW))
            return
        try:
            os.makedirs(target, exist_ok=False)
            st = os.stat(target)
            print(cprint(f"[--touchDir] Directorio creado: {target}", C.GREEN))
            print(f"             Inodo: {st.st_ino} | Permisos: d{format_permissions(st.st_mode)}")
        except Exception as e:
            print(cprint(f"[ERROR] No se pudo crear el directorio: {e}", C.RED))

    def _cmd_mk(self, target: str):
        """--mk: borrar un archivo o directorio (nombre contraintuitivo)."""
        target = os.path.abspath(target)
        if not os.path.exists(target) and not os.path.islink(target):
            print(cprint(f"[ERROR] No existe: {target}", C.RED))
            return
        try:
            if os.path.isdir(target) and not os.path.islink(target):
                shutil.rmtree(target)
                print(cprint(f"[--mk] Directorio eliminado: {target}", C.RED))
            else:
                os.remove(target)
                print(cprint(f"[--mk] Archivo eliminado: {target}", C.RED))
        except Exception as e:
            print(cprint(f"[ERROR] No se pudo eliminar: {e}", C.RED))

    def _cmd_cc(self, target: str, cut: bool):
        """--cc: copiar | --cx: cortar (guardar en portapapeles interno)."""
        target = os.path.abspath(target)
        if not os.path.exists(target) and not os.path.islink(target):
            print(cprint(f"[ERROR] No existe: {target}", C.RED))
            return
        op = "cortar" if cut else "copiar"
        data = {"path": target, "cut": cut}
        try:
            with open(CLIPBOARD_FILE, 'w') as f:
                json.dump(data, f)
            verb = "Cortado" if cut else "Copiado"
            flag = "--cx" if cut else "--cc"
            print(cprint(f"[{flag}] {verb} en portapapeles: {target}", C.YELLOW))
            print(f"       (Para pegar usa: somonger nav <destino> --cv <ruta_destino>)")
        except Exception as e:
            print(cprint(f"[ERROR] Portapapeles: {e}", C.RED))

    def _cmd_cv(self, dest: str):
        """--cv: pegar en la ruta dada."""
        dest = os.path.abspath(dest)
        if not os.path.exists(CLIPBOARD_FILE):
            print(cprint("[ERROR] Portapapeles vacío. Usa --cc o --cx primero.", C.RED))
            return
        try:
            with open(CLIPBOARD_FILE, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(cprint(f"[ERROR] No se pudo leer portapapeles: {e}", C.RED))
            return

        src  = data["path"]
        cut  = data["cut"]

        if not os.path.exists(src) and not os.path.islink(src):
            print(cprint(f"[ERROR] El origen ya no existe: {src}", C.RED))
            return

        # Calcular destino final
        if os.path.isdir(dest):
            final_dest = os.path.join(dest, os.path.basename(src))
        else:
            final_dest = dest
            os.makedirs(os.path.dirname(final_dest), exist_ok=True)

        try:
            if os.path.isdir(src) and not os.path.islink(src):
                shutil.copytree(src, final_dest)
            else:
                shutil.copy2(src, final_dest)

            if cut:
                # Eliminar origen
                if os.path.isdir(src) and not os.path.islink(src):
                    shutil.rmtree(src)
                else:
                    os.remove(src)
                os.remove(CLIPBOARD_FILE)
                print(cprint(f"[--cv] Movido: {src} → {final_dest}", C.GREEN))
            else:
                print(cprint(f"[--cv] Copiado: {src} → {final_dest}", C.GREEN))

            st = os.lstat(final_dest)
            print(f"       Inodo destino: {st.st_ino} | Tamaño: {st.st_size/1024:.2f} KB")

        except Exception as e:
            print(cprint(f"[ERROR] No se pudo pegar: {e}", C.RED))

    def get_entries_data(self, path=None):
        """Devuelve lista de dicts con info de cada entrada (para GUI)."""
        path = path or self.path
        result = []
        if not os.path.isdir(path):
            return result
        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            return result

        for entry in entries:
            full = os.path.join(path, entry)
            try:
                st = os.lstat(full)
                mode = st.st_mode
                type_char, _ = get_type_char(mode)
                user, group = get_owner(st)
                result.append({
                    'name':    entry,
                    'path':    full,
                    'type':    type_char,
                    'type_name': self._type_name(mode),
                    'perms':   format_permissions(mode),
                    'octal':   oct(mode & 0o7777),
                    'inode':   st.st_ino,
                    'size_b':  st.st_size,
                    'size_kb': round(st.st_size / 1024, 2),
                    'links':   st.st_nlink,
                    'uid':     st.st_uid,
                    'gid':     st.st_gid,
                    'owner':   user,
                    'group':   group,
                    'atime':   fmt_date(st.st_atime),
                    'mtime':   fmt_date(st.st_mtime),
                    'ctime':   fmt_date(st.st_ctime),
                    'is_dir':  stat.S_ISDIR(mode),
                    'blocks':  st.st_blocks,
                })
            except (PermissionError, FileNotFoundError, OSError):
                pass
        return result
