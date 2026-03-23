import streamlit as st
import pandas as pd
import os
import requests
import time
import base64

# ==============================================================================
# 1. FUNÇÃO LIMPA PARA LER A IMAGEM NOS BASTIDORES (Para o rodapé HTML)
# ==============================================================================
def obter_base64_da_imagem(caminho_imagem):
    """Lê a imagem local na hora e converte para uso em tags HTML."""
    try:
        with open(caminho_imagem, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

# Nome do seu arquivo de imagem
caminho_logo = "image_0.png"
logo_base64 = obter_base64_da_imagem(caminho_logo)

# ==============================================================================
# 2. CONFIGURAÇÃO DA PÁGINA E ESTILOS
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
    /* Centralizar o logo na sidebar */
    [data-testid="stSidebar"] div.stImage { display: flex; justify-content: center; padding-top: 20px; }
    
    /* Estilo para o rodapé fixo */
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%; background-color: #f8f9fa; color: #5f6368;
        text-align: center; padding: 10px; font-size: 12px; border-top: 1px solid #e0e0e0;
        z-index: 100; display: flex; align-items: center; justify-content: center;
    }
    /* Ajuste para o conteúdo não ficar escondido atrás do rodapé */
    .main-content { margin-bottom: 70px; }
</style>
"""
st.markdown(estilo_customizado, unsafe_allow_html=True)

# Container para o conteúdo principal
with st.container():
    st.markdown('<div class="main-content">', unsafe_allow_html=True)

    # ==============================================================================
    # 3. BARRA LATERAL
    # ==============================================================================
    with st.sidebar:
        # Usa o arquivo local DIRETAMENTE pelo Streamlit
        if os.path.exists(caminho_logo):
            st.image(caminho_logo, width=180)
        else:
            st.markdown("### Seleção Natural")
            st.warning(f"Arquivo '{caminho_logo}' não encontrado.")

        st.markdown("### Sobre o Desenvolvedor")
        st.info("Este aplicativo foi desenvolvido pela **Seleção Natural**, especialista em soluções ambientais e tecnológicas.")
        st.markdown("[Acesse nosso site oficial](https://www.selecaonatural.com.br/)")
        st.write("---")
        st.caption("Versão 1.0.1 | © 2024 Seleção Natural")

    # ==============================================================================
    # 4. CORPO DO APLICATIVO
    # ==============================================================================
    st.title("🔍 Verificador de Espécies")
    st.markdown("Verificação do Grau de Ameaça de Extinção (MMA) com resolução taxonômica (GBIF).")

    if 'tabela_dados' not in st.session_state:
        st.session_state['tabela_dados'] = None

    aba1, aba2 = st.tabs(["📋 Copiar e Colar", "📁 Upload de Planilha"])

    with aba1:
        texto_nomes = st.text_area("Cole os nomes científicos aqui (um por linha):", height=150)
        if st.button("Carregar Nomes"):
            if texto_nomes.strip():
                lista_nomes = [nome.strip() for nome in texto_nomes.split('\n') if nome.strip()]
                st.session_state['tabela_dados'] = pd.DataFrame({"Espécie": lista_nomes})
            else:
                st.warning("Cole algum nome antes de carregar.")

    with aba2:
        arquivo_upload = st.file_uploader("Ou faça upload do CSV", type=["csv"])
        if arquivo_upload is not None:
            st.session_state['tabela_dados'] = pd.read_csv(arquivo_upload)

    if st.session_state['tabela_dados'] is not None:
        st.write("---")
        st.write("### Lista para Verificação:")
        
        df = st.session_state['tabela_dados'].copy()
        nome_coluna_especie = df.columns[0]
        st.dataframe(df, use_container_width=True)
        
        if st.button("Consultar Status e Sinônimos"):
            caminho_mma = "fauna-ameacada-2021.csv"
            
            if not os.path.exists(caminho_mma):
                st.error(f"Arquivo '{caminho_mma}' não encontrado na pasta.")
            else:
                try:
                    df_mma = pd.read_csv(caminho_mma, sep=';', encoding='utf-8')
                except UnicodeDecodeError:
                    df_mma = pd.read_csv(caminho_mma, sep=';', encoding='latin1')
                
                df_mma['Espécie ou Subespécie'] = df_mma['Espécie ou Subespécie'].astype(str).str.strip()
                mma_dict = dict(zip(df_mma['Espécie ou Subespécie'].str.lower(), df_mma['Sugestão de Categoria 2021']))
                
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

    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# 5. RODAPÉ HTML
# ==============================================================================
if logo_base64:
    st.markdown(
        f"""
        <div class="footer">
            <img src="data:image/png;base64,{logo_base64}" alt="Logo Seleção Natural" width="80" style="vertical-align: middle; margin-right: 15px;">
            <span>Desenvolvido por <a href="https://www.selecaonatural.com.br/" target="_blank" style="color: #1a73e8; font-weight: bold; text-decoration: none;">Seleção Natural</a></span>
        </div>
        """, 
        unsafe_allow_html=True
    )
else:
     st.markdown(
        """
        <div class="footer">
            Desenvolvido por <a href="https://www.selecaonatural.com.br/" target="_blank" style="color: #1a73e8; font-weight: bold; text-decoration: none;">Seleção Natural</a>
        </div>
        """, 
        unsafe_allow_html=True
    )