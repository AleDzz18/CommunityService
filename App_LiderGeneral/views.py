# App_LiderGeneral/views.py

from django.contrib.auth.mixins import AccessMixin, LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.template.loader import get_template
from django.conf import settings
from App_Home.models import (CustomUser, MovimientoFinanciero, Tower, CensoMiembro,
                            CicloBeneficio, EntregaBeneficio, SolicitudDocumento,
                            InventarioBasura)
from App_Home.forms import CensoMiembroForm
from App_LiderTorre.views import BaseMovimientoCreateView 
from .forms import ( FormularioAdminUsuario, IngresoCondominioGeneralForm, EgresoCondominioGeneralForm, 
                    IngresoBasuraGeneralForm, EgresoBasuraGeneralForm, ProcesarCartaConductaForm,
                    ProcesarCartaMudanzaForm, ProcesarConstanciaSimpleForm, ProcesarConstanciaMigratoriaForm,
                    InventarioBasuraForm)
from datetime import date
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image , Table as PDFTable, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import black # Para el color del subrayado
from reportlab.lib.units import inch
from reportlab.lib import colors
import os
from io import BytesIO


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

class ProcesarSolicitudView(LoginRequiredMixin, UserPassesTestMixin, View):
    
    def test_func(self):
        # Solo Lideres Generales (LDG) pueden procesar documentos
        return self.request.user.rol == 'LDG'

    def get(self, request, pk):
        solicitud = get_object_or_404(SolicitudDocumento, pk=pk)
        
        if solicitud.tipo == 'CARTA_MUDANZA':
            form = ProcesarCartaMudanzaForm(instance=solicitud)

        elif solicitud.tipo == 'CONSTANCIA_RESIDENCIA':
            form = ProcesarConstanciaSimpleForm(instance=solicitud)

        elif solicitud.tipo == 'CONSTANCIA_MIGRATORIA':
            form = ProcesarConstanciaMigratoriaForm(instance=solicitud)

        else:
            # Por defecto, o para CARTA_CONDUCTA
            form = ProcesarCartaConductaForm(instance=solicitud)
            
        return render(request, 'lider_general/solicitudes_procesar.html', {
            'form': form, 
            'solicitud': solicitud
        })

    def post(self, request, pk):
        solicitud = get_object_or_404(SolicitudDocumento, pk=pk)
        
        if solicitud.tipo == 'CARTA_MUDANZA':
            form = ProcesarCartaMudanzaForm(request.POST, instance=solicitud)
        elif solicitud.tipo == 'CONSTANCIA_RESIDENCIA':
            form = ProcesarConstanciaSimpleForm(request.POST, instance=solicitud)
        elif solicitud.tipo == 'CONSTANCIA_MIGRATORIA':
            form = ProcesarConstanciaMigratoriaForm(request.POST, instance=solicitud)
        else:
            form = ProcesarCartaConductaForm(request.POST, instance=solicitud)

        if form.is_valid():
            solicitud_procesada = form.save(commit=False)
            solicitud_procesada.estado = 'PROCESADO'
            solicitud_procesada.procesado_por = request.user
            solicitud_procesada.fecha_proceso = timezone.now()
            solicitud_procesada.save()
            
            # --- LÓGICA DE GENERACIÓN DE PDF ---
            if solicitud.tipo == 'CARTA_MUDANZA':
                messages.success(request, f"Se ha procesado y generado el PDF de Carta de Mudanza para {solicitud.beneficiario.nombres}.")
                return self.generar_pdf_mudanza(solicitud_procesada)
            
            elif solicitud.tipo == 'CARTA_CONDUCTA':
                # ¡Esta es la línea que fallaba y ahora es posible!
                messages.success(request, f"Se ha procesado y generado el PDF de Carta de Conducta para {solicitud.beneficiario.nombres}.")
                return self.generar_pdf_conducta(solicitud_procesada)
            
            elif solicitud.tipo == 'CONSTANCIA_RESIDENCIA': 
                messages.success(request, f"Se ha procesado y generado el PDF de Constancia de Residencia para {solicitud.beneficiario.nombres}.")
                return self.generar_pdf_residencia(solicitud_procesada)
            
            elif solicitud.tipo == 'CONSTANCIA_MIGRATORIA': 
                messages.success(request, f"Se ha procesado y generado el PDF de Constancia Migratoria para {solicitud.beneficiario.nombres}.")
                return self.generar_pdf_migratoria(solicitud_procesada)
            
            else:
                messages.warning(request, "Documento procesado pero no se pudo generar el PDF (Tipo no implementado).")
                return redirect('lider_general:lista_solicitudes') 
        
        messages.error(request, "Error en los datos ingresados.")
        return render(request, 'lider_general/solicitudes_procesar.html', {'form': form, 'solicitud': solicitud})

    # --- GENERADOR 1: CARTA DE BUENA CONDUCTA (RESTAURADO) ---
    def generar_pdf_conducta(self, solicitud):
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
        if solicitud.logo_clap == True:
            try:
                # Opción más robusta si la imagen está en App_Home/static/img/clap_logo.png
                from django.conf import settings
                image_path = os.path.join(settings.BASE_DIR, 'App_Home', 'static', 'img', 'clap_logo.png')

                img = Image(image_path, width=350, height=75) # Ajusta width/height según necesites
                Story.append(img)
                Story.append(Spacer(1, 12))
            except FileNotFoundError:
                # Si la imagen no se encuentra, vuelve a poner el texto.
                Story.append(Paragraph("<b>CLAP</b>", estilo_titulo))
                messages.error(self.request, "La imagen del logo CLAP no fue encontrada. Se usó texto en su lugar.")

        header_text = """
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

        doc.build(Story)
        return response
    
    # NUEVO: Generador de PDF para Carta de Mudanza
    def generar_pdf_mudanza(self, solicitud):
        """Genera el PDF basado en el formato 'Carta de Mudanza.pdf'"""
        response = HttpResponse(content_type='application/pdf')
        filename = f"Carta_Mudanza_{solicitud.beneficiario.cedula}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        doc = SimpleDocTemplate(response, pagesize=letter, 
                                topMargin=72, bottomMargin=18, 
                                leftMargin=72, rightMargin=72)
        Story = []
        styles = getSampleStyleSheet()

        # Estilos Personalizados
        estilo_titulo = ParagraphStyle('Titulo', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, leading=18, spaceAfter=20)
        estilo_titulo_documento = ParagraphStyle('TituloDocumento', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12,
                                                leading=18, spaceAfter=20, fontName='Helvetica-Bold', underline=True, 
                                                underlineColor=black, underlineOffset=-2)
        
        estilo_cuerpo = ParagraphStyle('Cuerpo', parent=styles['Normal'], alignment=TA_JUSTIFY, fontSize=12, leading=18, spaceAfter=12)
        estilo_firma = ParagraphStyle('Firma', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, leading=14)

        if solicitud.logo_clap == True:
            try:
                # Opción más robusta si la imagen está en App_Home/static/img/clap_logo.png
                from django.conf import settings
                image_path = os.path.join(settings.BASE_DIR, 'App_Home', 'static', 'img', 'clap_logo.png')

                img = Image(image_path, width=350, height=75) # Ajusta width/height según necesites
                Story.append(img)
                Story.append(Spacer(1, 12))
            except FileNotFoundError:
                # Si la imagen no se encuentra, vuelve a poner el texto.
                Story.append(Paragraph("<b>CLAP</b>", estilo_titulo))
                messages.error(self.request, "La imagen del logo CLAP no fue encontrada. Se usó texto en su lugar.")

        # ENCABEZADO (Tomando texto de los PDFs)
        header_text = """
        República Bolivariana de Venezuela<br/>
        Ministerio del Poder Popular para las Comunas y Protección Social<br/>
        Comité Local de abastecimiento y Producción "BALCONES DE PARAGUANÁ I"<br/>
        Municipio Carirubana - Parroquia Punta Cardón.<br/>
        Sector Zarabón - Estado Falcón.<br/>
        """
        Story.append(Paragraph(header_text, estilo_titulo))
        Story.append(Spacer(1, 12))

        # TÍTULO DEL DOCUMENTO
        Story.append(Paragraph("<u>CARTA DE MUDANZA</u>", estilo_titulo_documento))
        Story.append(Spacer(1, 12))

        # CUERPO DEL DOCUMENTO
        nombre = f"{solicitud.beneficiario.nombres} {solicitud.beneficiario.apellidos}"
        cedula = solicitud.beneficiario.cedula
        torre = solicitud.beneficiario.tower.nombre
        piso = solicitud.beneficiario.get_piso_display()
        apto = solicitud.beneficiario.apartamento_letra
        # Usamos los campos nuevos
        anio_inicio = solicitud.mudanza_anio_inicio
        fecha_fin = solicitud.mudanza_fecha_fin 
        
        torre_modificada = torre[1:] if torre.startswith('T') else torre

        texto_principal = f"""
        Por medio de la presente nosotros integrantes del El Comité de Abastecimiento y
        Producción Balcones de Paraguaná I, hace constar que el ciudadano(a), {nombre}
        Titular de la cédula de identidad N°V.<u>{cedula}</u> residía desde el año {anio_inicio} hasta
        {fecha_fin} en el Conjunto Residencial Balcones de Paraguaná I, Torre {torre_modificada}, {piso},
        Apartamento {apto}.
        """
        Story.append(Paragraph(texto_principal, estilo_cuerpo))

        # FECHA Y CIERRE
        fecha_hoy = timezone.now()
        meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        fecha_texto = f"Constancia que se expide a petición de la parte interesada, en Zarabón a los {fecha_hoy.day} días del mes de {meses[fecha_hoy.month-1]} del año {fecha_hoy.year}."
        Story.append(Spacer(1, 0.2*inch))
        Story.append(Paragraph(fecha_texto, estilo_cuerpo))

        # FIRMA
        Story.append(Spacer(1, 0.5*inch))
        Story.append(Paragraph("Atentamente", estilo_firma))
        Story.append(Spacer(1, 0.5*inch))

        jefe_nombre = f"{self.request.user.first_name} {self.request.user.last_name}"
        jefe_cedula = self.request.user.cedula if self.request.user.cedula else "V-XX.XXX.XXX"
        
        Story.append(Paragraph("________________________", estilo_firma))
        Story.append(Spacer(1, 5))
        Story.append(Paragraph(f"{jefe_nombre}", estilo_firma))
        Story.append(Paragraph(f"V- {jefe_cedula}", estilo_firma))
        Story.append(Paragraph("Jefe de Comunidad", estilo_firma))
        

        doc.build(Story)
        return response
    
    def generar_pdf_residencia(self, solicitud):
        """Genera el PDF basado en el formato 'CONSTANCIA DE RESIDENCIA.pdf'"""
        response = HttpResponse(content_type='application/pdf')
        filename = f"Constancia_Residencia_{solicitud.beneficiario.cedula}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        doc = SimpleDocTemplate(response, pagesize=letter, 
                                topMargin=72, bottomMargin=18, 
                                leftMargin=72, rightMargin=72)
        Story = []
        styles = getSampleStyleSheet()

        # Estilos Personalizados
        estilo_titulo = ParagraphStyle('Titulo', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, leading=18, spaceAfter=20)
        estilo_titulo_documento = ParagraphStyle('TituloDocumento', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12,
                                                leading=18, spaceAfter=20, fontName='Helvetica-Bold', underline=True, 
                                                underlineColor=black, underlineOffset=-2)
        
        estilo_cuerpo = ParagraphStyle('Cuerpo', parent=styles['Normal'], alignment=TA_JUSTIFY, fontSize=12, leading=18, spaceAfter=12)
        estilo_firmas = ParagraphStyle('Firmas', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, leading=14)
        estilo_linea_firma = ParagraphStyle(name='LineaFirma', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, leading=1, spaceAfter=0)

        if solicitud.logo_clap == True:
            try:
                # Opción más robusta si la imagen está en App_Home/static/img/clap_logo.png
                from django.conf import settings
                image_path = os.path.join(settings.BASE_DIR, 'App_Home', 'static', 'img', 'clap_logo.png')

                img = Image(image_path, width=350, height=75) # Ajusta width/height según necesites
                Story.append(img)
                Story.append(Spacer(1, 12))
            except FileNotFoundError:
                # Si la imagen no se encuentra, vuelve a poner el texto.
                Story.append(Paragraph("<b>CLAP</b>", estilo_titulo))
                messages.error(self.request, "La imagen del logo CLAP no fue encontrada. Se usó texto en su lugar.")

        # ENCABEZADO
        header_text = """
        República Bolivariana de Venezuela<br/>
        Ministerio del Poder Popular para las Comunas y Protección Social<br/>
        Comité Local de abastecimiento y Producción "BALCONES DE PARAGUANÁ I"<br/>
        Municipio Carirubana - Parroquia Punta Cardón.<br/>
        Sector Zarabón - Estado Falcón.<br/>
        """
        Story.append(Paragraph(header_text, estilo_titulo))
        Story.append(Spacer(1, 12))

        # TÍTULO DEL DOCUMENTO
        Story.append(Paragraph("<u>CONSTANCIA DE RESIDENCIA</u>", estilo_titulo_documento))
        Story.append(Spacer(1, 12))

        # CUERPO DEL DOCUMENTO
        nombre = f"{solicitud.beneficiario.nombres} {solicitud.beneficiario.apellidos}"
        cedula = solicitud.beneficiario.cedula
        torre = solicitud.beneficiario.tower.nombre
        piso = solicitud.beneficiario.get_piso_display()
        apto = solicitud.beneficiario.apartamento_letra
        
        torre_modificada = torre[1:] if torre.startswith('T') else torre

        texto_principal = f"""
        El Comité de Abastecimiento y Producción Balcones de Paraguaná I, hace constar que el
        ciudadano(a), {nombre} Titular de la cédula de identidad N°V.<u>{cedula}</u> reside en el
        Sector Zarabón, Calle Prolongación Avenida Bolívar, Edificio Conjunto Residencial
        Balcones de Paraguaná I, Torre {torre_modificada}, {piso}, Apartamento {apto}, Parroquia Punta Cardón,
        Municipio Carirubana, Punto Fijo, Estado Falcón.
        """
        Story.append(Paragraph(texto_principal, estilo_cuerpo))

        # FECHA Y CIERRE
        fecha_hoy = timezone.now()
        meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        fecha_texto = f"Constancia que se expide a petición de la parte interesada, en Zarabón a los {fecha_hoy.day} días del mes de {meses[fecha_hoy.month-1]} del año {fecha_hoy.year}."
        Story.append(Paragraph(fecha_texto, estilo_cuerpo))
        Story.append(Spacer(1, 40))

        # --- SECCIÓN DE FIRMAS ---
        # Busca el Líder de Torre de la torre del vecino como Líder de Calle
        lider_calle_qs = CustomUser.objects.filter(
            rol='LDT', 
            tower=solicitud.beneficiario.tower, 
            is_active=True
        )
        lider_calle = lider_calle_qs.first()

        lc_nombre = f"{lider_calle.first_name} {lider_calle.last_name}" if lider_calle else "____________________"
        lc_cedula = lider_calle.cedula if lider_calle and lider_calle.cedula else "V-XX.XXX.XXX"

        # Datos del Jefe de Comunidad (HARDCODEADO según tu plantilla)
        jefe_nombre = f"{self.request.user.first_name} {self.request.user.last_name}"
        jefe_cedula = self.request.user.cedula if self.request.user.cedula else "V-XX.XXX.XXX"
        
        Story.append(Paragraph("Atentamente", estilo_firmas))
        Story.append(Spacer(1, 30))

        # Líneas de firma (Tabla para alineación)
        Story.append(PDFTable([
            [Paragraph("____________________", estilo_linea_firma), Paragraph("____________________", estilo_linea_firma)]
        ], colWidths=[250, 250]))

        Story.append(Spacer(1, 5)) 

        # Nombres, Cédulas y Roles
        Story.append(PDFTable([
            [Paragraph(jefe_nombre, estilo_firmas), Paragraph(lc_nombre, estilo_firmas)],
            [Paragraph(f"V- {jefe_cedula}", estilo_firmas), Paragraph(f"V- {lc_cedula}", estilo_firmas)],
            [Paragraph("Jefe de Comunidad", estilo_firmas), Paragraph("Líder de Calle", estilo_firmas)],
        ], colWidths=[250, 250]))

        doc.build(Story)
        return response
    
    def generar_pdf_migratoria(self, solicitud):
        """Genera el PDF basado en el formato 'CONSTANCIA MIGRATORIA.pdf'"""
        response = HttpResponse(content_type='application/pdf')
        filename = f"Constancia_Migratoria_{solicitud.beneficiario.cedula}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # Document Setup
        doc = SimpleDocTemplate(response, pagesize=letter, 
                                topMargin=72, bottomMargin=18, 
                                leftMargin=72, rightMargin=72)
        Story = []
        styles = getSampleStyleSheet()

        # Estilos (Usando los mismos que en los otros generadores)
        estilo_titulo = ParagraphStyle('Titulo', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, leading=18, spaceAfter=20)
        estilo_titulo_documento = ParagraphStyle(name='TituloDocumento', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12,
                                                spaceAfter=20, leading=18, fontName='Helvetica-Bold', underline=True, 
                                                underlineColor=black, underlineOffset=-2)
        estilo_cuerpo = ParagraphStyle(name='Cuerpo', parent=styles['Normal'], alignment=TA_JUSTIFY, fontSize=12, leading=18, spaceAfter=12)
        estilo_firmas = ParagraphStyle(name='Firmas', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, leading=14)
        

        # Obtención de Datos
        vecino = solicitud.beneficiario
        nombre_completo = f"{vecino.nombres} {vecino.apellidos}"
        cedula = vecino.cedula
        torre = vecino.tower.nombre if vecino.tower else "N/A"
        piso = vecino.get_piso_display()
        anio_inicio = solicitud.migratoria_anio_inicio
        anio_fin = solicitud.migratoria_anio_fin
        
        torre_modificada = torre[1:] if torre.startswith('T') else torre
        
        if solicitud.logo_clap == True:
            try:
                # Opción más robusta si la imagen está en App_Home/static/img/clap_logo.png
                from django.conf import settings
                image_path = os.path.join(settings.BASE_DIR, 'App_Home', 'static', 'img', 'clap_logo.png')
                
                img = Image(image_path, width=350, height=75) # Ajusta width/height según necesites
                Story.append(img)
                Story.append(Spacer(1, 12))
            except FileNotFoundError:
                # Si la imagen no se encuentra, vuelve a poner el texto.
                Story.append(Paragraph("<b>CLAP</b>", estilo_titulo))
                messages.error(self.request, "La imagen del logo CLAP no fue encontrada. Se usó texto en su lugar.")
        
        # ENCABEZADO (Adaptado de la plantilla)
        header_text = """
        República Bolivariana de Venezuela<br/>
        Ministerio del Poder Popular para las Comunas y Protección Social<br/>
        Comité Local de abastecimiento y Producción "BALCONES DE PARAGUANÁ I"<br/>
        Municipio Carirubana - Parroquia Punta Cardón.<br/>
        Sector Zarabón - Estado Falcón.<br/>
        """
        Story.append(Paragraph(header_text, estilo_titulo))
        Story.append(Spacer(1, 12))

        # TÍTULO DEL DOCUMENTO
        Story.append(Paragraph("<u>CONSTANCIA MIGRATORIA</u>", estilo_titulo_documento))
        Story.append(Spacer(1, 12))

        # CUERPO DEL DOCUMENTO
        # La Constancia Migratoria del ejemplo (CONSTANCIA MIGRATORIA.pdf) no incluye Piso/Apartamento, solo la Torre.
        
        texto = f"""
        Por medio de la presente nosotros integrantes del El Comité de Abastecimiento y
        Producción Balcones de Paraguaná I, hace constar que el ciudadano(a), {nombre_completo}
        Titular de la cédula de identidad N°V.<u>{cedula}</u> tenía su residencia desde el
        año {anio_inicio} hasta el año {anio_fin} en el Conjunto Residencial Balcones de Paraguaná I, Torre
        {torre_modificada}. A partir de esta fecha deja de estar incluido(a) en nuestros censos, para todos los fines
        consiguientes.

        """
        Story.append(Paragraph(texto, estilo_cuerpo))

        # FECHA Y CIERRE
        fecha_hoy = timezone.now()
        meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        # Formato de la migratoria: 'Punto Fijo Municipio Carirubana al 1 día del mes de Diciembre del año 2025.'
        fecha_texto = f"Constancia que se expide por solicitud de parte interesada, Punto Fijo Municipio Carirubana al {fecha_hoy.day} día del mes de {meses[fecha_hoy.month-1]} del año {fecha_hoy.year}."
        
        Story.append(Spacer(1, 0.2*inch))
        Story.append(Paragraph(fecha_texto, estilo_cuerpo))

        # --- SECCIÓN DE FIRMAS ---
        
        # Datos del Jefe de Comunidad (HARDCODEADO según tu plantilla)
        jefe_nombre = f"{self.request.user.first_name} {self.request.user.last_name}"
        jefe_cedula = self.request.user.cedula if self.request.user.cedula else "V-XX.XXX.XXX"
        
        Story.append(Spacer(1, 0.5*inch))
        Story.append(Paragraph("Atentamente", estilo_firmas))
        Story.append(Paragraph("Por el CLAP", estilo_firmas))
        Story.append(Spacer(1, 0.5*inch))
        
        # Línea de firma
        Story.append(Paragraph("____________________", estilo_firmas))
        Story.append(Spacer(1, 5)) 

        # Nombre, Cédula y Rol
        Story.append(Paragraph(jefe_nombre, estilo_firmas))
        Story.append(Paragraph(f"V- {jefe_cedula}", estilo_firmas))
        Story.append(Paragraph("Jefe de Comunidad", estilo_firmas))


        doc.build(Story)
        return response
    
class LiderGeneralRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.rol == 'LDG'

class CensoPDFGeneralView(LoginRequiredMixin, LiderGeneralRequiredMixin, View):
    """Genera un PDF con el listado completo del Censo Comunitario (Mejorado)."""
    
    def get(self, request, *args, **kwargs):
        # 1. Obtener los datos
        miembros = CensoMiembro.objects.select_related('tower').all().order_by('tower__nombre', 'piso', 'apartamento_letra')

        # 2. Configuración del PDF
        buffer = BytesIO()
        # Ajustamos los márgenes (topMargin) para aprovechar mejor la hoja
        doc = SimpleDocTemplate(buffer, pagesize=A4, title="Censo Comunitario General",
                                topMargin=30, bottomMargin=30, leftMargin=30, rightMargin=30)
        
        Story = []
        styles = getSampleStyleSheet()
        
        # Estilos personalizados
        estilo_titulo = ParagraphStyle('TituloPDF', parent=styles['Normal'], alignment=TA_CENTER, fontSize=18, fontName='Helvetica-Bold', spaceAfter=5)
        estilo_subtitulo = ParagraphStyle('SubtituloPDF', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, textColor=colors.grey, spaceAfter=15)
        estilo_fecha = ParagraphStyle('FechaPDF', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=9, spaceAfter=20)

        # Encabezado
        Story.append(Paragraph("Censo Comunitario General", estilo_titulo))
        Story.append(Paragraph("Balcones de Paraguaná I", estilo_subtitulo))
        Story.append(Paragraph(f"Generado el: {timezone.now().strftime('%d/%m/%Y %I:%M %p')}", estilo_fecha))
        
        # Eliminamos los Spacers gigantes que bajaban la tabla
        Story.append(Spacer(1, 10)) 

        # 3. Datos de la tabla
        data = []
        # Encabezados
        headers = ['Torre', 'Ubicación', 'Cédula', 'Nombre Completo', 'Jefe Fam.', 'Teléfono']
        data.append(headers)

        for m in miembros:
            piso_apto = f"{m.apartamento_completo}" # Usa la propiedad del modelo
            nombre_completo = f"{m.nombres} {m.apellidos}"
            
            # Cortar nombres muy largos si es necesario para que no rompa la tabla
            if len(nombre_completo) > 25:
                nombre_completo = nombre_completo[:22] + "..."

            data.append([
                m.tower.nombre,
                piso_apto,
                m.cedula,
                nombre_completo,
                'SÍ' if m.es_jefe_familia else 'NO',
                m.telefono if m.telefono else '-'
            ])
        
        # 4. Configuración de la Tabla
        # Ancho disponible en A4 (aprox 535 puntos con márgenes de 30)
        # Ajustamos columnas: Torre(40), Ubic(50), Ced(70), Nombre(200), Jefe(50), Tel(80) = ~490
        col_widths = [40, 60, 75, 210, 50, 90]
        
        table = PDFTable(data, colWidths=col_widths)
        
        # Estilo visual profesional
        table.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003049')), # Azul oscuro
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            
            # Cuerpo
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey), # Cuadrícula fina
            
            # Filas alternas (Efecto Pijama) para facilitar lectura
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))
        
        Story.append(table)
        Story.append(Spacer(1, 20))
        Story.append(Paragraph(f"Total de Registros: {len(miembros)}", estilo_fecha))

        # 5. Generar
        doc.build(Story)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Censo_General_{timezone.now().strftime("%Y%m%d")}.pdf"'
        response.write(buffer.getvalue())
        buffer.close()
        return response
    
# --- GESTIÓN DE INVENTARIO CUARTO DE BASURA ---

class InventarioBasuraListView(ListView):
    """
    Vista pública para la comunidad: Muestra la lista de instrumentos.
    Automáticamente verifica en el template si el usuario tiene permisos para mostrar los botones de edición.
    """
    model = InventarioBasura
    template_name = 'lider_general/inventario_lista.html'
    context_object_name = 'inventario'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Definimos si el usuario actual es administrador (solo si está autenticado)
        user = self.request.user
        
        # Usamos user.is_authenticated para evitar errores si el usuario no está logueado (AnonymousUser)
        if user.is_authenticated:
            context['es_admin_basura'] = user.rol == 'LDG' or user.es_admin_basura
        else:
            context['es_admin_basura'] = False # Si no está logueado, nunca puede ser administrador.
            
        return context

class InventarioBasuraCreateView(LoginRequiredMixin, LiderGeneralOrAdminBasuraRequiredMixin, CreateView):
    model = InventarioBasura
    form_class = InventarioBasuraForm
    template_name = 'lider_general/inventario_form.html'
    success_url = reverse_lazy('lider_general:inventario_lista')

    def form_valid(self, form):
        messages.success(self.request, "Ítem agregado al inventario correctamente.")
        return super().form_valid(form)

class InventarioBasuraUpdateView(LoginRequiredMixin, LiderGeneralOrAdminBasuraRequiredMixin, UpdateView):
    model = InventarioBasura
    form_class = InventarioBasuraForm
    template_name = 'lider_general/inventario_form.html'
    success_url = reverse_lazy('lider_general:inventario_lista')

    def form_valid(self, form):
        messages.success(self.request, "Inventario actualizado correctamente.")
        return super().form_valid(form)

class InventarioBasuraDeleteView(LoginRequiredMixin, LiderGeneralOrAdminBasuraRequiredMixin, DeleteView):
    model = InventarioBasura
    template_name = 'lider_general/inventario_confirm_delete.html'
    success_url = reverse_lazy('lider_general:inventario_lista')

    def form_valid(self, form):
        messages.success(self.request, "Ítem eliminado del inventario.")
        return super().form_valid(form)