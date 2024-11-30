import socket  # Importamos el módulo para trabajar con sockets.
import threading  # Importamos threading para manejar múltiples conexiones simultáneamente.

# Constantes para definir el host, puerto y tamaño del encabezado.
HOST = "127.0.0.1"  # Dirección IP en la que el servidor escuchará (localhost).
PORT = 5000  # Puerto en el que el servidor estará disponible.
HEADER_SIZE = 10  # Tamaño del encabezado para definir la longitud de los mensajes.


# Definimos la clase principal que maneja el servidor.
class Server:
    def __init__(
        self,
        on_client_connected=None,  # Callback para manejar eventos cuando un cliente se conecta.
        on_client_disconnected=None,  # Callback para manejar eventos de desconexión.
        on_message_received=None,  # Callback para manejar mensajes recibidos.
        on_error=None,  # Callback para manejar errores.
    ):
        """
        Constructor del servidor. Configura las variables y crea el socket.
        """
        self.connections = []  # Lista para almacenar todas las conexiones activas.
        self.aliases = (
            {}
        )  # Diccionario para asociar conexiones con alias de los clientes.
        self.on_client_connected = on_client_connected
        self.on_client_disconnected = on_client_disconnected
        self.on_message_received = on_message_received
        self.on_error = on_error

        # Configuración del socket.
        try:
            self.sock = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM
            )  # Creamos el socket TCP.
            self.sock.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
            )  # Permite reutilizar el socket.
            self.sock.bind(
                (HOST, PORT)
            )  # Vinculamos el socket a la IP y el puerto especificados.
            self.sock.listen()  # Colocamos el socket en modo de escucha.
        except Exception as e:
            self._handle_error(
                f"Error al inicializar el servidor: {e}"
            )  # Manejo de errores en la configuración.

    def run(self):
        """Ejecuta el servidor y espera conexiones entrantes."""
        try:
            while True:
                conn, addr = self.sock.accept()  # Acepta una conexión entrante.
                self._handle_new_connection(conn, addr)  # Maneja la nueva conexión.
        except Exception as e:
            self._handle_error(f"Error al ejecutar el servidor: {e}")

    def _handle_new_connection(self, conn, addr):
        """Maneja una nueva conexión de cliente."""
        try:
            # Recibe el encabezado que indica la longitud del alias.
            data_header = conn.recv(HEADER_SIZE).decode("utf-8").strip()
            if (
                not data_header
            ):  # Si no se recibe un encabezado válido, cierra la conexión.
                raise ValueError(
                    f"Encabezado vacío recibido para alias desde {addr}. Cerrando conexión."
                )
            alias_length = int(
                data_header
            )  # Convierte el encabezado en la longitud esperada.
            alias = (
                conn.recv(alias_length).decode("utf-8").strip()
            )  # Recibe el alias del cliente.

            if not alias:  # Si no se recibe un alias válido, cierra la conexión.
                raise ValueError(
                    f"Alias vacío recibido desde {addr}. Cerrando conexión."
                )

            # Almacena el alias y la conexión.
            self.aliases[conn] = alias
            self.connections.append(conn)

            # Llama al callback para notificar la conexión.
            if self.on_client_connected:
                self.on_client_connected(conn, addr, alias)

            # Si el alias no es 'chat_user', notifica a los demás usuarios.
            if alias != "chat_user":
                self._broadcast_system_message(f"{alias} se ha unido al chat.")

            # Inicia un hilo para manejar la comunicación con este cliente.
            threading.Thread(
                target=self._handle_client, args=(conn,), daemon=True
            ).start()
        except Exception as e:
            self._handle_error(str(e))
            conn.close()  # Cierra la conexión en caso de error.

    def _handle_client(self, conn):
        """Maneja la comunicación con un cliente."""
        alias = self.aliases.get(conn, "Desconocido")  # Obtiene el alias del cliente.
        try:
            while True:
                # Recibe el encabezado del mensaje.
                data_header = conn.recv(HEADER_SIZE)
                if (
                    not data_header
                ):  # Si no hay datos, se asume que el cliente se desconectó.
                    break

                # Recibe el contenido del mensaje basado en el encabezado.
                length = int(data_header.strip())
                data = conn.recv(length).decode("utf-8")

                # Llama al callback para manejar el mensaje recibido.
                if self.on_message_received:
                    self.on_message_received(alias, data)

                # Envía el mensaje a todos los demás clientes.
                self._broadcast_message(alias, data, conn)
        except Exception as e:
            self._handle_error(f"Error manejando mensajes de {alias}: {e}")
        finally:
            self._disconnect_client(conn)  # Desconecta al cliente si ocurre un error.

    def _broadcast_message(self, alias, message, sender_conn):
        """Envía un mensaje a todos los clientes excepto al remitente."""
        alias_message = (
            f"{alias}|{message}"  # Formatea el mensaje con alias y contenido.
        )
        for connection in self.connections:
            if connection != sender_conn:  # Evita enviar el mensaje al remitente.
                try:
                    # Prepara el encabezado y envía el mensaje.
                    header = f"{len(alias_message):<{HEADER_SIZE}}".encode("utf-8")
                    connection.send(header + alias_message.encode("utf-8"))
                except Exception as e:
                    self._handle_error(f"Error al retransmitir mensaje: {e}")

    def _broadcast_system_message(self, message):
        """Envía un mensaje del sistema a todos los clientes conectados."""
        alias = "Sistema"  # Define el alias para los mensajes del sistema.
        formatted_message = f"{alias}|{message}"  # Formatea el mensaje del sistema.
        for connection in self.connections:
            try:
                # Prepara el encabezado y envía el mensaje.
                header = f"{len(formatted_message):<{HEADER_SIZE}}".encode("utf-8")
                connection.send(header + formatted_message.encode("utf-8"))
            except Exception as e:
                self._handle_error(f"Error al enviar mensaje del sistema: {e}")

    def _disconnect_client(self, conn):
        """Desconecta a un cliente del servidor."""
        alias = self.aliases.pop(conn, "Desconocido")  # Obtiene el alias del cliente.
        if conn in self.connections:
            self.connections.remove(conn)  # Elimina la conexión de la lista.
        conn.close()  # Cierra el socket.

        # Si el alias no es 'chat_user', notifica la desconexión a los demás usuarios.
        if alias != "chat_user":
            self._broadcast_system_message(f"{alias} se ha desconectado.")

        # Llama al callback para notificar la desconexión.
        if self.on_client_disconnected:
            self.on_client_disconnected(alias)

    def _handle_error(self, error_message):
        """Maneja errores y los pasa al callback correspondiente."""
        if self.on_error:
            self.on_error(error_message)
