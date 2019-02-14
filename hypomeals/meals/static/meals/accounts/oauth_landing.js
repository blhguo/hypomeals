let ssoUrl;
let loginUrl;

$(function() {
    ssoUrl = $("#ssoUrl").attr("href");
    loginUrl = $("#loginUrl").attr("href");
    oauth_fix();
});

function oauth_fix() {
    $.post(window.location.pathname, {
        fragment: window.location.hash,
        csrfmiddlewaretoken: $("input[name=csrfmiddlewaretoken]").val()
    }, function(data, textStatus) {
        if (!showNetworkError(data, textStatus)) {
            return false;
        }
        if ("error" in data && data.error) {
            makeModalAlert("Error", data.error, null, function() {
                window.location.href = loginUrl;
            })
        } else if ("resp" in data) {
            window.location.href = data.resp;
        }
    });
}