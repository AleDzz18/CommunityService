# build_files.sh
echo "Iniciando Build..."

# 1. Crear y activar entorno virtual (Esto soluciona el error de pip/django)
python3 -m venv venv
source venv/bin/activate

# 2. Instalar dependencias dentro del entorno virtual
echo "Instalando dependencias..."
pip install -r requirements.txt

# 3. Construir Tailwind
# Nota: django-tailwind buscará npm, que ya está en Vercel
echo "Construyendo Tailwind..."
python manage.py tailwind install --no-input
python manage.py tailwind build --no-input

# 4. Recolectar estáticos
echo "Recolectando estáticos..."
python manage.py collectstatic --noinput --clear

echo "Build Finalizado."