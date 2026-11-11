"""E.D.I.T.H. — la IA de Mayamind.

Edith platica con el turista sobre su circuito: le explica por qué le tocó
cada lugar, le dice dónde le conviene hospedarse, qué comer, cómo moverse
y le propone cambios.

Usa el mismo núcleo que A.R.I.A.: Ollama en local con llama3 (sin API key,
sin nube). Si Ollama no está prendido (por ejemplo, en Render o Netlify),
Edith contesta con reglas propias para que la demo nunca se quede muda.
"""
import json
import os
import unicodedata
import urllib.request
from collections import Counter

OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434/api/chat')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3')

SYSTEM_PROMPT = """Eres E.D.I.T.H., la inteligencia artificial de Mayamind, creada por Nivara.
Ayudas a turistas a disfrutar su circuito por la Riviera Maya (Cancún, Playa del Carmen,
Tulum, Cozumel, Isla Mujeres, Akumal, Valladolid, Chichén Itzá).
Hablas en español, cálida, segura y breve: máximo 4 oraciones, sin listas largas.
Siempre te basas en el circuito del turista que viene abajo. No inventes precios exactos:
si no sabes un dato, dilo y da una recomendación práctica.
Cuando hable de hospedaje, recomienda la zona donde caen más paradas de su circuito."""


def zona_hospedaje(circuito):
    """La zona donde le conviene dormir: donde caen más paradas."""
    if not circuito:
        return None
    conteo = Counter(p.get('ubicacion', 'Cancún') for p in circuito)
    zona, veces = conteo.most_common(1)[0]
    return {'zona': zona, 'paradas': veces, 'total': len(circuito)}


def resumen_circuito(datos):
    """Texto corto del circuito para dárselo de contexto a la IA."""
    if not datos:
        return 'El turista todavía no arma su circuito.'
    lineas = []
    gustos = datos.get('gustos_top') or []
    if gustos:
        lineas.append('Gustos principales: ' + ', '.join(gustos) + '.')
    lineas.append(f"Viaja: {datos.get('acompanantes', '?')}, {datos.get('dias', '?')} días, "
                  f"ritmo {datos.get('ritmo', '?')}, presupuesto {datos.get('presupuesto', '?')}/3.")
    for p in datos.get('circuito', []):
        lineas.append(f"Día {p['dia']} ({p['momento']}): {p['nombre']} en {p.get('ubicacion')} "
                      f"— {p.get('descripcion', '')}")
    z = zona_hospedaje(datos.get('circuito', []))
    if z:
        lineas.append(f"Zona sugerida para hospedarse: {z['zona']} "
                      f"({z['paradas']} de {z['total']} paradas).")
    return '\n'.join(lineas)


def preguntar_ollama(pregunta, datos, historial=None):
    """Le pregunta a llama3 por Ollama. Regresa None si no está prendido."""
    mensajes = [{'role': 'system',
                 'content': SYSTEM_PROMPT + '\n\nCIRCUITO DEL TURISTA:\n' + resumen_circuito(datos)}]
    for m in (historial or [])[-8:]:
        if m.get('role') in ('user', 'assistant') and m.get('content'):
            mensajes.append({'role': m['role'], 'content': str(m['content'])[:1000]})
    mensajes.append({'role': 'user', 'content': pregunta})
    cuerpo = json.dumps({'model': OLLAMA_MODEL, 'messages': mensajes,
                         'stream': False}).encode('utf-8')
    try:
        req = urllib.request.Request(OLLAMA_URL, data=cuerpo,
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=60) as r:
            respuesta = json.loads(r.read().decode('utf-8'))
        texto = respuesta.get('message', {}).get('content', '').strip()
        return texto or None
    except Exception:
        return None


def _sin_acentos(texto):
    t = unicodedata.normalize('NFD', texto or '')
    return ''.join(c for c in t if unicodedata.category(c) != 'Mn').lower()


def _tiene(texto, *palabras):
    return any(_sin_acentos(p) in texto for p in palabras)


def respuesta_reglas(pregunta, datos):
    """Respuestas de respaldo cuando no hay IA local."""
    q = ' ' + _sin_acentos(pregunta) + ' '
    circuito = (datos or {}).get('circuito', [])
    if not circuito:
        return ('Primero arma tu circuito con tus gustos y luego platicamos: '
                'te digo dónde hospedarte, qué comer y cómo moverte.')

    z = zona_hospedaje(circuito)
    nombres = [p['nombre'] for p in circuito]

    if _tiene(q, 'hotel', 'hosped', 'dormir', 'duermo', 'quedar', 'glamping', 'hostal'):
        return (f"Te conviene hospedarte en {z['zona']}: ahí caen {z['paradas']} de tus "
                f"{z['total']} paradas, así que pierdes menos tiempo en carretera. "
                'Si quieres algo distinto, un glamping cerca de Tulum o Valladolid '
                'combina perfecto con cenotes y zonas arqueológicas.')

    if _tiene(q, 'comer', 'comida', 'que como', 'como algo', 'hambre', 'probar', 'restaur', 'cenar', 'desayun', 'taco'):
        gastro = [p['nombre'] for p in circuito if 'gastronomia' in p.get('tags', [])]
        if gastro:
            return (f"Tu momento fuerte de comida es {gastro[0]}. Además, prueba cochinita "
                    'pibil, panuchos y marquesitas; en las zonas arqueológicas lleva algo '
                    'ligero porque adentro casi no hay dónde comer.')
        return ('Prueba cochinita pibil, panuchos, ceviche y marquesitas. Los mejores '
                'precios están en los mercados y loncherías del centro, no en la zona hotelera.')

    if _tiene(q, 'llegar', 'llego', 'mover', 'muevo', 'traslad', 'transporte', 'carro', 'auto', 'ado', 'taxi', 'colectivo'):
        return ('Entre Cancún, Playa y Tulum lo más práctico es el ADO o rentar auto. '
                'En Playa del Carmen y Tulum los colectivos son baratos. Para Cozumel e '
                'Isla Mujeres tomas ferry. Cada parada tiene su botón "Cómo llegar".')

    if _tiene(q, 'cuánto', 'cuanto', 'precio', 'costo', 'caro', 'barato', 'dinero', 'presupuesto'):
        return ('Tu circuito ya está filtrado a tu presupuesto. Los parques como Xcaret o '
                'Xplor son lo más caro; playas, cenotes chicos y mercados son lo más barato. '
                'Compra entradas en línea con anticipación: casi siempre salen más baratas.')

    if _tiene(q, 'llev', 'ropa', 'mochila', 'bloqueador', 'empac'):
        return ('Lleva bloqueador biodegradable (en cenotes es obligatorio), traje de baño, '
                'sombrero, agua y efectivo. Para las zonas arqueológicas, tenis cómodos.')

    if _tiene(q, 'clima', 'lluvia', 'llueve', 'calor', 'huracán', 'huracan'):
        return ('Hace calor casi todo el año. Haz lo arqueológico temprano por el sol y deja '
                'cenotes o playa para la tarde. Si llueve, cambia la playa por un cenote '
                'o el Museo Maya.')

    if _tiene(q, 'por qué', 'porque', 'por que', 'elegiste', 'tocó', 'toco'):
        gustos = (datos or {}).get('gustos_top') or []
        g = ' y '.join(gustos[:2]) if gustos else 'tus gustos'
        return (f"Te armé el circuito según lo que más te gusta: {g}. Cada lugar suma "
                'puntos por cada interés que cubre, así que primero entran los que mejor '
                f"te quedan. Por eso arrancas con {nombres[0]}.")

    if _tiene(q, 'cambi', 'otro', 'no me gusta', 'quitar', 'reemplaz'):
        return ('Mueve los gustos de arriba y vuelve a darle a "Armar mi circuito": el '
                'algoritmo lo rehace al momento. Si bajas un gusto a 0, esos lugares ya no salen.')

    if _tiene(q, 'hola', 'buenas', 'quién eres', 'quien eres'):
        return ('Hola, soy Edith, la IA de Mayamind. Ya vi tu circuito: pregúntame dónde '
                'hospedarte, qué comer, cómo moverte o qué llevar.')

    return (f"Tu circuito tiene {len(circuito)} paradas, empezando por {nombres[0]}. "
            'Pregúntame dónde hospedarte, qué comer, cómo moverte, qué llevar o cuánto '
            'gastar y te ayudo.')


def preguntar(pregunta, datos, historial=None):
    """Punto de entrada: intenta llama3 y, si no hay, usa reglas."""
    texto = preguntar_ollama(pregunta, datos, historial)
    if texto:
        return {'respuesta': texto, 'motor': 'llama3'}
    return {'respuesta': respuesta_reglas(pregunta, datos), 'motor': 'reglas'}
