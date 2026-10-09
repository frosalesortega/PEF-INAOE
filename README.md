# Gasto en viajes, congresos y publicaciones del INAOE, 2015–2025

Código para reproducir las figuras del informe *Evolución del gasto en viajes,
congresos y publicaciones y del subejercicio presupuestal del INAOE,
2015–2025*, elaborado por el Colegio del Personal Académico (CPA) del Instituto
Nacional de Astrofísica, Óptica y Electrónica.

El análisis se construye exclusivamente a partir de dos fuentes públicas del
Gobierno Federal:

- Los **CSV de Cuenta Pública** no están aquí: pesan entre 96 y 311 MB cada uno
  y hay que descargarlos del portal oficial ([instrucciones abajo](#fuente-a--csv-de-cuenta-pública)).
- Los **archivos del Tomo VII** sí están incluidos, en `datos/tomo_vii/`, porque
  son once descargas manuales de 204 KB en total y conseguirlas a mano es la
  parte más tediosa de reproducir el análisis. Son copias sin modificar de lo
  publicado por Hacienda; [abajo se explica](#fuente-b--tomo-vii-de-la-cuenta-pública)
  cómo verificarlas contra el original.

Ningún dato derivado se versiona: los extractos del INAOE, las tablas y las
figuras los genera el código.

## Qué produce

Diez figuras en `graficas/`, que corresponden a las cinco figuras del informe.
Están incluidas en el repositorio para que puedan verse sin necesidad de correr
nada, y se sobrescriben al ejecutar el código:

| Archivo | Figura del informe |
|---|---|
| `aprobado_vs_ejercido_viaticos_nacionales.png` | Figura 1 |
| `aprobado_vs_ejercido_pasajes_nacionales.png` | Figura 1 |
| `aprobado_vs_ejercido_pasajes_internacionales.png` | Figura 1 |
| `aprobado_vs_ejercido_viaticos_internacionales.png` | Figura 1 |
| `aprobado_vs_ejercido_congresos.png` | Figura 1 |
| `aprobado_vs_ejercido_publicaciones.png` | Figura 1 |
| `evolucion_rubros_pesos_constantes.png` | Figura 2 |
| `subejercicio_destino_total.png` | Figura 3 |
| `subejercicio_pct_por_capitulo.png` | Figura 4 |
| `descomposicion_viajes.png` | Figura 5 |

Las notas metodológicas, las partidas que se agrupan en cada rubro y las
limitaciones del análisis están en [`METODOLOGIA.md`](METODOLOGIA.md).

## Requisitos

Python 3.10 o posterior. Para instalar las dependencias:

```bash
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Se necesitan unos **2 GB de espacio libre**: los archivos de Cuenta Pública son
grandes (de 96 a 311 MB cada uno) porque contienen el presupuesto federal
completo, del que el código extrae la parte del INAOE.

## Paso 1: descargar los datos

### Fuente A — CSV de Cuenta Pública

Portal: <https://www.transparenciapresupuestaria.gob.mx/Datos-Abiertos>

Busca los datos abiertos de **Cuenta Pública**, apartado de *Estado analítico
del ejercicio del presupuesto de egresos*. Los ejercicios recientes aparecen en
la Cuenta Pública anual; los más antiguos, en las **bases históricas** del
mismo apartado.

Descarga un archivo por año, de 2015 a 2025, y descomprímelos en
`datos/cuenta_publica/`. Los nombres originales son del tipo:

```
cuenta_publica_2016_gf_ecd_epe.csv   … hasta 2025
cuenta_publica_2015_ra_ecd_epe.csv   (2015 usa otra nomenclatura)
```

**Puedes renombrarlos como quieras siempre que el nombre contenga el año de
cuatro dígitos**: el código detecta el año a partir del nombre del archivo y
lo contrasta contra la columna `Ciclo` del propio CSV.

Si un año no está disponible, omítelo: el código trabaja con los años que
encuentre y avisa cuáles faltan. Las series del informe cubren 2015–2025.

> Los encabezados de estos archivos cambian de un año a otro, y en 2025 cambian
> por completo (`R`, `UR`, `PTDA`, `Original_Bruto`…). El código los resuelve
> con un diccionario de alias y nunca por posición de columna, así que no hace
> falta editarlos. Si un año futuro estrena nombres nuevos, basta con agregarlos
> a `COLUMN_ALIASES` en `inaoe_datos.py`.

### Fuente B — Tomo VII de la Cuenta Pública

**Ya está en el repositorio**, en `datos/tomo_vii/`: once archivos
`91U.03.F_OBJGASTO_<año>.xls`, de 2015 a 2025, de 13 a 42 KB cada uno. No hay
que descargar nada para correr el código.

Se incluyen porque son once descargas manuales a través de un buscador, sin URL
directa estable, y bajarlas a mano es la parte más tediosa de reproducir el
análisis. Son copias sin modificar de los archivos publicados por Hacienda.

Para verificarlas contra el original, o para agregar un año nuevo:

1. Entra a <https://www.cuentapublica.hacienda.gob.mx/> y elige el año.
2. Ve a **Tomo VII — Sector Paraestatal**.
3. En la búsqueda por informante, escribe **`91U`** (la clave del INAOE).
4. Descarga el **«Estado Analítico del Ejercicio del Presupuesto de Egresos en
   Clasificación por Objeto del Gasto (armonizado)»**.

Déjalo en `datos/tomo_vii/`. El código reconoce cualquier `.xls` que contenga
`OBJGASTO` y un año en el nombre.

### Estructura esperada

```
datos/
├── cuenta_publica/          ← lo que tienes que descargar
│   ├── cuenta_publica_2015_ra_ecd_epe.csv
│   ├── cuenta_publica_2016_gf_ecd_epe.csv
│   └── …  hasta 2025
├── tomo_vii/                ← ya incluido en el repositorio
│   ├── 91U.03.F_OBJGASTO_2015.xls
│   └── …  hasta 2025
└── intermedios/             ← lo genera el código
```

## Paso 2: generar las figuras

```bash
python genera_graficas.py
```

La primera corrida tarda unos minutos, casi todo en leer los CSV grandes. El
código guarda en `datos/intermedios/` un extracto con solo las filas del INAOE,
de modo que las corridas siguientes son casi inmediatas. Si quieres rehacer la
extracción desde cero, borra esa carpeta.

Las figuras quedan en `graficas/`.

## Qué verificar al correrlo

El programa imprime, concepto por concepto y año por año, la razón entre el
importe ejercido del CSV y el devengado del Tomo VII:

```
2024 concepto 3700: razon=0.98 -> verificado
2021 concepto 3700: razon=2.69 -> no verificable (ministracion)
```

Esa tabla es el control de calidad del análisis y determina qué barras salen en
verde y cuáles en naranja con trama en la Figura 1. La explicación de por qué
las dos fuentes difieren en ciertos años está en
[`METODOLOGIA.md`](METODOLOGIA.md), en «Ministración frente a gasto devengado».

## Organización del código

| Archivo | Qué hace |
|---|---|
| `inaoe_datos.py` | Lee las dos fuentes, filtra al INAOE, valida una contra otra y arma las tablas. |
| `genera_graficas.py` | Dibuja las diez figuras. Títulos, colores y leyendas están reunidos al inicio. |

El código está parametrizado por ramo y unidad responsable: cambiando `RAMO` y
`UR` al inicio de `inaoe_datos.py` corre para cualquier otra entidad del mismo
ramo, aunque los nombres de los rubros y las notas del informe son propios del
INAOE.

## Licencia

Código bajo licencia MIT; ver [`LICENSE`](LICENSE).

Los archivos de `datos/tomo_vii/` son documentos públicos del Gobierno Federal,
reproducidos sin modificación, y no están cubiertos por esa licencia.

## Aviso

Las cifras provienen del procesamiento de bases de datos públicas del Gobierno
Federal y se elaboraron de buena fe, con el único propósito de informar a la
comunidad académica del Instituto. No constituyen cifras oficiales ni sustituyen
la información que compete emitir a la Dirección de Administración y Finanzas u
otras instancias del INAOE, y están sujetas a confirmación, corrección o
aclaración por parte de la autoridad competente.

Si encuentras un error, un supuesto discutible o una mejor manera de hacer
alguno de estos cálculos, abre un *issue*.
