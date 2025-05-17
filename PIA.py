import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import pyodbc
import bcrypt
from datetime import datetime

# ===================== CONFIGURACIÓN DE COLORES Y FUENTES =====================
COLOR_PRIMARIO = "#2c3e50"
COLOR_SECUNDARIO = "#3498db"
COLOR_FONDO = "#ecf0f1"
COLOR_BOTONES = "#e74c3c"
FUENTE_TITULOS = ('Arial', 16, 'bold')
FUENTE_TEXTO = ('Arial', 10)

# ===================== CONEXIÓN A LA BASE DE DATOS =====================
conexion = pyodbc.connect(
    'DRIVER={ODBC Driver 18 for SQL Server};'
    'SERVER=LAPTOP-GC3SD472\\SQLEXPRESS;'
    'DATABASE=PIAPOO;'
    'Trusted_Connection=yes;'
    'TrustServerCertificate=yes;'
)
cursor = conexion.cursor()

# ===================== VARIABLES GLOBALES =====================
frames = {}
carrito = []
nombre_departamento = ""
id_requisicion = ""

# ===================== FUNCIÓN PARA CAMBIAR ENTRE FRAMES =====================
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

# ===================== FUNCIÓN DE LOGIN CON BCRYPT =====================
def verificar_login():
    global nombre_departamento
    clave_dpto = entry_login_clave.get()
    contrasena = entry_login_contrasena.get().encode('utf-8')

    cursor.execute("SELECT contraseña, Nombre FROM Departamento WHERE Clave_Dpto = ?", (clave_dpto,))
    resultado = cursor.fetchone()

    if resultado:
        contrasena_hash, nombre = resultado
        contrasena_hash = contrasena_hash.encode('utf-8')
        if bcrypt.checkpw(contrasena, contrasena_hash):
            nombre_departamento = nombre.strip() if nombre else "Departamento"
            messagebox.showinfo("Login exitoso", f"¡Bienvenido, departamento de {nombre_departamento}!")
            mostrar_frame("menu")
        else:
            messagebox.showerror("Error", "Contraseña incorrecta")
    else:
        messagebox.showerror("Error", "Departamento no encontrado")

# ===================== STOCK =====================
def cargar_stock():
    for row in tabla_stock.get_children():
        tabla_stock.delete(row)
    try:
        cursor.execute("SELECT Clave_Art, Descripcion, Stock FROM Articulo")
        for clave, desc, stock in cursor.fetchall():
            tabla_stock.insert("", "end", values=(clave, desc, stock))
    except Exception as e:
        messagebox.showerror("Error", f"Error al cargar stock: {str(e)}")

# ===================== REQUISICIÓN =====================
def preparar_requisicion():
    global id_requisicion
    carrito.clear()
    actualizar_carrito()
    cursor.execute("SELECT COUNT(*) FROM Requisicion")
    contador = cursor.fetchone()[0]
    parte_nombre = nombre_departamento[:5].replace(" ", "").upper().ljust(5, 'X')
    id_requisicion = f"{parte_nombre}{str(contador).zfill(10)}"
    label_id_requisicion.config(text=f"ID Requisición: {id_requisicion}")
    cargar_opciones()

def cargar_opciones():
    combo_opciones['values'] = []
    tipo = tipo_requisicion.get()
    if tipo == "Articulo":
        cursor.execute("SELECT Clave_Art, Descripcion FROM Articulo")
    else:
        cursor.execute("SELECT Clave_Serv, Descripcion FROM Servicio")
    opciones = [f"{row[0]} - {row[1]}" for row in cursor.fetchall()]
    combo_opciones['values'] = opciones

def agregar_al_carrito():
    opcion = combo_opciones.get()
    cantidad = entry_cantidad.get()
    if not opcion or not cantidad.isdigit():
        messagebox.showwarning("Faltan datos", "Selecciona una opción y cantidad válida")
        return
    clave = opcion.split(" - ")[0]
    carrito.append((clave, int(cantidad)))
    actualizar_carrito()

def actualizar_carrito():
    tabla_carrito.delete(*tabla_carrito.get_children())
    for i, (codigo, cantidad) in enumerate(carrito, start=1):
        tabla_carrito.insert("", "end", values=(i, codigo, cantidad))

def guardar_requisicion():
    if not carrito:
        messagebox.showwarning("Vacío", "El carrito está vacío")
        return
    try:
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("INSERT INTO Requisicion (Clave_Req, Clave_Dpto, Fecha) VALUES (?, ?, ?)",
                      (id_requisicion, entry_login_clave.get(), fecha_actual))
        for codigo, cantidad in carrito:
            if tipo_requisicion.get() == "Articulo":
                cursor.execute("INSERT INTO Detalle_Req (Estado, Clave_Req, Clave_Art, Cantidad) VALUES ('Proceso', ?, ?, ?)",
                              (id_requisicion, codigo, cantidad))
                cursor.execute("UPDATE Articulo SET Stock = Stock - ? WHERE Clave_Art = ?", (cantidad, codigo))
            else:
                cursor.execute("INSERT INTO Detalle_Req (Estado, Clave_Req, Clave_Serv, Cantidad) VALUES ('Proceso', ?, ?, ?)",
                              (id_requisicion, codigo, cantidad))
        conexion.commit()
        messagebox.showinfo("Éxito", "Requisición guardada correctamente")
        mostrar_frame("menu")
    except Exception as e:
        messagebox.showerror("Error", f"Error al guardar requisición: {str(e)}")
        conexion.rollback()

# ===================== HISTORIAL =====================
def cargar_historial():
    for row in tabla_historial.get_children():
        tabla_historial.delete(row)
    try:
        # Se hace LEFT JOIN para cubrir tanto artículos como servicios
        cursor.execute("""
            SELECT R.Clave_Req, R.Fecha, 
                   ISNULL(DR.Clave_Art, DR.Clave_Serv) AS Codigo, 
                   DR.Cantidad, DR.Estado
            FROM Requisicion R
            JOIN Detalle_Req DR ON R.Clave_Req = DR.Clave_Req
            WHERE R.Clave_Dpto = ?
            ORDER BY R.Fecha DESC
        """, (entry_login_clave.get(),))

        for clave, fecha, codigo, cantidad, estado in cursor.fetchall():
            # Asegurar que la fecha sea tipo string legible
            fecha_str = fecha.strftime("%Y-%m-%d") if isinstance(fecha, datetime) else str(fecha)
            tabla_historial.insert("", "end", values=(clave, fecha_str, codigo, cantidad, estado))

    except Exception as e:
        messagebox.showerror("Error", f"Error al cargar historial: {str(e)}")


# =============== ACTUALIZAR ESTADO ========================

def cambiar_estado(event):
    seleccionado = tabla_historial.selection()
    if seleccionado:
        item = tabla_historial.item(seleccionado)
        valores = item['values']
        
        if len(valores) < 5:
            messagebox.showwarning("Advertencia", "El registro seleccionado no es válido.")
            return

        clave_req, fecha, codigo, cantidad, estado_actual = valores

        if estado_actual == "Finalizada":
            messagebox.showinfo("Estado", "Esta requisición ya está finalizada.")
            return

        try:
            # Se actualiza ya sea un artículo o un servicio
            cursor.execute("""
                UPDATE Detalle_Req
                SET Estado = 'Finalizada'
                WHERE Clave_Req = ? AND (Clave_Art = ? OR Clave_Serv = ?)
            """, (clave_req, codigo, codigo))
            conexion.commit()
            cargar_historial()
            messagebox.showinfo("Éxito", "¡Estado actualizado a Finalizada!")
        except Exception as e:
            messagebox.showerror("Error", f"Error al cambiar estado: {str(e)}")


# ===================== INTERFAZ PRINCIPAL =====================
ventana = tk.Tk()
ventana.title("Sistema de Almacén")
ventana.geometry("1100x750")
ventana.configure(bg=COLOR_FONDO)

# Estilos
estilo = ttk.Style()
estilo.theme_use('clam')
estilo.configure('TFrame', background=COLOR_FONDO)
estilo.configure('TLabel', background=COLOR_FONDO, foreground=COLOR_PRIMARIO, font=FUENTE_TEXTO)
estilo.configure('TButton', background=COLOR_BOTONES, foreground='white', font=FUENTE_TEXTO)
estilo.map('TButton', background=[('active', COLOR_SECUNDARIO)])
estilo.configure("Treeview.Heading", background=COLOR_PRIMARIO, foreground='white', font=FUENTE_TITULOS)

# ===================== FRAME LOGIN =====================
frame_login = ttk.Frame(ventana)
ttk.Label(frame_login, text="🔐 LOGIN", font=FUENTE_TITULOS).pack(pady=20)
ttk.Label(frame_login, text="Clave Departamento:").pack()
entry_login_clave = ttk.Entry(frame_login)
entry_login_clave.pack()

ttk.Label(frame_login, text="Contraseña:").pack()
entry_login_contrasena = ttk.Entry(frame_login, show="*")
entry_login_contrasena.pack()

ttk.Button(frame_login, text="Ingresar", command=verificar_login).pack(pady=20)
frames["login"] = frame_login

# ===================== FRAME MENÚ =====================
frame_menu = ttk.Frame(ventana)
ttk.Label(frame_menu, text="Menú Principal", font=FUENTE_TITULOS).pack(pady=20)
for texto, destino in [("📦 Ver Stock", "stock"), ("🛒 Nueva Requisición", "requisicion"), ("📋 Ver Historial", "historial"), ("🚪 Cerrar Sesión", "login")]:
    ttk.Button(frame_menu, text=texto, command=lambda d=destino: mostrar_frame(d)).pack(pady=10, ipadx=10)
frames["menu"] = frame_menu

# ===================== FRAME STOCK =====================
frame_stock = ttk.Frame(ventana)
tabla_stock = ttk.Treeview(frame_stock, columns=("Clave", "Descripción", "Stock"), show="headings")
for col in ("Clave", "Descripción", "Stock"):
    tabla_stock.heading(col, text=col)
tabla_stock.pack(fill='both', expand=True, padx=20, pady=20)
frames["stock"] = frame_stock
ttk.Button(frame_stock, text="🔙 Volver al menú", command=lambda: mostrar_frame("menu")).pack(pady=10)



def agregar_articulo():
    ventana = tk.Toplevel()
    ventana.title("Agregar nuevo artículo")
    ventana.configure(bg="#f0f0f0")

    tk.Label(ventana, text="ID Artículo:").grid(row=0, column=0, padx=10, pady=5)
    tk.Label(ventana, text="Descripción:").grid(row=2, column=0, padx=10, pady=5)
    tk.Label(ventana, text="Stock Inicial:").grid(row=3, column=0, padx=10, pady=5)

    id_entry = tk.Entry(ventana)
    desc_entry = tk.Entry(ventana)
    stock_entry = tk.Entry(ventana)

    id_entry.grid(row=0, column=1, padx=10, pady=5)
    desc_entry.grid(row=2, column=1, padx=10, pady=5)
    stock_entry.grid(row=3, column=1, padx=10, pady=5)

    def guardar_articulo():
        clave = id_entry.get()
        descripcion = desc_entry.get()
        stock = stock_entry.get()

        if not (clave and descripcion and stock):
            messagebox.showerror("Error", "Todos los campos son obligatorios.")
            return
        try:
            cursor.execute("INSERT INTO Articulo (Clave_Art, Descripcion, Stock) VALUES (?, ?, ?)", 
                           (clave, descripcion, int(stock)))
            conexion.commit()
            messagebox.showinfo("Éxito", "Artículo agregado correctamente.")
            cargar_stock()
            ventana.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo agregar el artículo: {e}")

    tk.Button(ventana, text="Guardar", command=guardar_articulo).grid(row=4, column=0, columnspan=2, pady=10)

def actualizar_stock():
    ventana = tk.Toplevel()
    ventana.title("Actualizar stock")
    ventana.configure(bg="#f0f0f0")

    tk.Label(ventana, text="ID Artículo:").grid(row=0, column=0, padx=10, pady=5)
    tk.Label(ventana, text="Cantidad a agregar:").grid(row=1, column=0, padx=10, pady=5)

    id_entry = tk.Entry(ventana)
    cantidad_entry = tk.Entry(ventana)

    id_entry.grid(row=0, column=1, padx=10, pady=5)
    cantidad_entry.grid(row=1, column=1, padx=10, pady=5)

    def aplicar_actualizacion():
        clave = id_entry.get()
        cantidad = cantidad_entry.get()
        try:
            cursor.execute("UPDATE Articulo SET Stock = Stock + ? WHERE Clave_Art = ?", 
                           (int(cantidad), clave))
            conexion.commit()
            messagebox.showinfo("Éxito", "Stock actualizado correctamente.")
            cargar_stock()
            ventana.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo actualizar el stock: {e}")

    tk.Button(ventana, text="Actualizar", command=aplicar_actualizacion).grid(row=2, column=0, columnspan=2, pady=10)

tk.Button(frame_stock, text="➕ Agregar Artículo", command=agregar_articulo).pack(pady=5)
tk.Button(frame_stock, text="📦 Actualizar Stock", command=actualizar_stock).pack(pady=5)

# ===================== FRAME REQUISICIÓN =====================
frame_requisicion = ttk.Frame(ventana)
label_id_requisicion = ttk.Label(frame_requisicion, text="ID Requisición:")
label_id_requisicion.pack(pady=10)

tipo_requisicion = tk.StringVar(value="Articulo")
ttk.Radiobutton(frame_requisicion, text="Artículo", variable=tipo_requisicion, value="Articulo", command=cargar_opciones).pack()
ttk.Radiobutton(frame_requisicion, text="Servicio", variable=tipo_requisicion, value="Servicio", command=cargar_opciones).pack()

combo_opciones = ttk.Combobox(frame_requisicion, width=50)
combo_opciones.pack(pady=5)

entry_cantidad = ttk.Entry(frame_requisicion)
entry_cantidad.pack(pady=5)
ttk.Button(frame_requisicion, text="🔙 Volver al menú", command=lambda: mostrar_frame("menu")).pack(pady=10)


ttk.Button(frame_requisicion, text="Agregar al carrito", command=agregar_al_carrito).pack(pady=10)

tabla_carrito = ttk.Treeview(frame_requisicion, columns=("No", "Código", "Cantidad"), show="headings")
for col in ("No", "Código", "Cantidad"):
    tabla_carrito.heading(col, text=col)
tabla_carrito.pack(padx=10, pady=10)

ttk.Button(frame_requisicion, text="Guardar Requisición", command=guardar_requisicion).pack(pady=20)
frames["requisicion"] = frame_requisicion

# ===================== FRAME HISTORIAL =====================
frame_historial = ttk.Frame(ventana)
tabla_historial = ttk.Treeview(
    frame_historial, 
    columns=("Clave_Req", "Fecha", "Codigo", "Cantidad", "Estado"), 
    show="headings"
)
for col in ("Clave_Req", "Fecha", "Codigo", "Cantidad", "Estado"):
    tabla_historial.heading(col, text=col)
tabla_historial.pack(fill='both', expand=True, padx=20, pady=20)
frames["historial"] = frame_historial
ttk.Button(frame_historial, text="🔙 Volver al menú", command=lambda: mostrar_frame("menu")).pack(pady=10)
tabla_historial.bind("<Double-1>", cambiar_estado)



# ===================== INICIO DE APLICACIÓN =====================
mostrar_frame("login")
ventana.mainloop()
