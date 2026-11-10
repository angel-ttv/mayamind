# Mayamind — Guía turística personalizada (rescatado 6 nov 2026)

App Flask que recomienda lugares de la Riviera Maya según el perfil del turista.

## Cómo funciona
- `app.py` (181 líneas): rutas `/` y `/recomendar` (POST).
- Motor de recomendación: cada lugar tiene "pesos" en 5 necesidades — descanso, convivencia, estatus, aventura, crecimiento personal — y se puntúa según el perfil del turista.
- Arma la ruta del día y genera el mapa embebido de Google Maps + botón "Cómo llegar" por lugar.
- `generar_mensaje_guia()`: mensaje personalizado del guía asignado.

## Datos
- `lugares.json` — 10 lugares en 8 categorías (hotel, naturaleza, vida nocturna, arqueológico, aventura, crecimiento, deporte acuático, playa): Hotel Xcaret, Cenote Ik Kil, Quinta Avenida, Tulum, Coco Bongo, Retiro de Yoga Akumal, Snorkel Cozumel, Chichén Itzá, Xplor, Isla Mujeres.
- `guias.json` — 5 guías, uno por necesidad (Carlos Méndez aventura, María Fernández crecimiento personal/cultura maya, Jorge Rivera descanso, Laura Gómez convivencia, Roberto Salas estatus).

## FALTA
La carpeta `templates/` (el HTML que `render_template` carga) no se subió. Sin ella la app no muestra nada.
