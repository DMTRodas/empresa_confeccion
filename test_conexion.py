import cx_Oracle

def test_conexion():
    try:
        print("🔍 Probando conexión a Oracle...")
        
        # USAR TUS CREDENCIALES REALES
        dsn = cx_Oracle.makedsn('localhost', '1521', service_name='XE')
        conn = cx_Oracle.connect(
            user='system',  # CAMBIAR por tu usuario
            password='root',  # CAMBIAR por tu password
            dsn=dsn
        )
        
        print("✅ ¡Conexión exitosa a Oracle!")
        
        # Probar consulta básica
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM producto")
        resultado = cursor.fetchone()
        print(f"📊 Productos en BD: {resultado[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_conexion()