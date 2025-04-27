import tkinter as tk
from tkinter import ttk, messagebox
import pyodbc
import bcrypt
import datetime

# --- CONEXIÓN A BASE DE DATOS ---
conexion = pyodbc.connect(
    'DRIVER={ODBC Driver 18 for SQL Server};'
    'SERVER=LAPTOP-GC3SD472\\SQLEXPRESS;'
    'DATABASE=PIAPOO;'
    'Trusted_Connection=yes;'
    'TrustServerCertificate=yes;'
)
cursor = conexion.cursor()

# --- VARIABLES GLOBALES ---
frames = {}
carrito = []  
tipo_requisicion = None  

# --- FUNCIONES GENERALES ---

# Cambiar de pantalla
def mostrar_frame(nombre):
    for f in frames.values():
        f.pack_forget()
    frames[nombre].pack(fill="both", expand=True)

    if nombre == "stock":
        cargar_stock()
    elif nombre == "crear_requisicion":
        limpiar_requisicion()

# LOGIN
def verificar_login():
    clave_dpto = entry_login_clave.get()
    contrasena = entry_login_contra.get().encode('utf-8')

    cursor.execute("SELECT contraseña FROM Departamento WHERE Clave_Dpto = ?", (clave_dpto,))
    resultado = cursor.fetchone()

    if resultado:
        contrasena_hash = resultado[0].encode('utf-8')
        if bcrypt.checkpw(contrasena, contrasena_hash):
            global departamento_actual
            departamento_actual = clave_dpto
            messagebox.showinfo("Login exitoso", f"¡Bienvenido, departamento {clave_dpto}!")
            mostrar_frame("menu")
        else:
            messagebox.showerror("Error", "Contraseña incorrecta")
    else:
        messagebox.showerror("Error", "Departamento no encontrado")

# Cargar artículos en el stock
def cargar_stock():
    for row in tabla_stock.get_children():
        tabla_stock.delete(row)

    try:
        cursor.execute("SELECT Clave_Art, Descripcion, Stock FROM Articulo")
        for clave, desc, stock in cursor.fetchall():
            tabla_stock.insert("", "end", values=(clave, desc, stock))
    except Exception as e:
        messagebox.showerror("Error al cargar stock", str(e))

# Agregar artículo manualmente
def agregar_articulo():
    clave = entry_clave_art.get().strip()
    descripcion = entry_descripcion_art.get().strip()
    stock = entry_stock_art.get().strip()

    if not clave or not descripcion or not stock:
        messagebox.showwarning("Campos incompletos", "Por favor llena todos los campos.")
        return

    try:
        stock = int(stock)
        cursor.execute("INSERT INTO Articulo (Clave_Art, Descripcion, Stock) VALUES (?, ?, ?)", (clave, descripcion, stock))
        conexion.commit()
        messagebox.showinfo("Éxito", "Artículo agregado correctamente.")
        cargar_stock()
        entry_clave_art.delete(0, tk.END)
        entry_descripcion_art.delete(0, tk.END)
        entry_stock_art.delete(0, tk.END)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo agregar el artículo: {e}")

# --- FUNCIONES DE REQUISICIONES ---

# Limpiar la pantalla de crear requisición
def limpiar_requisicion():
    carrito.clear()
    actualizar_tabla_carrito()
    combo_seleccion.set("")
    entry_cantidad.delete(0, tk.END)

# Actualizar el carrito en la tabla
def actualizar_tabla_carrito():
    for item in tabla_carrito.get_children():
        tabla_carrito.delete(item)

    for item in carrito:
        tabla_carrito.insert("", "end", values=item)

# Buscar opciones de artículos o servicios según tipo de requisición
def cargar_opciones():
    opciones = []
    if tipo_requisicion.get() == "Artículo":
        cursor.execute("SELECT Clave_Art, Descripcion FROM Articulo")
        opciones = [f"{clave} - {desc}" for clave, desc in cursor.fetchall()]
    elif tipo_requisicion.get() == "Servicio":
        cursor.execute("SELECT Clave_Serv, Descripcion FROM Servicio")
        opciones = [f"{clave} - {desc}" for clave, desc in cursor.fetchall()]

    combo_seleccion["values"] = opciones

# Agregar item al carrito
def agregar_a_carrito():
    seleccion = combo_seleccion.get()
    cantidad = entry_cantidad.get()

    if not seleccion or not cantidad:
        messagebox.showwarning("Campos incompletos", "Selecciona un artículo/servicio y una cantidad.")
        return

    try:
        cantidad = int(cantidad)
        clave = seleccion.split(" - ")[0]
        descripcion = seleccion.split(" - ")[1]
        carrito.append((clave, descripcion, cantidad))
        actualizar_tabla_carrito()
        combo_seleccion.set("")
        entry_cantidad.delete(0, tk.END)
    except Exception as e:
        messagebox.showerror("Error", f"Error al agregar: {e}")

# Guardar requisición en base de datos
def guardar_requisicion():
    if not carrito:
        messagebox.showwarning("Carrito vacío", "No has agregado nada.")
        return

    try:
        # Crear nueva Requisición
        fecha_actual = datetime.date.today()
        cursor.execute("INSERT INTO Requisicion (Clave_Dpto, Fecha) VALUES (?, ?)", (departamento_actual, fecha_actual))
        conexion.commit()

        # Obtener clave de requisición creada
        cursor.execute("SELECT TOP 1 Clave_Req FROM Requisicion ORDER BY Clave_Req DESC")
        clave_req = cursor.fetchone()[0]

        # Agregar los detalles
        for clave, descripcion, cantidad in carrito:
            if tipo_requisicion.get() == "Artículo":
                cursor.execute(
                    "INSERT INTO Detalle_Req (Estado, Clave_Req, Clave_Art, Cantidad) VALUES (?, ?, ?, ?)",
                    ("Proceso", clave_req, clave, cantidad)
                )
            elif tipo_requisicion.get() == "Servicio":
                cursor.execute(
                    "INSERT INTO Detalle_Req (Estado, Clave_Req, Clave_Serv, Cantidad) VALUES (?, ?, ?, ?)",
                    ("Proceso", clave_req, clave, cantidad)
                )
        conexion.commit()
        messagebox.showinfo("Éxito", "Requisición guardada correctamente.")
        limpiar_requisicion()
        mostrar_frame("menu")
    except Exception as e:
        messagebox.showerror("Error", f"Error al guardar requisición: {e}")

# --- INICIAR VENTANA ---
ventana = tk.Tk()
ventana.title("Sistema de Almacén")
ventana.geometry("900x700")

tipo_requisicion = tk.StringVar()  # Ahora sí la podemos inicializar

# --- FRAMES ---

# LOGIN
frame_login = tk.Frame(ventana)
frames["login"] = frame_login

tk.Label(frame_login, text="Clave Departamento:").pack(pady=5)
entry_login_clave = tk.Entry(frame_login)
entry_login_clave.pack()

tk.Label(frame_login, text="Contraseña:").pack(pady=5)
entry_login_contra = tk.Entry(frame_login, show="*")
entry_login_contra.pack()

tk.Button(frame_login, text="Ingresar", command=verificar_login).pack(pady=10)

# MENÚ
frame_menu = tk.Frame(ventana)
frames["menu"] = frame_menu

tk.Label(frame_menu, text="Menú Principal", font=('Arial', 18)).pack(pady=10)
tk.Button(frame_menu, text="Ver Stock", command=lambda: mostrar_frame("stock")).pack(pady=5)
tk.Button(frame_menu, text="Crear Requisición", command=lambda: mostrar_frame("crear_requisicion")).pack(pady=5)
tk.Button(frame_menu, text="Cerrar Sesión", command=lambda: mostrar_frame("login")).pack(pady=10)

# STOCK
frame_stock = tk.Frame(ventana)
frames["stock"] = frame_stock

tk.Label(frame_stock, text="Stock de Artículos", font=('Arial', 16)).pack(pady=10)

tabla_stock = ttk.Treeview(frame_stock, columns=("Clave", "Descripcion", "Stock"), show="headings")
tabla_stock.heading("Clave", text="Clave del Artículo")
tabla_stock.heading("Descripcion", text="Descripción")
tabla_stock.heading("Stock", text="Stock")
tabla_stock.pack(pady=5)

tk.Button(frame_stock, text="Volver al Menú", command=lambda: mostrar_frame("menu")).pack(pady=10)

# Agregar artículo manualmente
frame_agregar = tk.Frame(frame_stock)
frame_agregar.pack(pady=10)

tk.Label(frame_agregar, text="Clave:").grid(row=0, column=0, padx=5, pady=5)
entry_clave_art = tk.Entry(frame_agregar)
entry_clave_art.grid(row=0, column=1)

tk.Label(frame_agregar, text="Descripción:").grid(row=1, column=0, padx=5, pady=5)
entry_descripcion_art = tk.Entry(frame_agregar)
entry_descripcion_art.grid(row=1, column=1)

tk.Label(frame_agregar, text="Stock inicial:").grid(row=2, column=0, padx=5, pady=5)
entry_stock_art = tk.Entry(frame_agregar)
entry_stock_art.grid(row=2, column=1)

tk.Button(frame_agregar, text="Agregar Artículo", command=agregar_articulo).grid(row=3, column=0, columnspan=2, pady=10)

# CREAR REQUISICIÓN
frame_crear_req = tk.Frame(ventana)
frames["crear_requisicion"] = frame_crear_req

tk.Label(frame_crear_req, text="Crear Requisición", font=('Arial', 18)).pack(pady=10)

frame_tipo = tk.Frame(frame_crear_req)
frame_tipo.pack()

tk.Label(frame_tipo, text="Tipo:").pack(side="left", padx=5)
tk.Radiobutton(frame_tipo, text="Artículo", variable=tipo_requisicion, value="Artículo", command=cargar_opciones).pack(side="left")
tk.Radiobutton(frame_tipo, text="Servicio", variable=tipo_requisicion, value="Servicio", command=cargar_opciones).pack(side="left")

frame_seleccion = tk.Frame(frame_crear_req)
frame_seleccion.pack(pady=10)

combo_seleccion = ttk.Combobox(frame_seleccion, state="readonly", width=50)
combo_seleccion.pack(side="left", padx=5)

entry_cantidad = tk.Entry(frame_seleccion, width=5)
entry_cantidad.pack(side="left", padx=5)

tk.Button(frame_seleccion, text="Agregar", command=agregar_a_carrito).pack(side="left", padx=5)

tabla_carrito = ttk.Treeview(frame_crear_req, columns=("Clave", "Descripción", "Cantidad"), show="headings")
tabla_carrito.heading("Clave", text="Clave")
tabla_carrito.heading("Descripción", text="Descripción")
tabla_carrito.heading("Cantidad", text="Cantidad")
tabla_carrito.pack(pady=10)

tk.Button(frame_crear_req, text="Guardar Requisición", command=guardar_requisicion).pack(pady=10)
tk.Button(frame_crear_req, text="Volver al Menú", command=lambda: mostrar_frame("menu")).pack(pady=5)

# INICIAR
mostrar_frame("login")
ventana.mainloop()
