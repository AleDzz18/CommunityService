from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as autenticar_login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required 
from django.contrib import messages
from django.contrib.messages import get_messages # 💡 RESTAURADO: Importación necesaria

from .forms import FormularioCreacionUsuario, FormularioPerfilUsuario 
from .models import CustomUser 

# ==============================================
# VISTAS DE NAVEGACIÓN
# ==============================================

def vista_dashboard(request):
    """
    Muestra la página principal o dashboard. Permite acceso a espectadores.
    """
    contexto = {
        'usuario_autenticado': request.user.is_authenticated,
        'rol_usuario': getattr(request.user, 'rol', None) if request.user.is_authenticated else None,
        'torre_asignada': getattr(request.user, 'torre', None) if request.user.is_authenticated else None,
    }
    return render(request, 'homeDashboard.html', contexto)


# Vista para CERRAR SESIÓN (LOGOUT)
@login_required 
def vista_logout(request):
    """
    Cierra la sesión del usuario y redirige al dashboard en modo espectador.
    """
    logout(request)
    return redirect('url_dashboard') 

# ==============================================
# VISTAS DE AUTENTICACIÓN (LOGIN & REGISTRO)
# ==============================================

# Vista para INICIAR SESIÓN (LOGIN)
def vista_login(request):
    """Maneja la autenticación del usuario."""
    
    # Si el usuario ya está autenticado, simplemente redirigimos.
    if request.user.is_authenticated:
        return redirect('url_dashboard')

    if request.method == 'POST':
        formulario_login = AuthenticationForm(request, data=request.POST)
        if formulario_login.is_valid():
            nombre_usuario = formulario_login.cleaned_data.get('username')
            contrasena = formulario_login.cleaned_data.get('password')
            
            usuario = authenticate(username=nombre_usuario, password=contrasena)
            
            if usuario is not None and usuario.is_active:
                autenticar_login(request, usuario)
                return redirect('url_dashboard') 
            elif usuario is not None and not usuario.is_active:
                messages.warning(request, 'Debes completar tu perfil para poder iniciar sesión.')
                return redirect('url_completar_perfil', user_id=usuario.pk)
            else:
                messages.error(request, 'Nombre de usuario o contraseña incorrectos.')
        else:
            messages.error(request, 'Error al procesar el formulario de inicio de sesión. Verifique sus credenciales.')
    else:
        # 💡 AJUSTE CLAVE: En la petición GET, consumimos y eliminamos TODOS los mensajes pendientes.
        storage = get_messages(request)
        for message in storage:
            pass # Al iterar sobre el storage, se consumen y se eliminan
        
        formulario_login = AuthenticationForm()

    formulario_registro = FormularioCreacionUsuario()
    return render(request, 'login.html', {
        'formulario_login': formulario_login, 
        'formulario_registro': formulario_registro
    })

# Vista para REGISTRO (Paso 1: Autenticación)
def vista_registro(request):
    """
    Crea el usuario básico y redirige a la página para completar el perfil.
    """
    if request.method == 'POST':
        formulario = FormularioCreacionUsuario(request.POST)
        if formulario.is_valid():
            user = formulario.save(commit=False)
            user.is_active = False 
            user.save()
            return redirect('url_completar_perfil', user_id=user.pk) 
        else:
            for campo, errores in formulario.errors.items():
                for error in errores:
                    messages.error(request, f"Error en {campo}: {error}")
            return redirect('url_login')

    return redirect('url_login') 

# NUEVA VISTA: Paso 2 (Completar Perfil y Asignación de Rol)
def vista_completar_perfil(request, user_id):
    """
    Permite al usuario recién creado completar sus datos (nombre, cédula, rol).
    """
    # Buscamos el usuario o devolvemos 404 si el ID es incorrecto
    usuario = get_object_or_404(CustomUser, pk=user_id)
    
    # Restricción: No permitir el acceso si el perfil ya está activo/completo
    if usuario.is_active:
         messages.warning(request, "Tu perfil ya está completo. Por favor, inicia sesión.")
         return redirect('url_login')
         
    if request.method == 'POST':
        formulario = FormularioPerfilUsuario(request.POST, instance=usuario)
        if formulario.is_valid():
            formulario.save()
            usuario.is_active = True
            usuario.save()
            autenticar_login(request, usuario)
            return redirect('url_dashboard')
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    
    else:
        formulario = FormularioPerfilUsuario(instance=usuario)
        
    return render(request, 'completar_perfil.html', {
        'formulario': formulario, 
        'usuario': usuario
    })