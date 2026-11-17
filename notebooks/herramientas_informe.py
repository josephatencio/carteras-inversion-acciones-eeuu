"""Da formato LaTeX a las tablas que el cuaderno copia al informe.

Este archivo no calcula nada del análisis. Recibe tablas ya calculadas y las escribe como
cuadros de LaTeX con el estilo del informe (líneas de booktabs, un mismo tamaño de letra y una
nota al pie del cuadro).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def dec(d: int):
    return lambda x: "" if pd.isna(x) else f"{x:.{d}f}".replace("-", "$-$")


def pct(d: int):
    return lambda x: "" if pd.isna(x) else f"{100 * x:.{d}f}\\,\\%".replace("-", "$-$")


def entero(x) -> str:
    return "" if pd.isna(x) else f"{int(round(x)):,}"


def estrellas(p) -> str:
    if pd.isna(p):
        return ""
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


def _armar(titulo: str, etiqueta: str, cuerpo: str, nota: str, letra: str,
           separacion: float | None) -> str:
    partes = [r"\begin{table}[htbp]", r"\centering", rf"\caption{{{titulo}}}",
              rf"\label{{{etiqueta}}}", letra]
    if separacion is not None:
        partes.append(rf"\setlength{{\tabcolsep}}{{{separacion}pt}}")
    partes.append(cuerpo)
    if nota:
        partes.append(rf"\fuente{{{nota}}}")
    partes.append(r"\end{table}")
    return "\n".join(partes) + "\n"


def cuadro(tabla: pd.DataFrame, columnas: list[tuple[str, str, object]], titulo: str, etiqueta: str,
           nota: str = "", primera: str = "Sector", letra: str = r"\small",
           separacion: float | None = None, alineacion: str | None = None,
           separar_despues: tuple = ()) -> str:
    alineacion = alineacion or "l" + "r" * len(columnas)
    encabezado = " & ".join([primera] + [c[0] for c in columnas]) + r" \\"
    filas = []
    for i, (nombre, fila) in enumerate(tabla.iterrows()):
        valores = [formato(fila[col]) for _, col, formato in columnas]
        filas.append(" & ".join([str(nombre)] + valores) + r" \\")
        if i in separar_despues:
            filas.append(r"\midrule")
    cuerpo = "\n".join([rf"\begin{{tabular}}{{{alineacion}}}", r"\toprule", encabezado, r"\midrule",
                        *filas, r"\bottomrule", r"\end{tabular}"])
    return _armar(titulo, etiqueta, cuerpo, nota, letra, separacion)


def matriz(tabla: pd.DataFrame, titulo: str, etiqueta: str, formato, nota: str = "",
           abreviaturas: dict | None = None, letra: str = r"\footnotesize",
           separacion: float | None = 3.5) -> str:
    """Matriz cuadrada con la diagonal sombreada (por ejemplo, la de covarianzas)."""
    abreviaturas = abreviaturas or {}
    nombres = list(tabla.index)
    encabezado = " & ".join([""] + [abreviaturas.get(c, c) for c in nombres]) + r" \\"
    filas = []
    for i, f in enumerate(nombres):
        celdas = [abreviaturas.get(f, f)]
        for j, c in enumerate(nombres):
            v = formato(tabla.loc[f, c])
            celdas.append(rf"\cellcolor{{fondo}}{v}" if i == j else v)
        filas.append(" & ".join(celdas) + r" \\")
    cuerpo = "\n".join([rf"\begin{{tabular}}{{l{'r' * len(nombres)}}}", r"\toprule", encabezado,
                        r"\midrule", *filas, r"\bottomrule", r"\end{tabular}"])
    return _armar(titulo, etiqueta, cuerpo, nota, letra, separacion)


def escribir(carpeta: Path, nombre: str, texto: str) -> None:
    Path(carpeta).mkdir(parents=True, exist_ok=True)
    (Path(carpeta) / f"{nombre}.tex").write_text(texto, encoding="utf-8")


def macros(cifras: dict[str, str]) -> str:
    lineas = ["% Generado por notebooks/analisis.ipynb. No editar a mano."]
    lineas += [f"\\newcommand{{\\cifra{nombre}}}{{{valor}}}" for nombre, valor in cifras.items()]
    return "\n".join(lineas) + "\n"


def lista(nombres, y: str = "y", ninguno: str = "ninguno") -> str:
    """["Salud", "Tecnología"] -> "salud y tecnología", para usarla dentro de una oración. En la
    versión en inglés, y="and" y ninguno="none"."""
    nombres = [n.lower() for n in nombres]
    if not nombres:
        return ninguno
    return nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + f" {y} " + nombres[-1]
