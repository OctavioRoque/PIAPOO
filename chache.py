import tkinter as tk
from tkinter import ttk, messagebox
import pyodbc
import bcrypt
from datetime import datetime

# --------------------------- CONEXIÓN A BASE DE DATOS ---------------------------
conexion = pyodbc.connect(
    'DRIVER={ODBC Driver 18 for SQL Server};'
    'SERVER=LAPTOP-GC3SD472\\SQLEXPRESS;'
    'DATABASE=PIAPOO;'
    'Trusted_Connection=yes;'
    'TrustServerCertificate=yes;'
)
cursor = conexion.cursor()

# --------------------------- VARIABLES GLOBALES ---------------------------
frames = {}
carrito = []
nombre_departamento = ""
id_requisicion = ""

# Variables para los Entry (declaradas globalmente)
entry_login_clave = None
entry_login_contrasena = None
entry_nuevo_clave = None
entry_nuevo_descripcion = None
entry_nuevo_stock = None
entry_cantidad = None
combo_opciones = None
tipo_requisicion = None
label_id_requisicion = None
tabla_stock = None
tabla_carrito = None
tabla_historial = None

# --------------------------- FUNCIONES ---------------------------
def mostrar_frame(nombre):
    for f in frames.values():
        f.pack_forget()
    frames[nombre].pack(fill='both', expand=True)

    if nombre == "stock":
        cargar_stock()
    elif nombre == "requisicion":
        preparar_requisicion()
    elif nombre == "historial":
        cargar_historial()

# Función de login
def verificar_login():
    global nombre_departamento  # Asegúrate de declararla como global
    clave_dpto = entry_login_clave.get()
    contrasena = entry_login_contrasena.get().encode('utf-8')

    cursor.execute("SELECT contraseña, Nombre FROM Departamento WHERE Clave_Dpto = ?", (clave_dpto,))
    resultado = cursor.fetchone()

    if resultado:
        contrasena_hash, nombre = resultado
        contrasena_hash = contrasena_hash.encode('utf-8')
        if bcrypt.checkpw(contrasena, contrasena_hash):
            nombre_departamento = nombre  # Asignación directa (sin espacios ni formatos)
            print(f"DEBUG: Nombre departamento obtenido -> {nombre_departamento}")  # Para diagnóstico
            messagebox.showinfo("Login exitoso", f"¡Bienvenido, departamento de {nombre_departamento}!")
            mostrar_frame("menu")
        else:
            messagebox.showerror("Error", "Contraseña incorrecta")
    else:
        messagebox.showerror("Error", "Departamento no encontrado")

# Función para cargar stock
def cargar_stock():
    for row in tabla_stock.get_children():
        tabla_stock.delete(row)

    try:
        cursor.execute("SELECT Clave_Art, Descripcion, Stock FROM Articulo")
        for clave, desc, stock in cursor.fetchall():
            tabla_stock.insert("", "end", values=(clave, desc, stock))
    except Exception as e:
        messagebox.showerror("Error al cargar stock", str(e))

# Función para agregar nuevo artículo
def agregar_articulo():
    clave = entry_nuevo_clave.get().strip()
    descripcion = entry_nuevo_descripcion.get().strip()
    stock = entry_nuevo_stock.get().strip()

    if not clave or not descripcion or not stock:
        messagebox.showwarning("Campos incompletos", "Por favor llena todos los campos.")
        return

    try:
        stock = int(stock)
        cursor.execute("INSERT INTO Articulo (Clave_Art, Descripcion, Stock) VALUES (?, ?, ?)", (clave, descripcion, stock))
        conexion.commit()
        messagebox.showinfo("Éxito", "Artículo agregado correctamente.")
        
        entry_nuevo_clave.delete(0, tk.END)
        entry_nuevo_descripcion.delete(0, tk.END)
        entry_nuevo_stock.delete(0, tk.END)
        cargar_stock()
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo agregar el artículo: {e}")

# Función para preparar requisición
def preparar_requisicion():
    global id_requisicion
    carrito.clear()
    actualizar_carrito()

    cursor.execute("SELECT COUNT(*) FROM Requisicion")
    contador = cursor.fetchone()[0]
    parte_nombre = nombre_departamento[:7].upper().ljust(7, 'X')
    id_requisicion = f"{parte_nombre}{str(contador).zfill(10)}"
    label_id_requisicion.config(text=f"ID Requisición: {id_requisicion}")

    cargar_opciones()

# Función para cargar artículos o servicios disponibles
def cargar_opciones():
    combo_opciones['values'] = []
    seleccion = tipo_requisicion.get()

    if seleccion == "Articulo":
        cursor.execute("SELECT Clave_Art, Descripcion FROM Articulo WHERE Stock > 0")
    elif seleccion == "Servicio":
        cursor.execute("SELECT Clave_Serv, Descripcion FROM Servicio")
    
    opciones = [f"{clave} - {desc}" for clave, desc in cursor.fetchall()]
    combo_opciones['values'] = opciones

# Función para agregar producto o servicio al carrito
def agregar_al_carrito():
    seleccion = combo_opciones.get()
    cantidad = entry_cantidad.get()

    if not seleccion or not cantidad:
        messagebox.showwarning("Campos incompletos", "Selecciona un producto o servicio y pon la cantidad.")
        return
    
    try:
        cantidad = int(cantidad)
        if cantidad <= 0:
            messagebox.showerror("Error", "La cantidad debe ser mayor a 0.")
            return
    except:
        messagebox.showerror("Error", "La cantidad debe ser un número válido.")
        return

    codigo = seleccion.split(" - ")[0]
    
    if tipo_requisicion.get() == "Articulo":
        cursor.execute("SELECT Stock FROM Articulo WHERE Clave_Art = ?", (codigo,))
        stock_actual = cursor.fetchone()[0]
        if stock_actual < cantidad:
            messagebox.showerror("Error", f"No hay suficiente stock. Stock actual: {stock_actual}")
            return

    carrito.append((codigo, cantidad))
    actualizar_carrito()
    combo_opciones.set("")
    entry_cantidad.delete(0, tk.END)

# Función para actualizar el carrito
def actualizar_carrito():
    tabla_carrito.delete(*tabla_carrito.get_children())
    for idx, (codigo, cantidad) in enumerate(carrito):
        tabla_carrito.insert("", "end", iid=idx, values=(codigo, cantidad))

#eliminar productos del carrito
def eliminar_del_carrito(event):
    seleccionado = tabla_carrito.selection()
    if seleccionado:
        idx = int(seleccionado[0])
        carrito.pop(idx)
        actualizar_carrito()

# guardar requisición
def guardar_requisicion():
    if not carrito:
        messagebox.showwarning("Vacío", "El carrito está vacío.")
        return

    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    clave_departamento = entry_login_clave.get()

    try:
        cursor.execute("INSERT INTO Requisicion (Clave_Req, Clave_Dpto, Fecha) VALUES (?, ?, ?)",
                       (id_requisicion, clave_departamento, fecha_actual))

        for codigo, cantidad in carrito:
            if tipo_requisicion.get() == "Articulo":
                cursor.execute("INSERT INTO Detalle_Req (Estado, Clave_Req, Clave_Art, Cantidad) VALUES ('Proceso', ?, ?, ?)",
                               (id_requisicion, codigo, cantidad))
                cursor.execute("UPDATE Articulo SET Stock = Stock - ? WHERE Clave_Art = ?", (cantidad, codigo))
            else:
                cursor.execute("INSERT INTO Detalle_Req (Estado, Clave_Req, Clave_Serv, Cantidad) VALUES ('Proceso', ?, ?, ?)",
                               (id_requisicion, codigo, cantidad))

        conexion.commit()
        messagebox.showinfo("Éxito", "¡Requisición creada exitosamente!")
        mostrar_frame("menu")
    except Exception as e:
        messagebox.showerror("Error", f"Error al guardar: {str(e)}")
        conexion.rollback()

# cargar historial de requisiciones
def cargar_historial():
    for row in tabla_historial.get_children():
        tabla_historial.delete(row)

    try:
        cursor.execute("""
        SELECT r.Clave_Req, r.Fecha, 
            ISNULL(d.Clave_Art, d.Clave_Serv) AS Codigo,
            d.Cantidad, d.Estado
        FROM Requisicion r
        JOIN Detalle_Req d ON r.Clave_Req = d.Clave_Req
        ORDER BY r.Fecha DESC
        """)
        for clave_req, fecha, codigo, cantidad, estado in cursor.fetchall():
            tabla_historial.insert("", "end", values=(clave_req, fecha, codigo, cantidad, estado), tags=(estado,))
        
        # Configurar colores
        tabla_historial.tag_configure("Proceso", background="orange")
        tabla_historial.tag_configure("Finalizada", background="lightgreen")

    except Exception as e:
        messagebox.showerror("Error", str(e))

# Función para cambiar estado
def cambiar_estado(event):
    seleccionado = tabla_historial.selection()
    if seleccionado:
        item = tabla_historial.item(seleccionado)
        clave_req, fecha, codigo, cantidad, estado_actual = item['values']

        if estado_actual == "Finalizada":
            messagebox.showinfo("Estado", "Esta requisición ya está finalizada.")
            return

        try:
            cursor.execute("""
            UPDATE Detalle_Req
            SET Estado = 'Finalizada'
            WHERE Clave_Req = ? AND (Clave_Art = ? OR Clave_Serv = ?)
            """, (clave_req, codigo, codigo))
            conexion.commit()
            cargar_historial()
            messagebox.showinfo("Éxito", "¡Estado actualizado a Finalizada!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

# --------------------------- INTERFAZ GRAFICA ---------------------------
ventana = tk.Tk()
ventana.title("Sistema de Almacén")
ventana.geometry("950x700")

# Frame Login
frame_login = tk.Frame(ventana)
frames["login"] = frame_login

tk.Label(frame_login, text="Clave Departamento:").pack(pady=5)
entry_login_clave = tk.Entry(frame_login)
entry_login_clave.pack()

tk.Label(frame_login, text="Contraseña:").pack(pady=5)
entry_login_contrasena = tk.Entry(frame_login, show="*")
entry_login_contrasena.pack()

tk.Button(frame_login, text="Ingresar", command=verificar_login).pack(pady=10)

# Frame Menú
frame_menu = tk.Frame(ventana)
frames["menu"] = frame_menu

tk.Label(frame_menu, text="Menú Principal", font=('Arial', 16)).pack(pady=10)
tk.Button(frame_menu, text="Ver Stock", command=lambda: mostrar_frame("stock")).pack(pady=10)
tk.Button(frame_menu, text="Nueva Requisición", command=lambda: mostrar_frame("requisicion")).pack(pady=10)
tk.Button(frame_menu, text="Historial Requisiciones", command=lambda: mostrar_frame("historial")).pack(pady=10)
tk.Button(frame_menu, text="Cerrar sesión", command=lambda: mostrar_frame("login")).pack(pady=10)

# Frame Stock
frame_stock = tk.Frame(ventana)
frames["stock"] = frame_stock

tk.Label(frame_stock, text="Stock de Artículos", font=('Arial', 16)).pack(pady=10)

tabla_stock = ttk.Treeview(frame_stock, columns=("Clave", "Descripcion", "Stock"), show="headings")
tabla_stock.heading("Clave", text="Clave del Artículo")
tabla_stock.heading("Descripcion", text="Descripción")
tabla_stock.heading("Stock", text="Stock")
tabla_stock.pack(pady=10)

# Agregar nuevo artículo
tk.Label(frame_stock, text="Agregar nuevo artículo", font=("Arial", 14)).pack(pady=10)
frame_agregar = tk.Frame(frame_stock)
frame_agregar.pack(pady=10)

tk.Label(frame_agregar, text="Clave:").grid(row=0, column=0)
entry_nuevo_clave = tk.Entry(frame_agregar)
entry_nuevo_clave.grid(row=0, column=1)

tk.Label(frame_agregar, text="Descripción:").grid(row=1, column=0)
entry_nuevo_descripcion = tk.Entry(frame_agregar)
entry_nuevo_descripcion.grid(row=1, column=1)

tk.Label(frame_agregar, text="Stock Inicial:").grid(row=2, column=0)
entry_nuevo_stock = tk.Entry(frame_agregar)
entry_nuevo_stock.grid(row=2, column=1)

tk.Button(frame_agregar, text="Agregar Artículo", command=agregar_articulo).grid(row=3, column=0, columnspan=2, pady=5)
tk.Button(frame_stock, text="Volver al menú", command=lambda: mostrar_frame("menu")).pack(pady=10)

# Frame Requisición
frame_requisicion = tk.Frame(ventana)
frames["requisicion"] = frame_requisicion

label_id_requisicion = tk.Label(frame_requisicion, text="ID Requisición:", font=("Arial", 14))
label_id_requisicion.pack(pady=5)

tipo_requisicion = tk.StringVar()
tipo_requisicion.set("Articulo")

opciones_tipo = ttk.Combobox(frame_requisicion, textvariable=tipo_requisicion, values=["Articulo", "Servicio"], state="readonly")
opciones_tipo.pack(pady=5)
opciones_tipo.bind("<<ComboboxSelected>>", lambda e: cargar_opciones())

combo_opciones = ttk.Combobox(frame_requisicion, state="readonly")
combo_opciones.pack(pady=5)

frame_cantidad = tk.Frame(frame_requisicion)
frame_cantidad.pack(pady=5)
tk.Label(frame_cantidad, text="Cantidad:").pack(side="left")
entry_cantidad = tk.Entry(frame_cantidad)
entry_cantidad.pack(side="left")

tk.Button(frame_requisicion, text="Agregar al carrito", command=agregar_al_carrito).pack(pady=5)

tabla_carrito = ttk.Treeview(frame_requisicion, columns=("Código", "Cantidad"), show="headings")
tabla_carrito.heading("Código", text="Código")
tabla_carrito.heading("Cantidad", text="Cantidad")
tabla_carrito.pack(pady=5)
tabla_carrito.bind("<Double-1>", eliminar_del_carrito)

tk.Button(frame_requisicion, text="Guardar Requisición", command=guardar_requisicion).pack(pady=10)
tk.Button(frame_requisicion, text="Volver al menú", command=lambda: mostrar_frame("menu")).pack(pady=10)

# Frame Historial
frame_historial = tk.Frame(ventana)
frames["historial"] = frame_historial

tk.Label(frame_historial, text="Historial de Requisiciones", font=("Arial", 16)).pack(pady=10)

tabla_historial = ttk.Treeview(frame_historial, columns=("Clave_Req", "Fecha", "Codigo", "Cantidad", "Estado"), show="headings")
for col in ("Clave_Req", "Fecha", "Codigo", "Cantidad", "Estado"):
    tabla_historial.heading(col, text=col)
tabla_historial.pack(pady=10)
tabla_historial.bind("<Double-1>", cambiar_estado)

tk.Button(frame_historial, text="Volver al menú", command=lambda: mostrar_frame("menu")).pack(pady=10)

# --------------------------- INICIAR PROGRAMA ---------------------------
mostrar_frame("login")
ventana.mainloop()