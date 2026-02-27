// Admin Login JS (Safe Version - No Fetch, No Storage)

document.addEventListener("DOMContentLoaded", () => {

    const form = document.getElementById("loginForm");

    if (!form) return;

    form.addEventListener("submit", () => {

        const btn = form.querySelector("button");

        if (btn) {
            btn.disabled = true;
            btn.innerText = "Logging in...";
        }

    });

});
