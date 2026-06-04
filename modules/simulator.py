"""
Módulo 4: Simulador de métodos de asignación
Comando: somonger sim <archivo>

Simula 3 particiones del TRIPLE del tamaño del archivo:
  - ext2  → Asignación por nodos-i (inode)
  - ext4  → Asignación por lista enlazada con índice mejorada
  - FAT32 → Asignación por tabla FAT (lista enlazada con índice en memoria)

Para cada partición:
  1. Crea imagen de disco (.img) con dd
  2. Formatea con mkfs correspondiente
  3. Monta en subdirectorio del directorio del archivo
  4. Copia el archivo
  5. Muestra espacio ocupado en KBs y sectores
  6. Si no hay espacio libre → usa VeraCrypt (archivos cifrados + montaje virtual)

NOTA: Requiere: dd, mkfs.ext2, mkfs.ext4, mkfs.fat, mount, umount (como root/sudo)
      Si no están disponibles → simulación lógica Python (estructuras de datos)
"""

import os
import sys
import math
import struct
import shutil
import subprocess
import datetime

SECTOR_SIZE = 512   # bytes por sector estándar


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

def separator(char="─", width=70):
    print(cprint(char * width, C.GRAY))

def run_cmd(cmd, check=True, capture=True):
    """Ejecuta comando del sistema. Devuelve (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=capture,
            text=True, timeout=60
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)

def check_tool(tool: str) -> bool:
    """Comprueba si una herramienta del sistema está disponible."""
    code, _, _ = run_cmd(f"which {tool} 2>/dev/null || command -v {tool} 2>/dev/null")
    return code == 0

def has_free_space(path: str, needed_bytes: int) -> bool:
    """Comprueba si hay suficiente espacio libre en la partición de 'path'."""
    try:
        disk = shutil.disk_usage(path)
        return disk.free >= needed_bytes
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Simulaciones lógicas (Python puro) cuando no hay herramientas del sistema
# ─────────────────────────────────────────────────────────────────────────────

class InodeTable:
    """
    Simulación de tabla de inodos (usado en ext2/ext3/ext4).
    Cada inodo almacena: tamaño, bloques directos, indirecto simple,
    doble indirecto y triple indirecto.
    """
    BLOCK_SIZE     = 4096   # bytes por bloque (ext2/4 default)
    DIRECT_BLOCKS  = 12     # bloques directos por inodo
    IND_BLOCKS     = 1      # bloque indirecto simple
    DIND_BLOCKS    = 1      # bloque doblemente indirecto
    TIND_BLOCKS    = 1      # bloque triplemente indirecto
    PTRS_PER_BLOCK = BLOCK_SIZE // 4   # punteros por bloque (4 bytes cada uno)

    def __init__(self, fs_size_bytes: int, fs_type: str = "ext2"):
        self.fs_type       = fs_type
        self.fs_size       = fs_size_bytes
        self.block_size    = self.BLOCK_SIZE
        self.total_blocks  = fs_size_bytes // self.BLOCK_SIZE
        # Reservar ~5% para metadatos del sistema de archivos
        self.reserved      = max(1, int(self.total_blocks * 0.05))
        self.free_blocks   = self.total_blocks - self.reserved
        self.used_blocks   = self.reserved
        # Tabla de inodos: dict inode_num → dict
        self.inodes        = {}
        self.next_inode    = 1
        # Bitmap de bloques: False = libre, True = usado
        self.block_bitmap  = [False] * self.total_blocks
        # Marcar reservados como usados
        for i in range(self.reserved):
            self.block_bitmap[i] = True

    def allocate_file(self, file_name: str, file_size: int):
        """
        Simula la asignación de inodo y bloques para un archivo.
        Retorna dict con info del inodo creado.
        """
        blocks_needed = math.ceil(file_size / self.block_size)
        if blocks_needed > self.free_blocks:
            raise RuntimeError(
                f"Sin espacio: se necesitan {blocks_needed} bloques, "
                f"disponibles {self.free_blocks}"
            )

        # Asignar bloques libres
        allocated = []
        for i, used in enumerate(self.block_bitmap):
            if not used and len(allocated) < blocks_needed:
                self.block_bitmap[i] = True
                allocated.append(i)

        self.free_blocks -= blocks_needed
        self.used_blocks += blocks_needed

        # Calcular estructura de punteros (12 directos + indirecto + ...)
        direct = allocated[:self.DIRECT_BLOCKS]
        remaining = allocated[self.DIRECT_BLOCKS:]

        indirect1_blocks = 0
        indirect2_blocks = 0
        indirect3_blocks = 0
        overhead_blocks  = 0  # bloques usados para tablas de punteros

        if remaining:
            # Bloque indirecto simple (almacena punteros)
            ind1_capacity = self.PTRS_PER_BLOCK
            ind1_data     = remaining[:ind1_capacity]
            remaining     = remaining[ind1_capacity:]
            indirect1_blocks = len(ind1_data)
            if ind1_data:
                overhead_blocks += 1  # 1 bloque de índice

        if remaining:
            # Bloque doblemente indirecto
            ind2_capacity = self.PTRS_PER_BLOCK * self.PTRS_PER_BLOCK
            ind2_data     = remaining[:ind2_capacity]
            remaining     = remaining[ind2_capacity:]
            indirect2_blocks = len(ind2_data)
            if ind2_data:
                overhead_blocks += 1 + math.ceil(len(ind2_data) / self.PTRS_PER_BLOCK)

        if remaining:
            indirect3_blocks = len(remaining)

        # Último bloque puede estar parcialmente lleno
        last_block_waste = (self.block_size - (file_size % self.block_size)) % self.block_size

        inode_num = self.next_inode
        self.next_inode += 1

        inode = {
            'inode_num':        inode_num,
            'file_name':        file_name,
            'file_size_bytes':  file_size,
            'file_size_kb':     file_size / 1024,
            'block_size':       self.block_size,
            'blocks_used':      blocks_needed,
            'blocks_overhead':  overhead_blocks,
            'direct_blocks':    len(direct),
            'indirect1_blocks': indirect1_blocks,
            'indirect2_blocks': indirect2_blocks,
            'indirect3_blocks': indirect3_blocks,
            'allocated_block_ids': allocated[:5],  # primeros 5 para mostrar
            'last_block_waste_bytes': last_block_waste,
            'size_on_disk_bytes': (blocks_needed + overhead_blocks) * self.block_size,
            'size_on_disk_kb':   (blocks_needed + overhead_blocks) * self.block_size / 1024,
            'size_on_disk_sectors': math.ceil(
                (blocks_needed + overhead_blocks) * self.block_size / SECTOR_SIZE
            ),
            'fs_free_blocks_after': self.free_blocks,
            'fs_used_bytes':    self.used_blocks * self.block_size,
            'fs_free_bytes':    self.free_blocks * self.block_size,
        }
        self.inodes[inode_num] = inode
        return inode


class FATTable:
    """
    Simulación de tabla FAT (File Allocation Table).
    Usado en FAT16/FAT32 y como base del método de lista enlazada con índice en memoria.
    """
    CLUSTER_SIZE = 4096   # bytes por clúster (FAT32 típico)
    RESERVED_CLUSTERS = 2 # FAT32 reserva los primeros 2

    # Valores especiales FAT32
    FAT_FREE      = 0x00000000
    FAT_EOF       = 0x0FFFFFF8
    FAT_BAD       = 0x0FFFFFF7
    FAT_RESERVED  = 0x0FFFFFF6

    def __init__(self, fs_size_bytes: int):
        self.cluster_size    = self.CLUSTER_SIZE
        self.total_clusters  = fs_size_bytes // self.CLUSTER_SIZE
        # La tabla FAT en sí ocupa espacio (4 bytes por entrada en FAT32)
        fat_size_bytes = self.total_clusters * 4
        fat_clusters   = math.ceil(fat_size_bytes / self.CLUSTER_SIZE)
        # Sectores reservados (boot sector, etc.)
        reserved_sectors = 32  # típico en FAT32
        reserved_clusters = math.ceil(reserved_sectors * SECTOR_SIZE / self.CLUSTER_SIZE)

        self.overhead_clusters = fat_clusters + reserved_clusters + self.RESERVED_CLUSTERS
        self.free_clusters     = self.total_clusters - self.overhead_clusters
        self.used_clusters     = self.overhead_clusters

        # Tabla FAT: lista donde fat[i] = siguiente clúster (o FAT_EOF/FAT_FREE)
        self.fat = [self.FAT_FREE] * self.total_clusters
        for i in range(self.overhead_clusters):
            self.fat[i] = self.FAT_RESERVED

        self.next_free_cluster = self.overhead_clusters

    def allocate_file(self, file_name: str, file_size: int):
        """Simula la asignación de clústeres para un archivo en FAT."""
        clusters_needed = math.ceil(file_size / self.cluster_size)
        if clusters_needed > self.free_clusters:
            raise RuntimeError(
                f"Sin espacio FAT: se necesitan {clusters_needed} clústeres, "
                f"disponibles {self.free_clusters}"
            )

        # Encontrar y enlazar clústeres libres (first-fit)
        allocated = []
        current   = self.next_free_cluster
        while len(allocated) < clusters_needed and current < self.total_clusters:
            if self.fat[current] == self.FAT_FREE:
                allocated.append(current)
            current += 1

        # Actualizar tabla FAT (cadena enlazada)
        for i in range(len(allocated) - 1):
            self.fat[allocated[i]] = allocated[i + 1]
        if allocated:
            self.fat[allocated[-1]] = self.FAT_EOF

        self.free_clusters  -= clusters_needed
        self.used_clusters  += clusters_needed
        # Actualizar puntero al siguiente libre aproximado
        if allocated:
            self.next_free_cluster = allocated[-1] + 1

        last_cluster_waste = (self.cluster_size - (file_size % self.cluster_size)) % self.cluster_size

        # Tamaño de la entrada FAT en disco (solo la cadena, no la tabla completa)
        fat_entry_bytes = clusters_needed * 4   # 4 bytes por entrada FAT32

        result = {
            'file_name':          file_name,
            'file_size_bytes':    file_size,
            'file_size_kb':       file_size / 1024,
            'cluster_size':       self.cluster_size,
            'clusters_used':      clusters_needed,
            'first_cluster':      allocated[0] if allocated else None,
            'cluster_chain':      allocated[:8],   # primeros 8 para mostrar
            'fat_entry_bytes':    fat_entry_bytes,
            'last_cluster_waste': last_cluster_waste,
            'size_on_disk_bytes': clusters_needed * self.cluster_size,
            'size_on_disk_kb':    clusters_needed * self.cluster_size / 1024,
            'size_on_disk_sectors': math.ceil(
                clusters_needed * self.cluster_size / SECTOR_SIZE
            ),
            'fat_overhead_clusters': self.overhead_clusters,
            'fat_overhead_kb':    self.overhead_clusters * self.cluster_size / 1024,
            'fs_free_clusters':   self.free_clusters,
            'fs_free_bytes':      self.free_clusters * self.cluster_size,
            'fs_free_kb':         self.free_clusters * self.cluster_size / 1024,
        }
        return result


# ─────────────────────────────────────────────────────────────────────────────
# Simulador principal
# ─────────────────────────────────────────────────────────────────────────────

class Simulator:
    """
    Simulador de métodos de asignación de espacio en disco.
    Intenta usar herramientas del sistema (dd, mkfs) y si no están
    disponibles realiza simulación lógica con Python.
    """

    PARTITIONS = [
        {'name': 'ext2',  'fs': 'ext2',  'mkfs': 'mkfs.ext2', 'color': C.GREEN},
        {'name': 'ext4',  'fs': 'ext4',  'mkfs': 'mkfs.ext4', 'color': C.BLUE},
        {'name': 'fat32', 'fs': 'fat32', 'mkfs': 'mkfs.fat',  'color': C.YELLOW},
    ]

    def __init__(self, file_path: str):
        self.file_path    = os.path.abspath(file_path)
        self.file_dir     = os.path.dirname(self.file_path)
        self.file_name    = os.path.basename(self.file_path)
        self.file_size    = 0
        self.part_size    = 0
        self.results      = []
        self.use_real     = False   # True = usar mkfs/mount, False = simulación lógica
        self.use_veracrypt= False

    def run(self):
        """Punto de entrada principal."""
        if not os.path.isfile(self.file_path):
            print(cprint(f"[ERROR] No es un archivo válido: {self.file_path}", C.RED))
            sys.exit(1)

        self.file_size = os.path.getsize(self.file_path)
        self.part_size = self.file_size * 3   # TRIPLE del tamaño

        print()
        print(cprint("=" * 70, C.CYAN, bold=True))
        print(cprint("  SOMONGER — Simulador de Métodos de Asignación", C.BOLD))
        print(cprint("=" * 70, C.CYAN, bold=True))
        print(f"  Archivo        : {cprint(self.file_path, C.WHITE)}")
        print(f"  Tamaño archivo : {cprint(self._fmt_size(self.file_size), C.WHITE)}")
        print(f"  Tamaño partición (x3): {cprint(self._fmt_size(self.part_size), C.WHITE)}")
        print(f"  Fecha          : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Verificar herramientas disponibles
        tools_available = all(check_tool(t) for t in ['dd', 'mkfs.ext2', 'mkfs.ext4', 'mkfs.fat', 'mount'])
        self.use_real = tools_available

        if tools_available:
            # Verificar espacio libre en disco
            needed = self.part_size * 3 + (10 * 1024 * 1024)  # 3 particiones + 10MB extra
            if not has_free_space(self.file_dir, needed):
                print(cprint("[AVISO] Espacio insuficiente en disco. Intentando VeraCrypt...", C.YELLOW))
                self.use_veracrypt = True
                self.use_real = False
            else:
                print(cprint("[INFO] Herramientas del sistema detectadas → usando particiones reales.", C.GREEN))
        else:
            print(cprint("[INFO] Herramientas mkfs/mount no disponibles → simulación lógica Python.", C.YELLOW))
            print(cprint("       (Para particiones reales: instala e2fsprogs, dosfstools, util-linux)", C.GRAY))

        print()
        separator()

        # Ejecutar simulación para cada sistema de archivos
        for part_info in self.PARTITIONS:
            if self.use_real:
                result = self._real_partition(part_info)
            elif self.use_veracrypt:
                result = self._veracrypt_partition(part_info)
            else:
                result = self._logical_simulation(part_info)
            self.results.append(result)

        # Mostrar resumen comparativo
        self._print_summary()

    # ── Partición real con mkfs ───────────────────────────────────────────────

    def _real_partition(self, part_info: dict) -> dict:
        """Crea imagen, formatea, monta, copia y mide (modo real Linux)."""
        name     = part_info['name']
        fs_type  = part_info['fs']
        mkfs_cmd = part_info['mkfs']
        color    = part_info['color']

        print(cprint(f"  [PARTICIÓN {name.upper()}]", color, bold=True))

        img_path   = os.path.join(self.file_dir, f"somonger_{name}.img")
        mount_dir  = os.path.join(self.file_dir, f"mount_{name}")

        # Tamaño en KB para dd
        part_kb = math.ceil(self.part_size / 1024)
        # Mínimos: ext2/4 necesita al menos 1440 KB, fat32 512KB
        if name in ('ext2', 'ext4'):
            part_kb = max(part_kb, 2048)
        else:
            part_kb = max(part_kb, 512)

        result = {
            'name': name, 'mode': 'real', 'color': color,
            'img_path': img_path, 'mount_dir': mount_dir,
            'success': False, 'error': None,
            'size_on_disk_kb': 0, 'size_on_disk_sectors': 0,
            'fs_used_kb': 0, 'fs_free_kb': 0, 'fs_total_kb': part_kb,
        }

        try:
            # 1. Crear imagen vacía con dd
            print(f"    → Creando imagen {part_kb} KB ...", end=" ", flush=True)
            rc, _, err = run_cmd(f"dd if=/dev/zero of='{img_path}' bs=1K count={part_kb} 2>&1")
            if rc != 0:
                result['error'] = f"dd falló: {err}"
                print(cprint("✗", C.RED))
                return result
            print(cprint("✓", C.GREEN))

            # 2. Formatear
            print(f"    → Formateando como {name.upper()} ...", end=" ", flush=True)
            if name == 'fat32':
                rc, _, err = run_cmd(f"mkfs.fat -F 32 '{img_path}' 2>&1")
            elif name == 'ext2':
                rc, _, err = run_cmd(f"mkfs.ext2 -F '{img_path}' 2>&1")
            else:  # ext4
                rc, _, err = run_cmd(f"mkfs.ext4 -F '{img_path}' 2>&1")
            if rc != 0:
                result['error'] = f"mkfs falló: {err}"
                print(cprint("✗", C.RED))
                return result
            print(cprint("✓", C.GREEN))

            # 3. Montar en subdirectorio
            os.makedirs(mount_dir, exist_ok=True)
            print(f"    → Montando en {mount_dir} ...", end=" ", flush=True)
            if name == 'fat32':
                rc, _, err = run_cmd(
                    f"sudo mount -o loop,uid=$(id -u),gid=$(id -g) '{img_path}' '{mount_dir}' 2>&1")
            else:
                rc, _, err = run_cmd(
                    f"sudo mount -o loop '{img_path}' '{mount_dir}' 2>&1")
            if rc != 0:
                result['error'] = f"mount falló: {err}"
                print(cprint("✗", C.RED))
                return result
            
            # Dar permisos en ext2/ext4 (por defecto son de root tras el mount)
            if name in ('ext2', 'ext4'):
                run_cmd(f"sudo chmod 777 '{mount_dir}'")

            print(cprint("✓", C.GREEN))

            # 4. Copiar archivo
            dest_file = os.path.join(mount_dir, self.file_name)
            print(f"    → Copiando {self.file_name} ...", end=" ", flush=True)
            shutil.copy2(self.file_path, dest_file)
            print(cprint("✓", C.GREEN))

            # 5. Medir espacio ocupado
            rc, out, _ = run_cmd(f"du -k '{dest_file}'")
            used_kb = int(out.split()[0]) if rc == 0 and out.strip() else 0

            rc, out, _ = run_cmd(f"df -k '{mount_dir}'")
            lines = out.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                fs_total_kb = int(parts[1]) if len(parts) > 1 else 0
                fs_used_kb  = int(parts[2]) if len(parts) > 2 else 0
                fs_free_kb  = int(parts[3]) if len(parts) > 3 else 0
            else:
                fs_total_kb = fs_used_kb = fs_free_kb = 0

            # 6. Desmontar
            run_cmd(f"sudo umount '{mount_dir}'")

            result.update({
                'success':            True,
                'size_on_disk_kb':    used_kb,
                'size_on_disk_sectors': math.ceil(used_kb * 1024 / SECTOR_SIZE),
                'fs_total_kb':        fs_total_kb,
                'fs_used_kb':         fs_used_kb,
                'fs_free_kb':         fs_free_kb,
            })
            print()

        except Exception as e:
            result['error'] = str(e)

        return result

    # ── Partición con VeraCrypt ───────────────────────────────────────────────

    def _veracrypt_partition(self, part_info: dict) -> dict:
        """Crea contenedor VeraCrypt cifrado, lo monta y copia el archivo."""
        name  = part_info['name']
        color = part_info['color']

        print(cprint(f"  [PARTICIÓN {name.upper()} — VeraCrypt]", color, bold=True))

        vc_file   = os.path.join(self.file_dir, f"somonger_vc_{name}.vc")
        mount_dir = os.path.join(self.file_dir, f"mount_{name}")
        part_mb   = max(1, math.ceil(self.part_size / 1024 / 1024))

        result = {
            'name': name, 'mode': 'veracrypt', 'color': color,
            'vc_file': vc_file, 'mount_dir': mount_dir,
            'success': False, 'error': None,
            'size_on_disk_kb': 0, 'size_on_disk_sectors': 0,
            'fs_used_kb': 0, 'fs_free_kb': 0, 'fs_total_kb': part_mb * 1024,
        }

        if not check_tool('veracrypt'):
            result['error'] = "VeraCrypt no está instalado. Instala: sudo apt install veracrypt"
            print(cprint(f"    ✗ {result['error']}", C.RED))
            # Caer a simulación lógica
            return self._logical_simulation(part_info)

        try:
            password = "somonger2024"

            # 1. Crear contenedor VeraCrypt
            print(f"    → Creando contenedor VeraCrypt {part_mb} MB ...", end=" ", flush=True)
            rc, _, err = run_cmd(
                f"veracrypt --text --create '{vc_file}' "
                f"--size={part_mb}M --password='{password}' "
                f"--volume-type=normal --encryption=AES "
                f"--hash=SHA-512 --filesystem={name} --pim=0 "
                f"--keyfiles='' --random-source=/dev/urandom -m=nokernelcrypto"
            )
            if rc != 0:
                result['error'] = f"VeraCrypt create: {err}"
                print(cprint("✗", C.RED))
                return self._logical_simulation(part_info)
            print(cprint("✓", C.GREEN))

            # 2. Montar
            os.makedirs(mount_dir, exist_ok=True)
            print(f"    → Montando contenedor ...", end=" ", flush=True)
            rc, _, err = run_cmd(
                f"veracrypt --text --mount '{vc_file}' '{mount_dir}' "
                f"--password='{password}' --pim=0 --keyfiles='' "
                f"--protect-hidden=no -m=nokernelcrypto"
            )
            if rc != 0:
                result['error'] = f"VeraCrypt mount: {err}"
                print(cprint("✗", C.RED))
                return self._logical_simulation(part_info)
            print(cprint("✓", C.GREEN))

            # 3. Copiar
            dest_file = os.path.join(mount_dir, self.file_name)
            shutil.copy2(self.file_path, dest_file)

            # 4. Medir
            rc, out, _ = run_cmd(f"du -k '{dest_file}'")
            used_kb = int(out.split()[0]) if rc == 0 and out.strip() else self.file_size // 1024

            # 5. Desmontar
            run_cmd(f"veracrypt --text --dismount '{mount_dir}'")

            result.update({
                'success':            True,
                'size_on_disk_kb':    used_kb,
                'size_on_disk_sectors': math.ceil(used_kb * 1024 / SECTOR_SIZE),
                'fs_free_kb':         (part_mb * 1024) - used_kb,
            })

        except Exception as e:
            result['error'] = str(e)
            return self._logical_simulation(part_info)

        return result

    # ── Simulación lógica Python ──────────────────────────────────────────────

    def _logical_simulation(self, part_info: dict) -> dict:
        """
        Simula matemáticamente la asignación sin herramientas del sistema.
        Crea una representación en disco (.img simulado) con la estructura real
        de metadatos y muestra cómo quedarían los datos asignados.
        """
        name  = part_info['name']
        color = part_info['color']

        print(cprint(f"  [PARTICIÓN {name.upper()}] — Simulación lógica", color, bold=True))

        result = {'name': name, 'mode': 'simulation', 'color': color,
                  'success': True, 'error': None}

        if name in ('ext2', 'ext4'):
            sim = InodeTable(self.part_size, name)
            try:
                inode_info = sim.allocate_file(self.file_name, self.file_size)
                result.update(inode_info)
                result['sim_type'] = 'inode'
                result['fs_total_kb'] = self.part_size / 1024
                result['size_on_disk_kb'] = inode_info['size_on_disk_kb']
                result['size_on_disk_sectors'] = inode_info['size_on_disk_sectors']
                result['fs_free_kb'] = inode_info['fs_free_bytes'] / 1024
                result['fs_used_kb'] = inode_info['fs_used_bytes'] / 1024
            except RuntimeError as e:
                result['success'] = False
                result['error'] = str(e)
                result['size_on_disk_kb'] = 0
                result['size_on_disk_sectors'] = 0
        else:  # fat32
            sim = FATTable(self.part_size)
            try:
                fat_info = sim.allocate_file(self.file_name, self.file_size)
                result.update(fat_info)
                result['sim_type'] = 'fat'
                result['fs_total_kb'] = self.part_size / 1024
                result['size_on_disk_kb'] = fat_info['size_on_disk_kb']
                result['size_on_disk_sectors'] = fat_info['size_on_disk_sectors']
                result['fs_free_kb'] = fat_info['fs_free_kb']
                result['fs_used_kb'] = (self.part_size - fat_info['fs_free_bytes']) / 1024
            except RuntimeError as e:
                result['success'] = False
                result['error'] = str(e)
                result['size_on_disk_kb'] = 0
                result['size_on_disk_sectors'] = 0

        # Crear archivo de imagen simulado (con metadatos mínimos)
        img_path  = os.path.join(self.file_dir, f"somonger_{name}_sim.img")
        mount_dir = os.path.join(self.file_dir, f"mount_{name}")
        result['img_path']  = img_path
        result['mount_dir'] = mount_dir

        # Crear directorio de montaje simulado y copiar archivo ahí
        os.makedirs(mount_dir, exist_ok=True)
        dest = os.path.join(mount_dir, self.file_name)
        try:
            shutil.copy2(self.file_path, dest)
            print(cprint(f"    → Archivo copiado en directorio simulado: {mount_dir}", C.GREEN))
        except Exception as e:
            print(cprint(f"    [AVISO] No se pudo copiar: {e}", C.YELLOW))

        # Crear archivo de imagen con cabecera simulada
        try:
            self._write_simulated_image(img_path, name, result)
            print(cprint(f"    → Imagen simulada creada: {img_path}", C.GREEN))
        except Exception as e:
            print(cprint(f"    [AVISO] Imagen simulada: {e}", C.YELLOW))

        return result

    def _write_simulated_image(self, img_path: str, fs_type: str, info: dict):
        """Escribe un archivo .img con cabecera que describe la simulación."""
        header = (
            f"SOMONGER SIMULATED FILESYSTEM IMAGE\n"
            f"FS_TYPE={fs_type}\n"
            f"FILE={self.file_name}\n"
            f"FILE_SIZE_BYTES={self.file_size}\n"
            f"PARTITION_SIZE_BYTES={self.part_size}\n"
            f"SIZE_ON_DISK_KB={info.get('size_on_disk_kb', 0):.2f}\n"
            f"SIZE_ON_DISK_SECTORS={info.get('size_on_disk_sectors', 0)}\n"
            f"FS_FREE_KB={info.get('fs_free_kb', 0):.2f}\n"
            f"SIMULATION=Python_logical\n"
            f"TIMESTAMP={datetime.datetime.now().isoformat()}\n"
        )
        with open(img_path, 'w', encoding='utf-8') as f:
            f.write(header)

    # ── Resumen comparativo ───────────────────────────────────────────────────

    def _print_summary(self):
        print()
        separator("═", 70)
        print(cprint("  RESUMEN COMPARATIVO DE MÉTODOS DE ASIGNACIÓN", C.BOLD))
        separator("═", 70)

        # Cabecera
        print(f"  {'PARTICIÓN':<10} {'MÉTODO':<30} {'TAMAÑO DISCO':>13} {'SECTORES':>10} {'LIBRE':>12}")
        separator("-", 70)

        for r in self.results:
            name  = r.get('name', '?').upper()
            color = r.get('color', C.WHITE)
            ok    = r.get('success', False)

            if not ok:
                err = r.get('error', 'Error desconocido')
                print(f"  {cprint(name, color):<10} {'ERROR':<30} {cprint(err[:40], C.RED)}")
                continue

            # Método de asignación según FS
            if name == 'EXT2':
                method = "Nodos-i (inode) — 12 directos + indirectos"
            elif name == 'EXT4':
                method = "Nodos-i extendido (extents)"
            else:
                method = "FAT32 — lista enlazada con índice en memoria"

            size_kb   = r.get('size_on_disk_kb', 0)
            sectors   = r.get('size_on_disk_sectors', 0)
            free_kb   = r.get('fs_free_kb', 0)
            mode      = r.get('mode', 'sim')
            mode_tag  = f"[{mode[:4]}]"

            print(f"  {cprint(name, color, bold=True):<10} "
                  f"{method:<30} "
                  f"{size_kb:>10.2f} KB "
                  f"{sectors:>10} sect "
                  f"{free_kb:>9.2f} KB libre")

        separator("═", 70)

        # Descripción teórica de cada método
        print()
        print(cprint("  DESCRIPCIÓN TEÓRICA DE MÉTODOS (Tema 28):", C.CYAN, bold=True))
        print()

        teorias = [
            ("EXT2 — Nodos-i",
             "Cada archivo tiene un 'nodo i' con 12 punteros directos, 1 indirecto\n"
             "  simple, 1 doble y 1 triple. Permite acceso rápido a archivos pequeños\n"
             "  y eficiente para archivos grandes. No sufre fragmentación externa.\n"
             "  Usado en Linux, implementado en este sistema."),
            ("EXT4 — Extents",
             "Evolución de ext2/ext3. Usa 'extents' (rangos contiguos de bloques)\n"
             "  en lugar de punteros individuales. Reduce overhead de metadatos para\n"
             "  archivos grandes. Compatible con ext2/ext3. Journaling mejorado."),
            ("FAT32 — Lista enlazada con índice en memoria",
             "Tabla de asignación de archivos (FAT) almacenada al inicio de la\n"
             "  partición. Cada entrada apunta al siguiente clúster del archivo\n"
             "  (EOF = fin). Toda la tabla se carga en RAM → acceso rápido.\n"
             "  Inconveniente: pierde espacio en disco para mantener la tabla."),
        ]

        for title, desc in teorias:
            print(f"  {cprint('▶ ' + title, C.YELLOW, bold=True)}")
            for line in desc.split('\n'):
                print(f"    {line}")
            print()

        # Mostrar rutas creadas
        separator("-", 70)
        print(cprint("  ARCHIVOS Y DIRECTORIOS CREADOS:", C.CYAN))
        for r in self.results:
            if r.get('success'):
                name = r.get('name', '?').upper()
                img  = r.get('img_path', '')
                mnt  = r.get('mount_dir', '')
                mode = r.get('mode', '')
                print(f"  [{name}]")
                if img:  print(f"    Imagen : {img}")
                if mnt:  print(f"    Montaje: {mnt}")
                print(f"    Modo   : {mode}")
        separator("═", 70)
        print()

    @staticmethod
    def _fmt_size(b: int) -> str:
        if b < 1024:
            return f"{b} bytes"
        elif b < 1024**2:
            return f"{b/1024:.2f} KB"
        elif b < 1024**3:
            return f"{b/1024**2:.2f} MB"
        else:
            return f"{b/1024**3:.2f} GB"

    def get_results(self):
        """Devuelve resultados para uso en GUI."""
        return self.results
