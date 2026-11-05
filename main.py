import json
from pathlib import Path

def funcion_prueba():
    pass

def crear_estructura_proyecto():
    # Directorio raíz del proyecto
    base_dir = Path("sistema-supermercado")
    
    # Lista de subdirectorios
    directorios = [
        "interfaz",
        "negocio",
        "persistencia",
        "datos",
        "documentacion"
    ]
    
    # Lista de archivos de código y texto
    archivos_generales = [
        "main.py",
        "interfaz/__init__.py",
        "interfaz/vistas.py",
        "interfaz/utilidades_ui.py",
        "negocio/__init__.py",
        "negocio/inventario.py",
        "negocio/ventas.py",
        "negocio/caja.py",
        "negocio/validaciones.py",
        "persistencia/__init__.py",
        "persistencia/gestor_json.py",
        "documentacion/README.md",
        "documentacion/pruebas.pdf",
        "documentacion/manual_usuario.pdf",
        "documentacion/diagrama_flujo.pdf"
    ]
    
    # Lista de archivos JSON persistentes
    archivos_json = [
        "datos/productos.json",
        "datos/ventas.json",
        "datos/caja.json"
    ]

    # 1. Crear el directorio base y los subdirectorios
    for directorio in directorios:
        ruta_dir = base_dir / directorio
        ruta_dir.mkdir(parents=True, exist_ok=True)
        print(f"Directorio creado: {ruta_dir}")

    # 2. Crear los archivos de Python y documentación (vacíos)
    for archivo in archivos_generales:
        ruta_archivo = base_dir / archivo
        ruta_archivo.touch()
        print(f"Archivo creado: {ruta_archivo}")

    # 3. Crear los archivos JSON inicializados con arreglos vacíos
    for archivo in archivos_json:
        ruta_archivo = base_dir / archivo
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print(f"Archivo JSON inicializado: {ruta_archivo}")

    print("\n¡La estructura del proyecto monolítico se ha creado con éxito!")

if __name__ == "__main__":
    crear_estructura_proyecto()