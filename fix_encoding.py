# -*- coding: utf-8 -*-
"""
fix_encoding.py
Lee cada HTML como Latin-1, reemplaza caracteres corruptos
por entidades HTML, y guarda como UTF-8.
Ejecutar: python fix_encoding.py
"""
import os
import glob

TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

# Cada tupla: (bytes_corruptos_en_latin1, entidad_html_correcta)
# Los emojis UTF-8 leidos como latin-1 producen secuencias como \xc3\xb0\xc2\x9f etc.
# Los usamos como strings latin-1 escapados con \xNN

FIXES = [
    # ---- EMOJIS ----
    # pulmon 1FAC1 -> F0 9F AB 81 -> en latin1: \xf0\x9f\xab\x81
    ("\xf0\x9f\xab\x81", "&#x1FAC1;"),
    # grafico barras 1F4CA -> F0 9F 93 8A
    ("\xf0\x9f\x93\x8a", "&#x1F4CA;"),
    # portapapeles 1F4CB -> F0 9F 93 8B
    ("\xf0\x9f\x93\x8b", "&#x1F4CB;"),
    # llave inglesa 1F527 -> F0 9F 94 A7
    ("\xf0\x9f\x94\xa7", "&#x1F527;"),
    # libros 1F4DA -> F0 9F 93 9A
    ("\xf0\x9f\x93\x9a", "&#x1F4DA;"),
    # libro abierto 1F4D6 -> F0 9F 93 96
    ("\xf0\x9f\x93\x96", "&#x1F4D6;"),
    # libro azul 1F4D8 -> F0 9F 93 98
    ("\xf0\x9f\x93\x98", "&#x1F4D8;"),
    # chincheta 1F4CC -> F0 9F 93 8C
    ("\xf0\x9f\x93\x8c", "&#x1F4CC;"),
    # memo 1F4DD -> F0 9F 93 9D
    ("\xf0\x9f\x93\x9d", "&#x1F4DD;"),
    # lupa izq 1F50D -> F0 9F 94 8D
    ("\xf0\x9f\x94\x8d", "&#x1F50D;"),
    # lupa der 1F50E -> F0 9F 94 8E
    ("\xf0\x9f\x94\x8e", "&#x1F50E;"),
    # microscopio 1F52C -> F0 9F 94 AC
    ("\xf0\x9f\x94\xac", "&#x1F52C;"),
    # pergamino 1F4DC -> F0 9F 93 9C
    ("\xf0\x9f\x93\x9c", "&#x1F4DC;"),
    # eslabon 1F517 -> F0 9F 94 97
    ("\xf0\x9f\x94\x97", "&#x1F517;"),
    # documento 1F4C4 -> F0 9F 93 84
    ("\xf0\x9f\x93\x84", "&#x1F4C4;"),
    # calendario 1F4C5 -> F0 9F 93 85
    ("\xf0\x9f\x93\x85", "&#x1F4C5;"),
    # grafico subiendo 1F4C8 -> F0 9F 93 88
    ("\xf0\x9f\x93\x88", "&#x1F4C8;"),
    # bandeja salida 1F4E4 -> F0 9F 93 A4
    ("\xf0\x9f\x93\xa4", "&#x1F4E4;"),
    # diskette 1F4BE -> F0 9F 92 BE
    ("\xf0\x9f\x92\xbe", "&#x1F4BE;"),
    # bombilla 1F4A1 -> F0 9F 92 A1
    ("\xf0\x9f\x92\xa1", "&#x1F4A1;"),
    # viento 1F4A8 -> F0 9F 92 A8
    ("\xf0\x9f\x92\xa8", "&#x1F4A8;"),
    # mano saludando 1F44B -> F0 9F 91 8B
    ("\xf0\x9f\x91\x8b", "&#x1F44B;"),
    # laptop 1F4BB -> F0 9F 92 BB
    ("\xf0\x9f\x92\xbb", "&#x1F4BB;"),
    # hospital 1F3E5 -> F0 9F 8F A5
    ("\xf0\x9f\x8f\xa5", "&#x1F3E5;"),
    # edificio 1F3E8 -> F0 9F 8F A8
    ("\xf0\x9f\x8f\xa8", "&#x1F3E8;"),
    # cerebro 1F9E0 -> F0 9F A7 A0
    ("\xf0\x9f\xa7\xa0", "&#x1F9E0;"),
    # puzzle 1F9E9 -> F0 9F A7 A9
    ("\xf0\x9f\xa7\xa9", "&#x1F9E9;"),
    # circulo verde 1F7E2 -> F0 9F 9F A2
    ("\xf0\x9f\x9f\xa2", "&#x1F7E2;"),
    # circulo amarillo 1F7E1 -> F0 9F 9F A1
    ("\xf0\x9f\x9f\xa1", "&#x1F7E1;"),
    # circulo rojo 1F534 -> F0 9F 94 B4
    ("\xf0\x9f\x94\xb4", "&#x1F534;"),
    # circulo blanco 26AA -> E2 9A AA
    ("\xe2\x9a\xaa", "&#x26AA;"),
    # rayo 26A1 -> E2 9A A1
    ("\xe2\x9a\xa1", "&#x26A1;"),
    # engranaje 2699 FE0F -> E2 9A 99 EF B8 8F
    ("\xe2\x9a\x99\xef\xb8\x8f", "&#x2699;&#xFE0F;"),
    ("\xe2\x9a\x99", "&#x2699;"),
    # check verde 2705 -> E2 9C 85
    ("\xe2\x9c\x85", "&#x2705;"),
    # flecha derecha 2192 -> E2 86 92
    ("\xe2\x86\x92", "&rarr;"),
    # flecha izquierda 2190 -> E2 86 90
    ("\xe2\x86\x90", "&larr;"),
    # flechas circulares 1F504 -> F0 9F 94 84
    ("\xf0\x9f\x94\x84", "&#x1F504;"),
    # campana 1F514 -> F0 9F 94 94
    ("\xf0\x9f\x94\x94", "&#x1F514;"),
    # monitor 1F5A5 FE0F -> F0 9F 96 A5 EF B8 8F
    ("\xf0\x9f\x96\xa5\xef\xb8\x8f", "&#x1F5A5;&#xFE0F;"),
    ("\xf0\x9f\x96\xa5", "&#x1F5A5;"),
    # escudo 1F6E1 FE0F -> F0 9F 9B A1 EF B8 8F
    ("\xf0\x9f\x9b\xa1\xef\xb8\x8f", "&#x1F6E1;&#xFE0F;"),
    ("\xf0\x9f\x9b\xa1", "&#x1F6E1;"),
    # herramienta 1F6E0 FE0F -> F0 9F 9B A0 EF B8 8F
    ("\xf0\x9f\x9b\xa0\xef\xb8\x8f", "&#x1F6E0;&#xFE0F;"),
    ("\xf0\x9f\x9b\xa0", "&#x1F6E0;"),
    # ojo 1F441 FE0F -> F0 9F 91 81 EF B8 8F
    ("\xf0\x9f\x91\x81\xef\xb8\x8f", "&#x1F441;&#xFE0F;"),
    ("\xf0\x9f\x91\x81", "&#x1F441;"),
    # hombre llave 1F468 200D 1F527
    ("\xf0\x9f\x91\xa8\xe2\x80\x8d\xf0\x9f\x94\xa7", "&#x1F468;&#x200D;&#x1F527;"),
    # hombre maletin 1F468 200D 1F4BC
    ("\xf0\x9f\x91\xa8\xe2\x80\x8d\xf0\x9f\x92\xbc", "&#x1F468;&#x200D;&#x1F4BC;"),
    # hombre laptop 1F468 200D 1F4BB
    ("\xf0\x9f\x91\xa8\xe2\x80\x8d\xf0\x9f\x92\xbb", "&#x1F468;&#x200D;&#x1F4BB;"),
    # estetoscopio 1FA7B -> F0 9F A9 BB
    ("\xf0\x9f\xa9\xbb", "&#x1FA7B;"),
    # birrete 1F393 -> F0 9F 8E 93
    ("\xf0\x9f\x8e\x93", "&#x1F393;"),
    # cohete 1F680 -> F0 9F 9A 80
    ("\xf0\x9f\x9a\x80", "&#x1F680;"),
    # globo terraqueo 1F30E -> F0 9F 8C 8E
    ("\xf0\x9f\x8c\x8e", "&#x1F30E;"),
    # carpeta 1F5C2 FE0F
    ("\xf0\x9f\x97\x82\xef\xb8\x8f", "&#x1F5C2;&#xFE0F;"),
    ("\xf0\x9f\x97\x82", "&#x1F5C2;"),
    # info i 2139 FE0F -> E2 84 B9 EF B8 8F
    ("\xe2\x84\xb9\xef\xb8\x8f", "&#x2139;&#xFE0F;"),
    ("\xe2\x84\xb9", "&#x2139;"),
    # ndash E2 80 93
    ("\xe2\x80\x93", "&ndash;"),
    # ldquo E2 80 9C
    ("\xe2\x80\x9c", "&ldquo;"),
    # rdquo E2 80 9D
    ("\xe2\x80\x9d", "&rdquo;"),

    # ---- ACENTOS (UTF-8 leido como latin-1) ----
    # a con acento agudo: C3 A1
    ("\xc3\xa1", "&aacute;"),
    # e con acento agudo: C3 A9
    ("\xc3\xa9", "&eacute;"),
    # i con acento agudo: C3 AD
    ("\xc3\xad", "&iacute;"),
    # o con acento agudo: C3 B3
    ("\xc3\xb3", "&oacute;"),
    # u con acento agudo: C3 BA
    ("\xc3\xba", "&uacute;"),
    # n con tilde: C3 B1
    ("\xc3\xb1", "&ntilde;"),
    # u con dieresis: C3 BC
    ("\xc3\xbc", "&uuml;"),
    # A con acento agudo: C3 81
    ("\xc3\x81", "&Aacute;"),
    # E con acento agudo: C3 89
    ("\xc3\x89", "&Eacute;"),
    # I con acento agudo: C3 8D
    ("\xc3\x8d", "&Iacute;"),
    # O con acento agudo: C3 93
    ("\xc3\x93", "&Oacute;"),
    # U con acento agudo: C3 9A
    ("\xc3\x9a", "&Uacute;"),
    # N con tilde: C3 91
    ("\xc3\x91", "&Ntilde;"),
    # signo interrogacion apertura: C2 BF
    ("\xc2\xbf", "&iquest;"),
    # signo exclamacion apertura: C2 A1
    ("\xc2\xa1", "&iexcl;"),
]


def fix_file(path):
    with open(path, "rb") as f:
        raw = f.read()
    # Decodificar como latin-1 para no perder bytes
    text = raw.decode("latin-1")
    for old, new in FIXES:
        text = text.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


html_files = glob.glob(os.path.join(TEMPLATES, "*.html"))
count = 0
for path in html_files:
    try:
        fix_file(path)
        print("OK: " + os.path.basename(path))
        count += 1
    except Exception as e:
        print("ERROR " + os.path.basename(path) + ": " + str(e))

print("\nTotal: " + str(count) + "/" + str(len(html_files)))
