document.addEventListener('DOMContentLoaded', function() {
    const widget = document.getElementById('bus-schedule-widget');
    const toggleBtn = document.getElementById('bus-widget-toggle');
    const closeBtn = document.getElementById('bus-widget-close');
    const widgetContent = document.getElementById('bus-widget-content');
    
    // Vérifier si l'utilisateur a déjà vu le widget aujourd'hui
    const today = new Date().toDateString();
    const lastSeen = localStorage.getItem('busWidgetLastSeen');
    
    // Si c'est la première visite de la journée, montrer l'animation
    if (lastSeen !== today) {
        toggleBtn.classList.add('pulse');
        localStorage.setItem('busWidgetLastSeen', today);
    }
    
    // Basculer l'affichage du widget
    function toggleWidget() {
        widgetContent.classList.toggle('show');
        toggleBtn.classList.remove('pulse');
    }
    
    // Fermer le widget
    function closeWidget() {
        widgetContent.classList.remove('show');
    }
    
    // Événements
    toggleBtn.addEventListener('click', toggleWidget);
    closeBtn.addEventListener('click', closeWidget);
    
    // Fermer le widget en cliquant à l'extérieur
    document.addEventListener('click', function(event) {
        if (!widget.contains(event.target)) {
            closeWidget();
        }
    });
    
    // Empêcher la propagation des clics à l'intérieur du widget
    widgetContent.addEventListener('click', function(event) {
        event.stopPropagation();
    });
    
    // Mettre à jour le jour actif dans l'interface
    function updateActiveDay() {
        const days = document.querySelectorAll('.schedule-day');
        const now = new Date();
        const currentDay = now.getDate();
        const currentMonth = now.getMonth();
        
        // Supprimer la classe active de tous les jours
        days.forEach(day => day.classList.remove('active'));
        
        // Vérifier la date actuelle par rapport aux jours du festival
        const festivalDates = [25, 26, 27, 28]; // 25-28 juillet
        const festivalMonth = 6; // Juillet (0-indexé)
        
        if (currentMonth === festivalMonth && festivalDates.includes(currentDay)) {
            // Si nous sommes pendant le festival, mettre en surbrillance le jour actuel
            const dayIndex = festivalDates.indexOf(currentDay);
            if (dayIndex !== -1) {
                days[dayIndex].classList.add('active');
                // Faire défiler jusqu'au jour actuel
                days[dayIndex].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        } else if (currentMonth < festivalMonth || (currentMonth === festivalMonth && currentDay < 25)) {
            // Si c'est avant le festival, mettre en surbrillance le premier jour
            days[0].classList.add('active');
        } else {
            // Si c'est après le festival, mettre en surbrillance le dernier jour
            days[days.length - 1].classList.add('active');
        }
    }
    
    // Mettre à jour le jour actif au chargement
    updateActiveDay();
    
    // Mettre à jour toutes les heures pour refléter l'heure actuelle
    function updateCurrentTime() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('fr-BE', { hour: '2-digit', minute: '2-digit' });
        document.querySelectorAll('.current-time').forEach(el => {
            el.textContent = timeString;
        });
    }
    
    // Mettre à jour l'heure toutes les minutes
    updateCurrentTime();
    setInterval(updateCurrentTime, 60000);
});
