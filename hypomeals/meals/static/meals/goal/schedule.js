const IGNORE_SENDER_ID = 1;
const WORK_HOURS_PER_DAY = 10;  // TODO: Get this from HTML
const WORK_HOURS_START = 8;
const WORK_HOURS_END = 18;
const SECONDS_PER_HOUR = 3600;
const MILLISECONDS_PER_HOUR = SECONDS_PER_HOUR * 1000;

var timeline = null;
var items = null;
var groups = null;
var goalItemsMap = null;

$(function() {
    let completionTimeUrl = $("#completionTimeUrl").attr("href");
    $("[data-toggle='tooltip']").tooltip();
    $("#showHelpButton").click(function() {
        $("#helpDiv").toggle("fast");
    });

    goalItemsMap = new Map();
    let mfgLines = new Set();
    $(".goalItems[data-schedulable=true]").each((i, item) => {
        item = $(item);
        let goalItemId = Number(item.attr("data-goal-item-id"));
        let lines = item.attr("data-lines").split(",");
        goalItemsMap.set(goalItemId, {
            name: `${item.text().trim()}`,
            hours: Number(item.attr("data-hours")),
            lines: lines,
            skuId: Number(item.attr("data-sku-id")),
            goalId: Number(item.attr("data-goal-id")),
            goalItemId: goalItemId,
            deadline: moment(item.attr("data-goal-deadline")).hours(WORK_HOURS_END),
        });
        lines.forEach((l) => mfgLines.add(l));
    }).on("dragstart", function(event) {
        let src = $(this);
        let goalItemId = Number(src.attr("data-goal-item-id"));
        let goalItem = goalItemsMap.get(goalItemId);
        let item = {
            id: goalItemId,
            content: goalItem.name,
            type: "range"
        };
        event.originalEvent.dataTransfer.effectAllowed = "move";
        event.originalEvent.dataTransfer.setData("text", JSON.stringify(item));
        highlightGroups(goalItem.lines, true);
    }).on("click", function() {
        let goalItemId = Number($(this).attr("data-goal-item-id"));
        if (items.get(goalItemId) !== null) {
            timeline.focus(goalItemId);
        }
    });
    $(document).on("dragend", function() {
        highlightGroups("*", false);
    });

    console.log(goalItemsMap);
    console.log(mfgLines);

    groups = new vis.DataSet([]);
    mfgLines.forEach((l) => {
        groups.add({
            id: l,
            content: l,
            visible: true,
        })
    });
    groups.add({
        id: "DT3",
        content: "DT3",
        visible: true,
    });

    console.log(groups);
    items = new vis.DataSet([]);

    items.on("update", function(event, properties, senderId) {
        if (senderId === IGNORE_SENDER_ID) return;
        let item = properties.data[0];
        let itemInfo = goalItemsMap.get(item.id);
        if (!itemInfo.lines.includes(item.group)) {
            makeModalAlert("Cannot Schedule",
                `Manufacturing Line '${item.group}' cannot produce SKU #${itemInfo.skuId}.
                Operation will be reverted.`);
            items.update(properties.oldData[0]);
            return;
        }
        if ("start" in item) {
            try {
                adjustEnd(item, item.start, true);
            } catch (e) {
                makeModalAlert("Error",
                    `Production overlaps on Manufacturing Line '${item.group}'.
                    Operation will be reverted.`,
                    null,
                    function() {
                    items.update(properties.oldData[0], IGNORE_SENDER_ID);
                });
            }
        }
    });
    items.on("add", function(event, properties, senderId) {
        let item = items.get(properties.items[0]);
        let itemInfo = goalItemsMap.get(item.id);
        if (!itemInfo.lines.includes(item.group)) {
            makeModalAlert("Cannot Schedule",
                `Manufacturing Line '${item.group}' cannot produce SKU #${itemInfo.skuId}.
                This item has been removed.`);
            items.remove({id: item.id});
            return false;
        }
        toggleGoalItem(item.id, true);
        if ("start" in item) {
            try {
                adjustEnd(item, item.start, !item.suppressWarning);
            } catch (e) {
                makeModalAlert("Error",
                    `Production overlaps on Manufacturing Line '${item.group}'.
                    This item will be removed.`,
                    null,
                    function () {items.remove({id: item.id});});
            }
        }
    });
    items.on("remove", function(event, properties, senderId) {
        toggleGoalItem(properties.items[0], false);
    });

    function highlightGroups(groupIds, highlighted) {
        if (groupIds === "*") {
            groupIds = groups.distinct("id");
        }
        let updates = [];
        let className = highlighted ? "bg-success text-white" : "1";
        for (let group of groupIds) {
            updates.push({id: group, className: className});
        }
        groups.update(updates);
    }

    function checkOverlap(item) {
        let itemsInGroup = items.get({
            filter: (i) => i.group === item.group,
            returnType: "Array",
        });
        if (itemsInGroup.length === 1) return false;
        itemsInGroup.sort(function(a, b) {
            return moment(a.start) - moment(b.start);
        });
        for (let i = 0; i < itemsInGroup.length - 1; i++) {
            if (moment(itemsInGroup[i + 1].start) < moment(itemsInGroup[i].end)) {
                return true;
            }
        }
        return false;
    }

    function adjustEnd(item, start, showWarning) {
        let itemId = item.id;
        start = moment(start);
        let itemInfo = goalItemsMap.get(itemId);
        let end = getCompletionTime(start, itemInfo.hours);
        let updates = {id: itemId, start: start, end: end, type: "range"};
        if (end > itemInfo.deadline) {
            console.log(`Item ${itemId} will exceed deadline`);
            updates["className"] = "bg-danger text-white";
            updates["title"] = `Start: ${start.format("lll")}.
            Warning: item exceeds deadline ${itemInfo.deadline.format("lll")}`;
            if (showWarning) {
                makeModalAlert("Warning",
                    `Scheduling this item to start at \
                ${start.format("lll")} will exceed predetermined \
                deadline of ${itemInfo.deadline.format("lll")} in the goal.
                Consider moving this item earlier.`);
            }
        } else {
            updates["className"] = "";
            updates["title"] = `Start: ${start.format("lll")}`;
        }
        items.update(updates, IGNORE_SENDER_ID);
        if (checkOverlap(item)) {
            throw "Overlap detected!";
        }
    }

    function toggleGoalItem(goalItemId, scheduled) {
        $(`a[data-goal-item-id=${goalItemId}]`)
            .toggleClass("text-muted", scheduled);
    }

    function getCompletionTime(startTime, hours) {
        startTime = moment(startTime);
        let endTime = startTime.clone();
        let numDays = Math.floor(hours / WORK_HOURS_PER_DAY);
        let remainingHours = hours % WORK_HOURS_PER_DAY;
        if (remainingHours === 0) {
            numDays--;
            remainingHours = WORK_HOURS_PER_DAY;
        }
        if (startTime.hour() >= WORK_HOURS_START && startTime.hour() <= WORK_HOURS_END) {
            let startOfDay = startTime.clone().startOf("day").hours(WORK_HOURS_START);
            remainingHours -= startTime.diff(startOfDay) / MILLISECONDS_PER_HOUR;
        }
        endTime.add(numDays, "days");
        if (remainingHours > 0) {
            endTime.add(1, "days").hours(WORK_HOURS_START).add(remainingHours, "hours");
        } else {
            endTime.startOf("day").hours(WORK_HOURS_END).add(remainingHours, "hours");
        }

        console.log("start: ", startTime.format(), "end: ", endTime.format());
        return endTime;
    }

    timeline = new vis.Timeline($("#timelineDiv")[0], items, groups, {
        editable: true,
        zoomable: true,
        start: moment().add(-3, "days"),
        end: moment().add(4, "days"),
        tooltipOnItemUpdateTime: true,
        onAdd: function(item, callback) {
            if (!goalItemsMap.has(item.id)) {
                makeModalAlert("Cannot Schedule",
                    "Invalid item detected. Double-clicking to create " +
                    "new item has been disabled.");
                callback(null);
            } else {
                if (items.get(item.id) !== null) {
                    makeModalAlert("Cannot Schedule",
                        "This item has already been scheduled.");
                    callback(null);
                    return;
                }
                callback(item);
            }
        },
    });

    $(".vis-timeline").css("visibility", "visible");


    /****************** Sync with Form **********************/
    let form = $("form");
    form.find("div[data-is-scheduled=true]").each(function(i, div) {
        div = $(div);
        let id = Number(div.attr("data-goal-item-id"));
        let itemInfo = goalItemsMap.get(id);
        items.add({
            id: id,
            type: "range",
            content: itemInfo.name,
            start: moment(div.attr("data-start-time")),
            end: moment(div.attr("data-end-time")),
            group: div.attr("data-line"),
            suppressWarning: true,
        })
    });

    $("#submitButton").click(function(e) {
        for (let itemId of goalItemsMap.keys()) {
            let formDiv = form.find(`div[data-goal-item-id=${itemId}]`);
            let select = formDiv.find("select");
            let startTime = formDiv.find("input[name*=start_time]");
            let scheduledItem = items.get(itemId);
            if (scheduledItem !== null) {
                select.find(`option[value=${scheduledItem.group}]`).prop("selected", true);
                startTime.val(moment(scheduledItem.start).toISOString());
            } else {
                select.find("option:eq(0)").prop("selected", true);
                startTime.val("");
            }
        }
        form.submit();
    });


    /****************** Timeline controls *******************/
    function fitTo(unit) {
        let center = moment($("#dateInput").val());
        if (!center.isValid()) {
            center = moment();
        }
        let start = center.clone().startOf(unit);
        let end = center.clone().endOf(unit);
        timeline.setWindow(start, end);
    }
    $("#currentMonthButton").click(_.partial(fitTo, "month"));
    $("#currentQuarterButton").click(_.partial(fitTo, "quarter"));
    $("#currentYearButton").click(_.partial(fitTo, "year"));
    $("#fitAllButton").click(function() {
        timeline.fit();
    });
    $("#dateInput").change(function() {
        let center = moment($(this).val());
        if (!center.isValid()) {
            return;
        }
        timeline.setWindow(center.clone().startOf("week"),
            center.clone().endOf("week"));
    });
});