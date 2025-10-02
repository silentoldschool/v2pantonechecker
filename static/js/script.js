let token = "";
let role = "";

function login() {
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
    }).then(res => res.json())
      .then(data => {
        if(data.token){
            token = data.token;
            role = data.role;
            document.getElementById("loginDiv").style.display = "none";
            document.getElementById("mainDiv").style.display = "block";
            fetchColors();
        } else {
            alert("Login fehlgeschlagen");
        }
    });
}

function fetchColors() {
    fetch("/colorchecks", {
        headers: { "Authorization": "Token " + token }
    }).then(res => res.json())
      .then(data => {
        const table = document.getElementById("colorTable");
        table.innerHTML = "<tr><th>Pantone</th><th>Hex</th><th>Points</th><th>Status</th><th>Alt Farbe</th></tr>";
        data.forEach(c => {
            const row = table.insertRow();
            row.insertCell(0).innerText = c.pantone;
            row.insertCell(1).innerHTML = `<div style="width:30px;height:20px;background:${c.hex_color || '#fff'};"></div>`;
            row.insertCell(2).innerText = c.points.join(", ");
            row.insertCell(3).innerText = c.status;
            row.insertCell(4).innerText = c.alt_color || "";
        });
    });
}

function sendRequest() {
    const pantone = document.getElementById("pantoneInput").value;
    const checkboxes = document.querySelectorAll("input[type=checkbox]:checked");
    const points = Array.from(checkboxes).map(c => c.value);

    fetch("/colorchecks/request", {
        method: "POST",
        headers: { 
            "Content-Type": "application/json",
            "Authorization": "Token " + token
        },
        body: JSON.stringify({ pantone, points, user_id: 1 })
    }).then(res => res.json())
      .then(data => {
        alert("Anfrage gesendet!");
        fetchColors();
    });
}
