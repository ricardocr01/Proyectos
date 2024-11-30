import socket  # Importamos el módulo socket para manejar la conexión cliente-servidor.
import threading  # Importamos threading para manejar el cliente y recibir mensajes simultáneamente.

# Constantes globales
PORT = 5000  # Puerto en el que se conectará el cliente.
HEADER_SIZE = 10  # Tamaño del encabezado que indica la longitud del mensaje.


# Definimos la clase `Client` que representa al cliente TCP.
class Client:
    def __init__(
        self, address, username="chat_user", on_message_received=None, on_error=None
    ):
        """
        Inicializa el cliente TCP.

        :param address: Dirección IP del servidor al que se conectará el cliente.
        :param username: Alias o nombre del usuario en el chat.
        :param on_message_received: Callback para manejar mensajes recibidos del servidor.
        :param on_error: Callback para manejar errores durante la ejecución.
        """
        self.username = username  # Guardamos el alias del usuario.
        self.address = address  # Dirección IP del servidor.
        self.on_message_received = (
            on_message_received  # Callback para procesar mensajes recibidos.
        )
        self.on_error = on_error  # Callback para manejar errores.
        self.connected = False  # Bandera para indicar si el cliente está conectado.

        try:
            # Creamos un socket TCP para la conexión cliente-servidor.
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Intentamos conectarnos al servidor en la dirección y puerto proporcionados.
            self.sock.connect((address, PORT))
            self.connected = True  # Marcamos como conectado si no hay errores.

            # Si la conexión es exitosa, enviamos el alias del cliente al servidor.
            if self.connected:
                # Creamos el encabezado con la longitud del alias.
                alias_header = f"{len(self.username):<{HEADER_SIZE}}".encode("utf-8")
                # Codificamos el alias y lo enviamos al servidor.
                alias_data = self.username.encode("utf-8")
                self.sock.send(alias_header + alias_data)

            # Iniciamos un hilo para recibir mensajes desde el servidor.
            self.receive_thread = threading.Thread(
                target=self.receive_messages, daemon=True
            )
            self.receive_thread.start()  # Ejecutamos el hilo en segundo plano.

        except Exception as e:
            # Si hay un error durante la conexión, llamamos al callback de error.
            self._handle_error(f"Error al conectar al servidor: {e}")

    def receive_messages(self):
        """
        Escucha mensajes del servidor y los pasa al callback `on_message_received`.
        """
        while self.connected:  # Seguimos recibiendo mientras estemos conectados.
            try:
                # Leemos el encabezado del mensaje para obtener la longitud del contenido.
                data_header = self.sock.recv(HEADER_SIZE)
                if (
                    not data_header
                ):  # Si el encabezado está vacío, el servidor cerró la conexión.
                    self._handle_error("Conexión cerrada por el servidor")
                    break

                # Convertimos el encabezado a un entero para saber el tamaño del mensaje.
                length = int(data_header.strip())
                # Leemos el contenido del mensaje basado en la longitud recibida.
                data = self.sock.recv(length).decode("utf-8")

                # Verificamos si el mensaje tiene el formato `alias|message`.
                if "|" in data:
                    alias, message = data.split(
                        "|", 1
                    )  # Dividimos el mensaje en alias y contenido.
                else:
                    alias, message = (
                        "Desconocido",  # Si el formato no es el esperado, asignamos un alias por defecto.
                        data,
                    )

                # Si tenemos un callback para manejar mensajes, lo llamamos con alias y mensaje.
                if self.on_message_received:
                    self.on_message_received(alias, message)

            except Exception as e:
                # Si hay un error durante la recepción, lo manejamos y salimos del bucle.
                if self.connected:
                    self._handle_error(f"Error recibiendo mensajes: {e}")
                break

    def send_message(self, message):
        """
        Envía un mensaje al servidor.
        """
        try:
            if self.connected:  # Solo enviamos mensajes si estamos conectados.
                # Creamos el encabezado con la longitud del mensaje.
                header = f"{len(message):<{HEADER_SIZE}}".encode("utf-8")
                # Codificamos el mensaje y lo enviamos junto con el encabezado.
                self.sock.send(header + message.encode("utf-8"))
            else:
                # Si no estamos conectados, enviamos un error al callback.
                self._handle_error("No está conectado al servidor")
        except Exception as e:
            # Si ocurre un error al enviar el mensaje, lo manejamos con el callback.
            self._handle_error(f"Error enviando mensaje: {e}")

    def close(self):
        """
        Cierra la conexión con el servidor.
        """
        self.connected = False  # Cambiamos el estado a desconectado.
        try:
            self.sock.close()  # Cerramos el socket para liberar recursos.
        except Exception as e:
            # Si hay un error al cerrar el socket, lo manejamos.
            self._handle_error(f"Error al cerrar la conexión: {e}")

    def _handle_error(self, error_message):
        """
        Maneja errores llamando al callback `on_error` si está definido.
        """
        if self.on_error:  # Si hay un callback definido para errores, lo llamamos.
            self.on_error(error_message)
