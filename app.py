import os
import sqlite3
#import yagmail
import base64
import shutil

from flask import Flask, render_template, request, jsonify, redirect, url_for
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from PIL import Image
from io import BytesIO

# -----------------------------
# RUTAS DEL PROYECTO
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CARPETA_PDF = os.path.join(BASE_DIR, "comprobantes_pdf")
os.makedirs(CARPETA_PDF, exist_ok=True)

# Carpeta de respaldo de comprobantes
CARPETA_BACKUP = os.path.join(BASE_DIR, "backup_comprobantes")
if not os.path.isdir(CARPETA_BACKUP):
    os.makedirs(CARPETA_BACKUP)

# -----------------------------
# APP FLASK
# -----------------------------
app = Flask(__name__)


# -----------------------------
# CONFIGURACION CORREO
# -----------------------------
#CORREO_REMITENTE = "anakvianap0327@gmail.com"
#PASSWORD_CORREO = "zfjc arhf knrw paks"
#CORREO_DESTINO = "erick_merc@hotmail.com"


# -----------------------------
# CONEXION BASE DE DATOS
# -----------------------------
def get_db():
    conn = sqlite3.connect("database.db", timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------------
# CREAR TABLAS
# -----------------------------
def crear_tablas():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comprobantes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT,
        documento TEXT,
        nombre TEXT,
        direccion TEXT,
        celular TEXT,
        concepto TEXT,
        valor REAL,
        fecha TEXT,
        firma TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trabajadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        documento TEXT UNIQUE,
        nombre TEXT,
        direccion TEXT,
        celular TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proveedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        documento TEXT UNIQUE,
        nombre TEXT,
        direccion TEXT,
        celular TEXT
    )
    """)

    conn.commit()
    conn.close()


# -----------------------------
# CONTADOR COMPROBANTE
# -----------------------------
def obtener_siguiente_comprobante():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT MAX(id) FROM comprobantes")
    resultado = cursor.fetchone()[0]

    conn.close()

    if resultado is None:
        numero = 1
    else:
        numero = resultado + 1

    return f"CE-{numero:05d}"


def generar_pdf(numero, comprobante):

    import textwrap

    os.makedirs("comprobantes_pdf", exist_ok=True)

    ruta = f"comprobantes_pdf/{numero}.pdf"

    c = canvas.Canvas(ruta, pagesize=A4)

    # -----------------------------
    # TITULO
    # -----------------------------
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(300, 800, "COMPROBANTE DE EGRESO")

    # NUMERO
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(550, 770, f"No. {comprobante['numero']}")

    # LINEA
    c.line(60, 760, 550, 760)

    y = 730

    # -----------------------------
    # PAGADOR
    # -----------------------------
    c.setFillColor(HexColor("#eef5ff"))
    c.rect(60, y-45, 480, 55, fill=1, stroke=0)

    c.setFillColor("black")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(70, y, "Datos del pagador")

    c.setFont("Helvetica", 10)
    c.drawString(70, y-15, "Nombre: Erick Mercado Otero")
    c.drawString(70, y-30, "Documento: 1082867642")

    y -= 70

    # -----------------------------
    # BENEFICIARIO
    # -----------------------------
    c.setFillColor(HexColor("#eefaf1"))
    c.rect(60, y-70, 480, 80, fill=1, stroke=0)

    c.setFillColor("black")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(70, y, "Datos del beneficiario")

    c.setFont("Helvetica", 10)
    c.drawString(70, y-15, f"Documento: {comprobante['documento']}")
    c.drawString(70, y-30, f"Nombre: {comprobante['nombre']}")
    c.drawString(70, y-45, f"Dirección: {comprobante['direccion']}")
    c.drawString(70, y-60, f"Celular: {comprobante['celular']}")

    y -= 95

    # -----------------------------
    # INFORMACION DEL PAGO
    # -----------------------------
    concepto = comprobante['concepto']

    lineas = textwrap.wrap(concepto, width=70)

    altura_concepto = len(lineas) * 15

    altura_cuadro = 90 + altura_concepto

    c.setFillColor(HexColor("#fff9e6"))
    c.rect(60, y-altura_cuadro+20, 480, altura_cuadro, fill=1, stroke=0)

    c.setFillColor("black")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(70, y, "Información del pago")

    c.setFont("Helvetica", 10)
    c.drawString(70, y-15, "Concepto:")

    y_concepto = y - 30

    for linea in lineas:
        c.drawString(70, y_concepto, linea)
        y_concepto -= 15

    valor = int(float(comprobante['valor'] or 0))

    c.setFont("Helvetica-Bold", 11)
    c.drawString(70, y_concepto-10, f"Valor: $ {valor:,}")

    c.setFont("Helvetica", 10)
    c.drawString(70, y_concepto-25, f"Fecha: {comprobante['fecha']}")
    c.drawString(70, y_concepto-40, "Método de pago: Transferencia")

    y = y_concepto - 80

    # -----------------------------
    # TEXTO LEGAL
    # -----------------------------
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(300, y, "Declaración de recibido:")

    y -= 20

    c.setFont("Helvetica", 9)

    texto = [
        "Mediante la presente firma declaro que he recibido a mi entera satisfacción",
        "la suma de dinero indicada en este comprobante, correspondiente al concepto",
        "anteriormente descrito. Manifiesto que el pago ha sido realizado en su totalidad",
        "y que no tengo reclamación posterior alguna por este concepto."
    ]

    for linea in texto:
        c.drawCentredString(300, y, linea)
        y -= 14

    y -= 20

    # -----------------------------
    # FIRMA
    # -----------------------------
    firma_base64 = comprobante['firma']

    if firma_base64:
        try:
            firma_base64 = firma_base64.split(",")[1]
            firma_bytes = base64.b64decode(firma_base64)

            imagen = Image.open(BytesIO(firma_bytes))

            buffer = BytesIO()
            imagen.save(buffer, format="PNG")
            buffer.seek(0)

            firma_image = ImageReader(buffer)

            c.drawImage(
                firma_image,
                190,
                y-70,
                width=250,
                height=100,
                mask='auto'
            )

        except:
            pass

    c.line(180, y-80, 420, y-80)

    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(300, y-100, comprobante['nombre'])

    c.setFont("Helvetica", 9)
    c.drawCentredString(300, y-115, f"CC {comprobante['documento']}")

    c.save()
# -----------------------------
# ENVIAR COMPROBANTE POR EMAIL
# -----------------------------
#def enviar_comprobante_email(numero):

    #try:

        #ruta_pdf = os.path.join(CARPETA_PDF, f"{numero}.pdf")

        #if not os.path.exists(ruta_pdf):
            #print("No existe el PDF para enviar")
            #return

        #yag = yagmail.SMTP(CORREO_REMITENTE, PASSWORD_CORREO)

        #asunto = f"Comprobante de egreso {numero}"

        #mensaje = f"""
        #Buen día

        #Se adjunta el comprobante de egreso {numero}
        #generado automáticamente por el sistema.
        #"""

        #yag.send(
            #to=CORREO_DESTINO,
            #subject=asunto,
            #contents=mensaje,
            #attachments=ruta_pdf
        

        #print("Correo enviado correctamente")

    #except Exception as e:

        #print("Error enviando correo:", e)

# -----------------------------
# BUSCAR PERSONA
# -----------------------------
@app.route("/buscar_persona")
def buscar_persona():

    documento = request.args.get("documento")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT nombre,direccion,celular FROM trabajadores WHERE documento=?",
        (documento,)
    )

    persona = cursor.fetchone()

    if not persona:

        cursor.execute(
            "SELECT nombre,direccion,celular FROM proveedores WHERE documento=?",
            (documento,)
        )

        persona = cursor.fetchone()

    conn.close()

    if persona:
        return jsonify({
            "nombre": persona["nombre"],
            "direccion": persona["direccion"],
            "celular": persona["celular"]
        })
    else:
        return jsonify({})


# -----------------------------
# PANTALLA REGISTRAR PERSONAS
# -----------------------------
@app.route("/personas")
def personas():

    documento = request.args.get("documento")

    persona = None
    tipo = None

    if documento:

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT documento,nombre,direccion,celular FROM trabajadores WHERE documento=?",
            (documento,)
        )

        persona = cursor.fetchone()
        tipo = "trabajador"

        if not persona:

            cursor.execute(
                "SELECT documento,nombre,direccion,celular FROM proveedores WHERE documento=?",
                (documento,)
            )

            persona = cursor.fetchone()
            tipo = "proveedor"

        conn.close()

    return render_template("personas.html", persona=persona, tipo=tipo)


# -----------------------------
# GUARDAR PERSONA
# -----------------------------
@app.route("/guardar_persona", methods=["POST"])
def guardar_persona():

    tipo = request.form["tipo"]
    documento = request.form["documento"]
    nombre = request.form["nombre"]
    direccion = request.form["direccion"]
    celular = request.form["celular"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT documento FROM trabajadores WHERE documento=?", (documento,))
    existe = cursor.fetchone()

    if not existe:
        cursor.execute("SELECT documento FROM proveedores WHERE documento=?", (documento,))
        existe = cursor.fetchone()

    if existe:

        if tipo == "trabajador":

            cursor.execute("""
            UPDATE trabajadores
            SET nombre=?,direccion=?,celular=?
            WHERE documento=?
            """,(nombre,direccion,celular,documento))

        else:

            cursor.execute("""
            UPDATE proveedores
            SET nombre=?,direccion=?,celular=?
            WHERE documento=?
            """,(nombre,direccion,celular,documento))

    else:

        if tipo == "trabajador":

            cursor.execute("""
            INSERT INTO trabajadores (documento,nombre,direccion,celular)
            VALUES (?,?,?,?)
            """,(documento,nombre,direccion,celular))

        else:

            cursor.execute("""
            INSERT INTO proveedores (documento,nombre,direccion,celular)
            VALUES (?,?,?,?)
            """,(documento,nombre,direccion,celular))

    conn.commit()
    conn.close()

    return redirect(url_for("consultar_personas"))


# -----------------------------
# CONSULTAR PERSONAS
# -----------------------------
@app.route("/consultar_personas")
def consultar_personas():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT documento,nombre,direccion,celular FROM trabajadores ORDER BY nombre")
    trabajadores = cursor.fetchall()

    cursor.execute("SELECT documento,nombre,direccion,celular FROM proveedores ORDER BY nombre")
    proveedores = cursor.fetchall()

    conn.close()

    return render_template("consultar_personas.html", trabajadores=trabajadores, proveedores=proveedores)


# -----------------------------
# ELIMINAR PERSONA
# -----------------------------
@app.route("/eliminar_persona/<documento>")
def eliminar_persona(documento):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM trabajadores WHERE documento=?", (documento,))
    cursor.execute("DELETE FROM proveedores WHERE documento=?", (documento,))

    conn.commit()
    conn.close()

    return redirect(url_for("consultar_personas"))


# -----------------------------
# CREAR COMPROBANTE
# -----------------------------
@app.route("/comprobante")
def comprobante():

    numero = obtener_siguiente_comprobante()

    return render_template("comprobante.html", numero=numero)


# -----------------------------
# GUARDAR COMPROBANTE
# -----------------------------
@app.route("/guardar_comprobante", methods=["POST"])
def guardar_comprobante():

    numero = request.form["numero"]
    documento = request.form["documento"]
    nombre = request.form["nombre"]
    direccion = request.form["direccion"]
    celular = request.form["celular"]
    concepto = request.form["concepto"]
    valor = request.form["valor"]
    fecha = request.form["fecha"]
    firma = request.form["firma"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO comprobantes
    (numero,documento,nombre,direccion,celular,concepto,valor,fecha,firma)
    VALUES (?,?,?,?,?,?,?,?,?)
    """,(numero,documento,nombre,direccion,celular,concepto,valor,fecha,firma))

    conn.commit()
    conn.close()

    comprobante = {
        "numero": numero,
        "documento": documento,
        "nombre": nombre,
        "direccion": direccion,
        "celular": celular,
        "concepto": concepto,
        "valor": valor,
        "fecha": fecha,
        "firma": firma
    }

    generar_pdf(numero, comprobante)

    backup_seguridad(numero)

    #enviar_comprobante_email(numero)

    return redirect(url_for("consultar_comprobantes"))
# -----------------------------
# BACKUP SEGURIDAD
# -----------------------------
def backup_seguridad(numero):

    try:

        # Backup base de datos
        origen_db = os.path.join(BASE_DIR, "database.db")
        destino_db = os.path.join(BASE_DIR, "database_backup.db")

        if os.path.exists(origen_db):
            shutil.copy(origen_db, destino_db)

        # Backup PDF
        origen_pdf = os.path.join(CARPETA_PDF, f"{numero}.pdf")
        destino_pdf = os.path.join(CARPETA_BACKUP, f"{numero}.pdf")

        if os.path.exists(origen_pdf):
            shutil.copy(origen_pdf, destino_pdf)

    except Exception as e:

        print("Error en backup:", e)

# -----------------------------
# CONSULTAR COMPROBANTES
# -----------------------------
@app.route("/consultar_comprobantes", methods=["GET","POST"])
def consultar_comprobantes():

    conn = get_db()
    cursor = conn.cursor()

    numero = ""
    documento = ""
    nombre = ""
    fecha_inicio = ""
    fecha_fin = ""

    query = """
    SELECT id,numero,documento,nombre,valor,fecha
    FROM comprobantes
    WHERE 1=1
    """

    parametros = []

    if request.method == "POST":

        numero = request.form.get("numero")
        documento = request.form.get("documento")
        nombre = request.form.get("nombre")
        fecha_inicio = request.form.get("fecha_inicio")
        fecha_fin = request.form.get("fecha_fin")

        if numero:
            query += " AND numero LIKE ?"
            parametros.append("%"+numero+"%")

        if documento:
            query += " AND documento LIKE ?"
            parametros.append("%"+documento+"%")

        if nombre:
            query += " AND nombre LIKE ?"
            parametros.append("%"+nombre+"%")

        if fecha_inicio:
            query += " AND fecha >= ?"
            parametros.append(fecha_inicio)

        if fecha_fin:
            query += " AND fecha <= ?"
            parametros.append(fecha_fin)

    query += " ORDER BY id DESC"

    cursor.execute(query, parametros)
    comprobantes = cursor.fetchall()

    conn.close()

    return render_template(
        "consultar_comprobantes.html",
        comprobantes=comprobantes,
        numero=numero,
        documento=documento,
        nombre=nombre,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin
    )


# -----------------------------
# VER COMPROBANTE
# -----------------------------
@app.route("/ver_comprobante/<int:id>")
def ver_comprobante(id):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT numero,documento,nombre,direccion,celular,concepto,valor,fecha,firma
    FROM comprobantes
    WHERE id=?
    """,(id,))

    comprobante = cursor.fetchone()

    conn.close()

    return render_template("ver_comprobante.html", comprobante=comprobante)


# -----------------------------
# RUTA INICIO
# -----------------------------
@app.route("/")
def inicio():
    return render_template("index.html")


# -----------------------------
# INICIAR APP
# -----------------------------
if __name__ == "__main__":

    crear_tablas()
    app.run(debug=True)