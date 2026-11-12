// Ventana modal propia del sistema: muestra los errores y pide confirmación
// dentro de la misma página, en lugar de las ventanas nativas del navegador.
(function () {
  var modal = document.getElementById("modal");
  if (!modal || typeof modal.showModal !== "function") return;
  var titulo = modal.querySelector(".modal-titulo");
  var texto = modal.querySelector(".modal-texto");
  var aceptar = modal.querySelector(".modal-aceptar");
  var cancelar = modal.querySelector(".modal-cancelar");
  var formularioPendiente = null;

  function abrir(tipo, tituloModal, mensaje, textoBoton) {
    modal.className = "modal modal-" + tipo;
    titulo.textContent = tituloModal;
    texto.textContent = mensaje;
    aceptar.textContent = textoBoton;
    cancelar.hidden = tipo !== "confirmar";
    modal.showModal();
    (tipo === "confirmar" ? cancelar : aceptar).focus();
  }

  aceptar.addEventListener("click", function () {
    modal.close();
    if (formularioPendiente) {
      var formulario = formularioPendiente;
      formularioPendiente = null;
      formulario.submit();
    }
  });
  cancelar.addEventListener("click", function () {
    formularioPendiente = null;
    modal.close();
  });
  modal.addEventListener("cancel", function () { formularioPendiente = null; });

  // Si el servidor devolvió un error de validación, se muestra en el modal
  var error = document.querySelector(".error");
  if (error) {
    abrir("error", "No se guardó", error.textContent.trim(), "Entendido");
  }

  // Los formularios con data-confirmar piden confirmación antes de enviarse
  document.querySelectorAll("form[data-confirmar]").forEach(function (formulario) {
    formulario.addEventListener("submit", function (evento) {
      evento.preventDefault();
      formularioPendiente = formulario;
      abrir("confirmar", formulario.getAttribute("data-titulo") || "¿Confirmar?",
            formulario.getAttribute("data-confirmar"), formulario.getAttribute("data-boton") || "Confirmar");
    });
  });
})();
