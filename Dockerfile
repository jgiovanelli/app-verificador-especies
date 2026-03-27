FROM python:3.9-slim

WORKDIR /app

# Instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia TUDO (incluindo os CSVs que seu código exige)
COPY . .

# Porta padrão do Cloud Run
ENV PORT=8080
EXPOSE 8080

# Comando corrigido: substitua 'verificador.py' pelo nome exato do seu arquivo .py
CMD ["sh", "-c", "app.py --server.port=8080 --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false"]
