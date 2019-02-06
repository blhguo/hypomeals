$(function() {
    let confirmOverwriteButton = $("#confirmOverwriteButton");
    let confirmOverwriteCheckbox = $("#confirmOverwrite");

    confirmOverwriteButton.click(function() {
        if (!confirmOverwriteCheckbox.prop("checked")) {
            alert("You must check the box above before clicking this button.");
            return false;
        }
        return true;
    })
});