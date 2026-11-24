// CAPA DE VISTA - Comportamiento del lado del cliente
(function () {
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content;

  // Menú lateral en celulares (vista responsiva, RNF1)
  document.querySelectorAll('[data-toggle-sidebar]').forEach(b =>
    b.addEventListener('click', () => document.getElementById('sidebar').classList.toggle('abierto')));

  // Confirmación antes de acciones sensibles (dar de baja, rechazar, cerrar liquidación…)
  document.querySelectorAll('form[data-confirmar]').forEach(f =>
    f.addEventListener('submit', e => { if (!confirm(f.dataset.confirmar)) e.preventDefault(); }));

  // Seleccionar todas las marcas (aprobación masiva CU08)
  const todos = document.getElementById('seleccionar-todos');
  if (todos) todos.addEventListener('change', () =>
    document.querySelectorAll('input[name="ids"]').forEach(c => { c.checked = todos.checked; }));

  // Hora del servidor que avanza en pantalla (la marca usa la hora del servidor, RNF5)
  const reloj = document.getElementById('reloj-servidor');
  if (reloj) {
    let t = new Date(reloj.dataset.iso).getTime();
    setInterval(() => { t += 1000; reloj.textContent = new Date(t).toLocaleTimeString('es-PE', { hour12: false }); }, 1000);
  }

  // Cliente de la API REST con token CSRF
  window.api = async function (url, opciones = {}) {
    const r = await fetch(url, Object.assign({ headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf } }, opciones));
    return r.json();
  };
})();
