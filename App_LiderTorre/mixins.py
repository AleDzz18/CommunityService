# App_LiderTorre/mixins.py

from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from App_Home.models import CustomUser
from django.contrib import messages

class LiderTorreRequiredMixin(AccessMixin):
    """
    Mixin para asegurar que el usuario tenga el rol de Líder de Torre (LDT) o
    Líder General (LDG).
    """
    def dispatch(self, request, *args, **kwargs):
        # Verifica si el usuario está autenticado
        if not request.user.is_authenticated:
            # Redirige a la URL de inicio de sesión
            return self.handle_no_permission() 
        
        # Define los roles permitidos
        roles_permitidos = [CustomUser.ROL_LIDER_TORRE, CustomUser.ROL_LIDER_GENERAL]
        
        # Verifica si el rol del usuario está en los roles permitidos
        if request.user.rol not in roles_permitidos:
            messages.error(request, "No tienes permiso para registrar movimientos.")
            # Redirigir al dashboard principal si no tiene el rol
            return redirect(reverse_lazy('url_dashboard')) 

        return super().dispatch(request, *args, **kwargs)