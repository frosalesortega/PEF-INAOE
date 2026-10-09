#!/usr/bin/env python3
"""
Genera las diez figuras del informe del CPA sobre el gasto del INAOE en viajes,
congresos y publicaciones y sobre el subejercicio presupuestal, 2015-2025.

    python genera_graficas.py

Lee los datos con inaoe_datos.py y escribe los PNG en graficas/:

    aprobado_vs_ejercido_viaticos_nacionales.png       (Figura 1 del informe)
    aprobado_vs_ejercido_pasajes_nacionales.png        (Figura 1)
    aprobado_vs_ejercido_pasajes_internacionales.png   (Figura 1)
    aprobado_vs_ejercido_viaticos_internacionales.png  (Figura 1)
    aprobado_vs_ejercido_congresos.png                 (Figura 1)
    aprobado_vs_ejercido_publicaciones.png             (Figura 1)
    evolucion_rubros_pesos_constantes.png              (Figura 2)
    subejercicio_destino_total.png                     (Figura 3)
    subejercicio_pct_por_capitulo.png                  (Figura 4)
    descomposicion_viajes.png                          (Figura 5)

Los titulos, colores y posiciones de leyenda estan reunidos en el bloque de
configuracion de abajo para que se puedan ajustar sin tocar el codigo de
dibujo.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

import inaoe_datos as d  # noqa: E402


# =============================================================================
# Configuracion de las figuras
# =============================================================================

SALIDA_DIR = Path(__file__).resolve().parent / "graficas"
DPI = 150

COLOR_APROBADO = "#2b6ca3"   # azul: presupuesto aprobado / subejercicio
COLOR_REAL = "#2ca02c"       # verde: ejercido verificado / gasto real
COLOR_INCIERTO = "#ff7f0e"   # naranja: ejercido no verificable (ministracion)
COLOR_RETIRADO = "#d9833b"   # naranja quemado: presupuesto retirado (reduccion)
COLOR_NEGATIVO = "#bdbdbd"   # gris: barras de valor negativo

PESOS = FuncFormatter(lambda x, _: f"${x:,.0f}")
MILLONES = FuncFormatter(lambda x, _: f"${x:,.0f}M")

# Titulo que se dibuja dentro de cada figura.
TITULOS = {
    "aprobado_vs_ejercido_viaticos_nacionales.png": "Viáticos nacionales",
    "aprobado_vs_ejercido_pasajes_nacionales.png": "Pasajes nacionales",
    "aprobado_vs_ejercido_pasajes_internacionales.png": "Pasajes internacionales",
    "aprobado_vs_ejercido_viaticos_internacionales.png": "Viáticos internacionales",
    "aprobado_vs_ejercido_congresos.png": "Congresos",
    "aprobado_vs_ejercido_publicaciones.png": "Publicaciones",
    "evolucion_rubros_pesos_constantes.png": "Evolución del presupuesto aprobado",
    "subejercicio_destino_total.png": "Presupuesto de operación no ejercido y su causa",
    "subejercicio_pct_por_capitulo.png":
        "Proporción del presupuesto autorizado al cierre que no se ejerció",
    "descomposicion_viajes.png":
        "Destino del presupuesto de traslados y viáticos (concepto 3700)",
}

# Posicion de la leyenda cuando la automatica choca con las barras.
LEYENDA = {
    "aprobado_vs_ejercido_pasajes_nacionales.png": "lower left",
    "aprobado_vs_ejercido_publicaciones.png": "lower left",
}

# Que grupos de partidas entran en cada una de las seis graficas de la Figura 1.
PANELES_RUBRO = [
    ("viaticos_nacionales", ["Viaticos nacionales"]),
    ("viaticos_internacionales", ["Viaticos extranjero"]),
    ("pasajes_nacionales", ["Pasajes aereos nacionales", "Pasajes terrestres nacionales",
                            "Servicios integrales de traslado nacionales"]),
    ("pasajes_internacionales", ["Pasajes aereos internacionales",
                                 "Pasajes terrestres internacionales",
                                 "Servicios integrales de traslado extranjero"]),
    ("congresos", ["Congresos y convenciones", "Exposiciones / orden social"]),
    ("publicaciones", ["Publicaciones e impresiones", "Informacion en medios / difusion"]),
]

# Las cuatro series de la Figura 2.
RUBROS = {
    "Viáticos": ["Viaticos nacionales", "Viaticos extranjero"],
    "Pasajes": ["Pasajes aereos nacionales", "Pasajes aereos internacionales",
                "Pasajes terrestres nacionales", "Pasajes terrestres internacionales",
                "Servicios integrales de traslado nacionales",
                "Servicios integrales de traslado extranjero"],
    "Congresos": ["Congresos y convenciones", "Exposiciones / orden social"],
    "Publicaciones": ["Publicaciones e impresiones", "Informacion en medios / difusion"],
}

CONCEPTO_VIAJES = "3700"   # concepto del Tomo VII que descompone la Figura 5


def guarda(fig, archivo: str):
    SALIDA_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(SALIDA_DIR / archivo, dpi=DPI)
    plt.close(fig)
    print(f"  {archivo}")


def serie_rubro(resumen, rubro, columna):
    sub = resumen[resumen["grupo"].isin(RUBROS[rubro])]
    return sub.groupby("anio")[columna].sum().sort_index()


# =============================================================================
# Figura 1: aprobado vs. ejercido, seis rubros
# =============================================================================

def graficas_aprobado_vs_ejercido(resumen, df_val):
    """Seis graficas en pesos corrientes. La barra del ejercido va en verde
    cuando la cifra pudo verificarse contra el Tomo VII y en naranja con trama
    cuando no (ver inaoe_datos.anios_validos_grupo)."""
    for slug, grupos in PANELES_RUBRO:
        archivo = f"aprobado_vs_ejercido_{slug}.png"
        sub = resumen[resumen["grupo"].isin(grupos)].groupby("anio")[
            ["aprobado", "ejercido_o_devengado"]].sum()

        anios_ok = d.anios_validos_grupo(df_val, grupos[0])
        for otro in grupos[1:]:
            anios_ok &= d.anios_validos_grupo(df_val, otro)

        # Lienzo pequeno a proposito: en el informe van a 8 cm de ancho, asi que
        # mientras menos pulgadas tenga la figura, mas grande se lee el texto.
        fig, ax = plt.subplots(figsize=(4.8, 3.5))
        ax.bar(sub.index - 0.2, sub["aprobado"], width=0.4, color=COLOR_APROBADO)
        barras = ax.bar(sub.index + 0.2, sub["ejercido_o_devengado"], width=0.4,
                        color=[COLOR_REAL if a in anios_ok else COLOR_INCIERTO
                               for a in sub.index])
        for barra, anio in zip(barras, sub.index):
            if anio not in anios_ok:
                barra.set_hatch("////")

        handles = [
            plt.Rectangle((0, 0), 1, 1, color=COLOR_APROBADO, label="Aprobado"),
            plt.Rectangle((0, 0), 1, 1, color=COLOR_REAL, label="Ejercido (verificado)"),
            plt.Rectangle((0, 0), 1, 1, color=COLOR_INCIERTO, hatch="////",
                          label="Ejercido (por confirmar)"),
        ]
        ax.set_title(TITULOS[archivo], fontsize=10.5, fontweight="bold", pad=8)
        ax.set_xlabel("Año", fontsize=10)
        ax.set_ylabel("Pesos corrientes", fontsize=10)
        ax.yaxis.set_major_formatter(PESOS)
        ax.set_xticks(sorted(sub.index))
        ax.tick_params(axis="x", labelrotation=45, labelsize=9)
        ax.tick_params(axis="y", labelsize=9)
        ax.grid(axis="y", linewidth=0.4, alpha=0.4)
        ax.legend(handles=handles, fontsize=8, framealpha=0.9,
                  loc=LEYENDA.get(archivo, "best"))
        fig.tight_layout()
        guarda(fig, archivo)


# =============================================================================
# Figura 2: evolucion conjunta en pesos constantes
# =============================================================================

def grafica_evolucion_rubros(resumen):
    archivo = "evolucion_rubros_pesos_constantes.png"
    fig, ax = plt.subplots(figsize=(10, 5.2))
    for rubro in RUBROS:
        s = serie_rubro(resumen, rubro, "aprobado_real_2025")
        ax.plot(s.index, s.values, marker="o", linewidth=2, markersize=5, label=rubro)
    ax.set_title(TITULOS[archivo], fontsize=12.5, fontweight="bold", pad=10)
    ax.set_xlabel("Año")
    ax.set_ylabel(f"Pesos constantes de {d.ANIO_BASE_REAL}")
    ax.yaxis.set_major_formatter(PESOS)
    ax.set_xticks(sorted(resumen["anio"].unique()))
    ax.grid(axis="y", linewidth=0.4, alpha=0.4)
    ax.legend(fontsize=9)
    fig.tight_layout()
    guarda(fig, archivo)


# =============================================================================
# Figuras 3 y 4: subejercicio del presupuesto de operacion
# =============================================================================

def graficas_subejercicio(df_ind):
    # --- Figura 3: subejercicio vs. presupuesto retirado, agregado ---
    archivo = "subejercicio_destino_total.png"
    ope = df_ind[df_ind["nivel"] == d.NIVEL_TOTAL_ANALISIS].sort_values("anio").copy()
    ope["retirado"] = (-ope["ampliaciones"]).clip(lower=0)
    ope["no_gastado"] = ope["subejercicio"].clip(lower=0)
    ope["pct"] = ope["no_gastado"] / ope["aprobado"] * 100

    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    ax.bar(ope["anio"] - 0.2, ope["no_gastado"] / 1e6, width=0.4, color=COLOR_APROBADO,
           label="Lo tenía autorizado y no lo ejerció (subejercicio)")
    ax.bar(ope["anio"] + 0.2, ope["retirado"] / 1e6, width=0.4, color=COLOR_RETIRADO,
           label="Se le retiró durante el año (reducción)")
    for x, v, pct in zip(ope["anio"] - 0.2, ope["no_gastado"] / 1e6, ope["pct"]):
        if v > 0:
            ax.annotate(f"{pct:.0f}%", xy=(x, v), xytext=(0, 3), textcoords="offset points",
                        ha="center", fontsize=7.5, color=COLOR_APROBADO)
    ax.set_title(TITULOS[archivo], fontsize=12.5, fontweight="bold", pad=10)
    ax.set_xlabel("Año")
    ax.set_ylabel("Millones de pesos")
    ax.yaxis.set_major_formatter(MILLONES)
    ax.set_xticks(sorted(ope["anio"].unique()))
    ax.grid(axis="y", linewidth=0.4, alpha=0.4)
    ax.legend(fontsize=9, loc="upper right")
    fig.tight_layout()
    guarda(fig, archivo)

    # --- Figura 4: porcentaje no ejercido por capitulo ---
    archivo = "subejercicio_pct_por_capitulo.png"
    cap = df_ind[(df_ind["nivel"] == "capitulo")
                 & (df_ind["codigo"].isin(d.CAPITULOS_SUBEJERCICIO))]
    codigos = [c for c in d.CAPITULOS_SUBEJERCICIO if c in cap["codigo"].unique()]

    fig, axes = plt.subplots(1, len(codigos), figsize=(3.6 * len(codigos), 3.2))
    axes = axes if hasattr(axes, "flatten") else [axes]
    for ax, codigo in zip(axes, codigos):
        g = cap[cap["codigo"] == codigo].sort_values("anio")
        barras = ax.bar(g["anio"], g["pct_subejercicio"], width=0.7,
                        color=[COLOR_APROBADO if v >= 0 else COLOR_NEGATIVO
                               for v in g["pct_subejercicio"]])
        for barra, v in zip(barras, g["pct_subejercicio"]):
            if v < 0:
                barra.set_hatch("//")
                barra.set_edgecolor("dimgray")
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_title(d.NOMBRE_LLANO_CAPITULO.get(codigo, codigo), fontsize=10)
        ax.set_ylabel("% no ejercido", fontsize=9)
        ax.set_xticks(sorted(g["anio"].unique()))
        ax.tick_params(axis="x", labelrotation=45, labelsize=8)
        ax.tick_params(axis="y", labelsize=8)
        ax.grid(axis="y", linewidth=0.4, alpha=0.4)
    # Los paneles ya llevan el nombre del capitulo; el titulo general dice que
    # es lo que se mide en los tres.
    fig.suptitle(TITULOS[archivo], fontsize=12.5, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    guarda(fig, archivo)


# =============================================================================
# Figura 5: destino del presupuesto de traslados y viaticos
# =============================================================================

def grafica_descomposicion_viajes(df_ind):
    """Barras apiladas: gasto real + subejercicio + presupuesto retirado suman
    exactamente el presupuesto aprobado del concepto."""
    archivo = "descomposicion_viajes.png"
    vj = df_ind[(df_ind["nivel"] == "concepto")
                & (df_ind["codigo"] == CONCEPTO_VIAJES)].set_index("anio").sort_index()
    vj = vj.assign(reduccion=vj["aprobado"] - vj["modificado"])

    anios = vj.index.values
    dev = (vj["devengado"] / 1e6).values
    sub = (vj["subejercicio"].clip(lower=0) / 1e6).values
    red = (vj["reduccion"].clip(lower=0) / 1e6).values
    aprob = (vj["aprobado"] / 1e6).values

    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    ax.bar(anios, dev, width=0.66, color=COLOR_REAL, label="Gasto real (devengado)")
    ax.bar(anios, sub, bottom=dev, width=0.66, color=COLOR_APROBADO,
           label="Lo tenía autorizado y no lo ejerció (subejercicio)")
    ax.bar(anios, red, bottom=dev + sub, width=0.66, color=COLOR_RETIRADO,
           label="Se le retiró durante el año (reducción)")

    for x, total, gasto in zip(anios, aprob, dev):
        ax.annotate(f"{gasto / total * 100:.0f}%", xy=(x, total), xytext=(0, 4),
                    textcoords="offset points", ha="center", fontsize=8,
                    fontweight="bold", color="#333333")

    ax.set_title(TITULOS[archivo], fontsize=12.5, fontweight="bold", pad=10)
    ax.set_xlabel("Año")
    ax.set_ylabel("Millones de pesos")
    ax.yaxis.set_major_formatter(MILLONES)
    ax.set_xticks(anios)
    ax.set_ylim(0, max(aprob) * 1.16)
    ax.grid(axis="y", linewidth=0.4, alpha=0.4)
    ax.legend(fontsize=9, loc="lower left", framealpha=0.92)
    fig.tight_layout()
    guarda(fig, archivo)


def main():
    resumen, df_val, df_ind = d.carga_todo()
    print(f"\nGenerando figuras en {SALIDA_DIR}/")
    graficas_aprobado_vs_ejercido(resumen, df_val)
    grafica_evolucion_rubros(resumen)
    graficas_subejercicio(df_ind)
    grafica_descomposicion_viajes(df_ind)
    print("\nListo.")


if __name__ == "__main__":
    main()
