$(function() {
  /********* Remove Formula Functionality ***********/
  let removeFormulasUrl = $("#removeFormulasUrl").attr("href");
  let removeButton = $("#removeFormulaButton");
  let formulaCheckboxes = $(".formula-checkbox");
  let selectAllCheckbox = $("#selectAllCheckbox");
  let resetAllButton = $("#resetAllButton");
  let submitButton = $("#submitButton");
  const formulaUrl = $("#formulaUrl").attr("href");
  const formulaFilterForm = $("#formulaFilterForm");
  const ingredientsInputId = $("#ingredientsInputId").val();
  const acIngredientsUrl = $("#acIngredientsUrl").attr("href");


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
      $(`#${pageNumInputId}`).val(page);
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
      let toRemove = [];
      formulaCheckboxes.each(function(i, cb) {
          if (cb.checked) {
              toRemove.push(cb.id);
          }
      });
      if (toRemove.length < 0) return;
      makeModalAlert(`Remove ${toRemove.length} Formula(s)`,
          `Are you sure you want to remove ${toRemove.length} Formula(s)?\n` +
          "This cannot be undone.", function() {
          removeFormulas(toRemove);
          });
  });

  /****************** View Sku *******************/
  let viewSkuButtons = $(".viewSkuButtons");
  let viewSkuUrl = $("#editSkuUrl").attr("href");
  let loadingSpinner = $("#loadingSpinner");

  function viewFormula() {
      let skuNumber = $(this).attr("id");
      let url = viewSkuUrl.replace("0", String(skuNumber));
      window.location.href = url;
  }
  viewSkuButtons.click(viewFormula);
  registerAutocomplete($(`#${ingredientsInputId}`), acIngredientsUrl, true);

  let exportButton = $("#exportButton");

      exportButton.on("click", function() {
        const original = formulaFilterForm.attr("action");
        formulaFilterForm.attr("action", original + "?export=1")
            .submit()
            .attr("action", original);

        return false;
    });

});
