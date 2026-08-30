from flask import Flask, render_template, request, redirect, url_for, send_from_directory

import sqlite3
from datetime import datetime, date
import os
from werkzeug.utils import secure_filename


# =========================================================
# CONFIGURACIÓN DE FLASK
# =========================================================

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "biovent.db")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "manuales")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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

        # El estado ya NO lo selecciona el usuario.
        #
        # Al registrar un equipo nuevo se considera:
        # "Equipo apto y disponible para su uso"
        #
        # Posteriormente el estado podrá actualizarse
        # mediante las revisiones y mantenimientos.

        estado = "Equipo apto y disponible para su uso"

        conexion.execute("""
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

        conexion.commit()
        conexion.close()

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


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    conexion = conectar_bd()

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
    # CERRAR CONEXIÓN
    # =====================================================

    conexion.close()

    # =====================================================
    # ENVIAR INFORMACIÓN AL HTML
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

        total_mantenimientos=total_mantenimientos,

        mantenimientos_al_dia=mantenimientos_al_dia,

        mantenimientos_proximos=mantenimientos_proximos,

        mantenimientos_vencidos=mantenimientos_vencidos,

        ultimos_checklists=ultimos_checklists,

        ultimos_mantenimientos=ultimos_mantenimientos
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

@app.route(
    "/manuales/<int:id>/archivo/<nombre>"
)
def abrir_manual(id, nombre):

    carpeta_equipo = os.path.join(
        app.config["UPLOAD_FOLDER"],
        str(id)
    )

    return send_from_directory(
        carpeta_equipo,
        nombre
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
# =========================================================

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
# CREAR BASE DE DATOS
# =========================================================

crear_bd()


# =========================================================
# EJECUTAR APLICACIÓN
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )