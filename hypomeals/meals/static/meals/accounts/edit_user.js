$(function() {
    $("[data-toggle=tooltip]").tooltip();
    let form = $("#editUserForm");
    $("#nextButton").click(function() {
        form.submit();
    });
});
