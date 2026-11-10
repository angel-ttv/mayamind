from flask import Flask, request, jsonify, render_template
import json
import os
from urllib.parse import quote

app = Flask(__name__)

# Cargar bases de datos
with open('lugares.json', 'r', encoding='utf-8') as f:
    lugares = json.load(f)

with open('guias.json', 'r', encoding='utf-8') as f:
    guias = json.load(f)

NEEDS = ['descanso', 'convivencia', 'estatus', 'aventura', 'crecimiento_personal']

NOMBRES_NEEDS = {
    'descanso': 'descanso',
    'convivencia': 'convivencia',
    'estatus': 'experiencias exclusivas',
    'aventura': 'aventura',
    'crecimiento_personal': 'crecimiento personal'
}


def direccion_completa(lugar):
    """Arma una dirección legible para mostrar y para buscar en el mapa."""
    return f"{lugar['nombre']}, {lugar.get('ubicacion', 'Riviera Maya')}, Quintana Roo, México"


def link_mapa_lugar(lugar):
    """Link a Google Maps para un solo lugar (botón 'Cómo llegar')."""
    return f"https://www.google.com/maps/search/?api=1&query={quote(direccion_completa(lugar))}"


def embed_ruta_dia(lugares_dia):
    """Construye la URL de un mapa embebido con la ruta entre los lugares de un día."""
    direcciones = [quote(direccion_completa(l)) for l in lugares_dia]
    if not direcciones:
        return None
    if len(direcciones) == 1:
        return f"https://maps.google.com/maps?q={direcciones[0]}&output=embed"
    origen = direcciones[0]
    destino = direcciones[-1]
    intermedios = direcciones[1:-1]
    daddr = destino
    for wp in intermedios:
        daddr += f"+to:{wp}"
    return f"https://maps.google.com/maps?saddr={origen}&daddr={daddr}&output=embed"


def generar_mensaje_guia(guia, dias_dict, perfil, necesidad_principal):
    """Genera el texto que 'habla' el guía explicando el circuito, como si lo presentara en persona."""
    top_needs = sorted(perfil, key=perfil.get, reverse=True)[:2]
    intereses = ' y '.join(NOMBRES_NEEDS[n] for n in top_needs)

    partes = [
        f"Hola, soy {guia['nombre']}, tu guía de {NOMBRES_NEEDS.get(necesidad_principal, necesidad_principal)} en la Riviera Maya.",
        f"Por lo que me cuentas, buscas sobre todo {intereses}, así que armé un circuito pensado en eso."
    ]

    for dia_num in sorted(dias_dict.keys()):
        items = dias_dict[dia_num]
        if not items:
            continue
        nombres = [it['nombre'] for it in items]
        if len(nombres) == 1:
            lista = nombres[0]
        else:
            lista = ', '.join(nombres[:-1]) + ' y ' + nombres[-1]
        partes.append(f"Día {dia_num}: te llevo a {lista}.")

    partes.append("Toca cada parada para ver cómo llegar y qué encontrarás ahí. ¡Vamos!")
    return ' '.join(partes)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recomendar', methods=['POST'])
def recomendar():
    data = request.get_json()
    respuestas = data.get('respuestas', [])
    visitados = data.get('visitados', [])  # Lista de IDs de lugares ya visitados

    # 1. Calcular perfil del viajero
    perfil = {need: 0 for need in NEEDS}
    for r in respuestas:
        need = r.get('need')
        value = r.get('value', 0)
        if need in perfil:
            perfil[need] += value
    for need in NEEDS:
        perfil[need] = perfil[need] / len(respuestas) if respuestas else 0

    # 2. Determinar la necesidad principal (para elegir guía)
    necesidad_principal = max(perfil, key=perfil.get)
    guia_asignado = next((g for g in guias if g['especialidad'] == necesidad_principal), guias[0])

    # 3. Filtrar lugares NO visitados
    lugares_disponibles = [l for l in lugares if l['id'] not in visitados]

    # 4. Calcular score de compatibilidad
    for lugar in lugares_disponibles:
        pesos = lugar['pesos']
        score = sum(perfil[need] * pesos.get(need, 0) for need in NEEDS)
        lugar['score'] = score

    # 5. Ordenar y seleccionar top 6 (para llenar 3 días)
    recomendados = sorted(lugares_disponibles, key=lambda x: x['score'], reverse=True)[:6]

    # 6. Organizar ruta por días (alternando tipos para variedad)
    # Clasificar por tipo
    tipos = {}
    for l in recomendados:
        categoria = l.get('categoria', 'otro')
        if categoria not in tipos:
            tipos[categoria] = []
        tipos[categoria].append(l)
    
    # Distribuir en 3 días (intentamos poner un tipo distinto por día)
    dias = {1: [], 2: [], 3: []}
    categorias_list = list(tipos.keys())
    # Ordenar categorías por el score promedio para poner lo mejor primero
    for i in range(3):  # 3 días
        for cat in categorias_list:
            if tipos[cat]:
                # Añadir el mejor de esa categoría al día actual
                dias[i+1].append(tipos[cat].pop(0))
        # Si algún día tiene menos de 2, rellenar con lo que quede
        while len(dias[i+1]) < 2 and recomendados:
            # buscar un lugar no asignado aún
            agregado = False
            for l in recomendados:
                if not any(l['id'] == item['id'] for items in dias.values() for item in items):
                    dias[i+1].append(l)
                    agregado = True
                    break
            if not agregado:
                # ya no quedan lugares sin asignar, salir para no ciclar infinitamente
                break

    # Convertir a lista plana para respuesta, pero con marcado de día
    circuito_por_dias = []
    for dia_num, items in dias.items():
        for item in items:
            item['dia'] = dia_num
            circuito_por_dias.append(item)

    # Si hay menos de 3 lugares, ajustar
    if len(circuito_por_dias) < 3:
        # Rellenar con los mejores disponibles (ya filtrados)
        extra = [l for l in lugares_disponibles if l not in circuito_por_dias]
        for l in extra[:3-len(circuito_por_dias)]:
            l['dia'] = 1
            circuito_por_dias.append(l)

    # 7. Agregar dirección y link de "cómo llegar" a cada parada
    for item in circuito_por_dias:
        item['direccion'] = direccion_completa(item)
        item['maps_link'] = link_mapa_lugar(item)

    # 8. Armar el mapa de ruta y el mensaje del guía por día
    mapas_por_dia = {}
    for dia_num, items in dias.items():
        if items:
            mapas_por_dia[dia_num] = embed_ruta_dia(items)

    mensaje_guia = generar_mensaje_guia(guia_asignado, dias, perfil, necesidad_principal)

    return jsonify({
        'perfil': perfil,
        'guia': guia_asignado,
        'circuito': circuito_por_dias,
        'necesidad_principal': necesidad_principal,
        'mapas_por_dia': mapas_por_dia,
        'mensaje_guia': mensaje_guia
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)