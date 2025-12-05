from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(allowed_roles):
    """
    Decorador que comprueba si un usuario tiene al menos uno de los roles permitidos.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. Simulación de la obtención del rol del usuario
            #    (En un framework real, 'request.user.role' sería el lugar donde se encuentra el rol)
            current_user_role = getattr(request, "user_role", "guest")

            # 2. Lógica de filtrado: Verifica si el rol actual está en la lista de roles permitidos
            if current_user_role in allowed_roles:
                # Si el rol es permitido, ejecuta la función de la vista original
                return view_func(request, *args, **kwargs)
            else:
                # Si no es permitido, retorna un error de acceso
                return {"error": "Acceso denegado", "reason": "Rol no autorizado"}

        return _wrapped_view

    return decorator


def complete_profile(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            usuario = request.user
            # Utilizamos la Cédula (cedula) como el indicador principal de Perfil Incompleto.
            # Si está logueado y NO tiene cédula, lo enviamos a completar perfil.
            # Se usa getattr para seguridad en caso de que el campo no exista o sea None.
            if not getattr(usuario, "cedula", None):
                messages.warning(
                    request, "Debe completar su perfil para acceder al sistema."
                )
                return redirect("url_completar_perfil", user_id=usuario.id)
        return view_func(request, *args, **kwargs)

    return wrapper
