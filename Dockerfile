FROM python:3.9-slim

WORKDIR /app

# Instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código e os CSVs (essencial!)
COPY . .

# Informa ao Streamlit para usar a porta que o Google mandar
# Substitua 'seu_script.py' pelo nome real do seu arquivo (ex: verificador.py)
CMD ["sh", "-c", "app.py --server.port=${PORT:-8080} --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false"]
