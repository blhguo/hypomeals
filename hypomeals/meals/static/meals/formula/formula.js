$(function() {
  /********* Remove Formula Functionality ***********/
  let removeFormulasUrl = $("#removeFormulasUrl").attr("href");
  let pageNumberInput = $("input[name=page_num]");
  let removeButton = $("#removeFormulaButton");
  let formulaCheckboxes = $(".formula-checkbox");
  let selectAllCheckbox = $("#selectAllCheckbox");
  let resetAllButton = $("#resetAllButton");
  let submitButton = $("#submitButton");
  const formulaUrl = $("#formulaUrl").attr("href");
  const formulaFilterForm = $("#formulaFilterForm");


  $("[data-toggle='tooltip']").tooltip();

  function refreshPage() {
      window.location.href = formulaUrl;
  }

  formulaCheckboxes.change(function() {
      removeButton.attr("disabled",
          $(".formula-checkbox:selected").length > 0);
  });

  selectAllCheckbox.on("change", function(ev) {
      formulaCheckboxes.prop("checked",
          $(this).prop("checked"));
      formulaCheckboxes.trigger("change");
  });

  resetAllButton.click(function() {
      refreshPage();
      return false;
  });

  submitButton.click(function() {
      formulaFilterForm.submit();
  });

  $("#pageList").find("a").on("click", function() {
      let page = $(this).attr("page");
      pageNumberInput.val(page);
      $("#formulaFilterForm").submit();
  });

  function removeFormulas(toRemove) {
      let csrf_token = $("input[name=csrfmiddlewaretoken]").val();
      $.ajax(removeFormulasUrl, {
          type: "POST",
          data: {
              to_remove: JSON.stringify(toRemove),
              csrfmiddlewaretoken: csrf_token,
          },
          dataType: "json",
      }).done(function(data, textStatus) {
          if (!showNetworkError(data, textStatus)) {
              return;
          }
          if ("resp" in data) {
              makeToast("Success", data.resp, -1)
                  .done(refreshPage);
          }
      });
  }

  removeButton.on("click", function(ev) {
      let toRemove = $(".formula-checkbox:checked")
          .toArray()
          .map((cb) => $(cb).attr("data-formula-id"));
      if (toRemove.length <= 0) return;
      makeModalAlert(`Remove ${toRemove.length} Formula(s)`,
          `Are you sure you want to remove ${toRemove.length} Formula(s)? ` +
          "Note that you may not remove formulas that have SKUs associated with them.\n" +
          "This cannot be undone.", function() {
          removeFormulas(toRemove);
          });
  });

   /************* View Formula ***********/

    let viewFormulaButtons = $(".viewFormula");
    let loadingSpinner = $("#loadingSpinner");

    function viewFormula(e) {
        e.preventDefault();
        let url = $(this).attr("href");
        let modal = makeModalAlert("View Formula", loadingSpinner);
        modal.find(".modal-dialog").addClass("modal-lg");
        $.getJSON(url, {})
            .done(function (data, textStatus) {
                if (!showNetworkError(data, textStatus)) {
                    return;
                }
                if ("error" in data && data.error != null) {
                    alert(data.error);
                    modal.modal("hide");
                    return;
                }
                modal.find("#loadingSpinner").toggle(false);
                $(data.resp).appendTo(modal.find(".modal-body"));
            });
        return false;
    }

    viewFormulaButtons.click(viewFormula);

  /****************** View Sku *******************/
  let viewSkuButtons = $(".viewSkuButtons");
  let viewSkuUrl = $("#editSkuUrl").attr("href");

  function viewSkus() {
      let skuNumber = $(this).attr("id");
      let url = viewSkuUrl.replace("0", String(skuNumber));
      window.location.href = url;
  }
  viewSkuButtons.click(viewSkus);

  let exportButton = $("#exportButton");

      exportButton.on("click", function() {
        const original = formulaFilterForm.attr("action");
        formulaFilterForm.attr("action", original + "?export=1")
            .submit()
            .attr("action", original);

        return false;
    });

});
