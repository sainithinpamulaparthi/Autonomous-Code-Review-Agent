// Intentionally flawed sample used by Demo Mode.
function render(userInput) {
  document.getElementById("out").innerHTML = userInput;
}

function compute(expr) {
  // TODO: replace this with a safe expression parser
  return eval(expr);
}
