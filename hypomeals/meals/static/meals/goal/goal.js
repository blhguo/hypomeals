$(function() {
    $("[data-toggle='tooltip']").tooltip();
    $(".downloadCalculationsHeader").tooltip({
        placement: "left",
        title: "Download the calculated ingredients results to be sent to " +
            "manufacturers."
    });
    $(".downloadGoalHeader").tooltip({
        placement: "left",
        title: "Download the goal itself for your reference in the future."
    });
    $(".mfgScheduleTooltips").tooltip({
        placement: "bottom",
        title: "A manufacturing schedule is a combination of one or more goals " +
            "scheduled to begin production on different manufacturing lines."
    });

    $("#showAllCheckbox").change(function() {
        $(".ownerCol").toggle($(this).prop("checked"));
        $(".ownedRows").toggle($(this).prop("checked"));
    }).trigger("change");

    $("#selectAllCheckbox").change(function() {
        $("tbody tr:visible input[type=checkbox]")
            .prop("checked", ($(this).prop("checked")));
    });
});