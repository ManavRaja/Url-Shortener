let afterSubmit = document.getElementById("after-submit")
afterSubmit.hidden = true
let form = document.getElementById('url-form')
let redirectUrl = document.getElementById("redirect-url")
let path = document.getElementById("path")

form.onsubmit = async function (event) {
    event.preventDefault();

    let response = await fetch("https://<YOUR_DOMAIN>/add-url", {
        method: "post",
        body: new FormData(form),
        headers: {"csrf-token": ""}
    })
    let json_response = await response.json()
    if (response.ok === true) {
        form.hidden = true
        afterSubmit.hidden = false
        form.reset()
        redirectUrl.value = json_response.redirect_url
        path.value = "<YOUR_DOMAIN>/" + json_response.path

    } else if (json_response.detail === "Not a valid url.")  {
        alert("Please input a valid Url.")
    } else if (json_response.detail === "Path already in use.") {
        alert("That alias is already in use. Please try another one.")
    } else if (response.status === 422) {
        alert("Please fill out both parts before submitting.")
    }

}