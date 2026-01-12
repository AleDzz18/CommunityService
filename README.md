# 🏢 Sistema Administrativo - Balcones de Paraguaná 1

![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)
![Vue.js](https://img.shields.io/badge/Petite--Vue-4FC08D?style=for-the-badge&logo=vue.js&logoColor=white)

Solución tecnológica integral diseñada para optimizar la gestión de finanzas, censos y beneficios sociales de la comunidad **Balcones de Paraguaná 1**. Este sistema permite a los líderes de torre y al liderazgo general llevar un control transparente y organizado de los recursos comunitarios.

Desarrollado con compromiso académico por los **estudiantes de Ingeniería en Sistemas (D2) de la UNEFA**.

---

## ✨ Características Principales

- **💰 Gestión Financiera:** Control de ingresos y egresos (condominio, basura y mantenimiento).
- **📦 Gestión de Beneficios:** Seguimiento de entregas de bolsas CLAP, Gas y otros beneficios.
- **📊 Censo Comunitario:** Registro detallado de familias, jefes de calle y habitantes por torre.
- **🔐 Roles de Acceso:** Niveles de permisos diferenciados para Líder General y Líderes de Torre.
- **📑 Reportes y Consultas:** Visualización de estados de cuenta y listados de beneficiarios en tiempo real.

---

## 🛠️ Tecnologías Utilizadas

- **Backend:** [Django 5.x](https://www.djangoproject.com/)
- **Frontend:** [Tailwind CSS](https://tailwindcss.com/) para estilos y [Petite-Vue](https://github.com/vuejs/petite-vue) para interactividad ligera.
- **Base de Datos:** PostgreSQL (Alojada en Supabase).
- **Despliegue:** Configurado para [Vercel](https://vercel.com/).

---

## 🚀 Instalación y Ejecución Local

Sigue estos pasos para poner en marcha el proyecto en tu máquina:

### 1. Preparación del Entorno

```bash
# Clonar y entrar al proyecto
git clone [https://github.com/AleDzz18/CommunityService.git](https://github.com/AleDzz18/CommunityService.git)
cd nombre-del-repo

# Crear y activar entorno virtual
python -m venv venv
# En Windows:
venv\Scripts\activate
# En Linux/macOS:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

```

### 2. Configuración de Tailwind y Base de Datos

Asegúrate de tener configurado tu archivo `.env` con las credenciales de la base de datos antes de continuar.

```bash
# Instalar dependencias de Tailwind
python manage.py tailwind download_cli

# Ejecutar migraciones
python manage.py makemigrations
python manage.py migrate

```

### 3. Ejecución en Desarrollo (Modo Watch)

Para que los cambios en los estilos y el código se reflejen instantáneamente, debes ejecutar el servidor de desarrollo de Tailwind:

```bash
# Compila Tailwind y lanza el servidor de Django simultáneamente
python manage.py tailwind runserver

```

*Si prefieres ejecutar el servidor estándar de Django por separado, usa `python manage.py runserver`.*

---

## 🌐 Despliegue en Producción (Vercel)

El proyecto incluye una configuración automatizada para **Vercel** mediante el script `build_files.sh`.

### Proceso de Construcción

1. Vercel detecta `vercel.json` y ejecuta `build_files.sh`.
2. Se instalan las dependencias de Python.
3. Se compila Tailwind CSS para producción (`tailwind build`).
4. Se ejecutan los `collectstatic` para servir los archivos estáticos.

### Configuración en el Panel de Vercel

- **Build Command:** `sh build_files.sh`
- **Output Directory:** `staticfiles`
- **Environment Variables:** Debes cargar todas las variables de tu `.env` (DATABASE_URL, SECRET_KEY, etc.).

---

## 📁 Estructura del Proyecto

- `App_Home/`: Gestión de perfiles, login y vistas principales.
- `App_LiderGeneral/`: Módulo de administración global y finanzas.
- `App_LiderTorre/`: Gestión de censos y beneficios por torre.
- `templates/`: Estructura de componentes (Navbar, Sidebar) y layouts base.

---

## 👥 Equipo de Desarrollo

Proyecto realizado por los estudiantes de la **UNEFA (Sección D2 - Ingeniería en Sistemas)** como aporte tecnológico a la comunidad Balcones de Paraguaná 1.

---
