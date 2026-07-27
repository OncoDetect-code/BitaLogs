"""
Pantalla de carga (splash) de BitaLogs.

Overlay a pantalla completa que se dibuja de una vez y se auto-oculta con
CSS/JS (sin time.sleep, que en algunas versiones de Streamlit impide que
el iframe se pinte). Las barras del grafico crecen una por una
(verde -> morada -> roja), aparece la banda LOG y el titulo, y al final
todo se desvanece dejando ver la app.

Uso:
    from splash import mostrar_splash
    mostrar_splash(st)   # justo despues de set_page_config
"""

import streamlit.components.v1 as components

_AMARILLO = "#FFE177"
_AMARILLO_OSC = "#FDD35B"
_PAPEL = "#E9F6FF"
_PAPEL_BORDE = "#D3ECF8"
_VERDE = "#6AD59F"
_MORADO = "#C796E5"
_ROJO = "#FC5871"
_AZUL = "#98E6FC"
_AZUL_OSC = "#6FD3F2"
_TEXTO = "#3A9BC1"


def _html(dur: float) -> str:
    # El overlay se monta en el <body> superior (document.body del padre)
    # via JS, para cubrir TODA la ventana de la app, no solo el iframe.
    return f"""
<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
<script>
(function() {{
  var DUR = {dur};                 // segundos visibles
  var doc = window.parent.document; // documento de la app (no el iframe)
  if (doc.getElementById('bl-splash-overlay')) return;

  var css = `
    #bl-splash-overlay {{
      position: fixed; inset: 0; z-index: 2147483647;
      background: #FFFFFF; display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      font-family: Arial, Helvetica, sans-serif;
      animation: blOut .6s ease forwards; animation-delay: ${{DUR}}s;
    }}
    #bl-splash-overlay .t {{
      margin-top:16px; font-size:34px; font-weight:800;
      color:{_TEXTO}; letter-spacing:1px; opacity:0;
      animation: blIn .6s ease forwards; animation-delay:2.9s;
    }}
    #bl-splash-overlay .s {{
      margin-top:4px; font-size:14px; color:#8A9AA5; opacity:0;
      animation: blIn .6s ease forwards; animation-delay:3.2s;
    }}
    @keyframes blIn  {{ from{{opacity:0}} to{{opacity:1}} }}
    @keyframes blOut {{ to{{opacity:0; visibility:hidden}} }}
  `;
  var style = doc.createElement('style');
  style.id = 'bl-splash-style';
  style.textContent = css;
  doc.head.appendChild(style);

  var ov = doc.createElement('div');
  ov.id = 'bl-splash-overlay';
  ov.innerHTML = `
    <svg viewBox="0 0 300 300" width="220" height="220"
         xmlns="http://www.w3.org/2000/svg">
      <rect x="92" y="24" width="140" height="176" rx="12"
            fill="{_PAPEL}" stroke="{_PAPEL_BORDE}" stroke-width="3"/>
      <path d="M40 112 q0 -18 18 -18 h60 l16 16 h96 q18 0 18 18 v120
               q0 18 -18 18 H58 q-18 0 -18 -18 Z" fill="{_AMARILLO}"/>
      <path d="M40 180 h228 v68 q0 18 -18 18 H58 q-18 0 -18 -18 Z"
            fill="{_AMARILLO_OSC}" opacity="0.5"/>
      <rect x="110" y="196" width="30" height="0" rx="6" fill="{_VERDE}">
        <animate attributeName="height" values="0;104" begin="0.3s"
          dur="0.7s" fill="freeze" calcMode="spline" keySplines="0.2 0.8 0.2 1"/>
        <animate attributeName="y" values="196;92" begin="0.3s"
          dur="0.7s" fill="freeze" calcMode="spline" keySplines="0.2 0.8 0.2 1"/>
      </rect>
      <rect x="150" y="196" width="30" height="0" rx="6" fill="{_MORADO}">
        <animate attributeName="height" values="0;66" begin="1.1s"
          dur="0.7s" fill="freeze" calcMode="spline" keySplines="0.2 0.8 0.2 1"/>
        <animate attributeName="y" values="196;130" begin="1.1s"
          dur="0.7s" fill="freeze" calcMode="spline" keySplines="0.2 0.8 0.2 1"/>
      </rect>
      <rect x="190" y="196" width="30" height="0" rx="6" fill="{_ROJO}">
        <animate attributeName="height" values="0;40" begin="1.9s"
          dur="0.7s" fill="freeze" calcMode="spline" keySplines="0.2 0.8 0.2 1"/>
        <animate attributeName="y" values="196;156" begin="1.9s"
          dur="0.7s" fill="freeze" calcMode="spline" keySplines="0.2 0.8 0.2 1"/>
      </rect>
      <g opacity="0">
        <animate attributeName="opacity" from="0" to="1" begin="2.7s"
          dur="0.5s" fill="freeze"/>
        <rect x="24" y="206" width="170" height="52" rx="12" fill="{_AZUL}"/>
        <rect x="24" y="206" width="170" height="52" rx="12"
              fill="{_AZUL_OSC}" opacity="0.25"/>
        <text x="109" y="242" text-anchor="middle" font-family="Arial"
              font-size="34" font-weight="800" fill="#EAF6FB"
              letter-spacing="4">LOG</text>
      </g>
    </svg>
    <div class="t">BitaLogs</div>
    <div class="s">Cargando tu rendimiento...</div>
  `;
  doc.body.appendChild(ov);

  // Quitar el overlay del DOM cuando termine (DUR + fade)
  setTimeout(function() {{
    var o = doc.getElementById('bl-splash-overlay');
    var s = doc.getElementById('bl-splash-style');
    if (o) o.remove();
    if (s) s.remove();
  }}, (DUR + 0.8) * 1000);
}})();
</script>
</body></html>
"""


def mostrar_splash(st, duracion: float = 5.0, forzar: bool = False):
    """
    Inyecta el overlay de carga. Se auto-oculta tras 'duracion' segundos.
    - Una vez por sesion, salvo forzar=True.
    - Llamar justo despues de st.set_page_config().
    """
    if not forzar and st.session_state.get("_splash_visto"):
        return
    st.session_state["_splash_visto"] = True
    # height=0 para no ocupar espacio: el overlay se monta en el body padre.
    components.html(_html(duracion), height=0, width=0)