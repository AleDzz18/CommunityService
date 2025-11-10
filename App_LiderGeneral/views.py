# App_LiderGeneral/views.py

from django.contrib.auth.mixins import AccessMixin, LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from App_Home.models import CustomUser
from .forms import FormularioAdminUsuario
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import get_user_model

# Create your views here.

# ******************************************************************
# MIXIN DE AUTORIZACIÓN: Restringe el acceso solo a Líderes Generales
# ******************************************************************
class LiderGeneralRequiredMixin(AccessMixin):
    """Verifica que el usuario actual tenga el rol de Lider General."""
    def dispatch(self, request, *args, **kwargs):
        # Aseguramos que el usuario esté autenticado
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Usamos la constante del modelo para la comparación
        if request.user.rol != CustomUser.ROL_LIDER_GENERAL:
            messages.error(request, "No tienes permiso para acceder a esta sección administrativa.")
            # Redirigir al dashboard si no tiene el rol
            return redirect('homeDashboard') 
            
        return super().dispatch(request, *args, **kwargs)

# ******************************************************************
# 1. LISTADO DE USUARIOS (READ)
# ******************************************************************
class ListaUsuariosView(LoginRequiredMixin, LiderGeneralRequiredMixin, ListView):
    model = CustomUser
    template_name = 'lider_general/lista_usuarios.html' 
    context_object_name = 'usuarios'
    ordering = ['username'] 

# ******************************************************************
# 2. CREACIÓN DE USUARIOS (CREATE)
# Nota: La creación de usuarios por aquí requiere asignar una contraseña.
# Si prefieres que se registren por App_Home, puedes omitir esta vista.
# Aquí se usa un modelo simple sin manejo de contraseña.
# ******************************************************************
class CrearUsuarioView(LoginRequiredMixin, LiderGeneralRequiredMixin, CreateView):
    model = CustomUser
    form_class = FormularioAdminUsuario 
    template_name = 'lider_general/usuario_form.html'
    success_url = reverse_lazy('lider_general:lista_usuarios')
    
    def form_valid(self, form):
        # Recomendación: Si quieres crear el usuario con contraseña, 
        # debes usar un formulario de creación de usuario adecuado (ej: UserCreationForm)
        # o establecer una contraseña temporal hasheada aquí.
        messages.success(self.request, f"Usuario '{form.instance.username}' creado con éxito.")
        return super().form_valid(form)

# ******************************************************************
# 3. EDICIÓN DE USUARIOS (UPDATE)
# ******************************************************************
class EditarUsuarioView(LoginRequiredMixin, LiderGeneralRequiredMixin, UpdateView):
    model = CustomUser
    form_class = FormularioAdminUsuario 
    template_name = 'lider_general/usuario_form.html'
    success_url = reverse_lazy('lider_general:lista_usuarios')
    
    def form_valid(self, form):
        messages.success(self.request, f"Usuario '{form.instance.username}' editado con éxito.")
        return super().form_valid(form)

# ******************************************************************
# 4. ELIMINACIÓN DE USUARIOS (DELETE)
# ******************************************************************
class EliminarUsuarioView(LoginRequiredMixin, LiderGeneralRequiredMixin, DeleteView):
    model = CustomUser
    template_name = 'lider_general/usuario_confirm_delete.html'
    success_url = reverse_lazy('lider_general:lista_usuarios')
    context_object_name = 'usuario'

    def form_valid(self, form):
        messages.success(self.request, f"Usuario '{self.object.username}' eliminado con éxito.")
        return super().form_valid(form)