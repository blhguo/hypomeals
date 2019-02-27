$(function() {
    let selectAllCheckbox = $("#selectAllCheckbox");
    Mousetrap.bind(["command+a", "ctrl+a"], function(e) {
        e.preventDefault();
        selectAllCheckbox.prop("checked",
            !selectAllCheckbox.prop("checked")).trigger("change");
    });

    Mousetrap.bind(["command+e", "ctrl+e"], function(e) {
        e.preventDefault();
        $("#enableGoalsButton").trigger("click");
    });

    Mousetrap.bind(["command+d", "ctrl+d"], function(e) {
        e.preventDefault();
        $("#disableGoalsButton").trigger("click");
    });

    Mousetrap.bind("n", function(e) {
        e.preventDefault();
        console.log("n");
        window.location.href = $("#addGoalButton").attr("href");
    });

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

    selectAllCheckbox.change(function() {
        $(".selectGoalCheckboxes:visible")
            .prop("checked", ($(this).prop("checked")))
            .trigger("change");
    });

    $("#enableGoalsButton").click(_.partial(toggleGoal, true));
    $("#disableGoalsButton").click(_.partial(toggleGoal, false));

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
                `the table below before ${enabled ? 'enabling' : 'disabling'} them.`);
            return;
        }
        let urlId = `#${enabled ? 'enable' : 'disable'}GoalsUrl`;
        let url = new URL($(urlId).attr("href"), window.location.href);
        console.log(selectedGoals);
        $.getJSON(url, {g: JSON.stringify(selectedGoals)})
            .done(function(data, textStatus) {
                if (!showNetworkError(data, textStatus)) {
                    return;
                }
                if ("error" in data && data.error) {
                    makeModalAlert("Error", data.error);
                    return;
                }
                if ("resp" in data && data.resp) {
                    makeModalAlert("Success",
                        data.resp,
                        null,
                        () => $("#goalFilterForm").submit());
                }
            });
    }
});