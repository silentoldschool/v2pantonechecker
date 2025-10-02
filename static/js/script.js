const API_TOKEN = localStorage.getItem("api_token");
if(!API_TOKEN && !window.location.href.includes("login.html")){
    window.location.href="login.html";
}

async function fetchColors(){
    try{
        const res = await fetch("/colorchecks", {
            headers:{'X-API-TOKEN': API_TOKEN}
        });
        const data = await res.json();
        const tbody = document.querySelector("#colorTable tbody");
        tbody.innerHTML="";
        data.forEach(c=>{
            const tr = document.createElement("tr");
            const points = (c.points||[]).join(", ");
            const colorBox = `<span class="color-field" style="background:${c.hex_color||'#fff'}"></span>`;
            tr.innerHTML = `<td>${c.id}</td><td>${c.pantone}</td><td>${colorBox}</td><td>${c.status}</td><td>${points}</td><td>${c.alternative_hex||''}</td>`;
            tbody.appendChild(tr);
        });
    }catch(e){
        console.error(e);
    }
}

async function sendRequest(){
    const pantone = document.getElementById("pantone").value;
    const points = [];
    if(document.getElementById("point1").checked) points.push("Testliner weiß Coated");
    if(document.getElementById("point2").checked) points.push("Testliner braun");
    if(document.getElementById("point3").checked) points.push("Kraftliner braun");

    const res = await fetch("/colorchecks/request", {
        method:"POST",
        headers:{'Content-Type':'application/json','X-API-TOKEN': API_TOKEN},
        body: JSON.stringify({pantone, points})
    });
    const data = await res.json();
    const msg = document.getElementById("request-msg");
    if(res.ok){
        msg.innerText = "Farbe angefragt! ID: " + data.id;
        fetchColors();
    } else {
        msg.innerText = "Fehler: "+(data.error||"");
    }
}

function logout(){
    localStorage.removeItem("api_token");
    window.location.href="login.html";
}

fetchColors();
