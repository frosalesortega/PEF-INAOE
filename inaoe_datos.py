#!/usr/bin/env python3
"""
Lectura y preparacion de los datos presupuestales del INAOE (Ramo 38, UR 91U)
a partir de dos fuentes publicas:

  1. CSV de Cuenta Publica (Datos Abiertos de Transparencia Presupuestaria).
     Detalle por partida especifica de 5 digitos. Solo recursos fiscales.
  2. Tomo VII de la Cuenta Publica (informe del propio INAOE ante Hacienda).
     Detalle por capitulo y concepto. Mezcla recursos fiscales y propios.

Este modulo no produce nada por si solo: lo usa genera_graficas.py. Para
correrlo directamente y ver un resumen de lo que leyo:

    python inaoe_datos.py

Los nombres de columna del CSV cambian de un anio a otro (y cambian por
completo en 2025), por lo que el mapeo se hace por alias normalizados y nunca
por posicion de columna. Lo mismo con el Tomo VII, cuyo layout tiene dos
variantes: se localiza la celda "APROBADO" en lugar de fijar una posicion.

Esta parametrizado por RAMO y UR: cambiando esas dos constantes el pipeline
corre para cualquier otra unidad responsable del mismo ramo.
"""

from __future__ import annotations

import glob
import re
import unicodedata
from pathlib import Path

import duckdb
import pandas as pd

# ----------------------------------------------------------------------------
# Configuracion
# ----------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent
DATOS_DIR = ROOT / "datos"
CSV_DIR = DATOS_DIR / "cuenta_publica"      # los CSV anuales que descarga el usuario
XLS_DIR = DATOS_DIR / "tomo_vii"            # los .xls anuales que descarga el usuario
INTERMEDIOS_DIR = DATOS_DIR / "intermedios"  # se generan solos; no se versionan
CACHE_DIR = ROOT / ".cache"                  # copias UTF-8; regenerable, se puede borrar

RAMO = "38"
UR = "91U"

# Alias normalizados (minusculas, sin acentos, sin espacios) -> nombre canonico.
# Agregar alias aqui si un anio nuevo estrena nombres de columna.
COLUMN_ALIASES = {
    "ciclo": ["ciclo"],
    "ramo": ["id_ramo", "ramo", "r"],
    "desc_ramo": ["desc_ramo", "ramo_desc"],
    "ur": ["id_ur", "ur"],
    "desc_ur": ["desc_ur", "ur_desc"],
    "objeto_del_gasto": ["id_objeto_del_gasto", "objeto_del_gasto", "ptda"],
    "desc_objeto_del_gasto": ["desc_objeto_del_gasto", "ptda_desc"],
    "ff": ["id_ff", "ff"],
    "desc_ff": ["desc_ff", "ff_desc"],
    "monto_aprobado": ["monto_aprobado", "original_bruto", "aprobado"],
    "monto_modificado": ["monto_modificado", "modificado_bruto", "modificado"],
    "monto_devengado": ["monto_devengado", "devengado"],
    "monto_pagado": ["monto_pagado", "pagado"],
    "adefas": ["adefas", "monto_adefas"],
    "monto_ejercido": ["monto_ejercido", "ejercido_bruto", "ejercido", "ejercicio", "monto_ejercicio"],
}

# Columnas sin las cuales no se puede filtrar ni clasificar
REQUIRED = ["ciclo", "ramo", "ur", "objeto_del_gasto", "monto_aprobado", "monto_ejercido"]

# Grupos de partidas. Pasajes y servicios integrales de traslado se separan en
# nacional/internacional segun la descripcion del clasificador oficial
# (37101-37104 / 37201-37204 son nacionales; 37105-37106 / 37205-37206
# internacionales; 37801 nacional y 37802 "en el extranjero").
GRUPOS = {
    "Pasajes aereos nacionales": ["37101", "37102", "37103", "37104"],
    "Pasajes aereos internacionales": ["37105", "37106"],
    "Pasajes terrestres nacionales": ["37201", "37202", "37203", "37204"],
    "Pasajes terrestres internacionales": ["37205", "37206"],
    "Viaticos nacionales": ["37501", "37502", "37504"],
    "Viaticos extranjero": ["37601", "37602"],
    "Servicios integrales de traslado nacionales": ["37801"],
    "Servicios integrales de traslado extranjero": ["37802"],
    "Congresos y convenciones": ["38301"],
    "Exposiciones / orden social": ["38201", "38401"],
    "Alimentacion de mandos": ["38501"],
    "Publicaciones e impresiones": ["33603", "33604"],
    "Informacion en medios / difusion": ["33605", "36101", "36201"],
}
PARTIDA_A_GRUPO = {p: g for g, ps in GRUPOS.items() for p in ps}

# Concepto(s) de 2 digitos que cubre cada grupo, para saber en que anios el
# "ejercido" del CSV es gasto real y en cuales es ministracion.
GRUPO_A_CONCEPTOS2 = {g: sorted({p[:2] for p in ps}) for g, ps in GRUPOS.items()}

# INPC promedio anual, base 2Q julio 2018 = 100. PROVISIONAL: 2015-2017 estan
# retropropagados desde 2018=99.9 con la inflacion promedio anual de Banxico.
# Sustituir por la serie oficial del INEGI si se requiere precision en los
# montos reales.
INPC = {
    2015: 87.4, 2016: 89.8, 2017: 95.2,
    2018: 99.9, 2019: 103.6, 2020: 107.0, 2021: 112.9,
    2022: 121.6, 2023: 128.4, 2024: 134.6, 2025: 139.5,
}
ANIO_BASE_REAL = 2025

# Regla de validez: un anio-concepto del CSV sirve como gasto real si su
# ejercido coincide razonablemente con el devengado del Tomo VII.
RATIO_VALIDO_MIN = 0.85
RATIO_VALIDO_MAX = 1.15
CONCEPTOS_VALIDACION_CSV = ["33", "36", "37", "38"]

# Capitulos del analisis de subejercicio. Se excluye el 1000 (nomina): concentra
# la mayor parte del subejercicio del instituto, pero por dinamicas de plantilla
# (plazas vacantes, personal transitorio no contratado, estimulos
# sobrepresupuestados) que no hablan de la capacidad de ejercer el presupuesto
# de operacion, que es lo que aqui se quiere medir.
CAPITULOS_CON_DATOS = ["1000", "2000", "3000", "4000"]
CAPITULOS_EXCLUIDOS_SUBEJERCICIO = ["1000"]
CAPITULOS_SUBEJERCICIO = [c for c in CAPITULOS_CON_DATOS if c not in CAPITULOS_EXCLUIDOS_SUBEJERCICIO]
NIVEL_TOTAL_ANALISIS = "total sin capitulos excluidos"

# Nombres en lenguaje llano para las graficas (los nombres oficiales del
# clasificador no le dicen nada a un lector sin contexto presupuestal).
NOMBRE_LLANO_CAPITULO = {
    "1000": "Nómina y personal",
    "2000": "Materiales y suministros",
    "3000": "Servicios generales (incluye viajes)",
    "4000": "Becas y transferencias",
}


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------

def normaliza(texto: str) -> str:
    """minusculas, sin acentos, espacios -> guion bajo"""
    texto = str(texto).strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = texto.strip().lower()
    return re.sub(r"\s+", "_", texto)


def norm_texto(texto: str) -> str:
    """Como normaliza(), pero conserva espacios simples (las llaves de
    CAPITULO_MAP_TOMO / CONCEPTO_MAP_TOMO usan espacios)."""
    texto = str(texto).strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = texto.strip().lower()
    return re.sub(r"\s+", " ", texto)


def detecta_codificacion(path: Path) -> str:
    with open(path, "rb") as fh:
        muestra = fh.read(200_000)
    try:
        muestra.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "latin-1"


def asegura_utf8(path: Path) -> Path:
    """Los CSV vienen en Latin-1. Convierte a UTF-8 en .cache/ si hace falta y
    reutiliza la copia si ya esta al dia."""
    codificacion = detecta_codificacion(path)
    if codificacion == "utf-8":
        return path
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    destino = CACHE_DIR / f"{path.stem}_utf8.csv"
    if destino.exists() and destino.stat().st_mtime >= path.stat().st_mtime:
        return destino
    print(f"    Convirtiendo {path.name} de {codificacion} a UTF-8 (una sola vez)")
    with open(path, "r", encoding=codificacion, errors="replace") as fin, \
            open(destino, "w", encoding="utf-8") as fout:
        for linea in fin:
            fout.write(linea)
    return destino


def limpia_monto(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(
        serie.astype(str).str.replace(",", "", regex=False).str.replace('"', "", regex=False).str.strip(),
        errors="coerce",
    )


def detecta_anio_de_archivo(nombre: str) -> int | None:
    m = re.search(r"(20\d{2})", nombre)
    return int(m.group(1)) if m else None


# ----------------------------------------------------------------------------
# Fuente 1: CSV de Cuenta Publica
# ----------------------------------------------------------------------------

def encuentra_columnas(con, path_utf8: Path):
    headers = [r[0] for r in con.execute(
        f"DESCRIBE SELECT * FROM read_csv_auto('{path_utf8.as_posix()}', all_varchar=True, sample_size=200000)"
    ).fetchall()]
    norm_to_actual = {normaliza(h): h for h in headers}
    mapa = {}
    for canonico, alias in COLUMN_ALIASES.items():
        for a in alias:
            if a in norm_to_actual:
                mapa[canonico] = norm_to_actual[a]
                break
    faltantes = [c for c in REQUIRED if c not in mapa]
    if faltantes:
        print(f"    AVISO: columnas requeridas no encontradas en {path_utf8.name}: {faltantes}")
        print(f"    Encabezados disponibles: {headers}")
    return mapa


def procesa_archivo(con, path: Path) -> pd.DataFrame | None:
    """Filtra un CSV nacional al Ramo/UR de interes y guarda el extracto en
    datos/intermedios/ para no tener que volver a leer el archivo grande."""
    print(f"  Archivo: {path.name} ({path.stat().st_size / 1e6:.1f} MB)")
    path_utf8 = asegura_utf8(path)
    mapa = encuentra_columnas(con, path_utf8)

    if "ramo" not in mapa or "ur" not in mapa:
        print(f"    No se pudo mapear RAMO/UR en {path.name}; se omite.")
        return None

    cols_sql = ", ".join(f'"{actual}" AS {canon}' for canon, actual in mapa.items())
    query = f"""
        SELECT {cols_sql}
        FROM read_csv_auto('{path_utf8.as_posix()}', all_varchar=True, sample_size=200000)
        WHERE TRIM("{mapa['ramo']}") = '{RAMO}' AND TRIM("{mapa['ur']}") = '{UR}'
    """
    df = con.execute(query).fetchdf()

    if df.empty:
        print(f"    RAMO {RAMO} / UR {UR} no encontrado en {path.name}. "
              f"Revisa manualmente (posible cambio de clave del ramo o de la UR).")
        return None

    for c in ["monto_aprobado", "monto_modificado", "monto_devengado",
              "monto_pagado", "adefas", "monto_ejercido"]:
        df[c] = limpia_monto(df[c]) if c in df.columns else pd.NA

    df["objeto_del_gasto"] = df["objeto_del_gasto"].astype(str).str.strip()
    df["ciclo"] = pd.to_numeric(df["ciclo"], errors="coerce").astype("Int64")

    anio_ciclo = df["ciclo"].dropna().unique()
    anio_archivo = detecta_anio_de_archivo(path.name)
    if len(anio_ciclo) == 1:
        anio = int(anio_ciclo[0])
        if anio_archivo and anio_archivo != anio:
            print(f"    AVISO: el nombre del archivo sugiere {anio_archivo} pero la columna Ciclo "
                  f"dice {anio}. Se usa Ciclo={anio}.")
    else:
        anio = anio_archivo
        print(f"    AVISO: no se pudo determinar un unico Ciclo; se usa el anio del nombre "
              f"de archivo ({anio}).")

    df["anio"] = anio

    INTERMEDIOS_DIR.mkdir(parents=True, exist_ok=True)
    salida = INTERMEDIOS_DIR / f"inaoe_{UR}_{anio}.csv"
    df.to_csv(salida, index=False)
    print(f"    OK: {len(df)} filas, {df['objeto_del_gasto'].nunique()} partidas -> {salida.name}")
    return df


def carga_cuenta_publica() -> pd.DataFrame:
    """Lee los CSV crudos que encuentre y, para los anios que ya tengan
    extracto en datos/intermedios/, reutiliza el extracto en vez de volver a
    procesar el archivo nacional completo."""
    print("Cuenta Publica: extraccion del INAOE por archivo")
    con = duckdb.connect()

    crudos = sorted(Path(p) for p in glob.glob(str(CSV_DIR / "*.csv")))
    dfs = []
    anios_procesados = set()
    for path in crudos:
        df = procesa_archivo(con, path)
        if df is not None:
            dfs.append(df)
            anios_procesados.add(int(df["anio"].iloc[0]))

    for inter in sorted(INTERMEDIOS_DIR.glob(f"inaoe_{UR}_*.csv")):
        m = re.search(r"_(\d{4})\.csv$", inter.name)
        if not m:
            continue
        anio = int(m.group(1))
        if anio in anios_procesados:
            continue
        print(f"  Reutilizando extracto previo: {inter.name}")
        df = pd.read_csv(inter, dtype={"objeto_del_gasto": str})
        for c in ["monto_aprobado", "monto_modificado", "monto_devengado",
                  "monto_pagado", "adefas", "monto_ejercido"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        dfs.append(df)
        anios_procesados.add(anio)

    if not dfs:
        raise SystemExit(
            f"\nNo se encontro ningun CSV de Cuenta Publica en:\n  {CSV_DIR}\n\n"
            f"Descarga los archivos anuales de Datos Abiertos de Transparencia\n"
            f"Presupuestaria y colocalos ahi. Ver el README, 'Fuente A'."
        )

    print(f"  Anios con datos: {sorted(anios_procesados)}")
    faltantes = sorted(set(range(2015, 2026)) - anios_procesados)
    if faltantes:
        print(f"  Faltan anios: {faltantes}. Las graficas se generaran solo con los anios presentes.")

    return pd.concat(dfs, ignore_index=True)


# ----------------------------------------------------------------------------
# Fuente 2: Tomo VII
# ----------------------------------------------------------------------------

CAPITULO_MAP_TOMO = {
    "servicios personales": "1000",
    "materiales y suministros": "2000",
    "servicios generales": "3000",
    "transferencias, asignaciones, subsidios y otras ayudas": "4000",
    "bienes muebles, inmuebles e intangibles": "5000",
    "inversion publica": "6000",
    "inversiones financieras y otras provisiones": "7000",
    "participaciones y aportaciones": "8000",
    "deuda publica": "9000",
}

CONCEPTO_MAP_TOMO = {
    # Capitulo 1000 - Servicios personales
    "remuneraciones al personal de caracter permanente": ("1000", "1100"),
    "remuneraciones al personal de caracter transitorio": ("1000", "1200"),
    "remuneraciones adicionales y especiales": ("1000", "1300"),
    "seguridad social": ("1000", "1400"),
    "otras prestaciones sociales y economicas": ("1000", "1500"),
    "previsiones": ("1000", "1600"),
    "pago de estimulos a servidores publicos": ("1000", "1700"),
    # Capitulo 2000 - Materiales y suministros
    "materiales de administracion, emision de documentos y articulos oficiales": ("2000", "2100"),
    "alimentos y utensilios": ("2000", "2200"),
    "materias primas y materiales de produccion y comercializacion": ("2000", "2300"),
    "materiales y articulos de construccion y de reparacion": ("2000", "2400"),
    "productos quimicos, farmaceuticos y de laboratorio": ("2000", "2500"),
    "combustibles, lubricantes y aditivos": ("2000", "2600"),
    "vestuario, blancos, prendas de proteccion y articulos deportivos": ("2000", "2700"),
    "materiales y suministros para seguridad": ("2000", "2800"),
    "herramientas, refacciones y accesorios menores": ("2000", "2900"),
    # Capitulo 3000 - Servicios generales
    "servicios basicos": ("3000", "3100"),
    "servicios de arrendamiento": ("3000", "3200"),
    "servicios profesionales, cientificos, tecnicos y otros servicios": ("3000", "3300"),
    "servicios financieros, bancarios y comerciales": ("3000", "3400"),
    "servicios de instalacion, reparacion, mantenimiento y conservacion": ("3000", "3500"),
    "servicios de comunicacion social y publicidad": ("3000", "3600"),
    "servicios de traslado y viaticos": ("3000", "3700"),
    "servicios oficiales": ("3000", "3800"),
    "otros servicios generales": ("3000", "3900"),
    # Capitulo 4000 - Transferencias, asignaciones, subsidios y otras ayudas
    "transferencias internas y asignaciones al sector publico": ("4000", "4100"),
    "transferencias al resto del sector publico": ("4000", "4200"),
    "subsidios y subvenciones": ("4000", "4300"),
    "ayudas sociales": ("4000", "4400"),
    "pensiones y jubilaciones": ("4000", "4500"),
    "transferencias a fideicomisos, mandatos y otros analogos": ("4000", "4600"),
    "transferencias a la seguridad social": ("4000", "4700"),
    "donativos": ("4000", "4800"),
    "transferencias al exterior": ("4000", "4900"),
    # Capitulo 5000 - Bienes muebles, inmuebles e intangibles
    "mobiliario y equipo de administracion": ("5000", "5100"),
    "mobiliario y equipo educacional y recreativo": ("5000", "5200"),
    "equipo e instrumental medico y de laboratorio": ("5000", "5300"),
    "vehiculos y equipo de transporte": ("5000", "5400"),
    "equipo de defensa y seguridad": ("5000", "5500"),
    "maquinaria, otros equipos y herramientas": ("5000", "5600"),
    "activos biologicos": ("5000", "5700"),
    "bienes inmuebles": ("5000", "5800"),
    "activos intangibles": ("5000", "5900"),
    # Capitulo 6000 - Inversion publica
    "obra publica en bienes de dominio publico": ("6000", "6100"),
    "obra publica en bienes propios": ("6000", "6200"),
    "proyectos productivos y acciones de fomento": ("6000", "6300"),
}

HEADERS_ESPERADOS_TOMO = ["aprobado", "ampliaciones", "modificado", "devengado", "pagado"]


def parse_tomo_vii(path: Path) -> list[dict]:
    """Lee un 91U.03.F_OBJGASTO_<anio>.xls y regresa una lista de filas con
    nivel ('capitulo' | 'concepto' | 'total'), codigo, descripcion y los seis
    montos. El valor de SUBEJERCICIO se toma tal cual viene en el archivo.

    Hay dos layouts (10 columnas en 2015-2023, 11 en 2024-2025). Se detecta
    localizando la celda con texto 'APROBADO' en lugar de fijar posiciones.
    """
    import xlrd

    wb = xlrd.open_workbook(str(path))
    sh = wb.sheet_by_index(0)

    aprobado_col = header_row = None
    for r in range(sh.nrows):
        for c in range(sh.ncols):
            if normaliza(sh.cell_value(r, c)) == "aprobado":
                aprobado_col, header_row = c, r
                break
        if aprobado_col is not None:
            break
    if aprobado_col is None:
        print(f"    AVISO: no se encontro la columna APROBADO en {path.name}; se omite.")
        return []

    concept_col = aprobado_col - 1
    capitulo_col = 2
    cols = {nombre: aprobado_col + i for i, nombre in enumerate(
        ["aprobado", "ampliaciones", "modificado", "devengado", "pagado", "subejercicio"])}

    obtenido = [normaliza(sh.cell_value(header_row, aprobado_col + i)) for i in range(5)]
    if not all(obtenido[i].startswith(HEADERS_ESPERADOS_TOMO[i]) for i in range(5)):
        print(f"    AVISO: encabezados inesperados en {path.name}: {obtenido}")

    def val(r, c):
        v = sh.cell_value(r, c)
        return v if isinstance(v, (int, float)) else None

    filas = []
    capitulo_actual = None
    for r in range(header_row + 1, sh.nrows):
        etiqueta = str(sh.cell_value(r, 1)).strip()
        cap_txt = str(sh.cell_value(r, capitulo_col)).strip()
        con_txt = str(sh.cell_value(r, concept_col)).strip()
        if not isinstance(sh.cell_value(r, aprobado_col), (int, float)):
            continue

        montos = {nombre: val(r, c) for nombre, c in cols.items()}

        if "total" in etiqueta.lower():
            filas.append(dict(nivel="total", codigo="TOTAL", capitulo=None, desc=etiqueta, **montos))
        elif cap_txt and not con_txt:
            capitulo_actual = CAPITULO_MAP_TOMO.get(norm_texto(cap_txt))
            filas.append(dict(nivel="capitulo", codigo=capitulo_actual, capitulo=capitulo_actual,
                              desc=cap_txt, **montos))
        elif con_txt:
            mapeo = CONCEPTO_MAP_TOMO.get(norm_texto(con_txt))
            filas.append(dict(nivel="concepto", codigo=mapeo[1] if mapeo else None,
                              capitulo=capitulo_actual, desc=con_txt, **montos))
    return filas


def carga_tomo_vii() -> pd.DataFrame:
    """Lee todos los 91U*OBJGASTO*.xls disponibles, uno por anio."""
    print("\nTomo VII: lectura de los informes del INAOE ante Hacienda")
    candidatos = sorted(glob.glob(str(XLS_DIR / "*OBJGASTO*.xls")))
    filas_todas = []
    for path_str in candidatos:
        path = Path(path_str)
        anio = detecta_anio_de_archivo(path.name)
        if anio is None:
            continue
        filas = parse_tomo_vii(path)
        if not filas:
            continue
        for f in filas:
            f["anio"] = anio
        filas_todas.extend(filas)
        n = sum(1 for f in filas if f["nivel"] == "concepto")
        print(f"  {path.name}: {n} conceptos (anio {anio})")

    if not filas_todas:
        raise SystemExit(
            f"\nNo se encontro ningun archivo del Tomo VII en:\n  {XLS_DIR}\n\n"
            f"Descarga los '91U.03.F_OBJGASTO_<anio>.xls' de\n"
            f"cuentapublica.hacienda.gob.mx y colocalos ahi. Ver el README, 'Fuente B'."
        )

    df = pd.DataFrame(filas_todas)
    print(f"  Anios disponibles: {sorted(df['anio'].unique())}")
    return df


# ----------------------------------------------------------------------------
# Validacion cruzada: cuando el "ejercido" del CSV es gasto real
# ----------------------------------------------------------------------------

def valida_csv_vs_tomo(df_csv: pd.DataFrame, df_tomo: pd.DataFrame) -> pd.DataFrame:
    """En el CSV de Cuenta Publica, el importe registrado como ejercido para el
    INAOE es en varios anios la ministracion del subsidio y no el gasto
    devengado. Para saber en cuales, se compara concepto por concepto y anio
    por anio el ejercido del CSV contra el devengado del Tomo VII: el
    anio-concepto se considera verificado si la razon cae entre 0.85 y 1.15."""
    print("\nValidacion: ejercido del CSV contra devengado del Tomo VII")
    if df_csv.empty or df_tomo.empty:
        return pd.DataFrame()

    csv3 = df_csv.copy()
    csv3["concepto2"] = csv3["objeto_del_gasto"].str[:2]
    csv_agg = csv3[csv3["concepto2"].isin(CONCEPTOS_VALIDACION_CSV)].groupby(
        ["anio", "concepto2"]).agg(
        aprobado_csv=("monto_aprobado", "sum"),
        ejercido_csv=("monto_ejercido", "sum"),
    ).reset_index()

    tomo_c = df_tomo[(df_tomo["nivel"] == "concepto") & (df_tomo["codigo"].notna())].copy()
    tomo_c["concepto2"] = tomo_c["codigo"].str[:2]
    tomo_agg = tomo_c[tomo_c["concepto2"].isin(CONCEPTOS_VALIDACION_CSV)].groupby(
        ["anio", "concepto2"]).agg(devengado_tomo=("devengado", "sum")).reset_index()

    # Solo tiene sentido validar en anios donde el CSV existe.
    tomo_agg = tomo_agg[tomo_agg["anio"].isin(set(csv_agg["anio"].unique()))]

    rec = csv_agg.merge(tomo_agg, on=["anio", "concepto2"], how="outer").sort_values(
        ["anio", "concepto2"])
    rec["concepto"] = rec["concepto2"] + "00"
    rec["razon_csv_tomo"] = rec["ejercido_csv"] / rec["devengado_tomo"]
    rec["valido"] = rec["razon_csv_tomo"].between(RATIO_VALIDO_MIN, RATIO_VALIDO_MAX)
    rec = rec.drop(columns=["concepto2"])[
        ["anio", "concepto", "aprobado_csv", "ejercido_csv", "devengado_tomo",
         "razon_csv_tomo", "valido"]
    ]

    for r in rec.sort_values(["concepto", "anio"]).itertuples():
        estado = "verificado" if r.valido else "no verificable (ministracion)"
        razon = f"{r.razon_csv_tomo:.2f}" if pd.notna(r.razon_csv_tomo) else "s/d"
        print(f"  {r.anio} concepto {r.concepto}: razon={razon} -> {estado}")

    return rec


def anios_validos_grupo(df_validacion: pd.DataFrame, grupo: str) -> set[int]:
    """Anios en que el ejercido del CSV es gasto real para todos los conceptos
    que cubre ese grupo de partidas.

    Los conceptos sin ningun dato en el CSV para esta UR se ignoran: el grupo de
    publicaciones, por ejemplo, incluye en su definicion las partidas de
    comunicacion social (36101, 36201), que el INAOE no ejerce en ningun anio.
    Tratarlas como 'no verificables' marcaria todo el grupo como incierto, lo
    cual seria falso: lo que el Instituto si ejerce vive en el concepto 33."""
    conceptos2 = GRUPO_A_CONCEPTOS2.get(grupo, [])
    if df_validacion.empty or not conceptos2:
        return set()
    anios_por_concepto = []
    for c2 in conceptos2:
        sub = df_validacion[df_validacion["concepto"].str[:2] == c2]
        if sub.empty or sub["ejercido_csv"].isna().all():
            continue
        anios_por_concepto.append(set(int(a) for a in sub.loc[sub["valido"], "anio"]))
    return set.intersection(*anios_por_concepto) if anios_por_concepto else set()


# ----------------------------------------------------------------------------
# Tablas derivadas
# ----------------------------------------------------------------------------

def clasifica(df: pd.DataFrame) -> pd.DataFrame:
    """Se queda solo con las partidas que pertenecen a algun grupo de interes."""
    df = df.copy()
    df["grupo"] = df["objeto_del_gasto"].map(PARTIDA_A_GRUPO)
    return df[df["grupo"].notna()].copy()


def tabla_larga(df_grupos: pd.DataFrame) -> pd.DataFrame:
    return df_grupos.groupby(
        ["anio", "grupo", "objeto_del_gasto", "desc_objeto_del_gasto", "ff", "desc_ff"],
        dropna=False,
    ).agg(
        monto_aprobado=("monto_aprobado", "sum"),
        monto_modificado=("monto_modificado", "sum"),
        monto_devengado=("monto_devengado", "sum"),
        monto_pagado=("monto_pagado", "sum"),
        monto_ejercido=("monto_ejercido", "sum"),
    ).reset_index().sort_values(["anio", "objeto_del_gasto", "ff"])


def _ejercido_o_devengado(sub: pd.DataFrame) -> pd.Series:
    """Usa el ejercido si ese anio trae dato; si no, cae al devengado."""
    if sub["monto_ejercido"].notna().any() and sub["monto_ejercido"].sum() > 0:
        return sub["monto_ejercido"]
    return sub["monto_devengado"]


def _deflacta(monto, anio):
    anio = int(anio)
    return monto * INPC[ANIO_BASE_REAL] / INPC[anio] if anio in INPC and pd.notna(monto) else pd.NA


def resumen_por_grupo_anio(tabla_l: pd.DataFrame) -> pd.DataFrame:
    """Una fila por anio y grupo, con aprobado y ejercido, en pesos corrientes
    y en pesos constantes del anio base."""
    filas = []
    for (anio, grupo), sub in tabla_l.groupby(["anio", "grupo"]):
        aprobado = sub["monto_aprobado"].sum()
        ejercido = _ejercido_o_devengado(sub).sum()
        filas.append({
            "anio": anio, "grupo": grupo,
            "aprobado": aprobado,
            "ejercido_o_devengado": ejercido,
            "pct_ejercido_aprobado": (ejercido / aprobado * 100) if aprobado else pd.NA,
        })
    resumen = pd.DataFrame(filas).sort_values(["grupo", "anio"])
    resumen["aprobado_real_2025"] = resumen.apply(
        lambda r: _deflacta(r["aprobado"], r["anio"]), axis=1)
    resumen["ejercido_real_2025"] = resumen.apply(
        lambda r: _deflacta(r["ejercido_o_devengado"], r["anio"]), axis=1)
    return resumen


def indicadores_subejercicio(df_tomo: pd.DataFrame) -> pd.DataFrame:
    """Agrega a cada fila del Tomo VII los tres indicadores del informe:
    reduccion (aprobado - modificado, aqui via 'adecuaciones_netas' con signo
    invertido), subejercicio (modificado - devengado, que ya viene en el
    archivo) y no devengado (aprobado - devengado)."""
    df = df_tomo.copy()
    df["pct_subejercicio"] = df["subejercicio"] / df["modificado"] * 100
    df["adecuaciones_netas"] = df["modificado"] - df["aprobado"]
    df["no_devengado_vs_aprobado"] = df["aprobado"] - df["devengado"]
    df["pct_no_devengado_vs_aprobado"] = df["no_devengado_vs_aprobado"] / df["aprobado"] * 100
    return df


def agrega_total_sin_capitulos(df_indicadores: pd.DataFrame,
                               excluidos: list[str] | None = None) -> pd.DataFrame:
    """Agrega un nivel con el agregado del instituto MENOS los capitulos
    excluidos. Se calcula como total - excluidos, y no como suma de los
    capitulos restantes, para no perder los capitulos 5000/6000, que en
    2015-2017 tienen devengado real aunque su aprobado sea cero."""
    excluidos = list(CAPITULOS_EXCLUIDOS_SUBEJERCICIO if excluidos is None else excluidos)
    tot = df_indicadores[df_indicadores["nivel"] == "total"]
    exc = df_indicadores[(df_indicadores["nivel"] == "capitulo")
                         & (df_indicadores["codigo"].isin(excluidos))]
    if tot.empty or exc.empty:
        return df_indicadores

    montos = ["aprobado", "ampliaciones", "modificado", "devengado", "pagado", "subejercicio"]
    neto = (tot.set_index("anio")[montos] - exc.groupby("anio")[montos].sum()).reset_index()
    neto["nivel"] = NIVEL_TOTAL_ANALISIS
    neto["codigo"] = None
    neto["capitulo"] = None
    neto["desc"] = f"Total del instituto sin capitulo(s) {', '.join(excluidos)}"
    neto["pct_subejercicio"] = neto["subejercicio"] / neto["modificado"] * 100
    neto["adecuaciones_netas"] = neto["modificado"] - neto["aprobado"]
    neto["no_devengado_vs_aprobado"] = neto["aprobado"] - neto["devengado"]
    neto["pct_no_devengado_vs_aprobado"] = neto["no_devengado_vs_aprobado"] / neto["aprobado"] * 100
    return pd.concat([df_indicadores, neto], ignore_index=True)


# ----------------------------------------------------------------------------
# Punto de entrada unico que usa genera_graficas.py
# ----------------------------------------------------------------------------

def carga_todo():
    """Regresa (resumen_por_grupo, df_validacion, indicadores_subejercicio)."""
    # Se crean en la primera corrida para que quede claro donde van los datos.
    for carpeta in (CSV_DIR, XLS_DIR):
        carpeta.mkdir(parents=True, exist_ok=True)
    df_csv = carga_cuenta_publica()
    df_tomo = carga_tomo_vii()
    df_val = valida_csv_vs_tomo(df_csv, df_tomo)
    resumen = resumen_por_grupo_anio(tabla_larga(clasifica(df_csv)))
    df_ind = agrega_total_sin_capitulos(indicadores_subejercicio(df_tomo))
    return resumen, df_val, df_ind


if __name__ == "__main__":
    resumen, df_val, df_ind = carga_todo()
    print(f"\nResumen por grupo y anio: {len(resumen)} filas, "
          f"{resumen['grupo'].nunique()} grupos, anios {sorted(resumen['anio'].unique())}")
    print(f"Indicadores de subejercicio: {len(df_ind)} filas")
    print("\nDatos listos. Corre genera_graficas.py para producir las figuras.")
