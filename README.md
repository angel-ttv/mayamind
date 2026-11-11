# Mayamind — Tu circuito en la Riviera Maya

App Flask que arma un circuito turístico según tus gustos. Tú dices qué te
gusta y el algoritmo genera qué hacer, día por día.

## Cómo funciona el algoritmo

1. **Tus gustos:** calificas de 0 a 5 cada interés — playa, aventura, cultura,
   naturaleza, fiesta, gastronomía, relax y compras.
2. **Tu viaje:** presupuesto (económico / medio / premium), días (1–5),
   con quién viajas (solo, pareja, familia, amigos) y ritmo
   (tranquilo: 2 cosas al día, moderado: 3, intenso: 4).
3. **Puntaje:** cada lugar suma lo que le diste a los intereses que cubre.
   Un lugar con dos tags que te encantan vale más que uno con un solo tag
   que te gusta poco.
4. **Filtros:** fuera de presupuesto no entra; la vida nocturna pura
   (Coco Bongo) no se recomienda en familia.
5. **Circuito:** reparte los mejores lugares en mañana / tarde / noche,
   sin repetir lugar ni categoría el mismo día. Un lugar de día completo
   (Xplor, Xcaret) ocupa mañana y tarde.
6. **Guía:** te asigna un guía según tu gusto dominante y te presenta el
   circuito con su mensaje, más el mapa de ruta de cada día y el botón
   "Cómo llegar" por parada.

## E.D.I.T.H. — la IA de Mayamind

Después de armar el circuito aparece el chat con **Edith**. Ella conoce tu
circuito y te dice dónde hospedarte (la zona donde caen más paradas), qué
comer, cómo moverte, qué llevar y por qué te tocó cada lugar.

- Usa el mismo núcleo que A.R.I.A.: **Ollama + llama3 en local**, sin API key.
- Si Ollama no está prendido (por ejemplo en Render), Edith contesta en
  **modo sin conexión** con reglas propias, así la demo nunca se queda muda.
- El resultado del circuito incluye `hospedaje`: la zona recomendada para
  dormir. Ese es el gancho para hoteles: Mayamind manda huéspedes a la zona
  donde de verdad van a pasear.

## Archivos

- `app.py` — el algoritmo (`armar_circuito()`) y las rutas `/` y
  `/recomendar` (POST).
- `lugares.json` — 20 lugares con tags, presupuesto (1–3),
  duración en horas y momento del día (mañana / tarde / noche / día).
- `edith.py` — la IA: llama3 por Ollama con respaldo por reglas; ruta
  `/edith` (POST) en `app.py`.
- `guias.json` — 5 guías, uno por necesidad.
- `templates/index.html` — el quiz de gustos y el circuito con mapas.

## Cómo correrlo

```bash
pip install flask
python app.py
```

Abre http://localhost:5000, califica tus gustos y dale a "Armar mi circuito".

Para que Edith use IA de verdad, antes prende Ollama:

```bash
ollama pull llama3
ollama serve
```
