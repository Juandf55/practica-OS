#!/bin/bash
# =========================================================
# Instalador de dependencias para SOMONGER
# Útil para máquinas virtuales recién creadas o vacías
# =========================================================

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36m  Instalando dependencias de SOMONGER \033[0m"
echo -e "\033[1;36m========================================\033[0m"
echo ""

# 1. Actualizar repositorios
echo "1. Actualizando repositorios (necesitará contraseña de administrador)..."
sudo apt-get update

# 2. Instalar Python y Tkinter (Interfaz gráfica)
#    Y Python3-Matplotlib (Para evitar el error de pip en Ubuntu nuevo)
echo ""
echo "2. Instalando Python3, Tkinter y Matplotlib..."
sudo apt-get install -y python3 python3-tk python3-matplotlib

# 3. Instalar herramientas del sistema de archivos para el Simulador
#    e2fsprogs -> contiene mkfs.ext2 y mkfs.ext4
#    dosfstools -> contiene mkfs.fat (FAT32)
echo ""
echo "3. Instalando utilidades de disco (mkfs)..."
sudo apt-get install -y e2fsprogs dosfstools

echo ""
echo -e "\033[1;32m[✓] ¡INSTALACIÓN COMPLETADA!\033[0m"
echo "Ya puedes ejecutar el programa normalmente:"
echo "  ./somonger"
echo ""
