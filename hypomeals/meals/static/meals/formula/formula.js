$(function() {
  let removeFormulasUrl = $("#removeFormulasUrl").attr("href");
  let removeButton = $("#removeFormulaButton");
  let formulaCheckboxes = $(".formula-checkbox");

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
});
