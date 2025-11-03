function toggleDropdown() {
    const dropdownContent = document.getElementById("adminDropdownContent");
    
    // Verifica si el menú está actualmente visible (tiene la clase 'show')
    if (dropdownContent.classList.contains("show")) {
        // Si está visible, lo oculta
        dropdownContent.classList.remove("show");
    } else {
        // Si está oculto, lo muestra
        dropdownContent.classList.add("show");
    }
}

// Opcional: Cerrar el menú si se hace clic fuera de él
window.onclick = function(event) {
    if (!event.target.matches('.dropbtn') && !event.target.matches('.dropbtn i')) {
        const dropdownContent = document.getElementById("adminDropdownContent");
        if (dropdownContent.classList.contains("show")) {
            dropdownContent.classList.remove("show");
        }
    }
}