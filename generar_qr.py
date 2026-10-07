import os
import qrcode

os.makedirs("static/qr", exist_ok=True)

for equipo_id in range(1, 6):

    url = f"https://biomedic-jf5o.onrender.com/hoja-vida/{equipo_id}?desde_qr=1"

    imagen = qrcode.make(url)

    ruta = f"static/qr/equipo_{equipo_id}.png"

    imagen.save(ruta)

    print(f"QR creado: {ruta}")
    