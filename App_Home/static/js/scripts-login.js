const container = document.querySelector(".container");
const registerBtn = document.querySelector(".register-btn");
const loginBtn = document.querySelector(".login-btn");

registerBtn.addEventListener("click", () => {
    container.classList.add("active");
});

loginBtn.addEventListener("click", () => {
    container.classList.remove("active");
});

// --- CÓDIGO DE DESAPARICIÓN ---

document.addEventListener('DOMContentLoaded', function() {
    // Selecciona todos los mensajes de alerta dentro del contenedor
    const alerts = document.querySelectorAll('.message-container .alert');
    const DURATION = 7000; // 7 segundos para que el mensaje desaparezca
    
    // *** LÍNEA DE DEBUGGING: Abrir Consola (F12) para confirmar que se ejecuta. ***
    console.log(`[DEBUG] Alertas encontradas: ${alerts.length}`);
    // *************************************************************************

    if (alerts.length > 0) {
        alerts.forEach(alert => {
            // 1. Inicia el temporizador de desaparición (5 segundos)
            setTimeout(() => {
                // Añade la clase 'hide' para iniciar la transición CSS (opacidad y desplazamiento)
                alert.classList.add('hide');

                // 2. Opcional: Elimina el elemento del DOM después de que termine la transición
                // El tiempo (500ms) debe ser igual a la duración de la transición en styles-login.css
                setTimeout(() => {
                    alert.remove();
                }, 500); 
            }, DURATION); 
        });
    }
});