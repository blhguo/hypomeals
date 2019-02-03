$(function() {
    let removeButton = $("#removeButton");
    let skuCheckboxes = $(".sku-checkbox").toArray();
    const acIngredientUrl = $("#acIngredientUrl").attr("href");
    const acProductLineUrl = $("#acProductLineUrl").attr("href");
    const ingredientsInputId = $("#ingredientsInputId").val();
    const productLinesInputId = $("#productLinesInputId").val();
    const pageNumInputId = $("#pageNumInputId").val();
    const skuUrl = $("#skuUrl").attr("href");
    const removeSkuUrl = $("#removeSkuUrl").attr("href");
    let selectAllButton = $("#selectAll");

    function refreshPage() {
        window.location.href = skuUrl;
    }

    skuCheckboxes.forEach(function (cb) {
        cb.onchange = function(ev) {
            removeButton.prop("disabled", !skuCheckboxes.some(function(elem) {
                return elem.checked;
            }));
        }
    });

    selectAllButton.on("change", function(ev) {
        let value = $(this).prop("checked");
        skuCheckboxes.forEach(function(cb) {
            cb.checked = value;
        });
    });

    removeButton.on("click", function(ev) {
        let toRemove = [];
        skuCheckboxes.forEach(function(cb) {
            if (cb.checked) {
                toRemove.push(cb.id);
            }
        });
        if (confirm(
            `Are you sure you want to remove ${toRemove.length} SKU(s)?\n` +
            "This cannot be undone."
        )) {
            $.ajax(removeSkuUrl, {
                type: "POST",
                data: {to_remove: JSON.stringify(toRemove)},
                dataType: "json",
            }).done(function(data, textStatus) {
                if (textStatus !== "success") {
                    alert(
                        `[status=${textStatus}] Error removing` +
                        `${toRemove.length} SKU(s):` +
                        ("error" in data) ? data.error : "" +
                        `\nPlease refresh the page and try again later.`
                    );
                } else {
                    if ("resp" in data) {
                        alert(data.resp);
                    }
                }
                refreshPage();
            });
        }
    });

    /************** Pagination ****************/
    $("#pageList").find("a").on("click", function() {
        let page = $(this).attr("page");
        $(`#${pageNumInputId}`).val(page);
        $("#skuFilterForm").submit();
    });

    /************** Autocomplete for Ingredients and Product Lines **************/
    // Adapted from https://jqueryui.com/autocomplete/#multiple-remote

    function split(val) {
        return val.split(/,\s*/);
    }

    function lastTerm(val) {
        return split(val).pop();
    }

    function registerAutocomplete(input, url) {
        input.on("keydown", function(ev) {
            if (ev.keyCode === $.ui.keyCode.TAB
                && $(this).autocomplete("instance").menu.active) {
                ev.preventDefault();
            }
        })
        .autocomplete({
            source: function(request, response) {
                $.getJSON(url, {
                    term: lastTerm(request.term)
                }, response)
            },
            search: function() {
                let term = lastTerm(this.value);
                // Only perform a search when user has typed more than 2 chars
                return term.length >= 2;
            },
            focus: function() {
                return false;
            },
        });
    }

    registerAutocomplete($(`#${ingredientsInputId}`), acIngredientUrl);
    registerAutocomplete($(`#${productLinesInputId}`), acProductLineUrl);

    $("#resetAllButton").click(refreshPage);
});