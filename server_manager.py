import threading  # Importamos threading para manejar el servidor en un hilo separado.
import socket  # Importamos socket para las conexiones TCP/IP.
from server import Server  # Importamos la clase Server desde el módulo server.

# Variables globales para manejar la instancia del servidor y su hilo de ejecución.
_server_instance = None  # Variable para almacenar la instancia del servidor.
_server_thread = None  # Variable para almacenar el hilo del servidor.

def is_server_running(host="127.0.0.1", port=5000):
    """
    Verifica si el servidor está activo intentando conectarse a su puerto.

    :param host: Dirección IP donde se ejecuta el servidor.
    :param port: Puerto donde se ejecuta el servidor.
    :return: True si el servidor está activo, False de lo contrario.
    """
    try:
        # Intentamos conectarnos al servidor con un timeout de 2 segundos.
        test_sock = socket.create_connection((host, port), timeout=2)
        test_sock.close()  # Cerramos el socket de prueba si la conexión fue exitosa.
        return True
    except (ConnectionRefusedError, socket.timeout):
        # Si no podemos conectar, asumimos que el servidor no está corriendo.
        return False

def start_server(on_client_connected, on_client_disconnected, on_message_received, on_error, host="127.0.0.1", port=5000):
    """
    Inicia el servidor en un hilo separado si aún no está en ejecución.

    :param on_client_connected: Callback para manejar nuevos clientes conectados.
    :param on_client_disconnected: Callback para manejar clientes desconectados.
    :param on_message_received: Callback para manejar mensajes recibidos.
    :param on_error: Callback para manejar errores.
    :param host: Dirección IP del servidor.
    :param port: Puerto del servidor.
    """
    global _server_instance, _server_thread

    # Si el hilo del servidor ya está activo, no iniciamos otro.
    if _server_thread and _server_thread.is_alive():
        print("[DEBUG] El servidor ya está en ejecución.")
        return

    # Creamos una nueva instancia del servidor, pasando los callbacks correspondientes.
    _server_instance = Server(
        on_client_connected=on_client_connected,
        on_client_disconnected=on_client_disconnected,
        on_message_received=on_message_received,
        on_error=on_error,
    )

    # Creamos un hilo separado para ejecutar el servidor.
    _server_thread = threading.Thread(target=_server_instance.run, daemon=True)
    _server_thread.start()  # Iniciamos el hilo del servidor.
    print(f"[DEBUG] Servidor iniciado en {host}:{port}.")

def stop_server():
    """
    Detiene el servidor cerrando el socket y el hilo del servidor.
    """
    global _server_instance, _server_thread

    if _server_instance:
        _server_instance.sock.close()  # Cerramos el socket del servidor.
        print("[DEBUG] Servidor detenido.")
    if _server_thread:
        _server_thread.join(timeout=1)  # Esperamos a que el hilo termine.

# Callbacks predeterminados para manejar eventos del servidor.
def on_client_connected(conn, addr, alias):
    """
    Callback que se ejecuta cuando un cliente se conecta al servidor.

    :param conn: Objeto de socket del cliente.
    :param addr: Dirección del cliente.
    :param alias: Alias o nombre del cliente.
    """
    print(f"[INFO] Cliente conectado: {alias} desde {addr}")
    # Si el alias no es el predeterminado "chat_user", notificamos al sistema.
    if alias != "chat_user":
        print(f"[SYSTEM] {alias} se ha unido al chat.")

def on_client_disconnected(alias):
    """
    Callback que se ejecuta cuando un cliente se desconecta.

    :param alias: Alias o nombre del cliente desconectado.
    """
    print(f"[INFO] Cliente desconectado: {alias}")

def on_message_received(alias, message):
    """
    Callback que maneja los mensajes recibidos de los clientes.

    :param alias: Alias del cliente que envió el mensaje.
    :param message: Contenido del mensaje.
    """
    print(f"[MESSAGE] {alias}: {message}")

def on_error(message):
    """
    Callback para manejar errores ocurridos en el servidor.

    :param message: Mensaje de error.
    """
    print(f"[ERROR] {message}")

if __name__ == "__main__":
    """
    Punto de entrada principal (archivo que se ejecuta directamente)
    """
    print("[DEBUG] Ejecutando server_manager.")
    host = "127.0.0.1"  # Dirección IP del servidor.
    port = 5000  # Puerto del servidor.

    # Verificamos si el servidor ya está en ejecución.
    if is_server_running(host, port):
        print(f"[DEBUG] El servidor ya está en ejecución en {host}:{port}.")
    else:
        # Si no está corriendo, lo iniciamos.
        print(f"[DEBUG] Iniciando servidor en {host}:{port}...")
        start_server(
            on_client_connected=on_client_connected,
            on_client_disconnected=on_client_disconnected,
            on_message_received=on_message_received,
            on_error=on_error,
            host=host,
            port=port,
        )
        try:
            # Mantenemos el servidor activo hasta que el usuario ingrese "exit".
            print("[DEBUG] Escribe 'exit' para detener el servidor.")
            while True:
                cmd = input()  # Leemos el comando del usuario.
                if cmd.strip().lower() == "exit":
                    break
        except KeyboardInterrupt:
            # Si el usuario interrumpe con Ctrl+C, detenemos el servidor.
            print("[DEBUG] Deteniendo servidor...")
        finally:
            # Detenemos el servidor y salimos del programa.
            stop_server()
            print("[DEBUG] Servidor detenido.")
