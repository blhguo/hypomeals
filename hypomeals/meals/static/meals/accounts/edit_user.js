$(function() {
    $("[data-toggle=tooltip]").tooltip();

    $("#showPermMatrix").click(function() {
        let table = $("#permMatrixTable").clone();
        makeModalAlert("Permission Matrix", table)
            .find(".modal-dialog").addClass("modal-lg")
    })
});
