const SENDER_ID_IGNORE = 1;  // Sender should be ignored
const WORK_HOURS_PER_DAY = 10;  // TODO: Get this from HTML
const WORK_HOURS_START = 8;
const WORK_HOURS_END = 18;
const SECONDS_PER_HOUR = 3600;
const MILLISECONDS_PER_HOUR = SECONDS_PER_HOUR * 1000;

let timeline = null;
let items = new vis.DataSet([]);
let groups = new vis.DataSet([]);
let goalItemsMap = new Map();
let warnings = new vis.DataSet([]);
let ownedLines = new Set();
let undoMgr = new UndoManager();

$(function() {
    $("[data-toggle='tooltip']").tooltip();
    let warningUl = $("#warningUl");
    let warningDiv = $("#warningDiv");
    let suppressWarningCheckbox = $("#suppressWarningCheckbox")
        .change(generateWarnings);
    $("#showHelpButton").click(function() {
        $("#helpDiv").toggle("fast");
    });

    $("#ownedLines li").each(function (_, e) {
        ownedLines.add($(e).text());
    });

    $(".selectAllButtons").click(function() {
        let checkboxes = $(this)
            .parents(".card")
            .find("input[type='checkbox']:enabled");
        if (checkboxes.length === 0) {
            makeToast("All Scheduled",
                "All items in this goal have been scheduled.",
                3000);
            return;
        }
        if (checkboxes.filter(":checked").length === checkboxes.length) {
            checkboxes.prop("checked", false);
            $(this).text("Select All");
        } else {
            checkboxes.prop("checked", true);
            $(this).text("Deselect All");
        }
    });

    undoMgr.setCallback(function() {
        $("#undoButton").prop("disabled", !undoMgr.hasUndo());
        $("#redoButton").prop("disabled", !undoMgr.hasRedo());
    });

    $("#undoButton").click(undoMgr.undo);
    $("#redoButton").click(undoMgr.redo);

    let mfgLines = new Set();  // Set of MLs to display groups
    $("span.goalItems[data-schedulable=true]")
        .on("dragstart", function(event) {
        let src = $(this);
        let goalItemId = Number(src.attr("data-goal-item-id"));
        let itemInfo = goalItemsMap.get(goalItemId);
        event.originalEvent.dataTransfer.effectAllowed = "move";
        event.originalEvent.dataTransfer.setData("text",
            JSON.stringify(itemInfo));
        highlightGroups(intersection(new Set(itemInfo.lines), ownedLines),
            true);
    }).on("click", function(e) {
        e.preventDefault();
        let goalItemId = Number($(this).attr("data-goal-item-id"));
        if (items.get(goalItemId) !== null) {
            timeline.focus(goalItemId);
        }
    });
    $(document).on("dragend", function() {
        highlightGroups("*", false);
    });

    /**************** Timeline event listeners ***************/
    items.on("update", function(event, properties, senderId) {
        if (senderId === SENDER_ID_IGNORE) return;
        let item = properties.data[0];
        let oldItem = properties.oldData[0];
        item.start = moment(item.start);
        item.end = moment(item.end);
        oldItem.start = moment(oldItem.start);
        oldItem.end = moment(oldItem.end);
        if (!validGroup(item.id, item.group)) {
            items.update(properties.oldData[0], SENDER_ID_IGNORE);
            return;
        }
        if ("start" in item) {
            try {
                let newHours = item.end.diff(item.start, "hours");
                if (newHours !== (oldItem.end.diff(oldItem.start, "hours"))) {
                    // User has overridden the duration
                    adjustEnd(item, item.start, newHours, true);
                } else {
                    adjustEnd(item, item.start, null, true);
                }
            } catch (e) {
                if (e.message !== "overlap") throw e;
                makeModalAlert("Overlap detected",
                    `Production overlaps on Manufacturing Line '${item.group}'.
                    Operation will be reverted.`,
                    null);
                items.update(oldItem, SENDER_ID_IGNORE);
                return;
            }
        }
        undoMgr.add({
            undo: function() {
                items.update(oldItem, SENDER_ID_IGNORE);
            },
            redo: function() {
                items.update(item, SENDER_ID_IGNORE);
            }
        });
        generateWarnings();
    });
    items.on("add", function(event, properties, senderId) {
        let item = items.get(properties.items[0]);
        let itemInfo = goalItemsMap.get(item.id);
        toggleGoalItem(item.id, true);
        if ("start" in item) {
            itemInfo.start = item.start;
            try {
                adjustEnd(item, item.start, itemInfo.overrideHours, !item.suppressWarning);
            } catch (e) {
                makeModalAlert("Error",
                    `Production overlaps on Manufacturing Line '${item.group}'.
                    This item will be removed.`);
                items.remove({id: item.id}, SENDER_ID_IGNORE);
            }
        }
        generateWarnings();
        if (senderId === SENDER_ID_IGNORE) {
            return;
        }
        if (!validGroup(item.id, item.group)) {
            items.remove({id: item.id}, SENDER_ID_IGNORE);
            return;
        }
        undoMgr.add({
            undo: function () {
                items.remove({id: item.id});
            },
            redo: function () {
                let toAdd = Object.assign({}, itemInfo);
                toAdd = Object.assign(toAdd, item);
                items.add(toAdd);
            }
        });
    });
    items.on("remove", function(event, properties, senderId) {
        let itemId = properties.items[0];
        let item = properties.oldData[0];
        let itemInfo = goalItemsMap.get(itemId);
        itemInfo.start = null;
        itemInfo.overrideHours = null;
        toggleGoalItem(itemId, itemInfo.isOrphaned);
        if (senderId === SENDER_ID_IGNORE) {
            return;
        }
        undoMgr.add({
                undo: function () {
                    items.add(item, SENDER_ID_IGNORE);
                },
                redo: function () {
                    items.remove({id: itemId}, SENDER_ID_IGNORE)
                }
            });
        // generateWarnings();
    });

    function validGroup(itemId, group) {
        let itemInfo = goalItemsMap.get(itemId);
        if (!ownedLines.has(group)) {
            makeModalAlert("Not Authorized",
                `You are not authorized to manage manufacturing activities on 
                '${group}'. Operation will be reverted.`);
            return false;
        }
        if (!itemInfo.lines.includes(group)) {
            makeModalAlert("Cannot Schedule",
                `Manufacturing Line '${group}' cannot produce SKU #${itemInfo.skuId}.
                Operation will be reverted.`);
            return false;
        }
        return true;
    }

    /****************** Sync with Form **********************/
    let form = $("form");
    form.find("div.goalItems").each(function(i, div) {
        div = $(div);
        let id = Number(div.attr("data-goal-item-id"));
        let lines = div.attr("data-lines").split(",");
        let overrideHours = div.attr("data-override-hours");
        let itemInfo = {
            id: id,
            type: "range",
            content: `${div.attr("data-sku-verbose-name")}\
                (${Number(div.attr("data-quantity"))})`,
            skuId: Number(div.attr("data-sku-id")),
            goalId: Number(div.attr("data-goal-id")),
            goalItemId: Number(div.attr("data-goal-item-id")),
            deadline: moment(div.attr("data-goal-deadline")).hours(WORK_HOURS_END),
            overrideHours: overrideHours ? Number(overrideHours) : null,
            lines: lines,
            isOrphaned: JSON.parse(div.attr("data-is-orphaned")),
            rate: Number(div.attr("data-sku-rate")),
            hours: Number(div.attr("data-hours")),
            quantity: Number(div.attr("data-quantity")),
            suppressWarning: true,
        };

        if (itemInfo.isOrphaned) {
            itemInfo.className = "bg-warning text-dark";
            itemInfo.title = "Orphaned item. Consider removing.";
            itemInfo.editable = {
                add: false,
                updateTime: false,
                updateGroup: false,
                remove: true,
                overrideItems: false,
            };
        }

        let line = div.find("select option:selected").val();
        if (lines.includes(line)) {
            itemInfo.group = line;
        }
        lines.forEach((l) => mfgLines.add(l));

        let endTime = moment(div.find("input[name*=end_time]").val(),
            "YYYY-MM-DD HH:mm:ss");
        if (endTime.isValid()) {
            itemInfo.end = endTime;
        }

        let startTime = moment(div.find("input[name*=start_time]").val(),
            "YYYY-MM-DD HH:mm:ss");
        if (startTime.isValid()) {
            itemInfo.start = startTime;
            if (itemInfo.overrideHours) {
                itemInfo.end = itemInfo.start.clone().add(itemInfo.overrideHours, "hours");
            } else {
                if (!endTime.isValid()) {
                    endTime = getCompletionTime(startTime, itemInfo.hours);
                    itemInfo.end = endTime;
                }
            }
            goalItemsMap.set(id, itemInfo);
            items.add(itemInfo, SENDER_ID_IGNORE);
        }
        goalItemsMap.set(id, itemInfo);
    });
    generateWarnings();


    $("#submitButton").click(function(e) {
        let scheduled = [];
        for (let itemId of goalItemsMap.keys()) {
            let formDiv = form.find(`div[data-goal-item-id=${itemId}]`);
            let select = formDiv.find("select");
            let startTime = formDiv.find("input[name*=start_time]");
            let endTime = formDiv.find("input[name*=end_time]");
            let overrideHours = formDiv.find("input[name*=override_hours]");
            let scheduledItem = items.get(itemId);
            let itemInfo = goalItemsMap.get(itemId);
            if (scheduledItem !== null) {
                select.find(`option[value=${scheduledItem.group}]`).prop("selected", true);
                startTime.val(moment(scheduledItem.start).toISOString(true));
                endTime.val(moment(scheduledItem.end).toISOString(true));
                if (itemInfo.overrideHours) {
                    overrideHours.val(itemInfo.overrideHours);
                } else {
                    overrideHours.val("");
                }
                scheduled.push(scheduledItem);
            } else {
                select.find("option:eq(0)").prop("selected", true);
                startTime.val("");
                endTime.val("");
                overrideHours.val("");
            }
        }

        let html = null;
        if (scheduled.length > 0) {
            html = $(`<p>You have scheduled the following items:</p>`);
            let table = $("#confirmationTable").clone();
            for (let item of scheduled) {
                table.find("tbody").append($("<tr>").append([
                    $("<td>").text(item.content),
                    $("<td>").text(item.group),
                    $("<td>").text(moment(item.start).format("lll")),
                    $("<td>").text(moment(item.end).format("lll")),
                ]));
            }
            html.append(table);
        } else {
            html = $("<p>No items were scheduled.</p>");
        }
        html.append($(`<p class='mb-3'>Items not listed here will 
<b>all be unscheduled.</b> Do you want to save this schedule?</p>`));
        makeModalAlert("Confirm", html, function() {
            form.submit();
        }).find(".modal-dialog")
            .addClass("modal-lg");
    });

    /***************** Timeline *******************/
    groups = new vis.DataSet([]);
    mfgLines.forEach((l) => {
        let group = {
            id: l,
            content: l,
            visible: true,
        };
        if (!ownedLines.has(l)) {
            group.className = "bg-dark text-light opacity-5";
        }
        groups.add(group);
    });

    function highlightGroups(groupIds, highlighted) {
        if (groupIds === "*") {
            groupIds = groups.distinct("id");
        }
        let updates = [];
        let className = highlighted ? "bg-success text-white opacity-7" : "1";
        for (let group of groupIds) {
            if (!ownedLines.has(group)) continue;
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
        itemsInGroup.sort(sortItemByStartTime);
        for (let i = 0; i < itemsInGroup.length - 1; i++) {
            if (moment(itemsInGroup[i + 1].start) <= moment(itemsInGroup[i].end)) {
                throw Error("overlap");
            }
        }
        return false;
    }

    function adjustEnd(item, start, overrideHours, showWarning) {
        let itemId = item.id;
        let globalSuppress = suppressWarningCheckbox.prop("checked");
        start = moment(start);
        let itemInfo = goalItemsMap.get(itemId);
        let updates = {id: itemId};
        itemInfo.overrideHours = overrideHours;
        if (overrideHours) {
            updates["end"] = moment(start).add(overrideHours, "hours");
        } else {
            updates["end"] = getCompletionTime(start, itemInfo.hours);
        }
        updates["type"] = "range";
        if (updates.end > itemInfo.deadline) {
            updates["className"] = "bg-danger text-white";
            updates["title"] = `${start.format("lll")} - ${updates.end.format("lll")}.
        Warning: item exceeds deadline ${itemInfo.deadline.format("lll")}`;
            if (showWarning && !globalSuppress) {
                makeModalAlert("Warning",
                    `Scheduling this item to start at \
            ${start.format("lll")} will exceed predetermined \
            deadline of ${itemInfo.deadline.format("lll")} in the goal.
            Consider moving this item earlier.`);
            }
        } else if (itemInfo.isOrphaned) {
            updates["className"] = "bg-warning text-dark";
            updates["title"] = `${start.format("lll")} - ${updates.end.format("lll")}`;
        } else if (itemInfo.overrideHours) {
            updates["className"] = "bg-warning text-dark";
            updates["title"] = `${start.format("lll")} - ${updates.end.format("lll")} \
            Warning: item duration is overridden to ${overrideHours} hours`;
        } else {
            updates["className"] = "";
            updates["title"] = `${start.format("lll")} - ${updates.end.format("lll")}`
        }
        items.update(updates, SENDER_ID_IGNORE);
        checkOverlap(item);
    }

    function generateWarnings() {
        if (timeline === null) return;  // Timeline is not initialized yet.
        let visibleItems = timeline.getVisibleItems();
        let suppressWarning = $("#suppressWarningCheckbox").prop("checked");
        if (suppressWarning) {
            warningDiv.toggle(false);
            return;
        }
        let warnings = [];
        for (let itemId of visibleItems) {
            let item = items.get(itemId);
            let itemInfo = goalItemsMap.get(itemId);
            if (itemInfo.isOrphaned) {
                warnings.push(`'${itemInfo.content}': item is orphaned. \
                    consider removing the item.`);
                continue;  // other warnings are suppressed for orphaned items.
            }
            if (moment(item.end) > itemInfo.deadline) {
                warnings.push(`'${itemInfo.content}': item exceeds \
                    deadline of ${itemInfo.deadline.format("lll")}`);
            }
            if (itemInfo.overrideHours) {
                warnings.push(`'${itemInfo.content}': manufacturing duration \
                    has been overridden to ${itemInfo.overrideHours} hours.`);
            }
        }
        warningDiv.toggle(warnings.length > 0 && !suppressWarning);
        warningUl.find("li").remove();
        warnings.forEach(function(warning) {
            $("<li>", {text: warning}).appendTo(warningUl);
        });
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

    timeline.on("rangechanged", generateWarnings);

    $(".vis-timeline").css("visibility", "visible");


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

/**
 * Computes the difference of two sets. Taken from:
 * https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Set
 */
function difference(setA, setB) {
    let _difference = new Set(setA);
    for (let elem of setB) {
        _difference.delete(elem);
    }
    return _difference;
}

/**
 * Computes the intersection of two sets.
 */
function intersection(setA, setB) {
    let _intersection = new Set();
    for (let elem of setB) {
        if (setA.has(elem)) {
            _intersection.add(elem);
        }
    }
    return _intersection;
}

/**
 * For performance reasons, async query completion time is not feasible. This
 * is an exact port from the Python version.
 * @param startTime the start time of a manufacturing activity
 * @param hours the number of work hours
 * @return a {@code moment} object representing the end time
 */
function getCompletionTime(startTime, hours) {
    startTime = moment(startTime);
    let numDays = Math.floor(hours  / WORK_HOURS_PER_DAY);
    let remaining = hours % WORK_HOURS_PER_DAY;
    if (remaining === 0) {
        numDays--;
        remaining = WORK_HOURS_PER_DAY;
    }
    if ((startTime.hours() <= WORK_HOURS_END) && (startTime.hours() >= WORK_HOURS_START)) {
        let firstDayEnd = startTime.clone().startOf("day").hours(WORK_HOURS_END);
        remaining -= (firstDayEnd - startTime) / MILLISECONDS_PER_HOUR;
    }
    let endTime = startTime.clone().add(numDays, "days");
    if (remaining > 0) {
        if (startTime.hours() <= WORK_HOURS_START) {
            endTime.startOf("day").hours(WORK_HOURS_START).add(remaining, "hours");
        } else {
            endTime.add(1, "days")
                .startOf("day")
                .hours(WORK_HOURS_START)
                .add(remaining, "hours");
        }
    } else {
        endTime.startOf("day").hours(WORK_HOURS_END).add(remaining, "hours");
    }

    // console.log("start", startTime.format(), "hour", hours, "end", endTime.format());
    return endTime;
}

/**
 * Toggles a goal item on the palette. Specifically, it applies the text-muted
 * class to items that are scheduled, and removes the class if it's unscheduled
 * @param goalItemId the ID of the goal item
 * @param scheduled whether it is scheduled
 */
function toggleGoalItem(goalItemId, scheduled) {
    $(`span[data-goal-item-id=${goalItemId}]`)
        .toggleClass("text-muted", scheduled)
        .parents("label")
        .siblings("input")
        .prop("disabled", scheduled);
}

function sortItemByStartTime(a, b) {
    return moment(a.start) - moment(b.start);
}

/**
 * Bind shortcut keys
 */
$(function() {
    Mousetrap.bind("ctrl+x ctrl+s", function(e) {
        e.preventDefault();
        $("#submitButton").trigger("click");
    });
    Mousetrap.bind("ctrl+x ctrl+c", function(e) {
        e.preventDefault();
        $("#backToGoalsButton")[0].click();
    });
    Mousetrap.bind("ctrl+h", function(e) {
        e.preventDefault();
        $("#showHelpButton").trigger("click");
    });
    Mousetrap.bind(["ctrl+z", "command+z", "ctrl+/"], undoMgr.undo);
    Mousetrap.bind(["ctrl+shift+z", "command+shift+z"], undoMgr.redo);
    Mousetrap.bind(["ctrl+shift+s", "command+shift+s"], function(e) {
        e.preventDefault();
        $("#autoScheduleButton").trigger("click");
    });
    Mousetrap.bind(["ctrl+a", "command+a"], function(e) {
        e.preventDefault();
        $("#goalItemList input[type='checkbox']:enabled")
            .trigger("click");
    });
    ([
        ["m", "#currentMonthButton"],
        ["q", "#currentQuarterButton"],
        ["y", "#currentYearButton"],
        ["s", "#fitAllButton"]
    ]).forEach(function(key) {
        Mousetrap.bind("ctrl+f " + key[0], function(e) {
            e.preventDefault();
            $(key[1]).trigger("click");
        })
    });
});

/**
 * Auto-schedule logic
 */
$(function() {
    let checkboxes = $("#goalItemList input[type='checkbox']:enabled");
    $("#autoScheduleButton").click(function(ev) {
        ev.preventDefault();
        let button = $(this);
        let selected = checkboxes.filter(":checked")
            .toArray()
            .map(e => Number($(e).attr("data-goal-item-id")));
        if (selected.length === 0) {
            makeModalAlert("Cannot Auto-schedule",
                "You must select at least one item from the palette below.");
            return;
        }
        let existing = Object();
        for (let group of groups.getIds()) {
            existing[group] = items.get({
                filter: item => item.group === group,
                order: sortItemByStartTime
            }).map(item => item.id);
        }

        let toSchedule = [];
        for (let itemInfo of selected.map(e => goalItemsMap.get(e))) {
            toSchedule.push({
                id: itemInfo.id,
                groups: Array.from(intersection(new Set(itemInfo.lines), ownedLines)),
                hours: itemInfo.hours
            })
        }
        let original = button.html();
        let modal = makeModalAlert("Auto-schedule",
            $("#autoScheduleDateDiv"), doSchedule);
        focusDate();
        function doSchedule() {
            let start = moment(modal.find("#startDate").val(), "YYYY-MM-DD");
            let end = moment(modal.find("#endDate").val(), "YYYY-MM-DD");
            if (!start.isValid() || !end.isValid()) {
                focusDate();
                return false;
            }
            button.html(`<div class="spinner-border spinner-border-sm"></div> Auto-scheduling...`)
                .prop("disabled", true);
            postJson(button.attr("data-href"), {
                items: JSON.stringify(Array.from(toSchedule)),
                existing: JSON.stringify(existing),
                start: start.unix(),
                end: end.unix(),
                csrfmiddlewaretoken: $("input[name='csrfmiddlewaretoken']").val()
            }, true).done(function(data) {
                data = JSON.parse(data);
                addItems(data);
                undoMgr.add({
                    undo: function() {
                        items.remove(data.map(i => i.id));
                    },
                    redo: function() {
                        addItems(data);
                    }
                });
                makeToast("Auto-schedule",
                    `Successfully scheduled ${toSchedule.length} items.`, 3000);
                checkboxes.prop("checked", false);
            }).fail(function(error) {
                makeModalAlert("Auto-schedule",
                    "An error has occurred.\n" + error);
            }).always(function() {
                resetButton();
            });
        }
        function focusDate() {
            $(modal.find("input[type='date']")[0]).trigger("focus");
        }
        function resetButton() {
            button.html(original).prop("disabled", false);
        }
        function addItems(data) {
            for (let scheduled of data) {
                let itemInfo = goalItemsMap.get(Number(scheduled.id));
                let item = Object.assign({}, itemInfo);
                item.group = scheduled.group;
                item.start = moment.unix(scheduled.start);
                item.end = moment.unix(scheduled.end);

                items.add(item, SENDER_ID_IGNORE);
            }
        }
        modal.find("input[type='date']").change(function() {
            let value = $(this).val();
            if (value.length === 0) {
                $(this).removeClass("was-validated is-valid is-invalid");
                return;
            }
            $(this).addClass("was-validated");
            if (moment(value).isValid()) {
                $(this).removeClass("is-invalid").addClass("is-valid");
            } else {
                $(this).removeClass("is-valid").addClass("is-invalid");
            }
        })
    });
});