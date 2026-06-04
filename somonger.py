#!/usr/bin/env python3
"""
SOMONGER — Sistema Operativo Monitor-Manager
Herramienta de gestión del sistema de archivos Linux.

Uso:
  somonger explore <ruta>
  somonger nav <ruta>
  somonger nav --dir <ruta>
  somonger nav --rm <ruta>
  somonger nav --touchDir <ruta>
  somonger nav --mk <ruta>
  somonger nav --cc <ruta>
  somonger nav --cx <ruta>
  somonger nav --cv <ruta>
  somonger report <ruta> [--output archivo.csv]
  somonger sim <archivo>
  somonger --gui

Temas: 26 (Archivos), 27 (Directorios), 28 (Implementación FS)
Asignatura: Sistemas Operativos — Grado en Ingeniería Informática
"""

import sys
import os
import argparse

# Asegurar que el directorio del script esté en el path de Python
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


# ─── Parser de argumentos ────────────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        prog='somonger',
        description='SOMONGER — Gestor de Sistema de Archivos Linux\n'
                    'Temas 26, 27, 28 — Sistemas Operativos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  somonger explore /home/usuario
  somonger nav /home/usuario/
  somonger nav --dir /home/usuario/
  somonger nav --rm /home/usuario/nuevoArchivo.txt
  somonger nav --touchDir /home/usuario/nuevoDirectorio
  somonger nav --mk /home/usuario/directorioBorrar
  somonger nav --cc /home/usuario/archivo
  somonger nav --cx /home/usuario/archivo
  somonger nav --cv /home/usuario/nombreCopiadoDelArchivo
  somonger report /home/usuario
  somonger report /home/usuario --output informe.csv
  somonger sim /home/usuario/archivo.txt
  somonger --gui
        """
    )

    parser.add_argument('--gui', action='store_true',
                        help='Lanzar interfaz gráfica sin argumentos')
    parser.add_argument('--no-gui', action='store_true',
                        help='Forzar modo solo CLI (sin interfaz gráfica)')

    subparsers = parser.add_subparsers(dest='command')

    # ── explore ───────────────────────────────────────────────────────────────
    p_explore = subparsers.add_parser(
        'explore',
        help='Módulo 1: Explorador recursivo de directorios en árbol'
    )
    p_explore.add_argument('path', nargs='?', default=None,
                           help='Ruta a explorar (ej: /home/usuario)')

    # ── nav ───────────────────────────────────────────────────────────────────
    p_nav = subparsers.add_parser(
        'nav',
        help='Módulo 2: Navegador de archivos con atributos y operaciones'
    )
    p_nav.add_argument('path', nargs='?', default=None,
                       help='Ruta base (ej: /home/usuario/)')

    p_nav.add_argument('--dir',
                       metavar='RUTA',
                       dest='dir_arg',
                       help='Moverse a un directorio y mostrar su contenido')
    p_nav.add_argument('--rm',
                       metavar='RUTA',
                       help='Crear un fichero en la ruta indicada')
    p_nav.add_argument('--touchDir',
                       metavar='RUTA',
                       help='Crear un directorio en la ruta indicada')
    p_nav.add_argument('--mk',
                       metavar='RUTA',
                       help='Borrar un archivo o directorio')
    p_nav.add_argument('--cc',
                       metavar='RUTA',
                       help='Copiar un archivo/directorio (recordado hasta --cc o --cx)')
    p_nav.add_argument('--cx',
                       metavar='RUTA',
                       help='Cortar un archivo/directorio (recordado hasta --cc o --cx)')
    p_nav.add_argument('--cv',
                       metavar='RUTA',
                       help='Pegar en la ruta dada (requiere haber usado --cc o --cx)')

    # ── report ────────────────────────────────────────────────────────────────
    p_report = subparsers.add_parser(
        'report',
        help='Módulo 3: Informe estadístico del sistema de archivos'
    )
    p_report.add_argument('path', nargs='?', default=None,
                          help='Directorio a analizar (ej: /home/usuario)')
    p_report.add_argument('--output', metavar='ARCHIVO',
                          help='Exportar a .csv o .txt (ej: --output informe.csv)')

    # ── sim ───────────────────────────────────────────────────────────────────
    p_sim = subparsers.add_parser(
        'sim',
        help='Módulo 4: Simulador de métodos de asignación (ext2, ext4, FAT32)'
    )
    p_sim.add_argument('file', nargs='?', default=None,
                       help='Archivo para simular particiones')

    return parser


# ─── Ejecución CLI pura (sin GUI) ────────────────────────────────────────────

def run_cli(args):
    """Ejecuta el comando en modo terminal puro (sin ventana gráfica)."""
    cmd = args.command

    if cmd == 'explore':
        from modules.explorer import Explorer
        path = args.path or os.getcwd()
        Explorer(path).run()

    elif cmd == 'nav':
        from modules.navigator import Navigator

        # Determinar ruta base: --dir tiene prioridad, luego path posicional, luego cwd
        dir_target = getattr(args, 'dir_arg', None)
        path = getattr(args, 'path', None) or (os.path.dirname(dir_target) if dir_target else None) or os.getcwd()

        nav = Navigator(path)

        # Si no hay ningún subcomando, mostrar listing de la ruta
        has_subcommand = any([
            getattr(args, 'dir_arg',  None),
            getattr(args, 'rm',       None),
            getattr(args, 'touchDir', None),
            getattr(args, 'mk',       None),
            getattr(args, 'cc',       None),
            getattr(args, 'cx',       None),
            getattr(args, 'cv',       None),
        ])

        if not has_subcommand:
            # Sin subcomando: mostrar contenido de la ruta
            nav.run(args)
        else:
            nav.run(args)

    elif cmd == 'report':
        from modules.reporter import Reporter
        path   = args.path or os.getcwd()
        output = getattr(args, 'output', None)
        Reporter(path).run(output)

    elif cmd == 'sim':
        from modules.simulator import Simulator
        file_path = getattr(args, 'file', None)
        if not file_path:
            print("[ERROR] Debes especificar un archivo. Uso: somonger sim <archivo>")
            sys.exit(1)
        Simulator(file_path).run()

    else:
        # Sin subcomando: mostrar ayuda
        print_help_banner()


def print_help_banner():
    """Muestra el banner de ayuda con colores."""
    banner = """
\033[1m\033[95m╔══════════════════════════════════════════════════════╗
║         SOMONGER — Monitor-Manager de SSOO           ║
║       Temas 26 · 27 · 28  —  Sistemas Operativos     ║
╚══════════════════════════════════════════════════════╝\033[0m

\033[1mUso:\033[0m  somonger <comando> [ruta] [opciones]

\033[96m\033[1mMódulo 1 — Explorador de directorios:\033[0m
  somonger explore \033[93m<ruta>\033[0m

\033[96m\033[1mMódulo 2 — Navegador de archivos:\033[0m
  somonger nav \033[93m<ruta>\033[0m
  somonger nav \033[93m--dir      <ruta>\033[0m    Moverse a un directorio
  somonger nav \033[93m--rm       <ruta>\033[0m    Crear un fichero
  somonger nav \033[93m--touchDir <ruta>\033[0m    Crear un directorio
  somonger nav \033[93m--mk       <ruta>\033[0m    Borrar archivo/directorio
  somonger nav \033[93m--cc       <ruta>\033[0m    Copiar
  somonger nav \033[93m--cx       <ruta>\033[0m    Cortar
  somonger nav \033[93m--cv       <ruta>\033[0m    Pegar

\033[96m\033[1mMódulo 3 — Informe estadístico:\033[0m
  somonger report \033[93m<ruta>\033[0m
  somonger report \033[93m<ruta> --output informe.csv\033[0m

\033[96m\033[1mMódulo 4 — Simulador de asignación:\033[0m
  somonger sim \033[93m<archivo>\033[0m

\033[90mAñade --no-gui para forzar modo solo terminal (sin ventana gráfica)\033[0m
"""
    print(banner)


# ─── Punto de entrada ─────────────────────────────────────────────────────────

def main():
    parser = build_parser()
    args   = parser.parse_args()

    # Si no hay comando y no hay --gui → mostrar ayuda y lanzar GUI
    no_command = not args.command and not args.gui

    # Determinar si usar GUI
    force_cli = getattr(args, 'no_gui', False)
    use_gui   = not force_cli

    if use_gui:
        # Intentar lanzar GUI (requiere display / DISPLAY env var en Linux)
        try:
            import tkinter as _tk
            _tk.Tk().destroy()   # test rápido
            gui_available = True
        except Exception:
            gui_available = False

        if gui_available:
            if no_command:
                print_help_banner()

            # ── Si es report con --output, guardar el archivo ANTES de abrir la GUI ──
            # Así el CSV se crea siempre, aunque el usuario cierre la ventana
            if getattr(args, 'command', None) == 'report':
                output = getattr(args, 'output', None)
                path   = getattr(args, 'path',   None) or os.getcwd()
                if output:
                    try:
                        from modules.reporter import Reporter
                        r = Reporter(path)
                        r._analyze()
                        r._export(output)
                        print(f"\033[92m✔ Informe guardado en: {output}\033[0m")
                    except Exception as e:
                        print(f"\033[91m[ERROR] No se pudo guardar el informe: {e}\033[0m")

            # Siempre lanzar GUI, precargada con los argumentos
            try:
                from gui.app import launch_gui
                launch_gui(args if args.command else None)
            except KeyboardInterrupt:
                print("\n\033[93m[somonger] Ventana cerrada.\033[0m")
            return
        else:
            # Sin display: caer a CLI
            print("\033[93m[AVISO] No se pudo iniciar la interfaz gráfica "
                  "(sin DISPLAY). Usando modo CLI.\033[0m\n")
            use_gui = False

    # Modo CLI puro
    if no_command:
        print_help_banner()
        parser.print_help()
        return

    run_cli(args)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\033[93m[somonger] Saliendo...\033[0m")
        sys.exit(0)
