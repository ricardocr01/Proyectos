import customtkinter as ctk  # Biblioteca para la interfaz gráfica personalizable.
from client import Client  # Clase para manejar las funcionalidades del cliente TCP.
import server_manager  # Módulo para manejar la lógica del servidor.
from datetime import datetime  # Manejo de fechas y horas.
import threading  # Biblioteca para manejar hilos.

class TCPChat(ctk.CTk):
    def __init__(self):
        """
        Constructor de la clase principal de la aplicación de chat TCP.
        Configura la ventana principal y todos los elementos gráficos.
        """
        super().__init__()
        self.title("Chat TCP/IP App")  # Título de la ventana principal.
        self.geometry("500x600")  # Tamaño inicial de la ventana.
        self.resizable(False, False)  # Evita redimensionar la ventana.
        ctk.set_appearance_mode("dark")  # Configura el tema oscuro para la interfaz.

        # Variables internas.
        self.client = None  # Cliente TCP, inicializado como None.
        self.connected = False  # Bandera para saber si el cliente está conectado.
        self.last_message_date = None  # Para almacenar la fecha del último mensaje recibido.
        self.provisional_text = "Escriba un mensaje"  # Texto placeholder para la caja de entrada.

        # Configuración de los tres marcos principales.
        self.frm1 = ctk.CTkFrame(self)  # Primer marco: configuración de conexión.
        self.frm2 = ctk.CTkScrollableFrame(self)  # Segundo marco: área de mensajes.
        self.frm3 = ctk.CTkFrame(self)  # Tercer marco: entrada de texto y botón enviar.

        # Posicionamos los marcos en la ventana.
        self.frm1.pack(padx=5, pady=5, fill="x")  # Marco superior.
        self.frm2.pack(padx=5, pady=(5, 0), fill="both", expand=True)  # Marco central.
        self.frm3.pack(padx=5, pady=(0, 5), fill="x")  # Marco inferior.

        # Configuración del diseño del marco superior (frm1).
        self.frm1.columnconfigure(0, weight=1)  # Configuración de la columna 0
        self.frm1.columnconfigure(1, weight=2)  # Configuración de la columna 1
        self.frm1.columnconfigure(2, weight=1)  # Configuración de la columna 2
        self.frm1.columnconfigure(3, weight=2)  # Configuración de la columna 3
        self.frm1.columnconfigure(4, weight=1)  # Configuración de la columna 4

        # Configuración de los elementos de entrada y botones en frm1.
        self.lblHost = ctk.CTkLabel(self.frm1, text="Dirección IP:", text_color="white")  # Etiqueta para la IP.
        self.entryHost = ctk.CTkEntry(self.frm1, placeholder_text="127.0.0.1")  # Entrada para la IP.
        self.lblPort = ctk.CTkLabel(self.frm1, text="Puerto:", text_color="white")  # Etiqueta para el puerto.
        self.entryPort = ctk.CTkEntry(self.frm1, placeholder_text="5000")  # Entrada para el puerto.
        self.lblAlias = ctk.CTkLabel(self.frm1, text="Alias:", text_color="white")  # Etiqueta para el alias.
        self.entryAlias = ctk.CTkEntry(self.frm1, placeholder_text="chat_user")  # Entrada para el alias.
        self.btnConnect = ctk.CTkButton(self.frm1, text="Conectar", command=self.toggle_connection)  # Botón para conectar.

        # Posicionamiento de los elementos en el grid de frm1.
        self.lblHost.grid(row=0, column=0, padx=5, pady=5, sticky="e")  # Etiqueta de IP.
        self.entryHost.grid(row=0, column=1, padx=5, pady=5, sticky="ew")  # Entrada de IP.
        self.lblPort.grid(row=0, column=2, padx=5, pady=5, sticky="e")  # Etiqueta de puerto.
        self.entryPort.grid(row=0, column=3, padx=5, pady=5, sticky="ew")  # Entrada de puerto.
        self.lblAlias.grid(row=1, column=0, padx=5, pady=5, sticky="e")  # Etiqueta de alias.
        self.entryAlias.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")  # Entrada de alias.
        self.btnConnect.grid(row=1, column=3, padx=5, pady=5, sticky="ew")  # Botón de conectar.

        # Configuración del área de entrada de texto y botón enviar en frm3.
        self.inText = ctk.CTkTextbox(self.frm3, height=50, corner_radius=10, wrap="word")  # Área de entrada de texto.
        self.inText.insert("0.0", self.provisional_text)  # Inserta el texto placeholder inicial.
        self.inText.configure(state="normal", fg_color="#333333", text_color="gray", undo=True)  # Configuración de estilo.
        self.btnSend = ctk.CTkButton(self.frm3, text="Enviar", command=self.send_message)  # Botón de enviar.
        self.btnSend.grid_forget()  # Inicialmente ocultamos el botón.

        # Posicionamiento del área de texto en frm3.
        self.inText.grid(row=0, column=0, padx=5, pady=5, sticky="ew")  # Configuración de área de entrada.
        self.frm3.columnconfigure(0, weight=1)  # Configuración para que ocupe todo el espacio horizontal.

        # Eventos para manejar la interacción del área de texto.
        self.inText.bind("<FocusIn>", self.clear_texprov)  # Limpia el texto provisional al enfocar.
        self.inText.bind("<FocusOut>", self.restore_texprov)  # Restaura el texto provisional al desenfocar.
        self.inText.bind("<KeyRelease>", self.toggle_send_button)  # Habilita el botón enviar si hay texto.
        self.inText.bind("<Return>", self.send_message_from_enter)  # Envía el mensaje al presionar Enter.

        # Configuramos el cierre de la ventana principal.
        self.protocol("WM_DELETE_WINDOW", self.close_application)

    def toggle_connection(self):
        """
        Conecta o desconecta al cliente dependiendo de su estado actual.
        """
        if not self.connected:  # Si no está conectado.
            host = self.entryHost.get() or "127.0.0.1"  # Obtiene la IP, o usa la predeterminada.
            port = int(self.entryPort.get() or 5000)  # Obtiene el puerto, o usa el predeterminado.
            alias = self.entryAlias.get().strip()  # Obtiene el alias ingresado.

            if not alias:  # Si el alias está vacío, muestra un error.
                self.display_center_message("Error: El alias no puede estar vacío.")
                return

            # Verifica si el servidor está en ejecución.
            if server_manager.is_server_running(host, port):
                # Inicia un hilo para manejar la conexión del cliente.
                threading.Thread(target=self.start_client, args=(host, port, alias), daemon=True).start()
            else:
                # Muestra un error si el servidor no está en ejecución.
                self.display_center_message("Servidor no encontrado. Inicie el servidor primero.")
        else:
            # Si ya está conectado, cierra la conexión.
            self.close_connection()


    def start_client(self, host, port, alias):
        """
        Inicia el cliente y establece la conexión con el servidor.
        """
        try:
            # Crea una instancia de la clase Client para conectarse al servidor.
            self.client = Client(
                host,
                alias,
                on_message_received=self.handle_client_message,  # Callback para manejar mensajes recibidos.
                on_error=self.handle_client_error,  # Callback para manejar errores.
            )
            self.connected = True  # Marca al cliente como conectado.

            # Deshabilita las entradas de configuración para evitar cambios durante la conexión.
            self.entryHost.configure(state="disabled")
            self.entryPort.configure(state="disabled")
            self.entryAlias.configure(state="disabled")

            # Cambia el texto del botón para indicar que ahora sirve para desconectar.
            self.btnConnect.configure(text="Desconectar")

            # Habilita el área de entrada de mensajes.
            self.inText.configure(state="normal")

            # Muestra un mensaje centrado indicando que la conexión fue exitosa.
            self.display_center_message(f"Conectado a {host}:{port} como {alias}")
        except Exception as e:
            # Muestra un mensaje de error si algo falla al conectar.
            self.display_center_message(f"Error al conectar: {e}")

    def send_message(self):
        """
        Envía un mensaje al servidor.
        """
        if self.client and self.connected:  # Asegura que el cliente esté conectado.
            msg = self.inText.get("0.0", "end").strip()  # Obtiene el mensaje ingresado en el área de texto.
            if msg:  # Solo envía si el mensaje no está vacío.
                try:
                    # Llama al método de la clase Client para enviar el mensaje al servidor.
                    self.client.send_message(msg)

                    # Muestra el mensaje en la interfaz como enviado por el usuario.
                    self.log_message(msg, received=False)

                    # Limpia el área de entrada de texto.
                    self.inText.delete("0.0", "end")
                except Exception as e:
                    # Muestra un mensaje de error si no se pudo enviar.
                    self.log_message(f"Error enviando mensaje: {e}", received=True)

    def send_message_from_enter(self, event):
        """
        Envía un mensaje al presionar la tecla Enter.
        """
        self.send_message()  # Llama al método de enviar mensaje.
        return "break"  # Evita que se inserte un salto de línea en el área de texto.

    def log_message(self, message, received):
        """
        Muestra un mensaje en el historial de mensajes.
        """
        # Llama a un método interno para actualizar la interfaz en el hilo principal.
        self.after(0, self._log_message_ui, message, received)

    def _log_message_ui(self, message, received):
        """
        Muestra el mensaje recibido o enviado en el área de historial.
        """
        # Obtiene la fecha y hora actuales.
        current_date = datetime.now().strftime("%d/%m/%Y")
        current_time = datetime.now().strftime("%H:%M")

        # Si la fecha ha cambiado, muestra un separador de fecha en el historial.
        if self.last_message_date != current_date:
            date_label = ctk.CTkLabel(self.frm2, text=current_date, justify="center", anchor="center", width=500)
            date_label.pack(pady=5)
            self.last_message_date = current_date

        # Configura el mensaje en un marco con estilo diferente si es recibido o enviado.
        msg_frame = ctk.CTkFrame(self.frm2, corner_radius=15, fg_color="#0078D7" if not received else "#4CAF50")
        msg_label = ctk.CTkLabel(msg_frame, text=message, wraplength=400, justify="left", font=("Arial", 12))
        time_label = ctk.CTkLabel(msg_frame, text=current_time, font=("Arial", 10), text_color="lightgray", anchor="e")

        # Añade los elementos de mensaje y hora al marco.
        msg_label.pack(padx=10, pady=(5, 0), fill="x")
        time_label.pack(padx=10, pady=(0, 5), anchor="e")

        # Añade el marco del mensaje al área de historial.
        msg_frame.pack(padx=10, pady=5, anchor="e" if not received else "w")

        # Asegura que el área de historial haga scroll hasta el final.
        self.frm2.update_idletasks()
        self.frm2._parent_canvas.yview_moveto(1.0)

    def clear_texprov(self, event=None):
        """
        Limpia el texto provisional del área de entrada al hacer clic o escribir.
        """
        if self.inText.get("0.0", "end").strip() == self.provisional_text:
            self.inText.delete("0.0", "end")  # Borra el texto provisional.
            self.inText.configure(text_color="white")  # Cambia el color del texto a blanco para entradas.

    def restore_texprov(self, event=None):
        """
        Restaura el texto provisional si el área de entrada queda vacía.
        """
        if not self.inText.get("0.0", "end").strip():  # Si el área está vacía.
            self.inText.insert("0.0", self.provisional_text)  # Inserta el texto provisional.
            self.inText.configure(text_color="gray")  # Cambia el color del texto a gris.

    def toggle_send_button(self, event=None):
        """
        Muestra u oculta el botón de enviar dependiendo del contenido del área de entrada.
        """
        content = self.inText.get("0.0", "end").strip()  # Obtiene el contenido actual del área de texto.
        if content and content != self.provisional_text:  # Si hay texto y no es el placeholder.
            self.btnSend.grid(row=0, column=1, padx=5, pady=5)  # Muestra el botón.
        else:
            self.btnSend.grid_forget()  # Oculta el botón.

    def display_center_message(self, text):
        """
        Muestra un mensaje centrado en el historial (usado para mensajes del sistema).
        """
        self.after(0, self._display_center_message_ui, text)  # Llama al método en el hilo principal.

    def _display_center_message_ui(self, text):
        """
        Muestra un mensaje centrado en el área de historial.
        """
        center_label = ctk.CTkLabel(self.frm2, text=text, font=("Arial", 12, "bold"), justify="center", wraplength=450)
        center_label.pack(pady=10)  # Añade el mensaje al área de historial con un espaciado.

    def handle_client_message(self, alias, message):
        """
        Manejador para mensajes recibidos del servidor.
        """
        if alias == "Sistema":  # Si el mensaje proviene del sistema.
            self.display_center_message(message)  # Lo muestra centrado.
        else:  # Si es un mensaje de otro usuario.
            self.log_message(f"{alias}: {message}", received=True)  # Lo muestra en el historial.

    def handle_client_error(self, error_message):
        """
        Manejador para errores relacionados con el cliente.
        """
        self.log_message(f"Error del cliente: {error_message}", received=True)

    def close_connection(self):
        """
        Cierra la conexión con el servidor.
        """
        if self.connected:
            self.connected = False  # Cambia el estado del cliente a desconectado.
            if self.client:
                try:
                    self.client.close()  # Cierra la conexión del cliente.
                    self.client = None  # Elimina la referencia al cliente.
                except Exception as e:
                    self.log_message(f"Error al cerrar la conexión: {e}", received=True)

            # Rehabilita las entradas de configuración para permitir cambios.
            self.entryHost.configure(state="normal")
            self.entryPort.configure(state="normal")
            self.entryAlias.configure(state="normal")

            self.btnConnect.configure(text="Conectar")  # Cambia el texto del botón a "Conectar".
            self.inText.configure(state="disabled")  # Desactiva el área de texto.
            self.display_center_message("Conexión cerrada.")  # Muestra un mensaje indicando la desconexión.

    def close_application(self):
        """
        Cierra la aplicación.
        """
        self.close_connection()  # Cierra la conexión si está activa.
        self.destroy()  # Cierra la ventana principal.

if __name__ == "__main__":
    app = TCPChat()  # Crea una instancia de la aplicación.
    app.mainloop()  # Inicia el bucle principal de la interfaz gráfica.
