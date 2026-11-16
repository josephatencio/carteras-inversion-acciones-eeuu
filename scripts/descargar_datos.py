"""Descarga los datos del proyecto desde sus fuentes públicas.

Fuentes
* Yahoo Finance, para los precios de cierre ajustado mensuales y las acciones en circulación.
* Biblioteca de Kenneth French, para Mkt-RF, SMB, HML, RF y momentum.
* FRED, para el rendimiento del Tesoro a 20 años (tasa libre de riesgo vigente).
* Finviz, para el P/E esperado por sector.

Uso
    python scripts/descargar_datos.py --carpeta data_nueva

Los datos del informe están en data/. Las fuentes revisan sus series, así que una descarga nueva
no reproduce exactamente esos archivos; por eso el script escribe en otra carpeta, salvo que se le
pida data. Para actualizar el análisis, cambie DATOS, FIN, RF_VIGENTE_ANUAL y RF_VIGENTE_FECHA en
la primera celda del cuaderno (el script imprime la tasa y su fecha) y vuelva a correrlo.
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import re
import zipfile
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parents[1]
URL_FRENCH = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp"
URL_FF3 = f"{URL_FRENCH}/F-F_Research_Data_Factors_CSV.zip"
URL_MOM = f"{URL_FRENCH}/F-F_Momentum_Factor_CSV.zip"
URL_FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS20"
URL_FINVIZ = "https://finviz.com/groups.ashx?g=sector&v=120&o=name"
NAVEGADOR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

SECTORES = {
    "Bienes raíces": ["PLD", "AMT", "EQIX", "WELL"],
    "Comunicaciones": ["GOOG", "META", "NFLX", "TMUS"],
    "Consumo discrecional": ["AMZN", "TSLA", "HD", "TJX"],
    "Energía": ["XOM", "CVX", "EOG", "EPD"],
    "Finanzas": ["BRK-A", "JPM", "V", "BAC"],
    "Industrial": ["GE", "CAT", "RTX", "UNP"],
    "Materiales": ["SHW", "SCCO", "ECL", "APD"],
    "Consumo básico": ["WMT", "PG", "COST", "KO"],
    "Salud": ["LLY", "UNH", "JNJ", "ABBV"],
    "Tecnología": ["AAPL", "NVDA", "MSFT", "ORCL"],
    "Utilidades": ["NEE", "SO", "DUK", "CEG"],
}
FINVIZ_A_SECTOR = {
    "Real Estate": "Bienes raíces", "Communication Services": "Comunicaciones",
    "Consumer Cyclical": "Consumo discrecional", "Energy": "Energía", "Financial": "Finanzas",
    "Industrials": "Industrial", "Basic Materials": "Materiales",
    "Consumer Defensive": "Consumo básico", "Healthcare": "Salud", "Technology": "Tecnología",
    "Utilities": "Utilidades",
}


def bajar(url: str) -> bytes:
    respuesta = requests.get(url, headers=NAVEGADOR, timeout=60)
    respuesta.raise_for_status()
    return respuesta.content


def tabla_french(contenido_zip: bytes, columnas: list[str]) -> pd.DataFrame:
    """Lee la sección mensual de un CSV de Kenneth French, que termina en la primera línea que no
    empieza con AAAAMM."""
    with zipfile.ZipFile(io.BytesIO(contenido_zip)) as z:
        texto = z.read(z.namelist()[0]).decode("latin-1")
    filas = {}
    for linea in texto.splitlines():
        partes = [p.strip() for p in linea.split(",")]
        if re.fullmatch(r"\d{6}", partes[0]) and len(partes) >= len(columnas) + 1:
            mes = f"{partes[0][:4]}-{partes[0][4:]}"
            if mes not in filas:
                filas[mes] = [float(x) for x in partes[1 : len(columnas) + 1]]
        elif filas and not partes[0]:
            break
    tabla = pd.DataFrame.from_dict(filas, orient="index", columns=columnas)
    tabla.index.name = "fecha"
    return tabla


def factores_french() -> tuple[pd.DataFrame, pd.DataFrame]:
    ff3 = tabla_french(bajar(URL_FF3), ["mkt_rf", "smb", "hml", "rf"])
    mom = tabla_french(bajar(URL_MOM), ["mom"])
    return ff3, mom[mom["mom"] > -99]   # French usa -99.99 para datos faltantes


def tasa_tesoro_20_anios() -> tuple[float, str]:
    tabla = pd.read_csv(io.BytesIO(bajar(URL_FRED)))
    tabla.columns = ["fecha", "valor"]
    tabla["valor"] = pd.to_numeric(tabla["valor"], errors="coerce")
    ultimo = tabla.dropna().iloc[-1]
    return float(ultimo["valor"]) / 100, str(ultimo["fecha"])


def pe_finviz() -> pd.DataFrame:
    tablas = pd.read_html(io.BytesIO(bajar(URL_FINVIZ)))
    tabla = next(t for t in tablas if {"Name", "P/E", "Fwd P/E"}.issubset(set(map(str, t.columns))))
    tabla = tabla[tabla["Name"].isin(FINVIZ_A_SECTOR)]
    pe = pd.DataFrame({"sector": tabla["Name"].map(FINVIZ_A_SECTOR), "sector_finviz": tabla["Name"],
                       "pe": pd.to_numeric(tabla["P/E"], errors="coerce"),
                       "pe_forward": pd.to_numeric(tabla["Fwd P/E"], errors="coerce")})
    return pe.set_index("sector")


def precios_yahoo(tickers: list[str], inicio: str, fin: str) -> pd.DataFrame:
    import yfinance as yf

    hasta = (pd.Period(fin, "M") + 1).start_time.strftime("%Y-%m-%d")
    tabla = yf.download(tickers, start=f"{inicio}-01", end=hasta, interval="1mo", auto_adjust=True,
                        progress=False)["Close"]
    tabla.index = pd.DatetimeIndex(tabla.index).strftime("%Y-%m")
    tabla.index.name = "fecha"
    return tabla[tickers].astype(float)


def acciones_yahoo(tickers: list[str]) -> pd.Series:
    import yfinance as yf

    acciones = {}
    for ticker in tickers:
        info = yf.Ticker(ticker).info
        acciones[ticker] = float(info.get("sharesOutstanding")
                                 or info.get("impliedSharesOutstanding") or float("nan"))
    return pd.Series(acciones, name="acciones_en_circulacion")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--inicio", default="2003-09", help="Mes base, AAAA-MM")
    parser.add_argument("--fin", default=None,
                        help="Último mes, AAAA-MM; por defecto el último con datos en todas "
                             "las fuentes")
    parser.add_argument("--carpeta", default="data_nueva",
                        help="Carpeta de destino dentro del proyecto; data reemplaza los datos "
                             "del informe")
    args = parser.parse_args()

    carpeta = RAIZ / args.carpeta
    carpeta.mkdir(parents=True, exist_ok=True)
    tickers = [t for ts in SECTORES.values() for t in ts]
    sector_de = {t: s for s, ts in SECTORES.items() for t in ts}

    ff3, mom = factores_french()
    ultimo_cerrado = (pd.Period(dt.date.today(), "M") - 1).strftime("%Y-%m")
    fin = min(args.fin or ultimo_cerrado, ff3.index[-1], mom.index[-1])  # French publica con rezago
    precios = precios_yahoo(tickers, args.inicio, fin).loc[args.inicio:fin]
    acciones = acciones_yahoo(tickers)
    tasa, fecha_tasa = tasa_tesoro_20_anios()

    precios.to_csv(carpeta / "precios_mensuales.csv", float_format="%.10f")
    tabla = pd.DataFrame({"sector": pd.Series(sector_de), "acciones_en_circulacion": acciones})
    tabla.rename_axis("ticker").to_csv(carpeta / "empresas.csv")
    ff3.loc[:fin].to_csv(carpeta / "factores_fama_french.csv")
    mom.loc[:fin].to_csv(carpeta / "factor_momentum.csv")
    try:
        pe_finviz().to_csv(carpeta / "pe_por_sector.csv")
        origen_pe = "Finviz"
    except Exception as error:   # Finviz a veces bloquea las descargas automáticas
        origen_pe = f"no se pudo descargar ({error}); cópielo a mano desde {URL_FINVIZ}"
    print(f"Datos de {args.inicio} a {fin} ({len(precios)} meses) en {carpeta}")
    print(f"Tesoro a 20 años: {tasa:.4f} al {fecha_tasa}. P/E: {origen_pe}")


if __name__ == "__main__":
    main()
