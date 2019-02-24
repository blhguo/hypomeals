$(function() {
  /************ Add Formula Modal *********/
  const addFormulaUrl = $("#addFormulaUrl").attr("href");
  let addFormulaButton = $("#addFormulaButton");
  let loadingSpinner = $("#loadingSpinner");
  let modalDiv = $("#modalDiv");
  let modalBody = $("#modalBody");
  let modalSaveButton = $("#modalSaveButton");
  let modalForm = undefined;

  function modalSaveButtonClicked() {
      if (modalForm === undefined) {
          return;
      }
      modalSaveButton.attr("disabled", true);
      modalForm.ajaxSubmit({
          success: function(data, textStatus) {
              if (!showNetworkError(data, textStatus)) {
                  return;
              }
              if ("success" in data && data.success === true) {
                  if ("alert" in data) {
                      alert(data.alert);
                  }
                  modalDiv.modal("hide");
              }
              modalBody.trigger("modal:change", [$(data.resp)]);
          },
      })
  }

  modalBody.on("modal:change", modalChanged);
  function modalChanged(_, newContent) {
      let container = modalBody.find("div.container");
      if (container.length > 0) {
          container.remove();
      }
      newContent.appendTo(modalBody);
      modalForm = newContent.find("form");
      modalBody.find("#formSubmitBtnGroup").toggle("false");
      modalSaveButton.attr("disabled", false);
      let buttons = $("#oldButton")
      buttons.remove()
  }

  function ajaxDone(data, textStatus) {
      if (!showNetworkError(data, textStatus)) {
          return;
      }
      loadingSpinner.toggle(false);
      modalBody.trigger("modal:change", [$(data.resp)]);
  }

  addFormulaButton.click(function() {
      $.getJSON(addFormulaUrl, {})
          .done(ajaxDone)
          .fail(function(_, __, errorThrown) {
              alert(`Error loading content: ${errorThrown}`);
              modalDiv.modal("hide");
          })
  });

  modalSaveButton.click(modalSaveButtonClicked);
});
