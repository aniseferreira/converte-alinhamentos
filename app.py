import streamlit as st
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Conversor Alpheios -> Perseids", layout="wide")

def get_tokens_anywhere(obj):
    """Busca exaustiva por qualquer lista que contenha dicionários com 'word'."""
    tokens = []
    if isinstance(obj, dict):
        if 'tokens' in obj and isinstance(obj['tokens'], list):
            for t in obj['tokens']:
                if isinstance(t, dict) and 'word' in t:
                    tokens.append(t)
        for v in obj.values():
            tokens.extend(get_tokens_anywhere(v))
    elif isinstance(obj, list):
        for item in obj:
            tokens.extend(get_tokens_anywhere(item))
    return tokens

def convert_to_perseids(data):
    root = ET.Element("aligned-text", xmlns="http://alpheios.net/namespaces/aligned-text")
    ET.SubElement(root, "language", lnum="L1", **{"xml:lang": "grc"})
    ET.SubElement(root, "language", lnum="L2", **{"xml:lang": "por"})
    sentence_node = ET.SubElement(root, "sentence", n="1")
    
    id_map = {} # Mapeia ID original para 1-1, 1-2...

    # Extração de tokens de L1 e L2
    # Nos seus arquivos, 'origin' e 'target' são as chaves principais
    origin_tokens = get_tokens_anywhere(data.get('origin', {}))
    target_tokens = get_tokens_anywhere(data.get('target', {}))

    if not origin_tokens or not target_tokens:
        return None

    # Monta WDS L1
    wds1 = ET.SubElement(sentence_node, "wds", lnum="L1")
    for i, tok in enumerate(origin_tokens, 1):
        xml_id = f"1-{i}"
        original_id = tok.get('idWord') or tok.get('id')
        id_map[original_id] = xml_id
        w = ET.SubElement(wds1, "w", n=xml_id)
        ET.SubElement(w, "text").text = str(tok['word'])

    # Monta WDS L2
    wds2 = ET.SubElement(sentence_node, "wds", lnum="L2")
    for i, tok in enumerate(target_tokens, 1):
        xml_id = f"1-{i}"
        original_id = tok.get('idWord') or tok.get('id')
        id_map[original_id] = xml_id
        w = ET.SubElement(wds2, "w", n=xml_id)
        ET.SubElement(w, "text").text = str(tok['word'])

    # Alinhamentos
    alignments = data.get('alignments', [])
    for al in alignments:
        # Pega os IDs de origem e destino
        actions = al.get('actions', {})
        o_ids = actions.get('origin', [])
        t_ids = actions.get('target', [])
        
        # Cria as referências cruzadas
        for o_id in o_ids:
            if o_id in id_map:
                xml_o = id_map[o_id]
                w_node = sentence_node.find(f".//w[@n='{xml_o}']")
                if w_node is not None:
                    refs = w_node.find('refs')
                    if refs is None: refs = ET.SubElement(w_node, "refs", nrefs="")
                    current = refs.get('nrefs').split()
                    added = [id_map[tid] for tid in t_ids if tid in id_map]
                    refs.set('nrefs', " ".join(sorted(list(set(current + added)))))

        for t_id in t_ids:
            if t_id in id_map:
                xml_t = id_map[t_id]
                w_node = sentence_node.find(f".//w[@n='{xml_t}']")
                if w_node is not None:
                    refs = w_node.find('refs')
                    if refs is None: refs = ET.SubElement(w_node, "refs", nrefs="")
                    current = refs.get('nrefs').split()
                    added = [id_map[oid] for oid in o_ids if oid in id_map]
                    refs.set('nrefs', " ".join(sorted(list(set(current + added)))))

    xml_str = ET.tostring(root, encoding='utf-8')
    return minidom.parseString(xml_str).toprettyxml(indent="    ")

st.title("Conversor Alpheios (JSON) -> Perseids XML")

file = st.file_uploader("Suba o arquivo JSON", type="json")

if file:
    content = json.load(file)
    # Debug visual para o usuário
    st.write("Estrutura detectada. Tentando converter...")
    
    output = convert_to_perseids(content)
    if output:
        st.code(output, language="xml")
        st.download_button("Baixar XML", output, file_name="alinhamento.xml")
    else:
        st.error("Ainda não conseguimos extrair os dados. A estrutura desse JSON é diferente das anteriores.")
