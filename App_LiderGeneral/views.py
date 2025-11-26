# App_LiderGeneral/views.py

from django.contrib.auth.mixins import AccessMixin, LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from App_Home.models import (CustomUser, MovimientoFinanciero, Tower, CensoMiembro,
                            CicloBeneficio, EntregaBeneficio, SolicitudDocumento)
from App_Home.forms import CensoMiembroForm
from App_LiderTorre.views import BaseMovimientoCreateView 
from .forms import ( FormularioAdminUsuario, IngresoCondominioGeneralForm, EgresoCondominioGeneralForm, 
                    IngresoBasuraGeneralForm, EgresoBasuraGeneralForm, ProcesarCartaConductaForm)
from datetime import date
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image , Table as PDFTable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import black # Para el color del subrayado
import os


# --- MIXINS DE PERMISOS (Definirlos al principio) ---

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
            return redirect('url_dashboard') 
            
        return super().dispatch(request, *args, **kwargs)

class LiderGeneralOrAdminBasuraRequiredMixin(UserPassesTestMixin):
    """Permite el acceso solo a Líder General o a un Lider con rol de Admin Basura."""
    def test_func(self):
        user = self.request.user
        # Verificamos si está autenticado primero para evitar errores
        if not user.is_authenticated:
            return False
        return user.rol == CustomUser.ROL_LIDER_GENERAL or user.es_admin_basura

# ******************************************************************
# 1. GESTIÓN DE USUARIOS
# ******************************************************************

class ListaUsuariosView(LoginRequiredMixin, LiderGeneralRequiredMixin, ListView):
    model = CustomUser
    template_name = 'lider_general/lista_usuarios.html' 
    context_object_name = 'usuarios'
    ordering = ['username'] 

class CrearUsuarioView(LoginRequiredMixin, LiderGeneralRequiredMixin, CreateView):
    model = CustomUser
    form_class = FormularioAdminUsuario 
    template_name = 'lider_general/usuario_form.html'
    success_url = reverse_lazy('lider_general:lista_usuarios')
    
    def form_valid(self, form):
        messages.success(self.request, f"Usuario '{form.instance.username}' creado con éxito.")
        return super().form_valid(form)

class EditarUsuarioView(LoginRequiredMixin, LiderGeneralRequiredMixin, UpdateView):
    model = CustomUser
    form_class = FormularioAdminUsuario 
    template_name = 'lider_general/usuario_form.html'
    success_url = reverse_lazy('lider_general:lista_usuarios')
    
    def form_valid(self, form):
        messages.success(self.request, f"Usuario '{form.instance.username}' editado con éxito.")
        return super().form_valid(form)

class EliminarUsuarioView(LoginRequiredMixin, LiderGeneralRequiredMixin, DeleteView):
    model = CustomUser
    template_name = 'lider_general/usuario_confirm_delete.html'
    success_url = reverse_lazy('lider_general:lista_usuarios')
    context_object_name = 'usuario'

    def form_valid(self, form):
        messages.success(self.request, f"Usuario '{self.object.username}' eliminado con éxito.")
        return super().form_valid(form)

# ******************************************************************
# 2. GESTIÓN FINANCIERA (CONDOMINIO Y BASURA)
# ******************************************************************

# Condominio (Requiere ser LDG)
class RegistrarIngresoCondominioGeneralView(LiderGeneralRequiredMixin, BaseMovimientoCreateView):
    form_class = IngresoCondominioGeneralForm
    TIPO_MOVIMIENTO = 'Ingreso'
    CATEGORIA_MOVIMIENTO = 'Condominio'
    MONTO_FIELD = 'monto_condominio'

class RegistrarEgresoCondominioGeneralView(LiderGeneralRequiredMixin, BaseMovimientoCreateView):
    form_class = EgresoCondominioGeneralForm
    TIPO_MOVIMIENTO = 'Egreso'
    CATEGORIA_MOVIMIENTO = 'Condominio'
    MONTO_FIELD = 'monto_condominio'

# Cuarto de Basura (Ingreso: Requiere ser LDG)
class RegistrarIngresoBasuraGeneralView(LiderGeneralRequiredMixin, BaseMovimientoCreateView):
    form_class = IngresoBasuraGeneralForm
    TIPO_MOVIMIENTO = 'Ingreso'
    CATEGORIA_MOVIMIENTO = 'Cuarto de Basura'
    MONTO_FIELD = 'monto_basura'

# Cuarto de Basura (Egreso: Requiere ser LDG O Admin Basura)
class RegistrarEgresoBasuraGeneralView(LiderGeneralOrAdminBasuraRequiredMixin, BaseMovimientoCreateView):
    form_class = EgresoBasuraGeneralForm
    TIPO_MOVIMIENTO = 'Egreso'
    CATEGORIA_MOVIMIENTO = 'Cuarto de Basura'
    MONTO_FIELD = 'monto_basura'
    
class EstadoSolvenciaBasuraView(LoginRequiredMixin, LiderGeneralOrAdminBasuraRequiredMixin, TemplateView):
    template_name = 'lider_general/estado_solvencia_basura.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        hoy = date.today()
        try:
            mes = int(self.request.GET.get('mes', hoy.month))
            anio = int(self.request.GET.get('anio', hoy.year))
        except ValueError:
            mes = hoy.month
            anio = hoy.year

        torres = Tower.objects.all().order_by('nombre')
        
        pagos_registrados = MovimientoFinanciero.objects.filter(
            categoria='BAS',
            tipo='ING',
            fecha__year=anio,
            fecha__month=mes,
            tower__isnull=False
        ).values_list('tower_id', flat=True).distinct()

        reporte_solvencia = []
        for torre in torres:
            es_solvente = torre.id in pagos_registrados
            reporte_solvencia.append({
                'torre': torre,
                'status': 'SOLVENTE' if es_solvente else 'PENDIENTE',
                'css_class': 'bg-success text-white' if es_solvente else 'bg-warning text-dark'
            })

        context.update({
            'reporte': reporte_solvencia,
            'mes_actual': mes,
            'anio_actual': anio,
            'meses_choices': range(1, 13),
            'anios_choices': range(hoy.year - 2, hoy.year + 3),
        })
        return context
    
# ******************************************************************
# 3. GESTIÓN DE CENSO GLOBAL
# ******************************************************************

class CensoGeneralListView(LiderGeneralRequiredMixin, ListView):
    model = CensoMiembro
    template_name = 'lider_general/censo_list_general.html'
    context_object_name = 'miembros'
    ordering = ['tower', 'piso', 'apartamento_letra']

    def get_queryset(self):
        qs = super().get_queryset().select_related('tower')
        # Filtro por Torre desde el GET
        torre_id = self.request.GET.get('torre')
        if torre_id and torre_id.isdigit():
            qs = qs.filter(tower_id=int(torre_id))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['torres'] = Tower.objects.all() # Para el dropdown del filtro
        context['torre_seleccionada'] = self.request.GET.get('torre')
        return context

class CensoGeneralCreateView(LiderGeneralRequiredMixin, CreateView):
    model = CensoMiembro
    form_class = CensoMiembroForm
    template_name = 'lider_general/censo_form_general.html'
    success_url = reverse_lazy('lider_general:censo_lista') 

class CensoGeneralUpdateView(LiderGeneralRequiredMixin, UpdateView):
    model = CensoMiembro
    form_class = CensoMiembroForm
    template_name = 'lider_general/censo_form_general.html'
    success_url = reverse_lazy('lider_general:censo_lista')

class CensoGeneralDeleteView(LiderGeneralRequiredMixin, DeleteView):
    model = CensoMiembro
    template_name = 'lider_general/censo_confirm_delete.html'
    success_url = reverse_lazy('lider_general:censo_lista')

# --- GESTIÓN DE CICLOS (CREAR / ELIMINAR) ---

class CrearCicloView(LoginRequiredMixin, View):
    """Crea una nueva lista mensual y cierra la anterior si existe."""
    
    def post(self, request, *args, **kwargs):
        tipo = request.POST.get('tipo') # CLAP o GAS
        nombre = request.POST.get('nombre') # Ej: "Octubre 2024"
        
        # Validación de permisos (LDG o Admin Específico)
        permiso = False
        if request.user.rol == 'LDG': permiso = True
        elif tipo == 'CLAP' and request.user.es_admin_clap: permiso = True
        elif tipo == 'GAS' and request.user.es_admin_bombonas: permiso = True
        
        if not permiso:
            messages.error(request, "No tienes permiso para crear listas.")
            return redirect('url_dashboard')

        # 1. Desactivar ciclos anteriores del mismo tipo
        CicloBeneficio.objects.filter(tipo=tipo, activo=True).update(activo=False)
        
        # 2. Crear nuevo ciclo
        CicloBeneficio.objects.create(tipo=tipo, nombre=nombre, activo=True)
        
        slug = 'clap' if tipo == 'CLAP' else 'gas'
        messages.success(request, f"Nueva lista de {tipo} creada exitosamente.")
        return redirect('ver_beneficio', tipo_slug=slug)

class EliminarCicloView(LoginRequiredMixin, View):
    """Elimina (Cierra) la lista actual."""
    def post(self, request, pk):
        ciclo = get_object_or_404(CicloBeneficio, pk=pk)
        
        ciclo.delete()
        
        messages.warning(request, "Lista eliminada.")
        return redirect('url_dashboard')

# --- AGREGAR PERSONAS GLOBALMENTE ---
class AgregarBeneficiarioGeneralView(LoginRequiredMixin, LiderGeneralRequiredMixin, ListView):
    model = CensoMiembro
    template_name = 'lider_general/agregar_beneficiario_global.html' # Asegúrate de crear/usar este template
    context_object_name = 'miembros_disponibles'

    def get_queryset(self):
        tipo_slug = self.kwargs['tipo_slug']
        tipo_db = tipo_slug.upper() # CLAP o GAS

        try:
            # 1. Obtener el ciclo activo
            ciclo = CicloBeneficio.objects.get(tipo=tipo_db, activo=True)
        except CicloBeneficio.DoesNotExist:
            # Si no hay ciclo activo, no hay miembros que listar para agregar.
            messages.error(self.request, f"No existe un ciclo activo para {tipo_db}.")
            return CensoMiembro.objects.none()

        # 2. Obtener IDs de miembros que YA están en la lista (EntregaBeneficio)
        ids_en_lista = EntregaBeneficio.objects.filter(ciclo=ciclo).values_list('beneficiario_id', flat=True)

        # 3. Obtener todos los CensoMiembro que NO están en la lista
        # El Líder General puede ver todas las torres
        qs = CensoMiembro.objects.all().exclude(id__in=ids_en_lista).select_related('tower').order_by('tower__nombre', 'piso', 'apartamento_letra')
        
        # Opcional: Filtro por Torre (útil para el Líder General)
        torre_id = self.request.GET.get('torre')
        if torre_id and torre_id.isdigit():
            qs = qs.filter(tower_id=int(torre_id))

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tipo_slug = self.kwargs['tipo_slug']
        tipo_db = tipo_slug.upper()
        
        # Intentar obtener el ciclo activo para mostrar la información en el template
        ciclo = CicloBeneficio.objects.filter(tipo=tipo_db, activo=True).first()

        context['tipo_slug'] = tipo_slug
        context['titulo'] = f"Agregar Beneficiarios ({tipo_db})"
        context['ciclo_activo'] = ciclo
        context['torres'] = Tower.objects.all() # Para un posible filtro en el template
        context['torre_seleccionada'] = self.request.GET.get('torre')
        
        return context

    # El método POST se debe redefinir aquí para manejar la adición masiva de la lista.
    # Recibe 'tipo_slug' desde el argumento de la URL.
    def post(self, request, tipo_slug):
        miembros_ids = request.POST.getlist('miembros_ids') # Esperamos una lista de IDs de checkboxes
        
        if not miembros_ids:
            messages.error(request, "No seleccionaste a ningún miembro para agregar.")
            return redirect('lider_general:agregar_beneficiario_global', tipo_slug=tipo_slug)
            
        tipo_db = tipo_slug.upper()
        
        try:
            ciclo_activo = CicloBeneficio.objects.get(tipo=tipo_db, activo=True)
        except CicloBeneficio.DoesNotExist:
            messages.error(request, f"No existe un ciclo activo para {tipo_db}.")
            return redirect('ver_beneficio', tipo_slug=tipo_slug)

        # 4. Crear los objetos EntregaBeneficio
        objetos_a_crear = []
        miembros_seleccionados = CensoMiembro.objects.filter(id__in=miembros_ids)
        
        for miembro in miembros_seleccionados:
            objetos_a_crear.append(
                EntregaBeneficio(
                    ciclo=ciclo_activo,
                    beneficiario=miembro,
                    agregado_por=request.user
                )
            )

        # 5. Guardar en la base de datos de forma masiva
        try:
            # Usamos ignore_conflicts=True para evitar fallos si un beneficiario ya fue agregado
            EntregaBeneficio.objects.bulk_create(objetos_a_crear, ignore_conflicts=True)
            messages.success(request, f"Se agregaron **{len(objetos_a_crear)}** miembros a la lista de {tipo_db}.")
        except IntegrityError:
            messages.warning(request, "Algunos miembros ya estaban en la lista y fueron omitidos.")
        except Exception as e:
            messages.error(request, f"Error al guardar los beneficiarios: {e}")

        # 6. Redirigir a la lista principal de beneficios
        return redirect('ver_beneficio', tipo_slug=tipo_slug)
    

# ******************************************************************
# 4. GESTIÓN DE SOLICITUDES DE DOCUMENTOS
# ******************************************************************

class ListaSolicitudesView(LoginRequiredMixin, LiderGeneralRequiredMixin, ListView):
    """Muestra todas las solicitudes pendientes."""
    model = SolicitudDocumento
    template_name = 'lider_general/solicitudes_lista.html'
    context_object_name = 'solicitudes'
    
    def get_queryset(self):
        # Filtramos solo las pendientes, ordenadas por fecha (más viejas primero)
        return SolicitudDocumento.objects.filter(estado='PENDIENTE').order_by('fecha_solicitud')

class ProcesarSolicitudView(LoginRequiredMixin, LiderGeneralRequiredMixin, UpdateView):
    """
    Vista doble: 
    1. Muestra el formulario para ingresar 'años de residencia'.
    2. Al guardar, genera y descarga el PDF automáticamente.
    """
    model = SolicitudDocumento
    form_class = ProcesarCartaConductaForm
    template_name = 'lider_general/solicitudes_procesar.html'
    context_object_name = 'solicitud'

    def form_valid(self, form):
        # 1. Guardar datos del formulario (años de residencia)
        solicitud = form.save(commit=False)
        solicitud.estado = 'PROCESADO'
        solicitud.procesado_por = self.request.user
        solicitud.fecha_proceso = date.today() # Usamos la fecha actual
        solicitud.save()

        # 2. Generar el PDF
        return self.generar_pdf_carta_conducta(solicitud)

    def generar_pdf_carta_conducta(self, solicitud):
        response = HttpResponse(content_type='application/pdf')
        filename = f"Carta_Conducta_{solicitud.beneficiario.cedula}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        doc = SimpleDocTemplate(response, pagesize=letter, 
                                rightMargin=72, leftMargin=72, 
                                topMargin=72, bottomMargin=18)
        Story = []
        styles = getSampleStyleSheet()
        
        # Estilos Personalizados
        estilo_titulo = ParagraphStyle(
            'Titulo', parent=styles['Normal'], fontSize=12, leading=18, 
            alignment=TA_CENTER, spaceAfter=20
        )
        # --- MODIFICACIÓN 1: Nuevo estilo para el título subrayado ---
        estilo_titulo_documento = ParagraphStyle(
            'TituloDocumento', parent=styles['Normal'], fontSize=12, leading=18, 
            alignment=TA_CENTER, spaceAfter=20, fontName='Helvetica-Bold',
            # Subrayado
            underline=True, 
            underlineColor=black,
            underlineOffset=-2 # Ajusta la posición del subrayado
        )
        # --- FIN MODIFICACIÓN 1 ---

        estilo_cuerpo = ParagraphStyle(
            'Cuerpo', parent=styles['Normal'], fontSize=12, leading=18, 
            alignment=TA_JUSTIFY, spaceAfter=12
        )
        estilo_firmas = ParagraphStyle(
            'Firmas', parent=styles['Normal'], fontSize=11, leading=14, 
            alignment=TA_CENTER
        )
        # --- MODIFICACIÓN 3: Estilo para las líneas de firma ---
        estilo_linea_firma = ParagraphStyle(
            'LineaFirma', parent=styles['Normal'], fontSize=11, leading=14, 
            alignment=TA_CENTER, spaceBefore=10, spaceAfter=0 # Ajusta espaciado
        )
        # --- FIN MODIFICACIÓN 3 ---

        # --- MODIFICACIÓN 1: Insertar la imagen del CLAP ---
        # Ruta de la imagen: Asegúrate de que esta ruta sea correcta para tu proyecto.
        # Asumo que la imagen está en tu carpeta static de App_Home o en la general del proyecto.
        # Por ejemplo: 'static/img/clap_logo.png'
        # Tendrás que crear esta carpeta y colocar la imagen allí.
        try:
            # Reemplaza con la ruta real de tu imagen.
            # Puedes usar staticfiles_storage.path('img/clap_logo.png') si configuras STATIC_ROOT y collectstatic.
            # O simplemente una ruta relativa desde BASE_DIR
            
            # Opción más robusta si la imagen está en App_Home/static/img/clap_logo.png
            from django.conf import settings
            image_path = os.path.join(settings.BASE_DIR, 'App_Home', 'static', 'img', 'clap_logo.png')
            
            # Otra opción si está en un STATICFILES_DIRS configurado globalmente:
            # image_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'clap_logo.png')
            
            img = Image(image_path, width=200, height=50) # Ajusta width/height según necesites
            Story.append(img)
            Story.append(Spacer(1, 12))
        except FileNotFoundError:
            # Si la imagen no se encuentra, vuelve a poner el texto.
            Story.append(Paragraph("<b>CLAP</b>", estilo_titulo))
            messages.error(self.request, "La imagen del logo CLAP no fue encontrada. Se usó texto en su lugar.")


        header_text = """
        Comité Local de Abastecimiento y Producción<br/>
        República Bolivariana de Venezuela<br/>
        Ministerio del Poder Popular para las Comunas y Protección Social<br/>
        Comité Local de abastecimiento y Producción "BALCONES DE PARAGUANÁ I"<br/>
        Municipio Carirubana - Parroquia Punta Cardón.<br/>
        Sector Zarabón - Estado Falcón.<br/>
        """
        Story.append(Paragraph(header_text, estilo_titulo))
        Story.append(Spacer(1, 12))

        # --- MODIFICACIÓN 2: Usar el nuevo estilo para el título del documento ---
        Story.append(Paragraph("<u>CARTA DE BUENA CONDUCTA</u>", estilo_titulo_documento))
        Story.append(Spacer(1, 12))
        # --- FIN MODIFICACIÓN 2 ---

        # --- CUERPO DEL TEXTO (igual que antes) ---
        nombre = f"{solicitud.beneficiario.nombres} {solicitud.beneficiario.apellidos}"
        cedula = solicitud.beneficiario.cedula
        anios = solicitud.anios_residencia
        torre = solicitud.beneficiario.tower.nombre
        piso = solicitud.beneficiario.get_piso_display()
        apto = solicitud.beneficiario.apartamento_letra

        torre_modificada = torre[1:] if torre.startswith('T') else torre
        
        texto_principal = f"""
        El Comité de Abastecimiento y Producción Balcones de Paraguaná I, hace constar que el 
        ciudadano(a), {nombre} Titular de la cédula de identidad N°V.<u>{cedula}</u> reside en 
        esta comunidad por más de {anios} y damos fe de su gran comportamiento y como 
        colaborador ante esta comunidad por lo que hacemos su recomendación como una 
        persona educada y responsable, en el Sector Zarabón, Calle Prolongación Avenida 
        Bolívar, Edificio Conjunto Residencial Balcones de Paraguaná I, Torre {torre_modificada}, {piso}, 
        Apartamento {apto}, Parroquia Punta Cardón, Municipio Carirubana, Punto Fijo, Estado 
        Falcón.
        """
        Story.append(Paragraph(texto_principal, estilo_cuerpo))
        Story.append(Spacer(1, 12))

        # --- FECHA (igual que antes) ---
        fecha_actual = date.today()
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        fecha_texto = f"Constancia que se expide a petición de la parte interesada, en Zarabón a los {fecha_actual.day} días del mes de {meses[fecha_actual.month-1]} del año {fecha_actual.year}."
        
        Story.append(Paragraph(fecha_texto, estilo_cuerpo))
        Story.append(Spacer(1, 40))

        # --- MODIFICACIÓN 3: Firmas con líneas ---
        Story.append(Paragraph("Atentamente", estilo_firmas))
        Story.append(Spacer(1, 30))

        jefe_nombre = f"{self.request.user.first_name} {self.request.user.last_name}"
        jefe_cedula = self.request.user.cedula if self.request.user.cedula else "V-XX.XXX.XXX"
        
        lider_calle_qs = CustomUser.objects.filter(
            rol='LDT', 
            tower=solicitud.beneficiario.tower, 
            is_active=True
        )
        lider_calle = lider_calle_qs.first()

        lc_nombre = f"{lider_calle.first_name} {lider_calle.last_name}" if lider_calle else "____________________"
        lc_cedula = lider_calle.cedula if lider_calle and lider_calle.cedula else "V-XX.XXX.XXX"

        # Usamos Paragraphs para las líneas y nombres, y Spacer para los espacios.
        # Esto es más flexible que Table para solo dos elementos si no necesitas alineación compleja de celdas.

        # Líneas de firma
        Story.append(PDFTable([
            [Paragraph("____________________", estilo_linea_firma), Paragraph("____________________", estilo_linea_firma)]
        ], colWidths=[250, 250]))

        Story.append(Spacer(1, 5)) # Pequeño espacio entre línea y nombre

        # Nombres y Cédulas
        Story.append(PDFTable([
            [Paragraph(f"{jefe_nombre}", estilo_firmas), Paragraph(f"{lc_nombre}", estilo_firmas)],
            [Paragraph(f"V- {jefe_cedula}", estilo_firmas), Paragraph(f"V- {lc_cedula}", estilo_firmas)],
            [Paragraph("Jefe de Comunidad", estilo_firmas), Paragraph("Líder de Calle", estilo_firmas)]
        ], colWidths=[250, 250]))

        # --- FIN MODIFICACIÓN 3 ---

        doc.build(Story)
        return response