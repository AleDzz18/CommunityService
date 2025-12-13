# build_files.sh
echo "Iniciando Build..."

# 1. Instalar dependencias
python3.9 -m pip install -r requirements.txt

# 2. Construir Tailwind (Descarga el binario y compila)
echo "Construyendo Tailwind..."
python3.9 manage.py tailwind install --no-input
python3.9 manage.py tailwind build --no-input

# 3. Recolectar estáticos
echo "Recolectando estáticos..."
python3.9 manage.py collectstatic --noinput --clear

echo "Build Finalizado."