# Importo las librerías necesarias
import customtkinter as ctk  
import serial 
import serial.tools.list_ports 
import threading  
import time
from datetime import datetime

class SerialChat(ctk.CTk):
    def __init__(self):
        super().__init__()  
        self.title("Serial Chat App")  # Título de la ventana
        self.geometry("500x600")  # Tamaño de la ventana (ancho x alto)
        self.resizable(False, False)  # Fijo el tamaño de la ventana, no se puede redimensionar
        ctk.set_appearance_mode("dark")  # Modo oscuro para el diseño de la interfaz

        # Variables para manejar la conexión y el estado del chat
        self.serial_conn = None  # Objeto de conexión serial
        self.connected = False  # Bandera para verificar si hay conexión activa
        self.receive_thread = None  # Hilo para recibir datos
        self.stop_thread = False  # Controla cuándo detener el hilo de recepción
        self.last_message_date = None  # Última fecha de mensaje mostrado
        self.provisional_text = "Escriba un mensaje"  # Texto inicial de la caja de entrada

        # Defino los marcos de la interfaz
        self.frm1 = ctk.CTkFrame(self)  # Marco para configuración del puerto COM
        self.frm2 = ctk.CTkScrollableFrame(self)  # Marco para el historial de mensajes (con scroll)
        self.frm3 = ctk.CTkFrame(self)  # Marco para la caja de entrada y el botón de enviar

        # Ubico los marcos en la ventana
        self.frm1.pack(padx=5, pady=5, fill='x')  # Arriba, para la configuración
        self.frm2.pack(padx=5, pady=(5, 0), fill='both', expand=True)  # Centro, historial de mensajes
        self.frm3.pack(padx=5, pady=(0, 5), fill='x')  # Abajo, entrada de texto

        # --- Configuración del puerto COM (Frame 1) ---
        self.lblCOM = ctk.CTkLabel(self.frm1, text="Puerto COM:")  # Etiqueta para indicar puerto
        self.cboPort = ctk.CTkOptionMenu(self.frm1, values=self.get_com_ports())  # Menú desplegable con puertos disponibles
        self.btnConnect = ctk.CTkButton(self.frm1, text="Conectar", command=self.toggle_connection)  # Botón para conectar/desconectar

        # Organizo los elementos en una cuadrícula dentro del marco
        self.lblCOM.grid(row=0, column=0, padx=5, pady=5)
        self.cboPort.grid(row=0, column=1, padx=5, pady=5)
        self.btnConnect.grid(row=0, column=2, padx=5, pady=5)

        # --- Entrada de mensajes (Frame 3) ---
        self.inText = ctk.CTkTextbox(self.frm3, height=50, corner_radius=10, wrap="word")  # Caja de entrada para escribir mensajes
        self.inText.insert("0.0", self.provisional_text)  # Inserto el texto inicial
        self.inText.configure(state="normal", fg_color="#333333", text_color="gray", undo=True)  # Configuración visual
        self.btnSend = ctk.CTkButton(self.frm3, text="Enviar", command=self.send_message)  # Botón de enviar
        self.btnSend.grid_forget()  # Oculto el botón inicialmente hasta que haya texto

        # Organizo la caja de texto y el botón en el marco
        self.inText.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.frm3.columnconfigure(0, weight=1)  # Permito que la caja de texto se ajuste horizontalmente

        # --- Eventos para manejar el texto provisional y el botón enviar ---
        self.inText.bind("<FocusIn>", self.clear_texprov)  # Cuando hago clic en la caja, se borra el texto provisional
        self.inText.bind("<FocusOut>", self.restore_texprov)  # Si salgo de la caja sin escribir, se restaura el texto provisional
        self.inText.bind("<KeyRelease>", self.toggle_send_button)  # Muestra el botón de enviar cuando hay texto
        self.inText.bind("<Return>", self.send_message_from_enter)  # Permite enviar con la tecla Enter

        # Evento para cerrar la ventana correctamente
        self.protocol("WM_DELETE_WINDOW", self.close_application)

    # --- Funciones para manejar puertos COM ---
    def get_com_ports(self):
        """Obtiene una lista de puertos COM disponibles."""
        ports = serial.tools.list_ports.comports()  # Lista de puertos disponibles
        return [port.device for port in ports] or ["No hay puertos"]  # Devuelve los puertos o un mensaje si no hay ninguno

    def toggle_connection(self):
        """Establece o cierra la conexión al puerto COM."""
        if not self.connected:  # Si no está conectado
            try:
                port = self.cboPort.get()  # Obtengo el puerto seleccionado
                if port == "No hay puertos":  # Si no hay puertos, muestro un mensaje de error
                    self.display_center_message("Error: No hay puertos COM disponibles. Por favor, conecta un dispositivo.")
                    return

                # Intento establecer la conexión serial
                self.serial_conn = serial.Serial(port=port, baudrate=9600, timeout=2)
                self.connected = True  # Marco la conexión como activa
                self.stop_thread = False  # Habilito el hilo de recepción
                self.start_receive_thread()  # Inicio el hilo para recibir mensajes
                self.cboPort.configure(state='disabled')  # Desactivo el menú de selección de puertos
                self.btnConnect.configure(text="Desconectar")  # Cambio el texto del botón
                self.inText.configure(state='normal')  # Habilito la caja de entrada
                self.display_center_message(f"Conectado a {port}")  # Muestra un mensaje de conexión exitosa
            except Exception as e:
                # Si hay un error, lo muestro
                self.display_center_message(f"Error al conectar: {str(e)}. Revisa la conexión y los puertos disponibles.")
        else:
            # Si ya está conectado, cierro la conexión
            self.close_connection()

    # --- Funciones para manejar el hilo de recepción ---
    def start_receive_thread(self):
        """Inicia un hilo para recibir mensajes del puerto serial."""
        # El keyword daemon=True permite eliminar el thread si es que el programa principal se cierra
        self.receive_thread = threading.Thread(target=self.receive_messages, daemon=True)  # Defino el hilo como daemon
        self.receive_thread.start()  # Inicio el hilo

    def receive_messages(self):
        """Recibe mensajes del puerto serial y los muestra en el chat."""
        while not self.stop_thread:  # Mientras el hilo esté activo
            if self.serial_conn and self.connected: #Comprobamos el estado de la conexion serial
                try:
                    if self.serial_conn.in_waiting > 0:  # Verifico si hay datos en el buffer serial
                        message = self.serial_conn.readline().decode('utf-8').strip()  # Leo, decodifico, elimino espacios y saltos de linea al final del mensaje
                        self.log_message(message, received=True)  # Llamo a la funcion para mostrar en el chat como un mensaje recibido
                except Exception as e:
                    # Si hay un error al recibir, lo muestro
                    self.log_message(f"Error al recibir: {e}", received=True)
            time.sleep(0.1)  # Pausa breve para evitar sobrecarga del hilo

    # --- Funciones para enviar mensajes ---
    def send_message(self):
        """Envía un mensaje al puerto serial."""
        if self.serial_conn and self.connected: #Comprobamos el estado de la conexion serial
            msg = self.inText.get("0.0", "end").strip()  # Obtengo el mensaje de la caja de entrada
            if msg:  # Si el mensaje no está vacío
                try:
                    self.serial_conn.write((msg + '\n').encode("utf-8"))  # Envío el mensaje codificado al puerto serial
                    self.log_message(msg, received=False)  # Lo muestro en el chat como un mensaje enviado
                    self.inText.delete("0.0", "end")  # Limpio la caja de entrada
                except Exception as e:
                    # Si hay un error al enviar, lo muestro
                    self.log_message(f"Error al enviar: {e}", received=False)

    def send_message_from_enter(self, event):
        """Envia el mensaje al presionar Enter."""
        #Declaramos el parametro event, ya que el metodo bind envia ese parametro
        self.send_message()  # Llamo a la función de enviar
        #Evito que la tecla Enter agregue un salto de línea en la caja de texto
        return "break"  # Previene el salto de línea en la caja de texto

    # --- Registro de mensajes en el historial ---
    def log_message(self, message, received):
        """Muestra un mensaje en el frame de chat con diseño personalizado."""
        current_date = datetime.now().strftime("%d/%m/%Y")  # Obtengo la fecha actual
        current_time = datetime.now().strftime("%H:%M")  # Obtengo la hora actual

        # Si la fecha cambia, muestro una nueva etiqueta con la fecha
        if self.last_message_date != current_date:
            date_label = ctk.CTkLabel(self.frm2, text=current_date, justify="center", anchor="center", width=500)
            date_label.pack(pady=5)
            self.last_message_date = current_date

        # Configuro el marco y el texto del mensaje
        msg_frame = ctk.CTkFrame(self.frm2, corner_radius=15, fg_color="#0078D7" if not received else "#4CAF50")
        msg_label = ctk.CTkLabel(msg_frame, text=message, wraplength=400, justify="left", font=("Arial", 12))
        time_label = ctk.CTkLabel(msg_frame, text=current_time, font=("Arial", 10), text_color="lightgray", anchor="e")

        # Empaqueto el mensaje y la hora dentro del marco
        msg_label.pack(padx=10, pady=(5, 0), fill="x")
        time_label.pack(padx=10, pady=(0, 5), anchor="e")
        msg_frame.pack(padx=10, pady=5, anchor="e" if not received else "w")  # Alineo según sea enviado o recibido

        # Hago scroll automáticamente al final
        self.frm2.update_idletasks()   #Aseguro que los cambios visuales se procesen
        self.frm2._parent_canvas.yview_moveto(1.0)  #En el eje vertical, me muevo a la parte mas baja _0 inicio - 1 fin_

    # --- Mensajes de sistema ---
    def display_center_message(self, text):
        """Muestra un mensaje centrado en la ventana."""
        #Para evitar repetir codigo, creo una funcion encargada de mostrar mensajes al usuario
        center_label = ctk.CTkLabel(self.frm2, text=text, font=("Arial", 12, "bold"), justify="center", wraplength=450)
        center_label.pack(pady=10)

    # --- Texto provisional en la caja de entrada ---
    def clear_texprov(self, event):
        """Elimina el texto provisional al hacer clic o escribir."""
        #Declaramos el parametro event, ya que el metodo bind envia ese parametro
        if self.inText.get("0.0", "end").strip() == self.provisional_text:  #Compruebo si el texto provisional está siendo mostrado 
            self.inText.delete("0.0", "end")  
            #Configuramos el texto con color blanco, ya que es el usuario quien está escribiendo
            self.inText.configure(text_color="white")

    def restore_texprov(self, event):
        """Restaura el texto provisional si el campo está vacío."""
        #Compruebo si, después de eliminar los espacios en blanco, el cuadro de texto está vacío
        if not self.inText.get("0.0", "end").strip():
            self.inText.insert("0.0", self.provisional_text)  #Inserto el texto provisional al principio del cuadro de texto
            self.inText.configure(text_color="gray")  #Cambio el texto a gris ya que indica que es un texto provisional

    def toggle_send_button(self, event=None):
        """Muestra u oculta el botón de enviar según el contenido de la caja."""
        #Declaro el parametro event como None para llamar a la funcion directamente sin un evento KeyRelease
        #como cuando se pegue un mensaje con el mouse, se podrá controlar el mismo funcionamiento con futuras implementaciones
        content = self.inText.get("0.0", "end").strip()
        #Compruebo si content no está vacío y si no es el texto provisional
        if content and content != self.provisional_text:
            self.btnSend.grid(row=0, column=1, padx=5, pady=5)  # Muestra el botón si hay texto
        else:
            self.btnSend.grid_forget()  # Oculta el botón si no hay texto

    # --- Cierre de la aplicación y la conexión ---
    def close_connection(self):
        """Cierra la conexión al puerto serial."""
        self.stop_thread = True  # Detengo el hilo de recepción
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join()  # Espero a que termine el hilo
        if self.serial_conn:
            self.serial_conn.close()  # Cierro la conexión serial
        self.connected = False  # Cambio el estado de conexión
        self.cboPort.configure(state='normal')  # Habilito de nuevo el menú de puertos
        self.btnConnect.configure(text="Conectar")  # Cambio el texto del botón
        self.inText.configure(state='disabled')  # Deshabilito la caja de entrada
        self.display_center_message("Conexión cerrada.")  # Mensaje de cierre

    def close_application(self):
        """Cierra la aplicación de manera segura."""
        self.close_connection()  # Cierro la conexión si está activa
        self.destroy()  # Destruyo la ventana principal


# --- Ejecución de la aplicación ---
if __name__ == "__main__":
    app = SerialChat()  # Creo una instancia de la aplicación
    app.mainloop()  # Inicio el bucle principal de la ventana

