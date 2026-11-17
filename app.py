import time
from datetime import datetime

import pandas as pd
import pydeck as pdk
import streamlit as st

st.set_page_config(page_title="SIA - Semáforos Inteligentes", page_icon="🚦", layout="wide")

# ----------------------------- Dados simulados -----------------------------
VEICULOS = {
    "Ambulância 01 (SAMU)": {"tipo": "SAMU", "origem": (-23.5505, -46.6333)},
    "Ambulância 02 (SAMU)": {"tipo": "SAMU", "origem": (-23.5560, -46.6400)},
    "Viatura Bombeiros 01": {"tipo": "Bombeiros", "origem": (-23.5450, -46.6250)},
}
DESTINOS = ["Hospital Central", "UPA Norte", "Hospital Regional"]
ROTA = [  # cruzamentos na rota da emergência
    {"nome": "Cruzamento A", "lat": -23.5520, "lon": -46.6350},
    {"nome": "Cruzamento B", "lat": -23.5540, "lon": -46.6380},
    {"nome": "Cruzamento C", "lat": -23.5565, "lon": -46.6410},
]
HOSPITAL = (-23.5590, -46.6440)  # destino ilustrativo
COR_STATUS = {
    "Aguardando": [140, 140, 140],
    "Transição segura": [255, 200, 0],
    "Verde garantido": [0, 200, 80],
}
AMARELO_MIN_S = 3  # tempos mínimos de segurança (regra de negócio / EU 5)
VERMELHO_GERAL_S = 2

DADOS_ARMAZENADOS = pd.DataFrame(
    [
        ["Contagem de veículos", "Otimização dos tempos", 365, "Anonimizado"],
        ["Velocidade média", "Indicadores de desempenho", 365, "Anonimizado"],
        ["Telemetria de emergência", "Onda verde (SAMU)", 90, "Anonimizado"],
        ["Imagens de câmeras", "Detecção de filas", 7, "Faces/placas desfocadas"],
        ["Log de acesso de usuários", "Auditoria", 180, "Pseudonimizado"],
    ],
    columns=["Tipo", "Finalidade", "Retenção (dias)", "Status"],
)

# ----------------------------- Estado da sessão -----------------------------
ss = st.session_state
ss.setdefault("status_rota", ["Aguardando"] * len(ROTA))
ss.setdefault("onda_ativa", False)
ss.setdefault("auditoria", [])
ss.setdefault("anonimizacao_auto", True)


def log(evento: str):
    ss.auditoria.append({"Data/hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "Evento": evento})


# ----------------------------- Navegação -----------------------------
st.sidebar.title("🚦 SIA")
st.sidebar.caption("Otimização Inteligente de Semáforos")
pagina = st.sidebar.radio("Perfil", ["Onda verde (SAMU)", "Painel LGPD (Conformidade)"])

# ============================ SOCORRISTA DO SAMU ============================
if pagina == "Onda verde (SAMU)":
    st.title("Onda verde para emergências (SAMU)")

    col_mapa, col_info = st.columns([2, 1])

    with col_info:
        st.subheader("Veículo de emergência")
        veiculo = st.selectbox("Veículo", list(VEICULOS))
        destino = st.selectbox("Destino", DESTINOS)
        st.write(f"**{veiculo}** · {'Em rota' if ss.onda_ativa else 'Aguardando ativação'}")

        st.subheader("Cruzamentos na rota")
        lugares = {c["nome"]: st.empty() for c in ROTA}

        def desenha_status():
            for c, status in zip(ROTA, ss.status_rota):
                icone = {"Aguardando": "⏳", "Transição segura": "🟡", "Verde garantido": "🟢"}[status]
                lugares[c["nome"]].info(f"{icone} {c['nome']} · {status}")

        desenha_status()
        chegada = 2 + len(ROTA) * 2 if ss.onda_ativa else 6 + len(ROTA) * 3
        st.caption(f"Chegada estimada: {chegada} min")

    with col_mapa:
        mapa_ph = st.empty()

        def desenha_mapa():
            origem = VEICULOS[veiculo]["origem"]
            caminho = [[origem[1], origem[0]]] + [[c["lon"], c["lat"]] for c in ROTA] + [[HOSPITAL[1], HOSPITAL[0]]]
            cor_rota = [0, 200, 80] if ss.onda_ativa else [140, 140, 140]
            cruz = pd.DataFrame(
                [
                    {"nome": c["nome"], "lon": c["lon"], "lat": c["lat"], "cor": COR_STATUS[st_]}
                    for c, st_ in zip(ROTA, ss.status_rota)
                ]
            )
            extras = pd.DataFrame(
                [
                    {"nome": "Ambulância", "lon": origem[1], "lat": origem[0], "cor": [220, 30, 30]},
                    {"nome": "Destino", "lon": HOSPITAL[1], "lat": HOSPITAL[0], "cor": [30, 90, 220]},
                ]
            )
            camadas = [
                pdk.Layer("PathLayer", pd.DataFrame([{"path": caminho}]), get_path="path",
                          get_color=cor_rota, width_min_pixels=8),
                pdk.Layer("ScatterplotLayer", extras, get_position="[lon, lat]", get_fill_color="cor",
                          get_radius=80, radius_min_pixels=12, stroked=True,
                          get_line_color=[255, 255, 255], line_width_min_pixels=2),
                pdk.Layer("ScatterplotLayer", cruz, get_position="[lon, lat]", get_fill_color="cor",
                          get_radius=110, radius_min_pixels=18, stroked=True,
                          get_line_color=[0, 0, 0], line_width_min_pixels=3),
                pdk.Layer("TextLayer", pd.concat([cruz, extras]), get_position="[lon, lat]", get_text="nome",
                          get_size=14, get_color=[0, 0, 0], get_pixel_offset=[0, -28]),
            ]
            vista = pdk.ViewState(latitude=-23.5545, longitude=-46.639, zoom=13.3)
            mapa_ph.pydeck_chart(pdk.Deck(layers=camadas, initial_view_state=vista, map_style="light"))

        desenha_mapa()
        st.caption("🔴 Ambulância · 🔵 Destino · ⚪ Aguardando · 🟡 Transição segura · 🟢 Verde garantido (rota verde = onda ativa)")

        b1, b2, _ = st.columns([1, 1, 2])
        ativar = b1.button("Ativar onda verde", type="primary", disabled=ss.onda_ativa)
        cancelar = b2.button("Cancelar", disabled=not ss.onda_ativa)

    if ativar:
        ss.onda_ativa = True
        log(f"Onda verde ativada: {veiculo} → {destino}")
        inicio = time.time()
        for i, c in enumerate(ROTA):
            # Regra de negócio: a IA não viola amarelo e vermelho geral mínimos
            ss.status_rota[i] = "Transição segura"
            desenha_status()
            desenha_mapa()
            time.sleep(0.8)
            ss.status_rota[i] = "Verde garantido"
            desenha_status()
            desenha_mapa()
            log(f"{c['nome']}: verde garantido (amarelo {AMARELO_MIN_S}s + vermelho geral {VERMELHO_GERAL_S}s respeitados)")
        latencia = time.time() - inicio
        st.success(f"Onda verde ativa. Tempo de resposta da simulação: {latencia:.1f} s (meta do sistema: < 5 s em campo).")

    if cancelar:
        ss.onda_ativa = False
        ss.status_rota = ["Aguardando"] * len(ROTA)
        log("Onda verde cancelada pelo operador")
        st.warning("Onda verde cancelada. Os cruzamentos voltaram ao modo automático (IA).")
        desenha_status()
        desenha_mapa()

# ======================= ENCARREGADO DE CONFORMIDADE =======================
else:
    st.title("Painel LGPD")

    anon_pct = 100 if ss.anonimizacao_auto else 60
    c1, c2, c3 = st.columns(3)
    c1.metric("Dados pessoais identificáveis", 0 if ss.anonimizacao_auto else 2)
    c2.metric("Anonimizados", f"{anon_pct}%")
    c3.metric("Retenção máxima (dias)", int(DADOS_ARMAZENADOS["Retenção (dias)"].max()))

    st.subheader("Dados armazenados")
    st.dataframe(DADOS_ARMAZENADOS, use_container_width=True, hide_index=True)

    novo = st.toggle("Anonimização automática", value=ss.anonimizacao_auto)
    if novo != ss.anonimizacao_auto:
        ss.anonimizacao_auto = novo
        log(f"Anonimização automática {'ligada' if novo else 'desligada'}")
        st.rerun()
    if not ss.anonimizacao_auto:
        st.error("Atenção: com a anonimização desligada o sistema pode armazenar dados pessoais em desacordo com a LGPD.")

    b1, b2, _ = st.columns([1, 1, 3])
    gerar = b1.button("Gerar relatório", type="primary")
    relatorio = (
        f"RELATÓRIO DE AUDITORIA LGPD — {datetime.now():%d/%m/%Y %H:%M}\n"
        f"Anonimização automática: {'ATIVA' if ss.anonimizacao_auto else 'DESLIGADA'}\n"
        f"Percentual anonimizado: {anon_pct}%\n\nInventário:\n{DADOS_ARMAZENADOS.to_string(index=False)}\n\n"
        "Eventos:\n" + "\n".join(f"{e['Data/hora']} - {e['Evento']}" for e in ss.auditoria)
    )
    b2.download_button("Exportar", data=relatorio, file_name="relatorio_lgpd.txt", mime="text/plain")

    if gerar:
        log("Relatório de auditoria gerado")
        st.code(relatorio, language="text")

    st.subheader("Trilha de auditoria")
    if ss.auditoria:
        st.dataframe(pd.DataFrame(ss.auditoria), use_container_width=True, hide_index=True)
    else:
        st.caption("Nenhum evento registrado ainda. Ative uma onda verde ou gere um relatório.")