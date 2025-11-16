from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as autenticar_login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required 
from django.contrib import messages
from django.contrib.messages import get_messages
from django.http import HttpResponse # Importación para manejar la respuesta de PDF
from django.utils import timezone # Importación para manejar la fecha/hora actual
# Importaciones para generar PDF (Reportlab)
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph # <-- CRÍTICO
from reportlab.lib.styles import getSampleStyleSheet # <-- CRÍTICO
from reportlab.lib.units import inch
from .forms import FormularioCreacionUsuario, FormularioPerfilUsuario, FormularioFiltroMovimientos 
from .models import CustomUser, Tower, MovimientoFinanciero # Importación de los nuevos modelos
from decimal import Decimal

def vista_dashboard(request):
    """
    Muestra la página principal o dashboard. Permite acceso a espectadores.
    """
    
    # 🔑 LÓGICA CRÍTICA: REDIRECCIÓN FORZOSA A COMPLETAR PERFIL
    if request.user.is_authenticated:
        usuario = request.user
        
        # Utilizamos la Cédula (cedula) como el indicador principal de Perfil Incompleto.
        # Si está logueado y NO tiene cédula, lo enviamos a completar perfil.
        # Se usa getattr para seguridad en caso de que el campo no exista o sea None.
        if not getattr(usuario, 'cedula', None):
            messages.warning(request, "Debe completar su perfil para acceder al sistema.")
            return redirect('url_completar_perfil', user_id=usuario.id)
            
    # -------------------------------------------------------------------
    
    contexto = {
        'usuario_autenticado': request.user.is_authenticated,
        'rol_usuario': getattr(request.user, 'rol', None) if request.user.is_authenticated else None,
        'torre_asignada': getattr(request.user, 'torre', None) if request.user.is_authenticated else None,
    }
    return render(request, 'homeDashboard.html', contexto)

@login_required 
def vista_logout(request):
    """
    Cierra la sesión del usuario y redirige al dashboard en modo espectador.
    """
    logout(request)
    return redirect('url_dashboard') 

def vista_login(request):
    """Maneja la autenticación del usuario."""
    
    # Si el usuario ya está autenticado, simplemente se redirige.
    if request.user.is_authenticated:
        return redirect('url_dashboard')
    
    if request.method == 'POST':
        formulario = AuthenticationForm(request, data=request.POST)
        if formulario.is_valid():
            username = formulario.cleaned_data.get('username')
            password = formulario.cleaned_data.get('password')
            usuario = authenticate(username=username, password=password)
            if usuario is not None:
                # 🔑 MODIFICACIÓN AQUÍ: Usar 'cedula' para forzar la redirección a completar perfil, 
                # en lugar de 'is_active', si el login fue exitoso.
                if not getattr(usuario, 'cedula', None):
                    messages.warning(request, 'Su perfil está incompleto. Por favor, complete sus datos.')
                    return redirect('url_completar_perfil', user_id=usuario.id)
                
                # Si todo está completo, inicia sesión y redirige al dashboard
                autenticar_login(request, usuario)
                return redirect('url_dashboard') 
            else:
                messages.error(request, 'Nombre de usuario o contraseña incorrectos.')
        else:
            messages.error(request, 'Error en la forma de autenticación.')
    
    formulario = AuthenticationForm()
    
    # Obtener mensajes existentes para mostrarlos
    storage = get_messages(request)
    
    return render(request, 'login.html', {'formulario': formulario, 'messages': storage})

def vista_registro(request):
    """Maneja la creación de nuevos usuarios."""
    if request.user.is_authenticated:
        return redirect('url_dashboard')

    if request.method == 'POST':
        formulario = FormularioCreacionUsuario(request.POST)
        if formulario.is_valid():
            usuario = formulario.save(commit=False)
            
            # El usuario DEBE estar activo (True) para que autenticar_login funcione.
            # Por defecto, Django lo guarda como is_active=True.
            usuario.save() 
            
            # PASO CRÍTICO: Iniciar sesión y redirigir al perfil.
            autenticar_login(request, usuario) 
            
            messages.success(request, f'Cuenta creada exitosamente para {usuario.username}. Por favor, complete su perfil.')
            
            # Redirigir directamente al perfil para evitar el bucle inicial del dashboard.
            return redirect('url_completar_perfil', user_id=usuario.id) 
        else:
            # Mostrar errores de validación del formulario de registro
            for field, errors in formulario.errors.items():
                for error in errors:
                    field_name = formulario.fields.get(field).label if field in formulario.fields and formulario.fields.get(field).label else field
                    messages.error(request, f"Error en {field_name}: {error}")

    formulario = FormularioCreacionUsuario()
    return render(request, 'register.html', {'formulario': formulario})

@login_required
def vista_completar_perfil(request, user_id):
    """
    Permite a un nuevo usuario (Líder) completar sus datos de perfil (Torre, Cédula, etc.)
    y activar su cuenta.
    """
    usuario = get_object_or_404(CustomUser, pk=user_id)
    
    # Asegurar que solo el propio usuario pueda completar su perfil
    if request.user.id != usuario.id:
        messages.error(request, 'No tiene permisos para editar el perfil de otro usuario.')
        return redirect('url_dashboard')
    
    # 🔑 MODIFICACIÓN: Si el usuario tiene Cédula (perfil completo), lo redirigimos
    if getattr(usuario, 'cedula', None):
        messages.info(request, "Su perfil ya está completo.")
        return redirect('url_dashboard')
    
    # LÍNEA ELIMINADA: Ya no verificamos if usuario.is_active, sino la cédula.

    if request.method == 'POST':
        formulario = FormularioPerfilUsuario(request.POST, instance=usuario)
        if formulario.is_valid():
            formulario.save()
            
            # NO ES NECESARIO SETEAR is_active=True NI HACER login de nuevo
            # ya que el usuario siempre estuvo activo y logueado, solo que incompleto.
            
            messages.success(request, 'Perfil completado con éxito. ¡Bienvenido a la comunidad!')
            return redirect('url_dashboard')
        else:
            messages.error(request, 'El formulario contiene errores. Por favor, corrígelos a continuación:')
            
            # Iterar sobre todos los errores del formulario (incluidos los globales bajo el key '__all__')
            for field, errors in formulario.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, f"{error}")
                    else:
                        field_name = formulario.fields.get(field).label if field in formulario.fields else field
                        messages.error(request, f"Error en {field_name}: {error}")
    
    else:
        formulario = FormularioPerfilUsuario(instance=usuario)
        
    return render(request, 'completar_perfil.html', {
        'formulario': formulario, 
        'usuario': usuario
    })


# ------------------------------------------------------------------
# --- NUEVAS VISTAS: ADMINISTRACIÓN DE INGRESOS Y EGRESOS (USUARIO BÁSICO) ---
# ------------------------------------------------------------------

def ver_ingresos_egresos(request, categoria_slug):
    """
    Muestra la lista de movimientos financieros para Condominio o Cuarto de Basura.
    Accesible por usuarios NO autenticados (Usuario Básico).
    """
    # 1. Definir la categoría y el título basados en el slug de la URL
    if categoria_slug == 'condominio':
        categoria_filtro = 'CON'
        titulo = 'Administración de Ingresos y Egresos - Condominio'
        monto_field = 'monto_condominio' # Campo de monto dinámico
    elif categoria_slug == 'basura':
        categoria_filtro = 'BAS'
        titulo = 'Administración de Ingresos y Egresos - Cuarto de Basura'
        monto_field = 'monto_basura' # Campo de monto dinámico
    else:
        # Si la URL es inválida, se redirige al dashboard.
        return redirect('url_dashboard') 
        
    # =========================================================================
    # LÓGICA DE MANEJO DE POST (REGISTRO DE MOVIMIENTO)
    # Resuelve: 1. Saldo Negativo, 2. Restricción por Torre, 3. Registro/Redirección
    # =========================================================================
    if request.method == 'POST':
        # 1. Validar y Obtener datos del formulario POST
        try:
            fecha = request.POST['fecha']
            descripcion = request.POST['descripcion']
            tipo = request.POST['tipo'] # 'ING' o 'EGR'

            # --- AGREGADO: Extraer Tasa BCV ---
            tasa_bcv = Decimal(request.POST['tasa_bcv']) # Usar Decimal para precisión
            if tasa_bcv <= 0:
                raise ValueError("La Tasa BCV debe ser un valor positivo.")
            # ----------------------------------
            
            # Asegurar que el monto es un número positivo
            monto = float(request.POST['monto'])
            if monto <= 0: 
                raise ValueError("El monto debe ser una cantidad positiva.")
                
        except (KeyError, ValueError) as e:
            # Mensaje de error mejorado para el formulario
            messages.error(request, f'Error en los datos del movimiento. Verifique la fecha, descripción, tipo y monto. Detalle: {e}.')
            return redirect('ver_finanzas', categoria_slug=categoria_slug)
            
        # 2. Restricción por Torre (Se mantiene la lógica)
        if not request.user.is_authenticated or request.user.rol != 'LDT' or not request.user.tower:
            messages.error(request, 'Operación denegada. Solo los Líderes de Torre asignados pueden registrar movimientos.')
            return redirect('ver_finanzas', categoria_slug=categoria_slug)
            
        torre_asignada = request.user.tower
        
        # 3. **Prevenir Saldo Negativo (Problema 1 - REFORZADO)**
        if tipo == 'EGR':
            # Usa el Manager para calcular el saldo de la categoría correcta
            saldo_actual = MovimientoFinanciero.objects.calcular_saldo_torre(
                tower=torre_asignada, 
                categoria=categoria_filtro
            )
            
            # VALIDACIÓN CRÍTICA:
            if saldo_actual - monto < 0:
                messages.error(request, f'Operación denegada. Saldo insuficiente para este egreso. Saldo actual: Bs. {saldo_actual:.2f}')
                return redirect('ver_finanzas', categoria_slug=categoria_slug) # Redirección a la página actual

        # 4. Crear la instancia del Movimiento (aún sin guardar en DB)
        movimiento = MovimientoFinanciero(
            fecha=fecha,
            descripcion=descripcion,
            tasa_bcv=tasa_bcv,
            tipo=tipo,
            categoria=categoria_filtro, 
            creado_por=request.user,
            tower=torre_asignada,
        )
        
        # 5. **Asignar el Monto Correcto (Problema 2 - Registro de Basura)**
        # Se asigna el monto al campo correspondiente a la categoría.
        if categoria_filtro == 'CON':
            movimiento.monto_condominio = monto
            movimiento.monto_basura = 0.00 
        else: # categoria_filtro == 'BAS'
            movimiento.monto_basura = monto
            movimiento.monto_condominio = 0.00 

        # 6. Guardar la instancia (Una sola vez)
        try:
            movimiento.save() 
            messages.success(request, f'Movimiento de {movimiento.get_tipo_display()} registrado con éxito en {movimiento.get_categoria_display()}.')
        except Exception as e:
            # Capturar cualquier error inesperado de DB o modelo
            messages.error(request, f'Error inesperado al guardar el movimiento. Por favor, intente de nuevo. Detalle: {e}')
        
        # **Redirección Correcta (Problema 2 - Redirección)**
        # Redirecciona a la página con el slug correcto ('condominio' o 'basura')
        return redirect('ver_finanzas', categoria_slug=categoria_slug)


    # =========================================================================
    # LÓGICA DE MANEJO DE GET (LISTADO Y FILTROS)
    # =========================================================================

    # 2. Obtener opciones de filtro (Todas las Torres)
    torres = Tower.objects.all().order_by('nombre')
    
    # 3. Aplicar filtros iniciales y ordenar
    # --- CORRECCIÓN 1: Usar select_related('tower') para optimizar la consulta y cargar el objeto 'tower' ---
    # Nota: El código original usaba 'torre', lo ajusto a 'tower' para seguir la convención del modelo.
    movimientos_query = MovimientoFinanciero.objects.filter(categoria=categoria_filtro).select_related('tower').order_by('fecha', 'id')

    # Filtro por tipo (Ingreso, Egreso, Ambos)
    tipo_filtro = request.GET.get('tipo', 'AMBOS')
    if tipo_filtro == 'INGRESOS':
        movimientos_query = movimientos_query.filter(tipo='ING')
    elif tipo_filtro == 'EGRESOS':
        movimientos_query = movimientos_query.filter(tipo='EGR')

    # Filtro por torre 
    torre_id = request.GET.get('torre')
    if torre_id and torre_id.isdigit(): 
        movimientos_query = movimientos_query.filter(tower__id=int(torre_id))

    # -----------------------------------------------------------
    # ⚠️ AÑADIR NUEVO FILTRO POR RANGO DE FECHAS (Aquí están los cambios)
    # -----------------------------------------------------------
    filtro_form = FormularioFiltroMovimientos(request.GET)
    
    if filtro_form.is_valid():
        fecha_inicio = filtro_form.cleaned_data.get('fecha_inicio')
        fecha_fin = filtro_form.cleaned_data.get('fecha_fin')
        
        if fecha_inicio:
            # Filtrar movimientos donde la fecha es MAYOR O IGUAL a la fecha de inicio
            movimientos_query = movimientos_query.filter(fecha__gte=fecha_inicio)
            
        if fecha_fin:
            # Filtrar movimientos donde la fecha es MENOR O IGUAL a la fecha de fin
            movimientos_query = movimientos_query.filter(fecha__lte=fecha_fin)
        
    # 4. Cálculo del Saldo Acumulado
    movimientos_con_saldo = []
    saldo_acumulado = 0
    
    for mov in movimientos_query:
        # --- CORRECCIÓN 2 (Del turno anterior): Obtener el monto correcto del objeto ---
        monto = getattr(mov, monto_field)
        
        # Inicializar ingreso/egreso para el diccionario final
        ingreso_monto = None
        egreso_monto = None

        # Sumar o restar al saldo acumulado
        if mov.tipo == 'ING':
            saldo_acumulado += monto
            ingreso_monto = monto
        elif mov.tipo == 'EGR': # EGR
            saldo_acumulado -= monto
            egreso_monto = monto
            
        # --- CORRECCIÓN 3: Manejar el AttributeError para 'tower' ---
        # 1. Comprueba si el atributo 'tower' existe en el objeto (hasattr).
        # 2. Si existe y tiene un valor (es decir, no es None), usa el nombre de la torre.
        # 3. Si no existe o es None, usa 'General'.
        if hasattr(mov, 'tower') and mov.tower:
            nombre_torre = mov.tower.nombre
        else:
            nombre_torre = 'General'
            
        # Preparar los datos para la plantilla
        movimientos_con_saldo.append({
            'fecha': mov.fecha,
            'descripcion': mov.descripcion,
            'tasa_bcv': mov.tasa_bcv,
            # Mostrar solo el monto en la columna correcta 
            'ingreso': ingreso_monto if ingreso_monto and ingreso_monto > 0 else None, 
            'egreso': egreso_monto if egreso_monto and egreso_monto > 0 else None,
            'torre': nombre_torre, # Usar la variable segura
            'saldo': round(saldo_acumulado, 2), # Redondear a dos decimales
        })
        
    context = {
        'titulo': titulo,
        'movimientos': movimientos_con_saldo,
        'torres': torres,
        'tipo_seleccionado': tipo_filtro,
        'torre_seleccionada_id': torre_id,
        'categoria_slug': categoria_slug, # Para el botón de descarga
        'filtro_form': filtro_form, # Formulario de filtro para la plantilla
    }

    return render(request, 'finanzas/listado_movimientos.html', context)

def descargar_pdf(request, categoria_slug):
    """
    Genera y descarga el archivo PDF con la información financiera filtrada.
    """
    # 1. Definir la categoría, título y campo de monto (monto_field)
    if categoria_slug == 'condominio':
        categoria_filtro = 'CON'
        titulo = 'Reporte Financiero - Condominio'
        monto_field = 'monto_condominio' 
    elif categoria_slug == 'basura':
        categoria_filtro = 'BAS'
        titulo = 'Reporte Financiero - Cuarto de Basura'
        monto_field = 'monto_basura'
    else:
        # Redireccionar si el slug es inválido
        return redirect('url_dashboard')

    # 2. Obtener QuerySet Base
    movimientos_query = MovimientoFinanciero.objects.filter(categoria=categoria_filtro).select_related('tower').order_by('fecha', 'id')

    # 3. FILTROS POR TIPO Y TORRE (Lógica existente)
    tipo_filtro = request.GET.get('tipo', 'AMBOS')
    if tipo_filtro == 'INGRESOS':
        movimientos_query = movimientos_query.filter(tipo='ING')
    elif tipo_filtro == 'EGRESOS':
        movimientos_query = movimientos_query.filter(tipo='EGR')

    torre_id = request.GET.get('torre')
    if torre_id and torre_id.isdigit(): 
        movimientos_query = movimientos_query.filter(tower__id=int(torre_id))
    
    # 4. 🚀 APLICAR FILTRO POR RANGO DE FECHAS (NUEVO)
    filtro_form = FormularioFiltroMovimientos(request.GET)
    
    if filtro_form.is_valid():
        fecha_inicio = filtro_form.cleaned_data.get('fecha_inicio')
        fecha_fin = filtro_form.cleaned_data.get('fecha_fin')
        
        if fecha_inicio:
            # Filtrar movimientos donde la fecha es MAYOR O IGUAL a la fecha de inicio
            movimientos_query = movimientos_query.filter(fecha__gte=fecha_inicio)
            
        if fecha_fin:
            # Filtrar movimientos donde la fecha es MENOR O IGUAL a la fecha de fin
            movimientos_query = movimientos_query.filter(fecha__lte=fecha_fin)
            
    # --- FIN Lógica de Filtrado ---

    # 5. Configuración de la Respuesta HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=\"Reporte_{categoria_slug}_{timezone.now().strftime("%Y%m%d")}.pdf\"'

    # 6. Preparación del documento PDF con SimpleDocTemplate
    doc = SimpleDocTemplate(response, pagesize=letter, topMargin=inch/2, bottomMargin=inch/2, leftMargin=inch/2, rightMargin=inch/2)
    styles = getSampleStyleSheet()
    Story = []
    
    # --- 7. Encabezado del Reporte ---
    Story.append(Paragraph(f'<font size="16"><b>{titulo}</b></font>', styles['h1']))
    Story.append(Paragraph(f'<font size="10">Generado el: {timezone.now().strftime("%d/%m/%Y a las %H:%M")}</font>', styles['Normal']))
    Story.append(Paragraph('<br/>', styles['Normal']))
    
    # Info de Filtros (para mostrar qué se filtró)
    filtro_info_text = f"<b>Tipo:</b> {tipo_filtro} | <b>Torre ID:</b> {torre_id if torre_id else 'Todas'}"
    
    # Detalle de Fechas
    f_i = filtro_form.cleaned_data.get('fecha_inicio')
    f_f = filtro_form.cleaned_data.get('fecha_fin')
    
    fecha_text = "Todo el Historial"
    if f_i or f_f:
        inicio_str = f_i.strftime('%d/%m/%Y') if f_i else 'Inicio'
        fin_str = f_f.strftime('%d/%m/%Y') if f_f else 'Fin'
        fecha_text = f"{inicio_str} hasta {fin_str}"
        
    filtro_info_text += f" | <b>Rango de Fechas:</b> {fecha_text}"

    Story.append(Paragraph(f'<font size="10">{filtro_info_text}</font>', styles['Normal']))
    Story.append(Paragraph('<br/>', styles['Normal']))
    
    # --- 8. Preparación de la Tabla de Datos ---
    
    # Cabecera de la tabla
    data = [
        ['Fecha', 'Descripción', 'Torre', 'Tasa BCV', 'Ingreso (Bs.)', 'Egreso (Bs.)', 'Saldo Acumulado (Bs.)']
    ]

    # Inicializar Saldo Acumulado (Decimal para precisión)
    saldo_acumulado = Decimal(0.00)
    
    for mov in movimientos_query:
        # ✅ USO DE monto_field para acceder al campo correcto (condominio o basura)
        monto = getattr(mov, monto_field) 
        
        ingreso = ''
        egreso = ''
        
        if mov.tipo == 'ING':
            saldo_acumulado += monto
            ingreso = f"{monto:,.2f}" # Formato de moneda
        elif mov.tipo == 'EGR':
            saldo_acumulado -= monto
            egreso = f"({monto:,.2f})" # Usamos paréntesis para egresos
            
        nombre_torre = mov.tower.nombre if mov.tower else 'General'
        tasa_bcv_str = f"{mov.tasa_bcv:,.2f}"

        data.append([
            mov.fecha.strftime('%d/%m/%Y'),
            mov.descripcion,
            nombre_torre,
            tasa_bcv_str,
            ingreso,
            egreso,
            f"{saldo_acumulado:,.2f}", 
        ])
        
    # --- 9. Creación y Estilo de la Tabla ---
    
    # Anchos de columna
    table_col_widths = [1.0*inch, 2.5*inch, 0.7*inch, 0.7*inch, 1.0*inch, 1.0*inch, 1.4*inch]
    
    table = Table(data, colWidths=table_col_widths)
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')), 
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (3, -1), 'LEFT'), 
        ('ALIGN', (4, 1), (-1, -1), 'RIGHT'), # Alineación derecha para montos y saldo
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7f7f7')), 
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    
    Story.append(table)

    # --- 10. Saldo Total Final ---
    Story.append(Paragraph('<br/><br/>', styles['Normal']))
    Story.append(Paragraph(f'<font size="14"><b>SALDO FINAL CALCULADO: Bs. {saldo_acumulado:,.2f}</b></font>', styles['h2']))

    # 11. Construir el PDF
    doc.build(Story)
    return response