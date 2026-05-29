# test_admin.py
import cx_Oracle

def diagnosticar_admin():
    try:
        # Conectar a la BD
        dsn = cx_Oracle.makedsn('localhost', '1521', service_name='XE')
        conn = cx_Oracle.connect(
            user='system',  # Tu usuario
            password='root',  # Tu password
            dsn=dsn
        )
        
        cursor = conn.cursor()
        
        print("=== DIAGNÓSTICO ADMIN ===")
        
        # 1. Ver todos los empleados
        cursor.execute("SELECT empleado_id, nombre, usuario, puesto, contrasena FROM empleado")
        print("\n1. TODOS LOS EMPLEADOS:")
        for row in cursor:
            print(f"   ID: {row[0]}, Nombre: {row[1]}, Usuario: {row[2]}, Puesto: {row[3]}, Contraseña: {row[4]}")
        
        # 2. Probar login específico de smiron
        cursor.execute("""
            SELECT empleado_id, nombre, puesto, usuario 
            FROM empleado 
            WHERE usuario = 'smiron' AND contrasena = 'contra123'
        """)
        resultado = cursor.fetchone()
        print(f"\n2. LOGIN SMIRON: {resultado}")
        
        if resultado:
            print(f"   Puesto encontrado: '{resultado[2]}'")
            print(f"   ¿Es admin? {resultado[2].lower() == 'admin'}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    diagnosticar_admin()