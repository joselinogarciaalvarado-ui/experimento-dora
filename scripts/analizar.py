#!/usr/bin/env python3
"""Calcula las métricas DORA por condición y aplica las pruebas estadísticas.

Uso:
    python3 scripts/analizar.py [ruta/resultados.csv]

Genera en la carpeta resultados/:
    resumen_por_condicion.csv   métricas DORA y de proceso por condición
    detalle_cambios.csv         cada cambio con su clasificación
    pruebas_estadisticas.txt    Friedman, Wilcoxon, Cochran y McNemar
    lead_time.png, tasa_fallos.png
"""
import re
import sys
from itertools import combinations
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.contingency_tables import cochrans_q, mcnemar

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "resultados"
CONDICIONES = ["A", "B", "C"]
NOMBRES = {"A": "A. Manual", "B": "B. CI/CD", "C": "C. CI/CD + DevSecOps"}
EN_PRODUCCION = {"desplegado", "fallo_humo"}


def cargar(ruta):
    df = pd.read_csv(ruta)
    cat = pd.read_csv(RAIZ / "cambios" / "catalogo.csv")
    df["cambio"] = pd.to_numeric(df["cambio"], errors="coerce")
    df = df.merge(cat[["cambio", "tipo"]].rename(columns={"tipo": "tipo_cambio"}), on="cambio", how="left")
    for c in ["t_commit", "t_inicio", "t_fin", "duracion_s", "lead_time_s", "pasos_manuales",
              "errores_operador", "recuperacion_s"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # Los despliegues de la versión base (sin número de cambio) no entran al análisis.
    df = df.dropna(subset=["cambio"])
    return df.sort_values(["condicion", "t_fin"]).reset_index(drop=True)


def clasificar(df):
    """Marca, por cambio, si llegó a producción, si falló allí y cuánto tardó en recuperarse."""
    filas = []
    for cond, g in df.groupby("condicion"):
        cambios = g[g["tipo_registro"] == "cambio"].drop_duplicates("cambio", keep="last")
        correcciones = g[g["tipo_registro"] == "correccion"]
        for _, c in cambios.iterrows():
            en_prod = c["resultado"] in EN_PRODUCCION
            latente = c["resultado"] == "desplegado" and c["tipo_cambio"] != "normal"
            fallo = c["resultado"] == "fallo_humo" or latente
            corr = correcciones[(correcciones["cambio"] == c["cambio"]) & (correcciones["t_fin"] > c["t_fin"])]
            corr = corr.iloc[0] if len(corr) else None
            if c["resultado"] == "fallo_humo":
                recuperacion = c["recuperacion_s"]
            elif latente and corr is not None:
                recuperacion = corr["t_fin"] - c["t_fin"]
            else:
                recuperacion = np.nan
            filas.append({
                "condicion": cond, "cambio": int(c["cambio"]), "tipo_cambio": c["tipo_cambio"],
                "resultado": c["resultado"], "en_produccion": en_prod, "fallo_en_produccion": fallo,
                "defecto_latente": latente,
                "detectado_antes": c["resultado"] in {"bloqueado_pruebas", "bloqueado_seguridad"},
                "retrabajo": bool(fallo and corr is not None and corr["resultado"] in EN_PRODUCCION),
                "lead_time_s": c["lead_time_s"], "duracion_s": c["duracion_s"],
                "pasos_manuales": c["pasos_manuales"], "errores_operador": c["errores_operador"],
                "recuperacion_s": recuperacion,
            })
    return pd.DataFrame(filas)


def resumen(df, det):
    filas = []
    for cond in CONDICIONES:
        d = det[det["condicion"] == cond]
        if d.empty:
            continue
        g = df[df["condicion"] == cond]
        despliegues = int(g["resultado"].isin(EN_PRODUCCION).sum())
        normales = d[(d["tipo_cambio"] == "normal") & (d["resultado"] == "desplegado")]
        defectos = d[d["tipo_cambio"] != "normal"]
        filas.append({
            "condicion": NOMBRES[cond],
            "cambios_registrados": len(d),
            "despliegues_en_produccion": despliegues,
            "lead_time_mediana_s": normales["lead_time_s"].median(),
            "lead_time_RIC_s": normales["lead_time_s"].quantile(.75) - normales["lead_time_s"].quantile(.25),
            "duracion_mediana_s": normales["duracion_s"].median(),
            # Capacidad de despliegue: cuántos despliegues caben en una hora al ritmo medido.
            "capacidad_despliegues_por_hora": 3600 / normales["duracion_s"].median() if len(normales) else np.nan,
            "tasa_fallos_por_cambio": d["fallo_en_produccion"].sum() / despliegues if despliegues else np.nan,
            "tasa_retrabajo": d["retrabajo"].sum() / despliegues if despliegues else np.nan,
            "recuperacion_mediana_s": d["recuperacion_s"].median(),
            "defectos_detectados_antes": f"{int(defectos['detectado_antes'].sum())}/{len(defectos)}",
            "defectos_seguridad_en_produccion": int(((defectos["tipo_cambio"] == "defecto_seguridad")
                                                      & defectos["en_produccion"]).sum()),
            "pasos_manuales_promedio": d["pasos_manuales"].mean(),
            "errores_operador_total": int(d["errores_operador"].fillna(0).sum()),
        })
    return pd.DataFrame(filas)


def pruebas(det):
    lineas = []
    presentes = [c for c in CONDICIONES if c in set(det["condicion"])]
    if len(presentes) < 2:
        return "Se necesitan al menos dos condiciones para las pruebas estadísticas."

    for var in ["lead_time_s", "duracion_s"]:
        normales = det[(det["tipo_cambio"] == "normal") & (det["resultado"] == "desplegado")]
        ancho = normales.pivot(index="cambio", columns="condicion", values=var).dropna()
        lineas.append(f"\n=== {var} (cambios normales desplegados en todas las condiciones, n = {len(ancho)}) ===")
        if len(presentes) == 3 and len(ancho) >= 5:
            chi2, p = stats.friedmanchisquare(*[ancho[c] for c in presentes])
            w = chi2 / (len(ancho) * (len(presentes) - 1))
            lineas.append(f"Friedman: chi2 = {chi2:.3f}, p = {p:.4g}, W de Kendall = {w:.3f}")
        pares = list(combinations(presentes, 2))
        for a, b in pares:
            if len(ancho) >= 5:
                res = stats.wilcoxon(ancho[a], ancho[b])
                p_aj = min(res.pvalue * len(pares), 1.0)
                dif = (ancho[a] - ancho[b]).median()
                lineas.append(f"Wilcoxon {a} vs {b}: W = {res.statistic:.1f}, p ajustada (Bonferroni) = {p_aj:.4g}, "
                              f"diferencia mediana = {dif:.1f} s")

    ancho = det.pivot(index="cambio", columns="condicion", values="fallo_en_produccion").dropna().astype(int)
    lineas.append(f"\n=== Fallo en producción (los {len(ancho)} cambios en cada condición) ===")
    if len(presentes) == 3 and len(ancho) >= 5:
        q = cochrans_q(ancho[presentes].values)
        lineas.append(f"Q de Cochran: Q = {q.statistic:.3f}, p = {q.pvalue:.4g}")
    for a, b in combinations(presentes, 2):
        tabla = pd.crosstab(ancho[a], ancho[b]).reindex(index=[0, 1], columns=[0, 1], fill_value=0)
        m = mcnemar(tabla.values, exact=True)
        lineas.append(f"McNemar exacta {a} vs {b}: p = {m.pvalue:.4g}")
    return "\n".join(lineas)


def graficas(det):
    normales = det[(det["tipo_cambio"] == "normal") & (det["resultado"] == "desplegado")]
    presentes = [c for c in CONDICIONES if c in set(det["condicion"])]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.boxplot([normales[normales["condicion"] == c]["lead_time_s"] / 60 for c in presentes],
               tick_labels=[NOMBRES[c] for c in presentes])
    ax.set_ylabel("Tiempo de entrega del cambio (minutos)")
    ax.set_title("Tiempo de entrega por condición (cambios normales)")
    ax.grid(axis="y", alpha=.3)
    fig.tight_layout()
    fig.savefig(SALIDA / "lead_time.png", dpi=200)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    tasas = []
    for c in presentes:
        d = det[det["condicion"] == c]
        n = d["en_produccion"].sum() or np.nan
        tasas.append(100 * d["fallo_en_produccion"].sum() / n)
    ax.bar([NOMBRES[c] for c in presentes], tasas, color="#4a6fa5")
    ax.set_ylabel("Tasa de fallos por cambio (%)")
    ax.set_title("Despliegues que fallaron en producción")
    ax.grid(axis="y", alpha=.3)
    fig.tight_layout()
    fig.savefig(SALIDA / "tasa_fallos.png", dpi=200)


def main():
    from comun import ARCHIVO_DATOS
    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else ARCHIVO_DATOS
    SALIDA.mkdir(exist_ok=True)
    df = cargar(ruta)
    det = clasificar(df)
    res = resumen(df, det)
    det.to_csv(SALIDA / "detalle_cambios.csv", index=False)
    res.to_csv(SALIDA / "resumen_por_condicion.csv", index=False)
    texto = pruebas(det)
    (SALIDA / "pruebas_estadisticas.txt").write_text(texto, encoding="utf-8")
    graficas(det)
    pd.set_option("display.width", 200)
    print(res.T.to_string())
    print(texto)
    print(f"\nArchivos guardados en {SALIDA}")


if __name__ == "__main__":
    main()
