# Datos

Todos los archivos vienen de fuentes públicas y se pueden volver a descargar con `scripts/descargar_datos.py`. Las fechas tienen el formato `AAAA-MM`.

| Archivo | Contenido | Unidad | Fuente |
|---|---|---|---|
| `precios_mensuales.csv` | Cierre mensual de cada empresa, ajustado por dividendos y divisiones, de septiembre de 2003 a septiembre de 2026 | USD | [Yahoo Finance](https://finance.yahoo.com) |
| `empresas.csv` | Sector y acciones en circulación de cada empresa | Acciones | Yahoo Finance, con el sector según [Finviz](https://finviz.com) |
| `factores_fama_french.csv` | Mkt-RF, SMB, HML y RF desde julio de 1926 | % mensual | [Biblioteca de Kenneth French](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) |
| `factor_momentum.csv` | Factor de momentum desde enero de 1927 | % mensual | Biblioteca de Kenneth French |
| `pe_por_sector.csv` | P/E y P/E esperado por sector | Veces | [Finviz](https://finviz.com/groups.ashx?g=sector&v=120) |

La tasa libre de riesgo vigente que se usa en el costo de capital es el rendimiento del Tesoro de Estados Unidos a 20 años, de [FRED](https://fred.stlouisfed.org/series/DGS20), que fue de 5.34 % el 30 de octubre de 2026. Está definida en la primera celda del cuaderno.

El período termina en septiembre de 2026, el último mes con datos en todas las fuentes, porque los factores de Kenneth French se publican con rezago. Una empresa sin precio en un mes todavía no cotizaba y entra al índice en cuanto tiene precios. La capitalización histórica usa el número de acciones más reciente para todo el período, así que solo aproxima el peso histórico de cada empresa. Si se repite la descarga, los datos pueden cambiar, porque Yahoo recalcula los precios ajustados con cada dividendo y Kenneth French revisa sus factores.
