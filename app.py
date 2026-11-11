from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os
import sqlite3
import qrcode
from datetime import datetime, date

from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename


# =========================================================
# CONFIGURACIÓN DE FLASK
# =========================================================

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "biovent.db")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "manuales")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# =========================================================
# CARPETA DE EVIDENCIAS FOTOGRÁFICAS
# =========================================================

EVIDENCIAS_FOLDER = os.path.join(BASE_DIR, "evidencias")
app.config["EVIDENCIAS_FOLDER"] = EVIDENCIAS_FOLDER
os.makedirs(EVIDENCIAS_FOLDER, exist_ok=True)
print("CARPETA DE EVIDENCIAS:", EVIDENCIAS_FOLDER)

# =========================================================
# FORZAR UTF-8 EN TODAS LAS RESPUESTAS HTML
# =========================================================

@app.after_request
def forzar_utf8(response):
    if response.content_type.startswith("text/html"):
        response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response


# =========================================================
# CONFIGURACIÓN DE ARCHIVOS
# =========================================================

ALLOWED_EXTENSIONS = {
    "pdf"
}


def archivo_permitido(nombre):
    if not nombre:
        return False

    if "." not in nombre:
        return False

    extension = nombre.rsplit(".", 1)[1].lower()

    return extension in ALLOWED_EXTENSIONS
# =========================================================
# ARCHIVOS DE EVIDENCIA FOTOGRÁFICA
# =========================================================

ALLOWED_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}


def imagen_permitida(nombre):
    if not nombre:
        return False

    if "." not in nombre:
        return False

    extension = nombre.rsplit(".", 1)[1].lower()

    return extension in ALLOWED_IMAGE_EXTENSIONS

# =========================================================
# CONEXIÓN A BASE DE DATOS
# =========================================================

def conectar_bd():
    conexion = sqlite3.connect(DATABASE)
    conexion.row_factory = sqlite3.Row

    return conexion


# =========================================================
# CREAR BASE DE DATOS
# =========================================================

def crear_bd():

    conexion = conectar_bd()

    # =====================================================
    # TABLA EQUIPOS
    # =====================================================

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS equipos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL,
            marca TEXT NOT NULL,
            modelo TEXT NOT NULL,
            serie TEXT NOT NULL,
            ubicacion TEXT NOT NULL,
            servicio TEXT NOT NULL,
            estado TEXT NOT NULL,
            fecha TEXT,
            observaciones TEXT
        )
    """)

    # =====================================================
    # TABLA MANTENIMIENTOS
    # =====================================================

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS mantenimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            fecha TEXT NOT NULL,
            proxima_fecha TEXT NOT NULL,
            tecnico TEXT NOT NULL,
            observaciones TEXT,
            FOREIGN KEY (equipo_id)
                REFERENCES equipos(id)
        )
    """)

    # =====================================================
    # TABLA CHECKLISTS
    # =====================================================

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS checklists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            tecnico TEXT NOT NULL,
            inspeccion_visual TEXT NOT NULL,
            estado_fisico TEXT NOT NULL,
            cable_alimentacion TEXT NOT NULL,
            pantalla TEXT NOT NULL,
            alarmas TEXT NOT NULL,
            encendido TEXT NOT NULL,
            bateria TEXT NOT NULL,
            circuito_respiratorio TEXT NOT NULL,
            filtros TEXT NOT NULL,
            sensores TEXT NOT NULL,
            prueba_funcionamiento TEXT NOT NULL,
            limpieza TEXT NOT NULL,
            observaciones TEXT,
            resultado TEXT NOT NULL,
            FOREIGN KEY (equipo_id)
                REFERENCES equipos(id)
        )
    """)

    # =====================================================
    # TABLA MANUALES
    # =====================================================

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS manuales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            archivo TEXT NOT NULL,
            fecha_subida TEXT NOT NULL,
            FOREIGN KEY (equipo_id)
                REFERENCES equipos(id)
        )
    """)
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS evidencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_id INTEGER NOT NULL,
            archivo TEXT NOT NULL,
            descripcion TEXT,
            fecha_subida TEXT NOT NULL,
            FOREIGN KEY (equipo_id)
                REFERENCES equipos(id)
        )
    """)
    
    # =====================================================
    # TABLA FALLAS
    # =====================================================

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS fallas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_id INTEGER NOT NULL,
            fecha_falla TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            causa TEXT,
            gravedad TEXT NOT NULL,
            acciones_realizadas TEXT,
            fecha_reparacion TEXT,
            fecha_retorno_servicio TEXT,
            tiempo_fuera_servicio REAL,
            tecnico TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'Pendiente',
            observaciones TEXT,
            FOREIGN KEY (equipo_id)
                REFERENCES equipos(id)
        )
    """)
        # =====================================================
    # TABLA PRUEBAS FUNCIONALES
    # =====================================================

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS pruebas_funcionales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            tipo_prueba TEXT NOT NULL,
            parametro TEXT NOT NULL,
            valor_referencia REAL,
            valor_medido REAL,
            unidad TEXT,
            limite_inferior REAL,
            limite_superior REAL,
            resultado TEXT NOT NULL,
            tecnico TEXT NOT NULL,
            observaciones TEXT,
            FOREIGN KEY (equipo_id)
                REFERENCES equipos(id)
        )
    """)
    conexion.commit()
    conexion.close()
# =========================================================
# INICIO
# =========================================================

@app.route("/")
def inicio():

    return render_template(
        "index.html"
    )

@app.route("/inventario")
def inventario():
    conexion = conectar_bd()

    equipos = conexion.execute("""
        SELECT *
        FROM equipos
        ORDER BY id DESC
    """).fetchall()

    conexion.close()

    return render_template(
        "inventario.html",
        equipos=equipos
    )
    

# =====================================================
# REGISTRO Y CONSULTA DE FALLAS
# =====================================================

@app.route("/fallas", methods=["GET", "POST"])
def fallas():
    conexion = conectar_bd()

    if request.method == "POST":
        equipo_id = request.form.get("equipo_id", "").strip()
        fecha_falla = request.form.get("fecha_falla", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        causa = request.form.get("causa", "").strip()
        gravedad = request.form.get("gravedad", "").strip()
        tecnico = request.form.get("tecnico", "").strip()
        observaciones = request.form.get("observaciones", "").strip()

        error = None

        # Validar campos obligatorios
        if not all([
            equipo_id, fecha_falla, descripcion, gravedad, tecnico
        ]):
            error = "Completa todos los campos obligatorios."

        # Validar fecha: acepta fecha antigua o fecha con hora
        if error is None:
            try:
                datetime.fromisoformat(fecha_falla)
            except ValueError:
                error = "La fecha y hora de la falla no son válidas."

        # Validar que el equipo exista
        if error is None:
            equipo = conexion.execute(
                "SELECT id FROM equipos WHERE id = ?",
                (equipo_id,)
            ).fetchone()

            if equipo is None:
                error = "El equipo seleccionado no existe."

        # Si hay errores, volver a mostrar el formulario
        if error:
            equipos = conexion.execute("""
                SELECT id, codigo, marca, modelo
                FROM equipos
                ORDER BY codigo
            """).fetchall()

            registros = conexion.execute("""
                SELECT f.*, e.codigo, e.marca, e.modelo
                FROM fallas f
                JOIN equipos e ON e.id = f.equipo_id
                ORDER BY f.fecha_falla DESC, f.id DESC
            """).fetchall()

            conexion.close()

            return render_template(
                "fallas.html",
                equipos=equipos,
                fallas=registros,
                error=error
            )

        # Guardar la falla
        conexion.execute("""
            INSERT INTO fallas (
                equipo_id,
                fecha_falla,
                descripcion,
                causa,
                gravedad,
                tecnico,
                observaciones,
                estado
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Pendiente')
        """, (
            equipo_id,
            fecha_falla,
            descripcion,
            causa,
            gravedad,
            tecnico,
            observaciones
        ))

        conexion.commit()
        conexion.close()

        return redirect(url_for("fallas"))

    # Consultar equipos para el formulario
    equipos = conexion.execute("""
        SELECT id, codigo, marca, modelo
        FROM equipos
        ORDER BY codigo
    """).fetchall()

    # Consultar historial de fallas
    registros = conexion.execute("""
        SELECT f.*, e.codigo, e.marca, e.modelo
        FROM fallas f
        JOIN equipos e ON e.id = f.equipo_id
        ORDER BY f.fecha_falla DESC, f.id DESC
    """).fetchall()

    conexion.close()

    return render_template(
        "fallas.html",
        equipos=equipos,
        fallas=registros
    )

# =====================================================
# GESTIONAR UNA FALLA REGISTRADA
# =====================================================

@app.route("/fallas/gestionar/<int:falla_id>", methods=["GET", "POST"])
def gestionar_falla(falla_id):
    conexion = conectar_bd()

    falla = conexion.execute("""
        SELECT f.*, e.codigo, e.marca, e.modelo
        FROM fallas f
        JOIN equipos e ON e.id = f.equipo_id
        WHERE f.id = ?
    """, (falla_id,)).fetchone()

    if falla is None:
        conexion.close()
        return "La falla solicitada no existe.", 404

    if request.method == "POST":
        acciones = request.form.get(
            "acciones_realizadas", ""
        ).strip()

        fecha_reparacion = request.form.get(
            "fecha_reparacion", ""
        ).strip() or None

        fecha_retorno = request.form.get(
            "fecha_retorno_servicio", ""
        ).strip() or None

        tecnico = request.form.get(
            "tecnico", ""
        ).strip()

        estado = request.form.get("estado", "").strip()

        observaciones = request.form.get(
            "observaciones", ""
        ).strip()

        estados_validos = [
            "Pendiente",
            "En reparación",
            "Reparada"
        ]

        if not tecnico or estado not in estados_validos:
            return (
                "Debes indicar el técnico y un estado válido.",
                400
            )

        if estado == "Reparada" and not fecha_retorno:
            return (
                "Registra la fecha y hora de retorno al servicio "
                "antes de marcar la falla como reparada.",
                400
            )

        tiempo_fuera = None

        if fecha_retorno:
            try:
                inicio = datetime.fromisoformat(
                    falla["fecha_falla"]
                )
                retorno = datetime.fromisoformat(fecha_retorno)

                if retorno < inicio:
                    return (
                        "El retorno al servicio no puede ser "
                        "anterior a la fecha de la falla.",
                        400
                    )

                tiempo_fuera = (
                    retorno - inicio
                ).total_seconds() / 3600

            except ValueError:
                conexion.close()
                return (
                    "No se pudieron interpretar las fechas. "
                    "Verifica los datos registrados.",
                    400
                )

        conexion.execute("""
            UPDATE fallas
            SET acciones_realizadas = ?,
                fecha_reparacion = ?,
                fecha_retorno_servicio = ?,
                tiempo_fuera_servicio = ?,
                tecnico = ?,
                estado = ?,
                observaciones = ?
            WHERE id = ?
        """, (
            acciones,
            fecha_reparacion,
            fecha_retorno,
            tiempo_fuera,
            tecnico,
            estado,
            observaciones,
            falla_id
        ))

        conexion.commit()
        conexion.close()

        return redirect(url_for("fallas"))

    conexion.close()

    return render_template(
        "gestionar_falla.html",
        falla=falla
    )
    
@app.route("/fallas/eliminar/<int:falla_id>", methods=["POST"])
def eliminar_falla(falla_id):
    conexion = conectar_bd()

    try:
        # Verificar que la falla exista
        falla = conexion.execute(
            "SELECT id FROM fallas WHERE id = ?",
            (falla_id,)
        ).fetchone()

        if falla is None:
            flash("El registro de falla no existe.", "error")
            return redirect(url_for("fallas"))

        # Eliminar el registro
        conexion.execute(
            "DELETE FROM fallas WHERE id = ?",
            (falla_id,)
        )

        # Guardar los cambios antes de cerrar la conexión
        conexion.commit()

    except Exception as e:
        # Intentar revertir solo si la conexión sigue abierta
        try:
            conexion.rollback()
        except sqlite3.ProgrammingError:
            pass

        print(f"Error al eliminar la falla: {e}")
        flash("No se pudo eliminar el registro de falla.", "error")

        return redirect(url_for("fallas"))

    finally:
        conexion.close()

    flash("Registro de falla eliminado correctamente.", "success")
    return redirect(url_for("fallas"))



# =========================================================
# EQUIPOS
# =========================================================

@app.route("/equipos", methods=["GET", "POST"])
def equipos():

    conexion = conectar_bd()

    # =====================================================
    # REGISTRAR EQUIPO
    # =====================================================

    if request.method == "POST":

        codigo = request.form.get(
            "codigo",
            ""
        ).strip()

        marca = request.form.get(
            "marca",
            ""
        ).strip()

        modelo = request.form.get(
            "modelo",
            ""
        ).strip()

        serie = request.form.get(
            "serie",
            ""
        ).strip()

        ubicacion = request.form.get(
            "ubicacion",
            ""
        ).strip()

        servicio = request.form.get(
            "servicio",
            ""
        ).strip()

        fecha = request.form.get(
            "fecha",
            ""
        ).strip()

        observaciones = request.form.get(
            "observaciones",
            ""
        ).strip()

        # =================================================
        # ESTADO INICIAL DEL EQUIPO
        # =================================================

        estado = "Equipo apto y disponible para su uso"

        # =================================================
        # GUARDAR EQUIPO EN LA BASE DE DATOS
        # =================================================

        cursor = conexion.execute("""
            INSERT INTO equipos (
                codigo,
                marca,
                modelo,
                serie,
                ubicacion,
                servicio,
                estado,
                fecha,
                observaciones
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            codigo,
            marca,
            modelo,
            serie,
            ubicacion,
            servicio,
            estado,
            fecha,
            observaciones
        ))

        id_equipo = cursor.lastrowid

        # IMPORTANTE:
        # Guardamos y cerramos SQLite ANTES de generar el QR.
        conexion.commit()
        conexion.close()

        # =================================================
        # GENERAR QR AUTOMÁTICAMENTE
        # =================================================

        os.makedirs(
            os.path.join(BASE_DIR, "static", "qr"),
            exist_ok=True
        )

        url_qr = f"https://biomedic-jf5o.onrender.com/hoja-vida/{id_equipo}?desde_qr=1"

        imagen_qr = qrcode.make(url_qr)

        ruta_qr = os.path.join(
            BASE_DIR,
            "static",
            "qr",
            f"equipo_{id_equipo}.png"
        )

        imagen_qr.save(ruta_qr)

        return redirect(
            url_for("equipos")
        )

    # =====================================================
    # CONSULTAR EQUIPOS
    # =====================================================

    equipos_registrados = conexion.execute("""
        SELECT *
        FROM equipos
        ORDER BY codigo ASC
    """).fetchall()

    conexion.close()

    return render_template(
        "equipos.html",
        equipos=equipos_registrados
    )
    
# =====================================================
# HOJA DE VIDA DEL EQUIPO
# =====================================================

@app.route("/hoja-vida/<int:id>")
def hoja_vida(id):

    conexion = conectar_bd()

    # Buscar información del equipo
    equipo = conexion.execute("""
        SELECT *
        FROM equipos
        WHERE id = ?
    """, (id,)).fetchone()

    if equipo is None:
        conexion.close()
        return "Equipo no encontrado", 404

    # Buscar mantenimientos del equipo
    mantenimientos_equipo = conexion.execute("""
        SELECT *
        FROM mantenimientos
        WHERE equipo_id = ?
        ORDER BY fecha DESC, id DESC
    """, (id,)).fetchall()

    # Buscar checklists del equipo
    checklists_equipo = conexion.execute("""
        SELECT *
        FROM checklists
        WHERE equipo_id = ?
        ORDER BY fecha DESC, id DESC
    """, (id,)).fetchall()

    # Buscar manuales del equipo
    manuales_equipo = conexion.execute("""
        SELECT *
        FROM manuales
        WHERE equipo_id = ?
        ORDER BY tipo ASC
    """, (id,)).fetchall()

    # Buscar evidencias fotográficas
    evidencias_equipo = conexion.execute("""
        SELECT *
        FROM evidencias
        WHERE equipo_id = ?
        ORDER BY fecha_subida DESC, id DESC
    """, (id,)).fetchall()

    # Buscar fallas del equipo
    fallas_equipo = conexion.execute("""
        SELECT *
        FROM fallas
        WHERE equipo_id = ?
        ORDER BY fecha_falla DESC, id DESC
    """, (id,)).fetchall()

    conexion.close()

    # =====================================================
    # CONSTRUIR HISTORIAL GENERAL
    # =====================================================

    historial_general = []

    # Agregar mantenimientos
    for mantenimiento in mantenimientos_equipo:

        historial_general.append({
            "fecha": mantenimiento["fecha"],
            "tipo_evento": "Mantenimiento",
            "detalle": (
                f"Mantenimiento {mantenimiento['tipo']} "
                f"realizado por {mantenimiento['tecnico']}"
            ),
            "observaciones": mantenimiento["observaciones"]
        })

    # Agregar checklists
    for checklist in checklists_equipo:

        historial_general.append({
            "fecha": checklist["fecha"],
            "tipo_evento": "Checklist",
            "detalle": (
                f"Inspección realizada por {checklist['tecnico']}. "
                f"Resultado: {checklist['resultado']}"
            ),
            "observaciones": checklist["observaciones"]
        })

    # Agregar fallas
    for falla in fallas_equipo:

        historial_general.append({
            "fecha": falla["fecha_falla"],
            "tipo_evento": "Falla",
            "detalle": (
                f"{falla['descripcion']} "
                f"(Gravedad: {falla['gravedad']})"
            ),
            "observaciones": (
                falla["observaciones"] or
                falla["acciones_realizadas"] or
                "Sin observaciones"
            )
        })

    # Agregar evidencias fotográficas
    for evidencia in evidencias_equipo:

        historial_general.append({
            "fecha": evidencia["fecha_subida"],
            "tipo_evento": "Evidencia fotográfica",
            "detalle": (
                evidencia["descripcion"] or
                "Evidencia fotográfica registrada"
            ),
            "observaciones": evidencia["archivo"]
        })

    # Ordenar todas las actividades de la más reciente
    # a la más antigua
    historial_general.sort(
        key=lambda actividad: str(actividad["fecha"] or ""),
        reverse=True
    )

    # Detectar acceso desde código QR
    desde_qr = request.args.get("desde_qr") == "1"

    return render_template(
        "hoja_vida.html",
        equipo=equipo,
        mantenimientos=mantenimientos_equipo,
        checklists=checklists_equipo,
        manuales=manuales_equipo,
        evidencias=evidencias_equipo,
        fallas=fallas_equipo,
        historial_general=historial_general,
        desde_qr=desde_qr
    )

    # =========================================================
# CÓDIGO QR DE LA HOJA DE VIDA
# =========================================================
@app.route("/qr/<int:id>")
def codigo_qr(id):

    import qrcode
    from io import BytesIO
    from flask import send_file

    # URL de la Hoja de Vida del equipo
    url_hoja_vida = f"https://biomedic-jf5o.onrender.com/hoja-vida/{id}"

    # Crear código QR
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )

    qr.add_data(url_hoja_vida)
    qr.make(fit=True)

    imagen = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    # Guardar el QR temporalmente en memoria
    archivo = BytesIO()
    imagen.save(archivo, format="PNG")
    archivo.seek(0)

    return send_file(
        archivo,
        mimetype="image/png"
    )
# =========================================================
# ELIMINAR EQUIPO
# =========================================================
@app.route("/equipos/eliminar/<int:id>", methods=["POST", "GET"])
def eliminar_equipo(id):

    conexion = conectar_bd()


    # =====================================================
    # ELIMINAR MANUALES RELACIONADOS
    # =====================================================

    manuales = conexion.execute("""
        SELECT archivo
        FROM manuales
        WHERE equipo_id = ?
    """, (id,)).fetchall()

    carpeta_equipo = os.path.join(
        app.config["UPLOAD_FOLDER"],
        str(id)
    )
    print("CARPETA EQUIPO:", carpeta_equipo)
    

    for manual in manuales:

        ruta = os.path.join(
            carpeta_equipo,
            manual["archivo"]
        )

        if os.path.exists(ruta):

            try:
                os.remove(ruta)

            except OSError:
                pass

    # =====================================================
    # ELIMINAR REGISTROS RELACIONADOS
    # =====================================================

    conexion.execute("""
        DELETE FROM manuales
        WHERE equipo_id = ?
    """, (id,))

    conexion.execute("""
        DELETE FROM mantenimientos
        WHERE equipo_id = ?
    """, (id,))

    conexion.execute("""
        DELETE FROM checklists
        WHERE equipo_id = ?
    """, (id,))

    conexion.execute("""
        DELETE FROM equipos
        WHERE id = ?
    """, (id,))

    conexion.commit()
    conexion.close()

    return redirect(
        url_for("equipos")
    )


# =========================================================
# MANTENIMIENTOS
# =========================================================

@app.route("/mantenimientos", methods=["GET", "POST"])
def mantenimientos():

    conexion = conectar_bd()

    # =====================================================
    # REGISTRAR MANTENIMIENTO
    # =====================================================

    if request.method == "POST":

        equipo_id = request.form.get(
            "equipo_id"
        )

        tipo = request.form.get(
            "tipo",
            ""
        ).strip()

        fecha = request.form.get(
            "fecha",
            ""
        ).strip()

        proxima_fecha = request.form.get(
            "proxima_fecha",
            ""
        ).strip()

        tecnico = request.form.get(
            "tecnico",
            ""
        ).strip()

        observaciones = request.form.get(
            "observaciones",
            ""
        ).strip()

        conexion.execute("""
            INSERT INTO mantenimientos (
                equipo_id,
                tipo,
                fecha,
                proxima_fecha,
                tecnico,
                observaciones
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            equipo_id,
            tipo,
            fecha,
            proxima_fecha,
            tecnico,
            observaciones
        ))

        conexion.commit()
        conexion.close()

        return redirect(
            url_for("mantenimientos")
        )

    # =====================================================
    # EQUIPOS
    # =====================================================

    equipos_registrados = conexion.execute("""
        SELECT *
        FROM equipos
        ORDER BY codigo ASC
    """).fetchall()

    # =====================================================
    # MANTENIMIENTOS
    # =====================================================

    mantenimientos_registrados = conexion.execute("""
        SELECT
            mantenimientos.*,
            equipos.codigo,
            equipos.marca,
            equipos.modelo
        FROM mantenimientos
        INNER JOIN equipos
            ON mantenimientos.equipo_id = equipos.id
        ORDER BY
            mantenimientos.fecha DESC,
            mantenimientos.id DESC
    """).fetchall()

    # =====================================================
    # CALCULAR ESTADO
    # =====================================================

    mantenimientos_lista = []

    hoy = date.today()

    for mantenimiento in mantenimientos_registrados:

        try:

            fecha_proxima = datetime.strptime(
                mantenimiento["proxima_fecha"],
                "%Y-%m-%d"
            ).date()

            diferencia = (
                fecha_proxima - hoy
            ).days

            if diferencia < 0:

                estado_mantenimiento = "VENCIDO"

            elif diferencia <= 30:

                estado_mantenimiento = "PRÓXIMO"

            else:

                estado_mantenimiento = "AL DÍA"

        except (ValueError, TypeError):

            estado_mantenimiento = "SIN FECHA"

        mantenimientos_lista.append({

            "id":
                mantenimiento["id"],

            "equipo_id":
                mantenimiento["equipo_id"],

            "codigo":
                mantenimiento["codigo"],

            "marca":
                mantenimiento["marca"],

            "modelo":
                mantenimiento["modelo"],

            "tipo":
                mantenimiento["tipo"],

            "fecha":
                mantenimiento["fecha"],

            "proxima_fecha":
                mantenimiento["proxima_fecha"],

            "tecnico":
                mantenimiento["tecnico"],

            "observaciones":
                mantenimiento["observaciones"],

            "estado_mantenimiento":
                estado_mantenimiento
        })

    conexion.close()

    return render_template(
        "mantenimientos.html",
        equipos=equipos_registrados,
        mantenimientos=mantenimientos_lista
    )


# =========================================================
# ELIMINAR MANTENIMIENTO
# =========================================================

@app.route(
    "/mantenimientos/eliminar/<int:id>",
    methods=["GET", "POST"]
)
def eliminar_mantenimiento(id):

    conexion = conectar_bd()

    conexion.execute("""
        DELETE FROM mantenimientos
        WHERE id = ?
    """, (id,))

    conexion.commit()
    conexion.close()

    return redirect(
        url_for("mantenimientos")
    )


# =========================================================
# CHECKLIST
# =========================================================

@app.route("/checklist", methods=["GET", "POST"])
def checklist():

    conexion = conectar_bd()

    # =====================================================
    # GUARDAR CHECKLIST
    # =====================================================

    if request.method == "POST":

        equipo_id = request.form.get(
            "equipo_id"
        )

        fecha = request.form.get(
            "fecha",
            ""
        ).strip()

        tecnico = request.form.get(
            "tecnico",
            ""
        ).strip()

        inspeccion_visual = request.form.get(
            "inspeccion_visual"
        )

        estado_fisico = request.form.get(
            "estado_fisico"
        )

        cable_alimentacion = request.form.get(
            "cable_alimentacion"
        )

        pantalla = request.form.get(
            "pantalla"
        )

        alarmas = request.form.get(
            "alarmas"
        )

        encendido = request.form.get(
            "encendido"
        )

        bateria = request.form.get(
            "bateria"
        )

        circuito_respiratorio = request.form.get(
            "circuito_respiratorio"
        )

        filtros = request.form.get(
            "filtros"
        )

        sensores = request.form.get(
            "sensores"
        )

        prueba_funcionamiento = request.form.get(
            "prueba_funcionamiento"
        )

        limpieza = request.form.get(
            "limpieza"
        )

        observaciones = request.form.get(
            "observaciones",
            ""
        ).strip()

        # =================================================
        # RESPUESTAS
        # =================================================

        respuestas = [

            inspeccion_visual,
            estado_fisico,
            cable_alimentacion,
            pantalla,
            alarmas,
            encendido,
            bateria,
            circuito_respiratorio,
            filtros,
            sensores,
            prueba_funcionamiento,
            limpieza

        ]

        # =================================================
        # RESULTADO
        # =================================================

        cantidad_no_cumple = respuestas.count(
            "No cumple"
        )

        cantidad_atencion = respuestas.count(
            "Atención"
        )

        if cantidad_no_cumple > 0:

            resultado = "NO APROBADO"

        elif cantidad_atencion > 0:

            resultado = "ATENCIÓN REQUERIDA"

        else:

            resultado = "APROBADO"

        # =================================================
        # INSERTAR
        # =================================================

        conexion.execute("""
            INSERT INTO checklists (
                equipo_id,
                fecha,
                tecnico,
                inspeccion_visual,
                estado_fisico,
                cable_alimentacion,
                pantalla,
                alarmas,
                encendido,
                bateria,
                circuito_respiratorio,
                filtros,
                sensores,
                prueba_funcionamiento,
                limpieza,
                observaciones,
                resultado
            )
            VALUES (
                ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?
            )
        """, (
            equipo_id,
            fecha,
            tecnico,
            inspeccion_visual,
            estado_fisico,
            cable_alimentacion,
            pantalla,
            alarmas,
            encendido,
            bateria,
            circuito_respiratorio,
            filtros,
            sensores,
            prueba_funcionamiento,
            limpieza,
            observaciones,
            resultado
        ))

        conexion.commit()
        conexion.close()

        return redirect(
            url_for("checklist")
        )

    # =====================================================
    # EQUIPOS
    # =====================================================

    equipos_registrados = conexion.execute("""
        SELECT *
        FROM equipos
        ORDER BY codigo ASC
    """).fetchall()

    # =====================================================
    # CHECKLISTS
    # =====================================================

    checklists_registrados = conexion.execute("""
        SELECT
            checklists.*,
            equipos.codigo,
            equipos.marca,
            equipos.modelo
        FROM checklists
        INNER JOIN equipos
            ON checklists.equipo_id = equipos.id
        ORDER BY
            checklists.fecha DESC,
            checklists.id DESC
    """).fetchall()

    conexion.close()

    return render_template(
        "checklist.html",
        equipos=equipos_registrados,
        checklists=checklists_registrados
    )


# =========================================================
# NUEVO CHECKLIST
# =========================================================

@app.route("/checklist_nuevo")
def checklist_nuevo():

    conexion = conectar_bd()

    equipos_registrados = conexion.execute("""
        SELECT *
        FROM equipos
        ORDER BY codigo ASC
    """).fetchall()

    conexion.close()

    return render_template(
        "nuevo_checklist.html",
        equipos=equipos_registrados
    )


# =========================================================
# LISTA DE CHECKLISTS
# =========================================================

@app.route("/checklists")
def checklists():

    conexion = conectar_bd()

    lista_checklists = conexion.execute("""
        SELECT
            checklists.*,
            equipos.codigo,
            equipos.marca,
            equipos.modelo
        FROM checklists
        INNER JOIN equipos
            ON checklists.equipo_id = equipos.id
        ORDER BY
            checklists.fecha DESC,
            checklists.id DESC
    """).fetchall()

    conexion.close()

    return render_template(
        "lista_checklists.html",
        checklists=lista_checklists
    )


# =========================================================
# VER CHECKLIST
# =========================================================

@app.route("/ver_checklist/<int:id>")
def ver_checklist(id):

    conexion = conectar_bd()

    checklist_registrado = conexion.execute("""
        SELECT
            checklists.*,
            equipos.codigo,
            equipos.marca,
            equipos.modelo,
            equipos.serie,
            equipos.ubicacion,
            equipos.servicio
        FROM checklists
        INNER JOIN equipos
            ON checklists.equipo_id = equipos.id
        WHERE checklists.id = ?
    """, (id,)).fetchone()

    conexion.close()

    if checklist_registrado is None:

        return "Checklist no encontrado", 404

    return render_template(
        "ver_checklist.html",
        checklist=checklist_registrado
    )


# =========================================================
# RUTA ALTERNATIVA CHECKLIST
# =========================================================

@app.route("/checklist/ver/<int:id>")
def checklist_ver(id):

    return redirect(
        url_for(
            "ver_checklist",
            id=id
        )
    )


# =========================================================
# ELIMINAR CHECKLIST
# =========================================================

@app.route(
    "/checklist/eliminar/<int:id>",
    methods=["GET", "POST"]
)
def eliminar_checklist(id):

    conexion = conectar_bd()

    conexion.execute("""
        DELETE FROM checklists
        WHERE id = ?
    """, (id,))

    conexion.commit()
    conexion.close()

    return redirect(
        url_for("checklist")
    )

    # =====================================================
# PRUEBAS FUNCIONALES
# =====================================================

@app.route("/pruebas-funcionales", methods=["GET", "POST"])
def pruebas_funcionales():

    conexion = conectar_bd()

    # =================================================
    # GUARDAR PRUEBA FUNCIONAL
    # =================================================

    if request.method == "POST":

        equipo_id = request.form.get("equipo_id")
        fecha = request.form.get("fecha", "").strip()
        tipo_prueba = request.form.get("tipo_prueba", "").strip()
        parametro = request.form.get("parametro", "").strip()
        valor_referencia = request.form.get("valor_referencia")
        valor_medido = request.form.get("valor_medido")
        unidad = request.form.get("unidad", "").strip()
        limite_inferior = request.form.get("limite_inferior")
        limite_superior = request.form.get("limite_superior")
        tecnico = request.form.get("tecnico", "").strip()
        observaciones = request.form.get("observaciones", "").strip()

        try:
            medido = float(valor_medido)
            inferior = float(limite_inferior)
            superior = float(limite_superior)

            if inferior > superior:
                conexion.close()
                return "El límite inferior no puede ser mayor al superior.", 400

            if inferior <= medido <= superior:
                resultado = "APROBADO"
            else:
                resultado = "NO APROBADO"

            referencia = (
                float(valor_referencia)
                if valor_referencia else None
            )

        except (ValueError, TypeError):
            conexion.close()
            return "Verifica los valores numéricos de la prueba.", 400

        conexion.execute("""
            INSERT INTO pruebas_funcionales (
                equipo_id,
                fecha,
                tipo_prueba,
                parametro,
                valor_referencia,
                valor_medido,
                unidad,
                limite_inferior,
                limite_superior,
                resultado,
                tecnico,
                observaciones
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            equipo_id,
            fecha,
            tipo_prueba,
            parametro,
            referencia,
            medido,
            unidad,
            inferior,
            superior,
            resultado,
            tecnico,
            observaciones
        ))

        conexion.commit()
        conexion.close()

        return redirect(url_for("pruebas_funcionales"))

    # =================================================
    # CONSULTAR EQUIPOS
    # =================================================

    equipos = conexion.execute("""
        SELECT *
        FROM equipos
        ORDER BY codigo ASC
    """).fetchall()

    # =================================================
    # CONSULTAR PRUEBAS REGISTRADAS
    # =================================================

    pruebas = conexion.execute("""
        SELECT
            pruebas_funcionales.*,
            equipos.codigo,
            equipos.marca,
            equipos.modelo
        FROM pruebas_funcionales
        INNER JOIN equipos
            ON pruebas_funcionales.equipo_id = equipos.id
        ORDER BY pruebas_funcionales.fecha DESC,
                 pruebas_funcionales.id DESC
    """).fetchall()

    conexion.close()

    return render_template(
        "pruebas_funcionales.html",
        equipos=equipos,
        pruebas=pruebas
    )

# =====================================================
# ELIMINAR PRUEBA FUNCIONAL
# =====================================================

@app.route("/eliminar-prueba-funcional/<int:prueba_id>", methods=["POST"])
def eliminar_prueba_funcional(prueba_id):

    conexion = conectar_bd()

    conexion.execute("""
        DELETE FROM pruebas_funcionales
        WHERE id = ?
    """, (prueba_id,))

    conexion.commit()
    conexion.close()

    return redirect(url_for("pruebas_funcionales"))

# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():
    conexion = conectar_bd()

    try:
        # =====================================================
        # RESUMEN DE EQUIPOS
        # =====================================================

        total_equipos = conexion.execute("""
            SELECT COUNT(*) AS total FROM equipos
        """).fetchone()["total"]

        equipos_operativos = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM equipos
            WHERE estado = 'Equipo apto y disponible para su uso'
        """).fetchone()["total"]

        equipos_mantenimiento = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM mantenimientos
            WHERE id IN (
                SELECT MAX(id)
                FROM mantenimientos
                GROUP BY equipo_id
            )
        """).fetchone()["total"]

        equipos_fuera_servicio = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM equipos
            WHERE estado = 'Fuera de servicio'
        """).fetchone()["total"]

        # =====================================================
        # RESUMEN DE CHECKLISTS
        # =====================================================

        total_checklists = conexion.execute("""
            SELECT COUNT(*) AS total FROM checklists
        """).fetchone()["total"]

        checklists_aprobados = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM checklists
            WHERE resultado = 'APROBADO'
        """).fetchone()["total"]

        checklists_atencion = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM checklists
            WHERE resultado = 'ATENCIÓN REQUERIDA'
        """).fetchone()["total"]

        checklists_no_aprobados = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM checklists
            WHERE resultado = 'NO APROBADO'
        """).fetchone()["total"]

        porcentaje_checklists_aprobados = (
            round(checklists_aprobados / total_checklists * 100, 1)
            if total_checklists > 0 else 0
        )

        # =====================================================
        # RESUMEN DE MANTENIMIENTOS
        # =====================================================

        total_mantenimientos = conexion.execute("""
            SELECT COUNT(*) AS total FROM mantenimientos
        """).fetchone()["total"]

        hoy = date.today().isoformat()

        mantenimientos_proximos = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM mantenimientos
            WHERE proxima_fecha >= ?
              AND proxima_fecha <= date(?, '+30 day')
        """, (hoy, hoy)).fetchone()["total"]

        mantenimientos_vencidos = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM mantenimientos
            WHERE proxima_fecha < ?
        """, (hoy,)).fetchone()["total"]

        mantenimientos_al_dia = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM mantenimientos
            WHERE proxima_fecha > date(?, '+30 day')
        """, (hoy,)).fetchone()["total"]

        # =====================================================
        # EVIDENCIAS Y REGISTROS PENDIENTES
        # =====================================================

        total_evidencias = conexion.execute("""
            SELECT COUNT(*) AS total FROM evidencias
        """).fetchone()["total"]

        equipos_sin_checklist = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM equipos e
            WHERE NOT EXISTS (
                SELECT 1 FROM checklists c
                WHERE c.equipo_id = e.id
            )
        """).fetchone()["total"]

        equipos_sin_mantenimiento = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM equipos e
            WHERE NOT EXISTS (
                SELECT 1 FROM mantenimientos m
                WHERE m.equipo_id = e.id
            )
        """).fetchone()["total"]

        # =====================================================
        # ÚLTIMOS CHECKLISTS
        # =====================================================

        ultimos_checklists = conexion.execute("""
            SELECT c.*, e.codigo, e.marca, e.modelo
            FROM checklists c
            INNER JOIN equipos e ON c.equipo_id = e.id
            ORDER BY c.fecha DESC, c.id DESC
            LIMIT 10
        """).fetchall()

        # =====================================================
        # ÚLTIMOS MANTENIMIENTOS
        # =====================================================

        ultimos_mantenimientos = conexion.execute("""
            SELECT m.*, e.codigo, e.marca, e.modelo
            FROM mantenimientos m
            INNER JOIN equipos e ON m.equipo_id = e.id
            ORDER BY m.fecha DESC, m.id DESC
            LIMIT 10
        """).fetchall()

        # =====================================================
        # RESUMEN DE FALLAS
        # =====================================================

        total_fallas = conexion.execute("""
            SELECT COUNT(*) AS total FROM fallas
        """).fetchone()["total"]

        fallas_pendientes = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM fallas
            WHERE estado = 'Pendiente'
        """).fetchone()["total"]

        fallas_en_reparacion = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM fallas
            WHERE estado = 'En reparación'
        """).fetchone()["total"]

        fallas_reparadas = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM fallas
            WHERE estado = 'Reparada'
        """).fetchone()["total"]

        ultimas_fallas = conexion.execute("""
            SELECT
                f.id,
                f.fecha_falla,
                f.descripcion,
                f.gravedad,
                f.tecnico,
                f.estado,
                e.codigo,
                e.marca,
                e.modelo
            FROM fallas f
            INNER JOIN equipos e ON f.equipo_id = e.id
            ORDER BY f.fecha_falla DESC, f.id DESC
            LIMIT 10
        """).fetchall()

        # =====================================================
        # MTTR: TIEMPO MEDIO DE REPARACIÓN, EN HORAS
        # =====================================================

        mttr_resultado = conexion.execute("""
            SELECT AVG(tiempo_fuera_servicio) AS promedio
            FROM fallas
            WHERE estado = 'Reparada'
              AND tiempo_fuera_servicio IS NOT NULL
              AND tiempo_fuera_servicio >= 0
        """).fetchone()["promedio"]

        mttr = round(mttr_resultado, 2) if mttr_resultado is not None else 0

        # =====================================================
        # MTBF: INTERVALO MEDIO ENTRE FALLAS, EN HORAS
        # =====================================================

        registros_fallas = conexion.execute("""
            SELECT equipo_id, fecha_falla
            FROM fallas
            WHERE fecha_falla IS NOT NULL
              AND TRIM(fecha_falla) != ''
            ORDER BY equipo_id, fecha_falla, id
        """).fetchall()

        fallas_por_equipo = {}
        intervalos_mtbf = []

        for registro in registros_fallas:
            equipo_id = registro["equipo_id"]
            fecha_texto = str(registro["fecha_falla"]).strip()

            try:
                fecha_falla = datetime.fromisoformat(fecha_texto)
            except (ValueError, TypeError):
                continue

            fallas_por_equipo.setdefault(equipo_id, []).append(
                fecha_falla
            )

        for fechas in fallas_por_equipo.values():
            fechas.sort()

            for i in range(1, len(fechas)):
                horas = (
                    fechas[i] - fechas[i - 1]
                ).total_seconds() / 3600

                if horas > 0:
                    intervalos_mtbf.append(horas)

        mtbf = (
            round(sum(intervalos_mtbf) / len(intervalos_mtbf), 2)
            if intervalos_mtbf
            else None
        )


        # =====================================================
        # DISPONIBILIDAD OPERATIVA ACTUAL
        # =====================================================

        disponibilidad = (
            round(equipos_operativos / total_equipos * 100, 1)
            if total_equipos > 0 else 0
        )

    finally:
        conexion.close()

    # =====================================================
    # ENVIAR DATOS AL HTML
    # =====================================================

    return render_template(
        "dashboard.html",
        total_equipos=total_equipos,
        equipos_operativos=equipos_operativos,
        equipos_mantenimiento=equipos_mantenimiento,
        equipos_fuera_servicio=equipos_fuera_servicio,
        total_checklists=total_checklists,
        checklists_aprobados=checklists_aprobados,
        checklists_atencion=checklists_atencion,
        checklists_no_aprobados=checklists_no_aprobados,
        porcentaje_checklists_aprobados=porcentaje_checklists_aprobados,
        total_mantenimientos=total_mantenimientos,
        mantenimientos_al_dia=mantenimientos_al_dia,
        mantenimientos_proximos=mantenimientos_proximos,
        mantenimientos_vencidos=mantenimientos_vencidos,
        total_evidencias=total_evidencias,
        equipos_sin_checklist=equipos_sin_checklist,
        equipos_sin_mantenimiento=equipos_sin_mantenimiento,
        ultimos_checklists=ultimos_checklists,
        ultimos_mantenimientos=ultimos_mantenimientos,
        total_fallas=total_fallas,
        fallas_pendientes=fallas_pendientes,
        fallas_en_reparacion=fallas_en_reparacion,
        fallas_reparadas=fallas_reparadas,
        ultimas_fallas=ultimas_fallas,
        mtbf=mtbf,
        mttr=mttr,
        disponibilidad=disponibilidad
    )

# =========================================================
# REPORTES GENERALES
# =========================================================

@app.route("/reportes")
def reportes():

    conexion = conectar_bd()

    try:
        # Resumen de equipos
        total_equipos = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM equipos
        """).fetchone()["total"]

        equipos_operativos = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM equipos
            WHERE estado = 'Equipo apto y disponible para su uso'
        """).fetchone()["total"]

        equipos_fuera_servicio = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM equipos
            WHERE estado = 'Fuera de servicio'
        """).fetchone()["total"]

        # Resumen de mantenimientos
        total_mantenimientos = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM mantenimientos
        """).fetchone()["total"]

        # Resumen de checklists
        total_checklists = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM checklists
        """).fetchone()["total"]

        checklists_aprobados = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM checklists
            WHERE resultado = 'APROBADO'
        """).fetchone()["total"]

        checklists_no_aprobados = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM checklists
            WHERE resultado = 'NO APROBADO'
        """).fetchone()["total"]

        # Resumen de fallas
        total_fallas = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM fallas
        """).fetchone()["total"]

        fallas_pendientes = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM fallas
            WHERE estado = 'Pendiente'
        """).fetchone()["total"]

        fallas_en_reparacion = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM fallas
            WHERE estado = 'En reparación'
        """).fetchone()["total"]

        fallas_reparadas = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM fallas
            WHERE estado = 'Reparada'
        """).fetchone()["total"]

        # Equipos disponibles para generar informes técnicos
        equipos = conexion.execute("""
            SELECT id, codigo, marca, modelo, serie, ubicacion,
                   servicio, estado, fecha, observaciones
            FROM equipos
            ORDER BY codigo ASC
        """).fetchall()

    finally:
        conexion.close()

    return render_template(
        "reportes.html",
        total_equipos=total_equipos,
        equipos_operativos=equipos_operativos,
        equipos_fuera_servicio=equipos_fuera_servicio,
        total_mantenimientos=total_mantenimientos,
        total_checklists=total_checklists,
        checklists_aprobados=checklists_aprobados,
        checklists_no_aprobados=checklists_no_aprobados,
        total_fallas=total_fallas,
        fallas_pendientes=fallas_pendientes,
        fallas_en_reparacion=fallas_en_reparacion,
        fallas_reparadas=fallas_reparadas,
        equipos=equipos
    )
    
# =========================================================
# GENERAR INFORME TÉCNICO DEL EQUIPO
# =========================================================

@app.route("/informe-tecnico/<int:equipo_id>")
def informe_tecnico(equipo_id):

    conexion = conectar_bd()

    try:
        equipo = conexion.execute("""
            SELECT *
            FROM equipos
            WHERE id = ?
        """, (equipo_id,)).fetchone()

        if equipo is None:
            flash("El equipo solicitado no existe.", "error")
            return redirect(url_for("reportes"))

        mantenimientos = conexion.execute("""
            SELECT *
            FROM mantenimientos
            WHERE equipo_id = ?
            ORDER BY fecha DESC, id DESC
        """, (equipo_id,)).fetchall()

        checklists = conexion.execute("""
            SELECT *
            FROM checklists
            WHERE equipo_id = ?
            ORDER BY fecha DESC, id DESC
        """, (equipo_id,)).fetchall()

        fallas = conexion.execute("""
            SELECT *
            FROM fallas
            WHERE equipo_id = ?
            ORDER BY fecha_falla DESC, id DESC
        """, (equipo_id,)).fetchall()

        evidencias = conexion.execute("""
            SELECT *
            FROM evidencias
            WHERE equipo_id = ?
            ORDER BY fecha_subida DESC, id DESC
        """, (equipo_id,)).fetchall()

    finally:
        conexion.close()

    return render_template(
        "informe_tecnico.html",
        equipo=equipo,
        mantenimientos=mantenimientos,
        checklists=checklists,
        fallas=fallas,
        evidencias=evidencias,
        fecha_informe=date.today().strftime("%d/%m/%Y")
    )



    # =====================================================
    # RESUMEN DE EQUIPOS
    # =====================================================

    total_equipos = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM equipos
    """).fetchone()["total"]

    equipos_operativos = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM equipos
        WHERE estado = 'Equipo apto y disponible para su uso'
    """).fetchone()["total"]

    equipos_mantenimiento = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM mantenimientos
        WHERE id IN (
            SELECT MAX(id)
            FROM mantenimientos
            GROUP BY equipo_id
        )
    """).fetchone()["total"]

    equipos_fuera_servicio = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM equipos
        WHERE estado = 'Fuera de servicio'
    """).fetchone()["total"]

    # =====================================================
    # RESUMEN DE CHECKLISTS
    # =====================================================

    total_checklists = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM checklists
    """).fetchone()["total"]

    checklists_aprobados = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM checklists
        WHERE resultado = 'APROBADO'
    """).fetchone()["total"]

    checklists_atencion = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM checklists
        WHERE resultado = 'ATENCIÓN REQUERIDA'
    """).fetchone()["total"]

    checklists_no_aprobados = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM checklists
        WHERE resultado = 'NO APROBADO'
    """).fetchone()["total"]

    # =====================================================
    # RESUMEN DE MANTENIMIENTOS
    # =====================================================

    total_mantenimientos = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM mantenimientos
    """).fetchone()["total"]
    
    # =====================================================
    # NUEVOS INDICADORES DEL DASHBOARD
    # =====================================================

    # Total de evidencias fotográficas
    total_evidencias = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM evidencias
    """).fetchone()["total"]

    # Equipos que no tienen checklists registrados
    equipos_sin_checklist = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM equipos e
        WHERE NOT EXISTS (
            SELECT 1
            FROM checklists c
            WHERE c.equipo_id = e.id
        )
    """).fetchone()["total"]

    # Equipos que no tienen mantenimientos registrados
    equipos_sin_mantenimiento = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM equipos e
        WHERE NOT EXISTS (
            SELECT 1
            FROM mantenimientos m
            WHERE m.equipo_id = e.id
        )
    """).fetchone()["total"]

    # Porcentaje de checklists aprobados
    porcentaje_checklists_aprobados = (
        round(
            checklists_aprobados / total_checklists * 100,
            1
        )
        if total_checklists > 0
        else 0
    )


    # =====================================================
    # FECHA ACTUAL
    # =====================================================

    hoy = date.today().isoformat()

    # =====================================================
    # MANTENIMIENTOS PRÓXIMOS
    # =====================================================

    mantenimientos_proximos = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM mantenimientos
        WHERE proxima_fecha >= ?
        AND proxima_fecha <= date(?, '+30 day')
    """, (
        hoy,
        hoy
    )).fetchone()["total"]

    # =====================================================
    # MANTENIMIENTOS VENCIDOS
    # =====================================================

    mantenimientos_vencidos = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM mantenimientos
        WHERE proxima_fecha < ?
    """, (
        hoy,
    )).fetchone()["total"]

    # =====================================================
    # MANTENIMIENTOS AL DÍA
    # =====================================================

    mantenimientos_al_dia = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM mantenimientos
        WHERE proxima_fecha > date(?, '+30 day')
    """, (
        hoy,
    )).fetchone()["total"]

    # =====================================================
    # ÚLTIMOS CHECKLISTS
    # =====================================================

    ultimos_checklists = conexion.execute("""
        SELECT
            checklists.*,
            equipos.codigo,
            equipos.marca,
            equipos.modelo
        FROM checklists
        INNER JOIN equipos
            ON checklists.equipo_id = equipos.id
        ORDER BY
            checklists.fecha DESC,
            checklists.id DESC
        LIMIT 10
    """).fetchall()

    # =====================================================
    # ÚLTIMOS MANTENIMIENTOS
    # =====================================================

    ultimos_mantenimientos = conexion.execute("""
        SELECT
            mantenimientos.*,
            equipos.codigo,
            equipos.marca,
            equipos.modelo
        FROM mantenimientos
        INNER JOIN equipos
            ON mantenimientos.equipo_id = equipos.id
        ORDER BY
            mantenimientos.fecha DESC,
            mantenimientos.id DESC
        LIMIT 10
    """).fetchall()

    
    # =====================================================
    # RESUMEN DE FALLAS
    # =====================================================

    total_fallas = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM fallas
    """).fetchone()["total"]

    fallas_pendientes = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM fallas
        WHERE estado = 'Pendiente'
    """).fetchone()["total"]

    fallas_en_reparacion = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM fallas
        WHERE estado = 'En reparación'
    """).fetchone()["total"]

    fallas_reparadas = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM fallas
        WHERE estado = 'Reparada'
    """).fetchone()["total"]

    # =====================================================
    # ÚLTIMAS FALLAS REGISTRADAS
    # =====================================================

    ultimas_fallas = conexion.execute("""
        SELECT
            f.id,
            f.fecha_falla,
            f.descripcion,
            f.gravedad,
            f.tecnico,
            f.estado,
            e.codigo,
            e.marca,
            e.modelo
        FROM fallas f
        INNER JOIN equipos e ON f.equipo_id = e.id
        ORDER BY f.fecha_falla DESC, f.id DESC
        LIMIT 10
    """).fetchall()
    
    # =====================================================
    # INDICADORES MTBF, MTTR Y DISPONIBILIDAD
    # =====================================================

    # MTTR: tiempo medio de reparación en horas.
    # Se utilizan fallas reparadas que tengan tiempo registrado.
    mttr = conexion.execute("""
        SELECT AVG(tiempo_fuera_servicio) AS promedio
        FROM fallas
        WHERE estado = 'Reparada'
        AND tiempo_fuera_servicio IS NOT NULL
        AND tiempo_fuera_servicio >= 0
    """).fetchone()["promedio"]

    mttr = round(mttr, 2) if mttr is not None else 0

    # MTBF: promedio de horas entre fallas consecutivas
    # del mismo equipo. Se necesitan al menos dos fallas
    # registradas en un mismo equipo para calcular un intervalo.
    registros_fallas = conexion.execute("""
        SELECT equipo_id, fecha_falla
        FROM fallas
        WHERE fecha_falla IS NOT NULL
        ORDER BY equipo_id, fecha_falla
    """).fetchall()

    fallas_por_equipo = {}
    intervalos_mtbf = []

    for registro in registros_fallas:
        equipo_id = registro["equipo_id"]
        fecha_texto = str(registro["fecha_falla"])[:10]

        try:
            fecha_falla = date.fromisoformat(fecha_texto)
        except (ValueError, TypeError):
            continue

        if equipo_id not in fallas_por_equipo:
            fallas_por_equipo[equipo_id] = []

        fallas_por_equipo[equipo_id].append(fecha_falla)

    for fechas in fallas_por_equipo.values():
        fechas.sort()

        for i in range(1, len(fechas)):
            horas = (fechas[i] - fechas[i - 1]).total_seconds() / 3600
            intervalos_mtbf.append(horas)

    mtbf = (
        round(sum(intervalos_mtbf) / len(intervalos_mtbf), 2)
        if intervalos_mtbf
        else None
    )

    # Disponibilidad operativa actual según el estado
    # registrado para los equipos en BioMedic.
    disponibilidad = (
        round(equipos_operativos / total_equipos * 100, 1)
        if total_equipos > 0
        else 0
    )

    # =====================================================
    # CERRAR CONEXIÓN
    # =====================================================

    conexion.close()

    # =====================================================
    # ENVIAR INFORMACIÓN AL HTML
    # =====================================================

    return render_template(
        "dashboard.html",
        total_evidencias=total_evidencias,
        equipos_sin_checklist=equipos_sin_checklist,
        equipos_sin_mantenimiento=equipos_sin_mantenimiento,
        porcentaje_checklists_aprobados=porcentaje_checklists_aprobados,

        total_equipos=total_equipos,

        equipos_operativos=equipos_operativos,

        equipos_mantenimiento=equipos_mantenimiento,

        equipos_fuera_servicio=equipos_fuera_servicio,

        total_checklists=total_checklists,

        checklists_aprobados=checklists_aprobados,

        checklists_atencion=checklists_atencion,

        checklists_no_aprobados=checklists_no_aprobados,

        total_mantenimientos=total_mantenimientos,

        mantenimientos_al_dia=mantenimientos_al_dia,

        mantenimientos_proximos=mantenimientos_proximos,

        mantenimientos_vencidos=mantenimientos_vencidos,

        ultimos_checklists=ultimos_checklists,
        ultimos_mantenimientos=ultimos_mantenimientos,
        total_fallas=total_fallas,
        fallas_pendientes=fallas_pendientes,
        fallas_en_reparacion=fallas_en_reparacion,
        fallas_reparadas=fallas_reparadas,
        mtbf=mtbf,
        mttr=mttr,
        disponibilidad=disponibilidad,
        ultimas_fallas=ultimas_fallas
    )


# =========================================================
# MANUALES
# =========================================================

@app.route("/manuales")
def manuales():

    conexion = conectar_bd()

    equipos_registrados = conexion.execute("""
        SELECT
            id,
            codigo,
            marca,
            modelo,
            serie,
            ubicacion,
            servicio,
            estado
        FROM equipos
        ORDER BY codigo ASC
    """).fetchall()

    conexion.close()

    return render_template(
        "manuales.html",
        equipos=equipos_registrados
    )


# =========================================================
# MANUALES DE UN EQUIPO
# =========================================================

@app.route("/manuales/<int:id>")
def manual_equipo(id):

    conexion = conectar_bd()

    # =====================================================
    # BUSCAR EQUIPO
    # =====================================================

    equipo = conexion.execute("""
        SELECT
            id,
            codigo,
            marca,
            modelo,
            serie,
            ubicacion,
            servicio,
            estado,
            fecha,
            observaciones
        FROM equipos
        WHERE id = ?
    """, (id,)).fetchone()

    if equipo is None:

        conexion.close()

        return "Equipo no encontrado", 404

    # =====================================================
    # BUSCAR MANUALES
    # =====================================================

    manuales_registrados = conexion.execute("""
        SELECT
            id,
            equipo_id,
            tipo,
            archivo,
            fecha_subida
        FROM manuales
        WHERE equipo_id = ?
        ORDER BY tipo ASC
    """, (id,)).fetchall()

    conexion.close()

    return render_template(
        "manual_equipo.html",
        equipo=equipo,
        manuales=manuales_registrados
    )


# =========================================================
# SUBIR MANUAL
# =========================================================

@app.route(
    "/manuales/<int:id>/subir",
    methods=["POST"]
)
def subir_manual(id):

    tipo = request.form.get(
        "tipo"
    )

    archivo = request.files.get(
        "archivo"
    )

    # =====================================================
    # TIPOS PERMITIDOS
    # =====================================================

    tipos_permitidos = [
        "usuario",
        "servicio_tecnico",
        "mantenimiento"
    ]

    if tipo not in tipos_permitidos:

        return "Tipo de manual no válido.", 400

    # =====================================================
    # VALIDAR ARCHIVO
    # =====================================================

    if archivo is None:

        return "No se seleccionó ningún archivo.", 400

    if archivo.filename == "":

        return "No se seleccionó ningún archivo.", 400

    if not archivo_permitido(
        archivo.filename
    ):

        return "Solo se permiten archivos PDF.", 400

    # =====================================================
    # NOMBRE SEGURO
    # =====================================================

    nombre_original = secure_filename(
        archivo.filename
    )

    if not nombre_original:

        return "Nombre de archivo no válido.", 400

    # =====================================================
    # CONEXIÓN
    # =====================================================

    conexion = conectar_bd()

    equipo = conexion.execute("""
        SELECT
            id,
            codigo
        FROM equipos
        WHERE id = ?
    """, (id,)).fetchone()

    if equipo is None:

        conexion.close()

        return "Equipo no encontrado.", 404

    # =====================================================
    # CARPETA
    # =====================================================

    carpeta_equipo = os.path.join(
        app.config["UPLOAD_FOLDER"],
        str(id)
    )

    os.makedirs(
        carpeta_equipo,
        exist_ok=True
    )

    # =====================================================
    # NOMBRE FINAL
    # =====================================================

    nombre_archivo = (
        tipo
        + "_"
        + nombre_original
    )

    ruta_archivo = os.path.join(
        carpeta_equipo,
        nombre_archivo
    )

    # =====================================================
    # BUSCAR MANUAL ANTERIOR
    # =====================================================

    manual_anterior = conexion.execute("""
        SELECT
            id,
            archivo
        FROM manuales
        WHERE equipo_id = ?
        AND tipo = ?
    """, (
        id,
        tipo
    )).fetchone()

    # =====================================================
    # ELIMINAR ARCHIVO ANTERIOR
    # =====================================================

    if manual_anterior:

        ruta_anterior = os.path.join(
            carpeta_equipo,
            manual_anterior["archivo"]
        )

        if os.path.exists(
            ruta_anterior
        ):

            try:

                os.remove(
                    ruta_anterior
                )

            except OSError:

                pass

    # =====================================================
    # GUARDAR ARCHIVO
    # =====================================================

    archivo.save(
        ruta_archivo
    )

    # =====================================================
    # FECHA
    # =====================================================

    fecha_subida = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # =====================================================
    # ACTUALIZAR
    # =====================================================

    if manual_anterior:

        conexion.execute("""
            UPDATE manuales
            SET
                archivo = ?,
                fecha_subida = ?
            WHERE id = ?
        """, (
            nombre_archivo,
            fecha_subida,
            manual_anterior["id"]
        ))

    # =====================================================
    # INSERTAR
    # =====================================================

    else:

        conexion.execute("""
            INSERT INTO manuales (
                equipo_id,
                tipo,
                archivo,
                fecha_subida
            )
            VALUES (?, ?, ?, ?)
        """, (
            id,
            tipo,
            nombre_archivo,
            fecha_subida
        ))

    conexion.commit()
    conexion.close()

    return redirect(
        url_for(
            "manual_equipo",
            id=id
        )
    )


# =========================================================
# ABRIR / DESCARGAR MANUAL
# =========================================================

@app.route("/manuales/<int:id>/archivo/<path:nombre>")
def abrir_manual(id, nombre):

    carpeta_equipo = os.path.join(
        app.config["UPLOAD_FOLDER"],
        str(id)
    )

    ruta_archivo = os.path.join(
        carpeta_equipo,
        nombre
    )

    if not os.path.isfile(ruta_archivo):
        return "El manual no existe en el servidor.", 404

    return send_from_directory(
        carpeta_equipo,
        nombre,
        as_attachment=False
    )


# =========================================================
# ELIMINAR MANUAL
# =========================================================

@app.route(
    "/manuales/<int:id>/eliminar/<int:manual_id>",
    methods=["GET", "POST"]
)
def eliminar_manual(
    id,
    manual_id
):

    conexion = conectar_bd()

    manual = conexion.execute("""
        SELECT
            archivo
        FROM manuales
        WHERE id = ?
        AND equipo_id = ?
    """, (
        manual_id,
        id
    )).fetchone()

    if manual:

        carpeta_equipo = os.path.join(
            app.config["UPLOAD_FOLDER"],
            str(id)
        )

        ruta = os.path.join(
            carpeta_equipo,
            manual["archivo"]
        )

        if os.path.exists(ruta):

            try:

                os.remove(ruta)

            except OSError:

                pass

        conexion.execute("""
            DELETE FROM manuales
            WHERE id = ?
            AND equipo_id = ?
        """, (
            manual_id,
            id
        ))

        conexion.commit()

    conexion.close()

    return redirect(
        url_for(
            "manual_equipo",
            id=id
        )
    )

    # =====================================================
# SUBIR EVIDENCIA FOTOGRÁFICA
# =====================================================

@app.route("/evidencias/<int:id>/subir", methods=["POST"])
def subir_evidencia(id):

    conexion = conectar_bd()

    # Verificar que el equipo exista
    equipo = conexion.execute("""
        SELECT *
        FROM equipos
        WHERE id = ?
    """, (id,)).fetchone()

    if equipo is None:
        conexion.close()
        return "Equipo no encontrado", 404

    # Verificar que se haya enviado una fotografía
    if "foto" not in request.files:
        conexion.close()
        return "No se seleccionó ninguna fotografía", 400

    foto = request.files["foto"]

    # Verificar que tenga nombre
    if foto.filename == "":
        conexion.close()
        return "No se seleccionó ninguna fotografía", 400

    # Verificar extensión
    if not imagen_permitida(foto.filename):
        conexion.close()
        return "Formato de imagen no permitido", 400

    # Crear carpeta del equipo
    carpeta_equipo = os.path.join(
        app.config["EVIDENCIAS_FOLDER"],
        str(id)
    )

    os.makedirs(carpeta_equipo, exist_ok=True)

    # Crear nombre seguro para el archivo
    nombre_original = secure_filename(foto.filename)

    fecha_actual = datetime.now().strftime("%Y%m%d_%H%M%S")

    nombre_archivo = f"{fecha_actual}_{nombre_original}"

    ruta_archivo = os.path.join(
        carpeta_equipo,
        nombre_archivo
    )

    # Guardar fotografía
    foto.save(ruta_archivo)

    # Descripción
    descripcion = request.form.get("descripcion", "").strip()

    # Registrar en la base de datos
    conexion.execute("""
        INSERT INTO evidencias (
            equipo_id,
            archivo,
            descripcion,
            fecha_subida
        )
        VALUES (?, ?, ?, ?)
    """, (
        id,
        nombre_archivo,
        descripcion,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conexion.commit()
    conexion.close()

    return redirect(url_for("hoja_vida", id=id))


# =====================================================
# ABRIR EVIDENCIA FOTOGRÁFICA
# =====================================================

@app.route("/evidencias/<int:id>/archivo/<path:nombre>")
def abrir_evidencia(id, nombre):

    carpeta_equipo = os.path.join(
        app.config["EVIDENCIAS_FOLDER"],
        str(id)
    )

    ruta_archivo = os.path.join(
        carpeta_equipo,
        nombre
    )

    if not os.path.isfile(ruta_archivo):
        return "La evidencia fotográfica no existe.", 404

    return send_from_directory(
        carpeta_equipo,
        nombre,
        as_attachment=False
    )


# =====================================================
# ELIMINAR EVIDENCIA FOTOGRÁFICA
# =====================================================

@app.route(
    "/evidencias/<int:id>/eliminar/<int:evidencia_id>",
    methods=["POST"]
)
def eliminar_evidencia(id, evidencia_id):

    conexion = conectar_bd()

    # Buscar la evidencia
    evidencia = conexion.execute("""
        SELECT archivo
        FROM evidencias
        WHERE id = ?
        AND equipo_id = ?
    """, (
        evidencia_id,
        id
    )).fetchone()

    if evidencia is None:
        conexion.close()
        return "Evidencia no encontrada", 404

    # Ubicación de la carpeta del equipo
    carpeta_equipo = os.path.join(
        app.config["EVIDENCIAS_FOLDER"],
        str(id)
    )

    # Ruta del archivo
    ruta_archivo = os.path.join(
        carpeta_equipo,
        evidencia["archivo"]
    )

    # Eliminar archivo físico
    if os.path.exists(ruta_archivo):

        try:
            os.remove(ruta_archivo)

        except OSError:
            pass

    # Eliminar registro de la base de datos
    conexion.execute("""
        DELETE FROM evidencias
        WHERE id = ?
        AND equipo_id = ?
    """, (
        evidencia_id,
        id
    ))

    conexion.commit()
    conexion.close()

    return redirect(
        url_for(
            "hoja_vida",
            id=id
        )
    )

# =========================================================
# INFORMACIÓN DEL EQUIPO BIOMÉDICO
# =========================================================

@app.route("/proyecto/equipo-biomedico")
def equipo_biomedico():

    return render_template(
        "equipo_biomedico.html"
    )


# =========================================================
# NORMATIVA
# =========================================================
@app.route("/normativa")
def normativa():
    return render_template(
        "normativa.html"
    )


# =========================================================
# CASOS DE USO

@app.route("/casos-uso")
def casos_uso():
    return render_template(
        "casos_uso.html"
    )


# =========================================================
# BIBLIOGRAFÍA
# =========================================================

@app.route("/bibliografia")
def bibliografia():

    return render_template(
        "bibliografia.html"
    )


# =========================================================
# DIAGRAMA DE BLOQUES
# =========================================================
@app.route("/diagrama-bloques")
def diagrama_bloques():
    return render_template(
        "diagrama_bloques.html"
    )


# =========================================================
# DIAGRAMA DE FLUJO
# =========================================================
@app.route("/diagrama-flujo")
def diagrama_flujo():
    return render_template(
        "diagrama_flujo.html"
    )


# =========================================================
# CRONOGRAMA
# =========================================================
@app.route("/cronograma")
def cronograma():
    return render_template(
        "cronograma.html"
    )
# =========================================================
# CREAR BASE DE DATOS
# =========================================================
crear_bd()

# =========================================================
# EJECUTAR APLICACIÓN
# =========================================================
if __name__ == "__main__":
    crear_bd()
    app.run(debug=True, host="0.0.0.0", port=5000)
