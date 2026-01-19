/*!
* Start Bootstrap - Simple Sidebar v6.0.6 (https://startbootstrap.com/template/simple-sidebar)
* Copyright 2013-2023 Start Bootstrap
* Licensed under MIT (https://github.com/StartBootstrap/startbootstrap-simple-sidebar/blob/master/LICENSE)
*/
// 
// Scripts
// 

window.addEventListener('DOMContentLoaded', event => {

    // Toggle the side navigation
    const sidebarToggle = document.body.querySelector('#sidebarToggle');
    if (sidebarToggle) {
        // Uncomment Below to persist sidebar toggle between refreshes
        // if (localStorage.getItem('sb|sidebar-toggle') === 'true') {
        //     document.body.classList.toggle('sb-sidenav-toggled');
        // }
        sidebarToggle.addEventListener('click', event => {
            event.preventDefault();
            document.body.classList.toggle('sb-sidenav-toggled');
            localStorage.setItem('sb|sidebar-toggle', document.body.classList.contains('sb-sidenav-toggled'));
        });
    }

});



document.addEventListener("DOMContentLoaded", function() {
    const form = document.getElementById("carComparisonForm");
    form.addEventListener("submit", function(e) {
        e.preventDefault(); // Prevent default form submission

        const formData = new FormData(form);
        const data = new URLSearchParams(formData).toString();

        fetch(`/api/car-compare?${data}`, {
            method: 'GET', // Or 'POST', depending on your API endpoint
        })
        .then(response => response.json())
        .then(data => {
            console.log(data); // Process and display the response
            // For example, display the results in a <div> or alert
        })
        .catch(error => console.error('Error:', error));
    });
});
