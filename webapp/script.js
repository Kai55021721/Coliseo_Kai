document.addEventListener("DOMContentLoaded", function() {
    // Inicializa la Web App de Telegram
    const tg = window.Telegram.WebApp;
    tg.ready();

    const form = document.getElementById("inscription-form");

    form.addEventListener("submit", function(event) {
        event.preventDefault();

        const characterName = document.getElementById("character_name").value;
        const specialty = document.getElementById("specialty").value;

        if (characterName && specialty) {
            // Empaqueta los datos en un objeto JSON
            const data = {
                character_name: characterName,
                specialty: specialty
            };

            // Envía los datos al bot de Telegram
            tg.sendData(JSON.stringify(data));
            
            // Cierra la Web App
            tg.close();
        }
    });
});