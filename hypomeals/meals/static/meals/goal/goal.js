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
        $(".selectGoalCheckboxes:visible")
            .prop("checked", ($(this).prop("checked")))
            .trigger("change");
    });

    $("#showHelpButton").click(function() {
        $("#helpDiv").toggle("fast");
    });

    function toggleGoal(enabled) {
        enabled = Boolean(enabled);
        let selectedGoals = $(".selectGoalCheckboxes:visible:checked").toArray()
            .map(cb => $(cb).attr("data-goal-id"));
        if (selectedGoals.length === 0) {
            makeModalAlert(
                `Cannot ${enabled ? 'Enable' : 'Disable'}`,
                "You must select at least one goal from " +
                `the table below before ${enabled ? 'enabling' : 'disabling'} them`);
            return;
        }
        let urlId = `#${enabled ? 'enable' : 'disable'}GoalsUrl`;
        let url = new URL($(urlId).attr("href"), window.location.href);
        $.getJSON(url, {g: selectedGoals})
            .done(function(data, textStatus) {
                if (!showNetworkError(data, textStatus)) {
                    return;
                }
                if ("error" in data && data.error) {
                    makeModalAlert("Error", data.error);
                    return;
                }
                if ("resp" in data && data.resp) {
                    makeModalAlert("Success", data.resp);
                }
            });
    }


});