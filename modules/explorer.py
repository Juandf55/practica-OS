"""
Módulo 1: Explorador de directorios
Comando: somonger explore <ruta>
Implementa recorrido recursivo en árbol, clasificando cada entrada según tipo Unix.
"""

import os
import stat
import sys


# Colores ANSI para la terminal
class Color:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    BLUE    = "\033[94m"   # directorios
    CYAN    = "\033[96m"   # enlaces simbólicos
    YELLOW  = "\033[93m"   # dispositivos
    GREEN   = "\033[92m"   # ejecutables / archivos regulares
    RED     = "\033[91m"   # archivos especiales
    MAGENTA = "\033[95m"   # sockets / fifos
    WHITE   = "\033[97m"


def get_file_type(path, st=None):
    """
    Devuelve (letra_tipo, descripcion, color) según clasificación Unix.
    d = directorio
    - = archivo regular
    l = enlace simbólico
    c = dispositivo de caracteres
    b = dispositivo de bloques
    p = FIFO (named pipe)
    s = socket
    """
    if st is None:
        try:
            st = os.lstat(path)
        except (PermissionError, FileNotFoundError):
            return ('?', 'inaccesible', Color.RED)

    mode = st.st_mode
    if stat.S_ISDIR(mode):
        return ('d', 'directorio', Color.BLUE)
    elif stat.S_ISLNK(mode):
        return ('l', 'enlace simbólico', Color.CYAN)
    elif stat.S_ISCHR(mode):
        return ('c', 'dispositivo carácter', Color.YELLOW)
    elif stat.S_ISBLK(mode):
        return ('b', 'dispositivo bloque', Color.YELLOW)
    elif stat.S_ISFIFO(mode):
        return ('p', 'FIFO/pipe', Color.MAGENTA)
    elif stat.S_ISSOCK(mode):
        return ('s', 'socket', Color.MAGENTA)
    elif stat.S_ISREG(mode):
        # Detectar si es ejecutable
        if mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            return ('-', 'archivo regular (ejecutable)', Color.GREEN)
        return ('-', 'archivo regular', Color.WHITE)
    else:
        return ('?', 'desconocido', Color.RED)


def format_permissions(mode):
    """Convierte el modo stat a string rwxrwxrwx."""
    perms = ''
    for who in [(stat.S_IRUSR, stat.S_IWUSR, stat.S_IXUSR),
                (stat.S_IRGRP, stat.S_IWGRP, stat.S_IXGRP),
                (stat.S_IROTH, stat.S_IWOTH, stat.S_IXOTH)]:
        perms += 'r' if mode & who[0] else '-'
        perms += 'w' if mode & who[1] else '-'
        perms += 'x' if mode & who[2] else '-'
    return perms


class Explorer:
    """
    Explorador recursivo de directorios en formato árbol.
    Uso CLI: somonger explore <ruta>
    """

    def __init__(self, root_path: str):
        self.root_path = os.path.abspath(root_path)
        self.total_files = 0
        self.total_dirs = 0
        self.total_special = 0
        self.use_color = sys.stdout.isatty()

    def colorize(self, text, color):
        if self.use_color:
            return f"{color}{text}{Color.RESET}"
        return text

    def run(self):
        """Punto de entrada principal."""
        if not os.path.exists(self.root_path):
            print(f"[ERROR] La ruta no existe: {self.root_path}")
            sys.exit(1)

        print(self.colorize(f"\n📁 SOMONGER — Explorador de directorios", Color.BOLD))
        print(self.colorize(f"   Ruta raíz: {self.root_path}", Color.WHITE))
        print("─" * 60)
        print()

        type_char, desc, color = get_file_type(self.root_path)
        print(self.colorize(f"{type_char} {os.path.basename(self.root_path)}/", color))

        self._traverse(self.root_path, prefix="")

        print()
        print("─" * 60)
        print(f"  Resumen:")
        print(f"   📂 Directorios  : {self.total_dirs}")
        print(f"   📄 Archivos reg : {self.total_files}")
        print(f"   ⚙️  Especiales   : {self.total_special}")
        print(f"   TOTAL           : {self.total_dirs + self.total_files + self.total_special}")
        print()

    def _traverse(self, path: str, prefix: str):
        """Recorre recursivamente el directorio mostrando árbol."""
        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            print(f"{prefix}└── {self.colorize('[Permiso denegado]', Color.RED)}")
            return

        # Filtrar . y ..
        entries = [e for e in entries if e not in ('.', '..')]

        for i, entry in enumerate(entries):
            is_last = (i == len(entries) - 1)
            connector = "└── " if is_last else "├── "
            child_prefix = prefix + ("    " if is_last else "│   ")
            full_path = os.path.join(path, entry)

            try:
                st = os.lstat(full_path)
                type_char, desc, color = get_file_type(full_path, st)
                perms = format_permissions(st.st_mode)
                size_kb = st.st_size / 1024
                inode = st.st_ino

                # Construir nombre con información adicional
                if stat.S_ISDIR(st.st_mode):
                    name_str = self.colorize(f"{entry}/", color)
                    self.total_dirs += 1
                elif stat.S_ISLNK(st.st_mode):
                    try:
                        target = os.readlink(full_path)
                        name_str = self.colorize(f"{entry} -> {target}", color)
                    except Exception:
                        name_str = self.colorize(f"{entry}", color)
                    self.total_files += 1
                elif type_char in ('c', 'b', 'p', 's'):
                    name_str = self.colorize(f"{entry}", color)
                    self.total_special += 1
                else:
                    name_str = self.colorize(f"{entry}", color)
                    self.total_files += 1

                # Info compacta: [tipo] nombre  (perms, inode, size)
                info = f"[{type_char}]  {perms}  inodo:{inode}  {size_kb:.1f}KB"
                print(f"{prefix}{connector}{name_str}")
                print(f"{prefix}{'    ' if is_last else '│   '}     {self.colorize(info, Color.WHITE)}")

                # Recursión si es directorio (no enlace simbólico circular)
                if stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode):
                    self._traverse(full_path, child_prefix)

            except (PermissionError, FileNotFoundError, OSError) as e:
                print(f"{prefix}{connector}{self.colorize(entry, Color.RED)} — [{str(e)}]")

    def get_tree_data(self):
        """Devuelve estructura de árbol como lista de dicts (para GUI)."""
        result = []
        self._collect(self.root_path, result, 0)
        return result

    def _collect(self, path, result, depth):
        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            return

        for entry in entries:
            if entry in ('.', '..'):
                continue
            full_path = os.path.join(path, entry)
            try:
                st = os.lstat(full_path)
                type_char, desc, color = get_file_type(full_path, st)
                result.append({
                    'name': entry,
                    'path': full_path,
                    'depth': depth,
                    'type_char': type_char,
                    'type_desc': desc,
                    'inode': st.st_ino,
                    'size': st.st_size,
                    'perms': format_permissions(st.st_mode),
                    'is_dir': stat.S_ISDIR(st.st_mode),
                })
                if stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode):
                    self._collect(full_path, result, depth + 1)
            except (PermissionError, FileNotFoundError, OSError):
                pass
