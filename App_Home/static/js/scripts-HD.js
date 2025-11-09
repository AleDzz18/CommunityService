function toggleDropdown() {
    var content = document.getElementById("adminDropdownContent");
    var btn = document.getElementById("adminDropdownBtn");
    
    // 1. Cierra todos los dropdowns abiertos primero y remueve el estado 'active' del botón
    document.querySelectorAll('.dropdown-content.show').forEach(function(el) {
        if (el !== content) {
            el.classList.remove('show');
            el.style.height = '0'; // Cierra con animación
            // Busca el botón asociado para remover la clase 'active'
            const parentDropdown = el.closest('.dropdown');
            if (parentDropdown) {
                const associatedBtn = parentDropdown.querySelector('.dropbtn');
                if (associatedBtn) {
                    associatedBtn.classList.remove('active');
                }
            }
        }
    });

    // 2. Toggle del dropdown actual
    if (content.classList.contains('show')) {
        // Ocultar: Remueve las clases y pone la altura a 0
        content.classList.remove('show');
        content.style.height = '0';
        btn.classList.remove('active');
    } else {
        // Mostrar: Añade clases, calcula la altura y activa el botón
        content.classList.add('show');
        // Calcula la altura para que la animación funcione correctamente
        content.style.height = content.scrollHeight + 'px'; 
        btn.classList.add('active');
    }
}

// Opcional: Cerrar el menú si se hace clic fuera de él
window.onclick = function(event) {
    // CAMBIO: Se asegura que si se hace clic fuera, todos los dropdowns se cierren
    if (!event.target.matches('.dropbtn') && !event.target.matches('.dropbtn i')) {
        document.querySelectorAll('.dropdown-content.show').forEach(function(content) {
            content.classList.remove("show");
            content.style.height = '0';
            
            // Busca el botón asociado para remover la clase 'active'
            const parentDropdown = content.closest('.dropdown');
            if (parentDropdown) {
                const associatedBtn = parentDropdown.querySelector('.dropbtn');
                if (associatedBtn) {
                    associatedBtn.classList.remove('active');
                }
            }
        });
    }
}