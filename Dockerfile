FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8080
# Substitua 'nome_do_seu_script.py' pelo nome real do arquivo (ex: app.py)
CMD ["sh", "-c", "streamlit run nome_do_seu_script.py --server.port=${PORT:-8080} --server.address=0.0.0.0"]
