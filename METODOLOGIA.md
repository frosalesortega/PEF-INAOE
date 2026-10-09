# Notas metodológicas

Corresponden a la sección 3 del informe *Evolución del gasto en viajes,
congresos y publicaciones y del subejercicio presupuestal del INAOE,
2015–2025*, del Colegio del Personal Académico (CPA).

## Fuentes

- **Cuenta Pública, Datos Abiertos de Transparencia Presupuestaria**
  (<https://www.transparenciapresupuestaria.gob.mx/>), Ramo 38, Unidad
  Responsable 91U, ejercicios 2015–2025. De esta fuente se obtiene el detalle
  por *partida específica* de cinco dígitos, que es el único nivel en el que
  pueden distinguirse viáticos de pasajes, o gasto nacional de gasto al
  extranjero. Para el INAOE esta base registra exclusivamente recursos fiscales.

- **Tomo VII de la Cuenta Pública**
  (<https://www.cuentapublica.hacienda.gob.mx/>), Estado Analítico del Ejercicio
  del Presupuesto de Egresos en Clasificación por Objeto del Gasto, informante
  91U, ejercicios 2015–2025. Es el informe que el propio Instituto rinde a la
  Secretaría de Hacienda. Llega únicamente a nivel de *concepto* —no distingue
  viáticos de pasajes—, pero es la única fuente que reporta de forma
  desagregada el presupuesto aprobado, las ampliaciones y reducciones, el
  presupuesto modificado y el gasto devengado. De aquí proviene todo el análisis
  de subejercicio y la verificación del gasto ejercido.

## Indicadores

El presupuesto de una institución pública cambia a lo largo del año: al
*presupuesto aprobado* se le pueden asignar recursos adicionales o retirarle
recursos. El resultado de estas adecuaciones es el *presupuesto modificado*, es
decir, los recursos que la institución tiene efectivamente disponibles al cierre
del ejercicio. El *gasto devengado* corresponde a los recursos que la
institución llegó a comprometer y ejercer.

De estas tres cifras se derivan tres indicadores distintos:

| Indicador | Cómo se calcula | Qué capta |
|---|---|---|
| **Reducción** | aprobado − modificado | Recursos que le fueron **retirados** al Instituto durante el año. Es una decisión externa: ese dinero nunca estuvo disponible para gastarse. |
| **Subejercicio** | modificado − devengado | Recursos que el Instituto **sí tenía autorizados al cierre** y no llegó a ejercer. Es el indicador que habla de capacidad de ejecución. |
| **No devengado** | aprobado − devengado | Todo el presupuesto que **no se gastó**, sin importar por cuál de las dos vías salió. Es la suma de los dos anteriores. |

El indicador que suele citarse —el subejercicio— puede llegar a cero de forma
contable si se le retiran recursos al presupuesto antes del cierre del
ejercicio. Por ello, en el análisis se reportan los tres por separado.

## Partidas agrupadas en cada rubro

- **Viáticos:** 37504 (viáticos nacionales) y 37602 (viáticos en el extranjero).
- **Pasajes:** 37104 y 37204 (aéreos y terrestres nacionales); 37106 y 37206
  (aéreos y terrestres internacionales).
- **Congresos:** 38301 (congresos y convenciones).
- **Publicaciones y difusión:** 33603 (impresión de documentos oficiales), 33604
  (impresión y elaboración de material informativo) y 33605 (información en
  medios masivos). Se verificó que el Instituto no ejerce recursos en las
  partidas de comunicación social (36101 y 36201) en ninguno de los once años
  analizados.
- **Subejercicio:** capítulos 2000 (materiales y suministros), 3000 (servicios
  generales) y 4000 (transferencias, asignaciones y subsidios), más los
  capítulos de inversión cuando registran gasto. Se excluye el capítulo 1000
  (servicios personales).

## Limitaciones y supuestos

- **Ministración frente a gasto devengado.** En la base de Cuenta Pública, el
  importe registrado como ejercido para el INAOE corresponde en varios años a la
  ministración del subsidio —el recurso transferido por el ramo— y no al gasto
  efectivamente devengado. Esto se detecta porque en esos años los importes
  modificado, devengado, pagado y ejercido son idénticos entre sí en cada
  partida. Para distinguir unos años de otros se comparó, concepto por concepto
  y año por año, el ejercido de la Cuenta Pública contra el devengado del Tomo
  VII, y se consideró verificada la cifra cuando la razón entre ambas se sitúa
  entre 0.85 y 1.15. Los años que no superan esa prueba son los señalados en
  naranja en las gráficas de la sección 1 del informe.

- **Ejercicio 2023.** El Tomo VII de ese año registra el presupuesto modificado
  como idéntico al aprobado en todos los capítulos, es decir, sin una sola
  adecuación presupuestaria en todo el año, lo cual es implausible y no coincide
  con lo que el Instituto reportó a su Junta de Gobierno. En consecuencia, las
  cifras de subejercicio de 2023 están sobrestimadas, las de reducción están
  subestimadas, y ese año no es estrictamente comparable con el resto. Lo mismo
  ocurre, en menor medida, con 2018 y 2021.

- **Valores negativos de subejercicio.** En algunos años y capítulos el gasto
  devengado supera al presupuesto que el reporte registra como autorizado, lo
  que produce un subejercicio negativo. No se trata de un error de cálculo ni de
  un gasto irregular: ocurre en rubros de gasto inevitable cuyo presupuesto no
  se actualiza formalmente en el reporte, señaladamente los servicios básicos
  (energía eléctrica, agua) y, en el capítulo de nómina, el pago de estímulos al
  personal. En 2023 el fenómeno se multiplica por la razón expuesta en el punto
  anterior.

- **Alcance fiscal.** Todo el análisis de la sección 1 del informe se refiere a
  recursos fiscales. El Tomo VII, del que proviene el gasto devengado, mezcla
  recursos fiscales y propios sin que ninguna fuente pública permita separarlos
  a nivel de ejercicio. Dado que el Instituto capta y ejerce una proporción
  reducida de recursos propios, el sesgo que esto introduce se estima menor,
  pero no es nulo. Por la misma razón, los cuadros basados en Cuenta Pública y
  los basados en el Tomo VII no son directamente sumables entre sí.

- **Deflactor.** Los montos en pesos constantes de 2025 se obtuvieron con el
  Índice Nacional de Precios al Consumidor, promedio anual. Los valores
  empleados son provisionales y deberán sustituirse por la serie oficial del
  INEGI para cualquier uso que requiera precisión en los términos reales. Están
  en el diccionario `INPC` de `inaoe_datos.py`.

- **Herramientas.** Análisis realizado con asistencia de Claude Code
  (Anthropic), modelo Claude Opus 5, septiembre–octubre de 2026.

## Aviso

> Las cifras presentadas en este documento provienen del procesamiento de bases
> de datos públicas del Gobierno Federal y se elaboraron de buena fe, con el
> único propósito de informar a la comunidad académica del Instituto. No
> constituyen una cifra oficial ni sustituyen la información que compete emitir
> a la Dirección de Administración y Finanzas u otras instancias del INAOE, y
> están sujetas a confirmación, corrección o aclaración por parte de la
> autoridad competente. La metodología completa, los datos intermedios y el
> código utilizado están disponibles para quien desee verificarlos o señalar
> errores.
