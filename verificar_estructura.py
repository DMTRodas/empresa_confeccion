import os

def verificar_estructura():
    estructura_requerida = [
        'templates/',
        'templates/base.html',
        'templates/index.html', 
        'templates/login.html',
        'templates/admin/',
        'templates/admin/dashboard.html',
        'templates/admin/productos.html',
        'templates/admin/clientes.html',
        'templates/admin/inventario.html',
        'templates/admin/ordenes.html',
        'templates/cliente/',
        'templates/cliente/portal.html',
        'templates/empleado/',
        'templates/empleado/portal.html'
    ]
    
    print("🔍 Verificando estructura de carpetas...")
    
    for item in estructura_requerida:
        if os.path.exists(item):
            print(f"✅ {item}")
        else:
            print(f"❌ FALTANTE: {item}")
    
    print("\n📊 Resumen:")
    archivos = [f for f in estructura_requerida if os.path.exists(f)]
    print(f"Archivos encontrados: {len(archivos)}/{len(estructura_requerida)}")

if __name__ == "__main__":
    verificar_estructura()