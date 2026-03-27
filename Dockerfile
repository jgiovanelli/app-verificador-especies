# Usa uma imagem leve do Python
FROM python:3.10-slim

# Define o diretório de trabalho dentro do servidor
WORKDIR /app

# Copia todos os arquivos da sua pasta para dentro do servidor
COPY . /app

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Expõe a porta que o Cloud Run exige
EXPOSE 8080

# Comando para rodar o Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.enableCORS=false"]
