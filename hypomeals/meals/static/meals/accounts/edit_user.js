$(function() {
    $("[data-toggle=tooltip]").tooltip();

    $("#showPermMatrix").click(function() {
        let table = $("#permMatrixTable").clone();
        makeModalAlert("Permission Matrix", table)
            .find(".modal-dialog").addClass("modal-lg")
    });
    function togglePlMCheckbox() {
        let plmCheckbox = $("#id_is_plant_manager");
        plmCheckbox.prop("checked", ($("#id_lines").val().length > 0));
    }
    $("#id_lines").change(togglePlMCheckbox).on("keyup", togglePlMCheckbox);
});
