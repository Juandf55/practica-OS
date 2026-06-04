# SOMONGER — Sistema Operativo Monitor-Manager

**Proyecto SSOO — Gestor de Sistema de Archivos en Linux**
Asignatura: Sistemas Operativos | Grado en Ingeniería Informática | Universidad Europea

---

## Descripción

`somonger` es una herramienta dual (CLI + GUI) para explorar, analizar y operar sobre el sistema de archivos Linux. Implementa los conceptos de los **Temas 26, 27 y 28** de Sistemas Operativos:
- **Tema 26**: Archivos (tipos, atributos, inodos, operaciones)
- **Tema 27**: Directorios (organización jerárquica, rutas, operaciones)
- **Tema 28**: Implementación del sistema de archivos (FAT, nodos-i, asignación contigua/enlazada)

---

## Instalación y Dependencias

### 1. Requisitos del sistema (Linux)

```bash
sudo apt update
sudo apt install python3 python3-tk python3-pip
```

### 2. Dependencias Python

```bash
pip3 install -r requirements.txt
```

Solo necesita `matplotlib` (para las gráficas del Módulo 3). El resto es librería estándar de Python.

### 3. Hacer somonger ejecutable como comando de terminal

```bash
# En el directorio del proyecto:
chmod +x somonger

# Opción A: Añadir el directorio al PATH (temporal, solo esta sesión)
export PATH="$PATH:$(pwd)"

# Opción B: Copiar a /usr/local/bin para uso permanente
sudo cp somonger /usr/local/bin/somonger
```

---

## Uso

Una vez instalado, ejecuta **somonger** directamente desde la terminal:

```bash
# Sin argumentos → muestra ayuda y lanza la GUI
somonger

# O con python directamente:
python3 somonger.py
```

---

## Módulo 1 — Explorador de directorios

Recorrido recursivo en árbol, clasificando cada entrada según tipo Unix.

```bash
somonger explore /home/usuario
```

**Tipos de archivo detectados:**
| Símbolo | Tipo |
|---------|------|
| `d` | Directorio |
| `-` | Archivo regular |
| `l` | Enlace simbólico |
| `c` | Dispositivo de caracteres |
| `b` | Dispositivo de bloques |
| `p` | FIFO / Named pipe |
| `s` | Socket |

---

## Módulo 2 — Navegador de archivos

Muestra atributos completos y permite operar sobre archivos y directorios.

```bash
# Ver contenido de un directorio con todos sus atributos
somonger nav /home/usuario/

# Navegar a un directorio (mismo resultado que arriba)
somonger nav --dir /home/usuario/

# Crear un fichero
somonger nav --rm /home/usuario/nombreArchivo

# Crear un directorio
somonger nav --touchDir /home/usuario/nuevoDirectorio

# Borrar un archivo o directorio
somonger nav --mk /home/usuario/directorioBorrar

# Copiar (se recuerda hasta un nuevo --cc o --cx)
somonger nav --cc /home/usuario/archivo

# Cortar (se recuerda hasta un nuevo --cc o --cx)
somonger nav --cx /home/usuario/archivo

# Pegar en la ruta dada
somonger nav --cv /home/usuario/nombreCopiadoDelArchivo
```

**Atributos mostrados por archivo:**
- Tamaño en KBs
- Número de inodo
- Permisos (rwx y octal)
- Propietario (usuario y grupo)
- Fechas de creación/acceso/modificación
- Número de enlaces duros

---

## Módulo 3 — Análisis estadístico

```bash
# Mostrar informe en terminal
somonger report /home/usuario

# Exportar a CSV (separado por ";" con dobles comillas)
somonger report /home/usuario --output informe.csv

# Exportar a TXT
somonger report /home/usuario --output informe.txt
```

**El informe incluye:**
- Número total de archivos por tipo
- Porcentaje de espacio utilizado del directorio
- Porcentaje de espacio en disco/partición
- Estimación del espacio libre en la partición
- Top 10 de extensiones de archivo

---

## Módulo 4 — Simulador de métodos de asignación

```bash
somonger sim /home/usuario/archivo.txt
```

Crea 3 particiones del **triple del tamaño** del archivo:

| Partición | Sistema | Método de asignación |
|-----------|---------|----------------------|
| `ext2`    | Linux   | Nodos-i (inode) — 12 directos + simple + doble + triple indirecto |
| `ext4`    | Linux   | Nodos-i extendido con extents |
| `fat32`   | FAT     | Lista enlazada con índice en memoria (FAT Table) |

**Para cada partición muestra:**
- Espacio ocupado en KBs
- Espacio ocupado en sectores (sector = 512 bytes)
- Espacio libre en la partición

**Modos de funcionamiento:**
1. **Real** (si están disponibles `dd`, `mkfs.ext2`, `mkfs.ext4`, `mkfs.fat`, `mount`): crea imágenes reales de disco
2. **Simulación lógica** (modo fallback): simula matemáticamente las estructuras de datos (bitmap, FAT table, inode table)
3. **VeraCrypt** (si no hay espacio libre): usa contenedores cifrados

### Para habilitar particiones reales:
```bash
sudo apt install e2fsprogs dosfstools util-linux
```

---

## Interfaz Gráfica

La GUI se lanza automáticamente con cualquier comando. Para usar solo CLI:

```bash
somonger nav --dir /home/usuario/ --no-gui
```

Para lanzar solo la GUI:
```bash
somonger --gui
```

---

## Estructura del proyecto

```
somonger/
├── somonger         # Script bash ejecutable (comando de terminal)
├── somonger.py      # Punto de entrada Python (CLI + GUI)
├── requirements.txt # Dependencias pip
├── README.md        # Esta documentación
├── modules/
│   ├── __init__.py
│   ├── explorer.py  # Módulo 1: Explorador
│   ├── navigator.py # Módulo 2: Navegador
│   ├── reporter.py  # Módulo 3: Reporter estadístico
│   └── simulator.py # Módulo 4: Simulador de asignación
└── gui/
    ├── __init__.py
    ├── app.py           # Ventana principal
    ├── explorer_tab.py  # GUI Módulo 1
    ├── navigator_tab.py # GUI Módulo 2
    ├── reporter_tab.py  # GUI Módulo 3
    └── simulator_tab.py # GUI Módulo 4
```

---

## Comandos de referencia rápida

```bash
chmod +x somonger && export PATH="$PATH:$(pwd)"
somonger explore /home
somonger nav /home
somonger nav --dir /home/usuario
somonger report /home --output report.csv
somonger sim /home/usuario/archivo.txt
```
