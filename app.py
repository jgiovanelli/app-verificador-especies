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
        z-index: 100; display: flex; align-items: center; justify-content: center;
    }
    .main-content { margin-bottom: 70px; }
</style>
"""
st.markdown(estilo_customizado, unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="main-content">', unsafe_allow_html=True)

    # ==============================================================================
    # 2. BARRA LATERAL E MEMÓRIA
    # ==============================================================================
    with st.sidebar:
        
        # --- LOGOTIPO ---
        try:
            # Cole o link exato que você copiou do GitHub entre as aspas abaixo:
            url_logo = "https://raw.githubusercontent.com/SEU_USUARIO/SEU_REPOSITORIO/main/SN.png"
            st.image(url_logo, use_container_width=True)
        except Exception:
            st.markdown("### Seleção Natural")

        # --- NOVIDADE: CHAMADA PARA A PLATAFORMA ---
        st.markdown("### Nossa Plataforma")
        st.write("Conheça nossa solução completa para gestão de biodiversidade.")
        
        # Criando um botão de destaque que abre o link
        st.link_button("🌐 Plataforma Seleção Natural", "https://plataforma.selecaonatural.net/auth/sign-in/", use_container_width=True)
        
        st.write("---")

        # --- SOBRE O DESENVOLVEDOR ---
        st.markdown("### Sobre nós")
        st.info("Este aplicativo foi desenvolvido pela **Seleção Natural**.")
        
        # --- ÁREA RESTRITA (OPÇÃO B) ---
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

    # Memórias do aplicativo
    if 'tabela_dados' not in st.session_state:
        st.session_state['tabela_dados'] = None
    if 'email_cadastrado_download' not in st.session_state:
        st.session_state['email_cadastrado_download'] = False

    # ==============================================================================
    # 3. CORPO DO APLICATIVO
    # ==============================================================================
    st.title("Verificador de Espécies - Fauna e Flora")
    st.markdown("Verificação do Grau de Ameaça de Extinção (MMA) com resolução taxonômica (GBIF).")

    aba1, aba2 = st.tabs(["📋 Copiar e Colar", "📁 Upload de Planilha"])

    with aba1:
        texto_nomes = st.text_area("Cole os nomes científicos aqui (um por linha):", height=150)
        if st.button("Carregar Nomes"):
            if texto_nomes.strip():
                lista_nomes = [nome.strip() for nome in texto_nomes.split('\n') if nome.strip()]
                st.session_state['tabela_dados'] = pd.DataFrame({"Espécie": lista_nomes})
                st.session_state['email_cadastrado_download'] = False # Reseta o download ao carregar nova lista
            else:
                st.warning("Cole algum nome antes de carregar.")

    with aba2:
        arquivo_upload = st.file_uploader("Ou faça upload do CSV", type=["csv"])
        if arquivo_upload is not None:
            st.session_state['tabela_dados'] = pd.read_csv(arquivo_upload)
            st.session_state['email_cadastrado_download'] = False

    if st.session_state['tabela_dados'] is not None:
        st.write("---")
        st.write("### Lista para Verificação:")
        
        df = st.session_state['tabela_dados'].copy()
        nome_coluna_especie = df.columns[0]
        st.dataframe(df, use_container_width=True)
        
        # LÓGICA DE CONSULTA
        if st.button("Consultar Status e Sinônimos"):
            caminho_fauna = "fauna-ameacada-2021.csv"
            caminho_flora = "flora-ameacada-2021.csv"
            
            if not os.path.exists(caminho_fauna) or not os.path.exists(caminho_flora):
                st.error(f"Certifique-se de que os arquivos '{caminho_fauna}' e '{caminho_flora}' estão na mesma pasta do aplicativo.")
            else:
                # 1. Carregar Fauna
                try:
                    df_fauna = pd.read_csv(caminho_fauna, sep=';', encoding='utf-8')
                except UnicodeDecodeError:
                    df_fauna = pd.read_csv(caminho_fauna, sep=';', encoding='latin1')
                
                # 2. Carregar Flora
                try:
                    df_flora = pd.read_csv(caminho_flora, sep=';', encoding='utf-8')
                except UnicodeDecodeError:
                    df_flora = pd.read_csv(caminho_flora, sep=';', encoding='latin1')
                
                # 3. Criar dicionários e juntá-los
                df_fauna['Espécie ou Subespécie'] = df_fauna['Espécie ou Subespécie'].astype(str).str.strip()
                dict_fauna = dict(zip(df_fauna['Espécie ou Subespécie'].str.lower(), df_fauna['Sugestão de Categoria 2021']))

                # Tratamento da Flora: Separa as palavras pelo espaço e pega apenas as duas primeiras (Gênero e Espécie), ignorando o autor
                df_flora['Espécie Limpa'] = df_flora['Espécie (FB 2020)'].astype(str).str.strip().apply(lambda x: ' '.join(x.split()[:2]))
                dict_flora = dict(zip(df_flora['Espécie Limpa'].str.lower(), df_flora['Sugestão de Categoria 2021']))
                
                # Dicionário unificado (Fauna + Flora)
                mma_dict = {**dict_fauna, **dict_flora}
                
                status_final = []
                notas_taxon = []
                texto_progresso = st.empty()
                barra_progresso = st.progress(0)
                total_especies = len(df)
                
                for i, nome_original in enumerate(df[nome_coluna_especie]):
                    nome_limpo = str(nome_original).strip()
                    nome_lower = nome_limpo.lower()
                    texto_progresso.text(f"Analisando: {nome_limpo}...")
                    
                    if nome_lower in mma_dict:
                        status_final.append(mma_dict[nome_lower])
                        notas_taxon.append("Correspondência exata")
                    else:
                        url_gbif = "https://api.gbif.org/v1/species/match"
                        encontrou_sinonimo = False
                        try:
                            resp = requests.get(url_gbif, params={"name": nome_limpo, "strict": False}, timeout=5)
                            if resp.status_code == 200:
                                dados_gbif = resp.json()
                                if dados_gbif.get("matchType") != "NONE":
                                    nome_aceite_gbif = dados_gbif.get("species", "")
                                    if nome_aceite_gbif and nome_aceite_gbif.lower() != nome_lower:
                                        if nome_aceite_gbif.lower() in mma_dict:
                                            status_final.append(mma_dict[nome_aceite_gbif.lower()])
                                            notas_taxon.append(f"Sinônimo. Nome aceito (GBIF): {nome_aceite_gbif}")
                                            encontrou_sinonimo = True
                        except Exception:
                            pass 
                        
                        if not encontrou_sinonimo:
                            status_final.append("Não Ameaçada / Não Encontrada")
                            notas_taxon.append("-")
                            
                        time.sleep(0.1)
                    
                    barra_progresso.progress((i + 1) / total_especies)
                
                texto_progresso.empty()
                barra_progresso.empty()
                df["Status MMA (Portaria 148)"] = status_final
                df["Notas Taxonômicas (GBIF)"] = notas_taxon
                st.session_state['tabela_dados'] = df
                st.success("Análise finalizada!")
                st.rerun()

        # DASHBOARD E ÁREA DE DOWNLOAD COM CAPTURA DE LEADS
        if "Status MMA (Portaria 148)" in df.columns:
            st.write("---")
            st.write("### 📊 Resumo da Análise")
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.write("**Contagem de Status:**")
                contagem = df["Status MMA (Portaria 148)"].value_counts()
                st.dataframe(contagem)
            with col2:
                st.write("**Gráfico de Ameaças:**")
                st.bar_chart(contagem)
            
            st.write("### 📥 Exportar Resultados")
            
            # Se o usuário ainda não colocou o e-mail, mostra o formulário
            if not st.session_state['email_cadastrado_download']:
                st.info("💡 **Para baixar a tabela completa (CSV), cadastre-se abaixo:**")
                with st.form("form_captura_leads"):
                    nome_lead = st.text_input("Seu Nome")
   
           
              
