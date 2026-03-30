import streamlit as st
import pandas as pd
import os
import requests
import time
import csv
from datetime import datetime

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILOS
# ==============================================================================
st.set_page_config(
    page_title="Verificador de Espécies | Seleção Natural", 
    page_icon="🔍",
    layout="centered"
)

estilo_customizado = """
<style>
    /* Estilo dos botões */
    .stButton>button { 
        background-color: #1a73e8; color: white !important; border-radius: 4px; 
        border: none; padding: 8px 16px; font-weight: 500; transition: all 0.2s ease;
    }
    .stButton>button:hover { 
        background-color: #1557b0; box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15); 
    }
    
    /* Estilo para o rodapé fixo */
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%; background-color: #f8f9fa; color: #5f6368;
        text-align: center; padding: 10px; font-size: 12px; border-top: 1px solid #e0e0e0;
        z-index: 100;
    }
    .main-content { margin-bottom: 70px; }
</style>
"""
st.markdown(estilo_customizado, unsafe_allow_html=True)

# Container principal para aplicar o estilo de margem inferior
main_container = st.container()

# ==============================================================================
# 2. BARRA LATERAL (SIDEBAR)
# ==============================================================================
import os

with st.sidebar:
   # --- LOGOTIPO ---
    try:
        # Trocamos 'use_container_width' por 'use_column_width'
        st.image("SN.png", use_column_width=True)
    except Exception:
        st.markdown("### Seleção Natural")

    st.write("---")
    
    # --- NOVIDADE: CHAMADA PARA A PLATAFORMA ---
    st.markdown("### Nossa Plataforma")
    st.write("Conheça nossa solução completa para gestão de biodiversidade.")
    st.link_button("🌐 Plataforma Seleção Natural", "https://plataforma.selecaonatural.net/auth/sign-in/", use_container_width=True)
    
    st.write("---")

    # --- SOBRE O DESENVOLVEDOR ---
    st.markdown("### Sobre nós")
    st.info("Este aplicativo foi desenvolvido pela **Seleção Natural**.")
        
    # --- ÁREA RESTRITA ---
    with st.expander("🔐 Área Restrita"):
        senha_admin = st.text_input("Senha Admin", type="password", key="admin_pass")
        if senha_admin == "selecao2026":
            if os.path.exists("leads_capturados.csv"):
                with open("leads_capturados.csv", "rb") as f:
                    st.download_button(
                        label="📥 Baixar Backup de Leads",
                        data=f,
                        file_name="leads_backup.csv",
                        mime="text/csv"
                    )
            else:
                st.warning("Sem backup local.")

    st.write("---")
    st.caption("Versão 1.0 | © 2026 Seleção Natural")

# ==============================================================================
# 3. MEMÓRIA DO APLICATIVO (SESSION STATE)
# ==============================================================================
if 'tabela_dados' not in st.session_state:
    st.session_state['tabela_dados'] = None
if 'email_cadastrado_download' not in st.session_state:
    st.session_state['email_cadastrado_download'] = False

# ==============================================================================
# 4. CORPO DO APLICATIVO
# ==============================================================================
with main_container:
    st.title("Verificador de Espécies - Fauna e Flora")
    st.markdown("Verificação do Grau de Ameaça de Extinção (MMA) com resolução taxonômica (GBIF).")

    aba1, aba2 = st.tabs(["📋 Copiar e Colar", "📁 Upload de Planilha"])

    with aba1:
        texto_nomes = st.text_area("Cole os nomes científicos aqui (um por linha):", height=150)
        if st.button("Carregar Nomes"):
            if texto_nomes.strip():
                lista_nomes = [nome.strip() for nome in texto_nomes.split('\n') if nome.strip()]
                st.session_state['tabela_dados'] = pd.DataFrame({"Espécie": lista_nomes})
                st.session_state['email_cadastrado_download'] = False 
                st.rerun()
            else:
                st.warning("Cole algum nome antes de carregar.")

    with aba2:
        arquivo_upload = st.file_uploader("Ou faça upload do CSV", type=["csv"])
        if arquivo_upload is not None:
            st.session_state['tabela_dados'] = pd.read_csv(arquivo_upload)
            st.session_state['email_cadastrado_download'] = False

    # LÓGICA DE PROCESSAMENTO
    if st.session_state['tabela_dados'] is not None:
        st.write("---")
        df = st.session_state['tabela_dados'].copy()
        nome_coluna_especie = df.columns[0]
        
        st.write("### Lista para Verificação:")
        st.dataframe(df, use_container_width=True)
        
        if st.button("Consultar Status e Sinônimos"):
            caminho_fauna = "fauna-ameacada-2021.csv"
            caminho_flora = "flora-ameacada-2021.csv"
            
            if not os.path.exists(caminho_fauna) or not os.path.exists(caminho_flora):
                st.error("Erro: Arquivos de referência (fauna/flora-ameacada-2021.csv) não encontrados.")
            else:
                # Carregamento com tratamento de encoding
                def carregar_csv(caminho):
                    try:
                        return pd.read_csv(caminho, sep=';', encoding='utf-8')
                    except:
                        return pd.read_csv(caminho, sep=';', encoding='latin1')

                df_fauna = carregar_csv(caminho_fauna)
                df_flora = carregar_csv(caminho_flora)
                
                # Dicionários de busca
                dict_fauna = dict(zip(df_fauna['Espécie ou Subespécie'].astype(str).str.strip().str.lower(), df_fauna['Sugestão de Categoria 2021']))
                
                df_flora['Espécie Limpa'] = df_flora['Espécie (FB 2020)'].astype(str).str.strip().apply(lambda x: ' '.join(x.split()[:2]))
                dict_flora = dict(zip(df_flora['Espécie Limpa'].str.lower(), df_flora['Sugestão de Categoria 2021']))
                
                mma_dict = {**dict_fauna, **dict_flora}
                
                status_final = []
                notas_taxon = []
                progresso = st.progress(0)
                status_texto = st.empty()
                
                for i, nome_original in enumerate(df[nome_coluna_especie]):
                    nome_limpo = str(nome_original).strip()
                    nome_lower = nome_limpo.lower()
                    status_texto.text(f"Analisando ({i+1}/{len(df)}): {nome_limpo}")
                    
                    if nome_lower in mma_dict:
                        status_final.append(mma_dict[nome_lower])
                        notas_taxon.append("Correspondência exata")
                    else:
                        # Busca no GBIF
                        try:
                            resp = requests.get("https://api.gbif.org/v1/species/match", params={"name": nome_limpo}, timeout=5)
                            dados = resp.json()
                            nome_aceite = dados.get("species", "")
                            
                            if nome_aceite and nome_aceite.lower() in mma_dict:
                                status_final.append(mma_dict[nome_aceite.lower()])
                                notas_taxon.append(f"Sinônimo. Nome aceito: {nome_aceite}")
                            else:
                                status_final.append("Não Ameaçada / Não Encontrada")
                                notas_taxon.append("-")
                        except:
                            status_final.append("Erro na consulta")
                            notas_taxon.append("Falha de conexão")
                    
                    progresso.progress((i + 1) / len(df))
                
                df["Status MMA (Portaria 148)"] = status_final
                df["Notas Taxonômicas (GBIF)"] = notas_taxon
                st.session_state['tabela_dados'] = df
                st.success("Análise concluída!")
                st.rerun()

        # ÁREA DE RESULTADOS E DOWNLOAD
        if "Status MMA (Portaria 148)" in df.columns:
            st.write("---")
            st.write("### 📊 Resumo da Análise")
            
            c1, c2 = st.columns([1, 2])
            contagem = df["Status MMA (Portaria 148)"].value_counts()
            c1.dataframe(contagem)
            c2.bar_chart(contagem)
            
            st.write("### 📥 Exportar Resultados")
            
            if not st.session_state['email_cadastrado_download']:
                st.info("💡 Cadastre-se para baixar a planilha completa:")
                with st.form("form_leads"):
                    nome_l = st.text_input("Nome completo")
                    email_l = st.text_input("E-mail corporativo")
                    empresa_l = st.text_input("Empresa")
                    btn_enviar = st.form_submit_button("Liberar Download")
                    
                    if btn_enviar:
                        if nome_l and email_l:
                            # Salva o lead em CSV local
                            novo_lead = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nome_l, email_l, empresa_l]
                            file_exists = os.path.isfile("leads_capturados.csv")
                            with open("leads_capturados.csv", "a", newline='', encoding='utf-8') as f:
                                writer = csv.writer(f)
                                if not file_exists:
                                    writer.writerow(["Data", "Nome", "Email", "Empresa"])
                                writer.writerow(novo_lead)
                            
                            st.session_state['email_cadastrado_download'] = True
                            st.success("Agradecemos o contato! O download foi liberado.")
                            st.rerun()
                        else:
                            st.warning("Por favor, preencha nome e e-mail.")
            else:
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="✅ Baixar Planilha de Resultados",
                    data=csv_data,
                    file_name=f"resultado_especies_{datetime.now().strftime('%d%m%Y')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
   


   
       
             
              
