"""Mayamind — algoritmo de circuitos turísticos por gustos.

El turista dice qué le gusta (0-5 por interés), su presupuesto, cuántos días
tiene, con quién viaja y a qué ritmo. El algoritmo puntúa cada lugar según
sus gustos, filtra por presupuesto y arma un circuito día por día:
mañana / tarde / noche, sin repetir lugar ni categoría en el mismo día.
"""
from flask import Flask, request, jsonify, render_template
import json
import os
from urllib.parse import quote

BASE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE, 'lugares.json'), 'r', encoding='utf-8') as f:
    lugares = json.load(f)

with open(os.path.join(BASE, 'guias.json'), 'r', encoding='utf-8') as f:
    guias = json.load(f)

app = Flask(__name__)

# Los 8 gustos que el turista califica de 0 a 5.
GUSTOS = ['playa', 'aventura', 'cultura', 'naturaleza',
          'fiesta', 'gastronomia', 'relax', 'compras']

NOMBRES_GUSTOS = {
    'playa': 'playa', 'aventura': 'aventura', 'cultura': 'cultura',
    'naturaleza': 'naturaleza', 'fiesta': 'fiesta',
    'gastronomia': 'gastronomía', 'relax': 'descanso', 'compras': 'compras',
}

# Qué guía atiende cada gusto dominante (especialidades en guias.json).
GUIA_POR_GUSTO = {
    'playa': 'descanso', 'relax': 'descanso',
    'aventura': 'aventura',
    'cultura': 'crecimiento_personal', 'naturaleza': 'crecimiento_personal',
    'fiesta': 'estatus', 'compras': 'estatus',
    'gastronomia': 'convivencia',
}

# Huecos del día según el ritmo del viaje.
SLOTS_POR_RITMO = {
    'tranquilo': ['manana', 'tarde'],
    'moderado': ['manana', 'tarde', 'noche'],
    'intenso': ['manana', 'manana', 'tarde', 'noche'],
}

NOMBRE_MOMENTO = {'manana': 'Mañana', 'tarde': 'Tarde', 'noche': 'Noche'}


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


def puntuar(lugar, gustos):
    """Puntos de un lugar según los gustos: suma lo que el turista le dio
    a cada interés que el lugar cubre. Un lugar con 2 tags que te encantan
    vale más que uno con un solo tag que te gusta poco."""
    return sum(gustos.get(tag, 0) for tag in lugar.get('tags', []))


def armar_circuito(gustos, presupuesto=2, dias=3, acompanantes='pareja',
                   ritmo='moderado'):
    """El algoritmo. Devuelve el circuito completo como diccionario."""
    gustos = {g: max(0, min(5, int(gustos.get(g, 0)))) for g in GUSTOS}
    dias = max(1, min(5, int(dias)))
    presupuesto = max(1, min(3, int(presupuesto)))
    slots = SLOTS_POR_RITMO.get(ritmo, SLOTS_POR_RITMO['moderado'])

    # 1. Filtrar: fuera de presupuesto no entra; vida nocturna pura no
    # es para ir en familia.
    candidatos = []
    for lugar in lugares:
        if lugar.get('presupuesto', 2) > presupuesto:
            continue
        if acompanantes == 'familia' and lugar.get('tags') == ['fiesta']:
            continue
        candidatos.append(dict(lugar, score=puntuar(lugar, gustos)))

    # 2. Ordenar por puntaje (a igualdad de puntos, primero el más barato).
    candidatos.sort(key=lambda l: (-l['score'], l.get('presupuesto', 2)))

    # 3. Repartir en días: cada hueco toma el mejor lugar sin usar que
    # encaje en ese momento y no repita categoría ese día. Un lugar de
    # día completo solo entra por la mañana y ocupa mañana y tarde.
    # Si nada encaja exacto, vale un lugar de tarde por la mañana (o al
    # revés), pero con un punto menos: un cenote por la mañana vale más
    # que un museo que no te gusta nada.
    usados = set()
    circuito = []
    dias_dict = {}
    for dia in range(1, dias + 1):
        lugares_dia = []
        categorias_dia = set()
        huecos = list(slots)
        i = 0
        while i < len(huecos):
            momento = huecos[i]
            elegido = None
            mejor_ajuste = None
            for cand in candidatos:
                if cand['id'] in usados:
                    continue
                if cand.get('categoria') in categorias_dia:
                    continue
                lugar_momento = cand.get('momento')
                if lugar_momento == momento:
                    ajuste = cand['score']
                elif lugar_momento == 'dia' and momento == 'manana':
                    ajuste = cand['score']
                elif {lugar_momento, momento} == {'manana', 'tarde'}:
                    ajuste = cand['score'] - 1
                else:
                    continue
                if mejor_ajuste is None or ajuste > mejor_ajuste:
                    mejor_ajuste = ajuste
                    elegido = cand
            if elegido is None:
                i += 1
                continue
            usados.add(elegido['id'])
            categorias_dia.add(elegido.get('categoria'))
            item = dict(elegido)
            item['dia'] = dia
            # Lo que se muestra es el hueco que ocupa, no el momento
            # ideal del lugar: un cenote de tarde que cae en la mañana
            # es "Mañana". Solo el lugar de día completo se muestra así.
            item['momento'] = ('dia' if elegido.get('momento') == 'dia'
                               else momento)
            item['direccion'] = direccion_completa(item)
            item['maps_link'] = link_mapa_lugar(item)
            lugares_dia.append(item)
            circuito.append(item)
            # Un lugar de día completo se come también el siguiente hueco.
            if elegido.get('momento') == 'dia':
                i += 2
            else:
                i += 1
        dias_dict[dia] = lugares_dia

    # 4. Ordenar el circuito por día y por momento, para que se lea
    # de mañana a noche.
    orden_momento = {'manana': 0, 'dia': 1, 'tarde': 2, 'noche': 3}
    circuito.sort(key=lambda p: (p['dia'], orden_momento.get(p['momento'], 9)))

    # 5. Guía según el gusto dominante.
    gusto_top = max(gustos, key=gustos.get) if any(gustos.values()) else 'playa'
    especialidad = GUIA_POR_GUSTO.get(gusto_top, 'descanso')
    guia = next((g for g in guias if g['especialidad'] == especialidad), guias[0])

    # 5. Mapas por día y mensaje del guía.
    mapas_por_dia = {d: embed_ruta_dia(items)
                     for d, items in dias_dict.items() if items}
    mensaje = generar_mensaje_guia(guia, dias_dict, gustos, gusto_top)

    top_gustos = sorted(gustos, key=gustos.get, reverse=True)
    top_gustos = [g for g in top_gustos if gustos[g] > 0][:3]

    return {
        'gustos': gustos,
        'gustos_top': top_gustos,
        'gusto_principal': gusto_top,
        'guia': guia,
        'circuito': circuito,
        'mapas_por_dia': mapas_por_dia,
        'mensaje_guia': mensaje,
        'dias': dias,
        'presupuesto': presupuesto,
        'acompanantes': acompanantes,
        'ritmo': ritmo,
    }


def generar_mensaje_guia(guia, dias_dict, gustos, gusto_top):
    """El texto con el que el guía presenta el circuito, como si hablara."""
    top = sorted(gustos, key=gustos.get, reverse=True)
    top = [g for g in top if gustos[g] > 0][:2]
    intereses = ' y '.join(NOMBRES_GUSTOS[g] for g in top) or 'de todo un poco'
    partes = [
        f"Hola, soy {guia['nombre']}, tu guía de {NOMBRES_GUSTOS.get(gusto_top, gusto_top)} en la Riviera Maya.",
        f"Vi que lo tuyo es {intereses}, así que armé un circuito pensado en eso.",
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
        partes.append(f"Día {dia_num}: {lista}.")
    partes.append("Toca cada parada para ver cómo llegar y qué encontrarás ahí. ¡Vamos!")
    return ' '.join(partes)


@app.route('/')
def index():
    return render_template('index.html', gustos=GUSTOS,
                           nombres=NOMBRES_GUSTOS)


@app.route('/recomendar', methods=['POST'])
def recomendar():
    data = request.get_json(force=True) or {}
    resultado = armar_circuito(
        gustos=data.get('gustos', {}),
        presupuesto=data.get('presupuesto', 2),
        dias=data.get('dias', 3),
        acompanantes=data.get('acompanantes', 'pareja'),
        ritmo=data.get('ritmo', 'moderado'),
    )
    return jsonify(resultado)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
