import streamlit as st
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Conversor Alpheios Final", layout="wide")

def aspirar_tokens(objeto):
    """Varre o JSON inteiro e extrai qualquer objeto que tenha 'word' e um ID."""
    tokens = []
    if isinstance(objeto, dict):
        # Se achamos um dicionário que tem a palavra e o ID (seja 'id' ou 'idWord')
        if 'word' in objeto and ('idWord' in objeto or 'id' in objeto):
            tokens.append({
                'id': objeto.get('idWord') or objeto.get('id'),
                'word': objeto['word'],
                'type': objeto.get('textType', 'unknown') # Para saber se é origin ou target
            })
        else:
            for valor in objeto.values():
                tokens.extend(aspirar_tokens(valor))
    elif isinstance(objeto, list):
        for item in objeto:
            tokens.extend(aspirar_tokens(item))
    return tokens

def converter_para_perseids(data):
    # Base do XML Perseids
    root = ET.Element("aligned-text", xmlns="http://alpheios.net/namespaces/aligned-text")
    ET.SubElement(root, "language", lnum="L1", **{"xml:lang": "grc"})
    ET.SubElement(root, "language", lnum="L2", **{"xml:lang": "por"})
    sentence = ET.SubElement(root, "sentence", n="1")
    
    id_map = {} # Tradutor de ID Alpheios para ID Perseids

    # 1. Aspirar todos os tokens do arquivo
    todos_os_tokens = aspirar_tokens(data)
    
    # Separar o que é grego (L1) e o que é português (L2)
    # No Alpheios, 'origin' é L1 e 'target' é L2
    tokens_l1 = [t for t in todos_os_tokens if t['type'] == 'origin']
    tokens_l2 = [t for t in todos_os_tokens if t['type'] == 'target']

    if not tokens_l1 or not tokens_l2:
        return None

    # Criar palavras L1 (Grego)
    wds1 = ET.SubElement(sentence, "wds", lnum="L1")
    for i, tok in enumerate(tokens_l1, 1):
        p_id = f"1-{i}"
        id_map[tok['id']] = p_id
        w = ET.SubElement(wds1, "w", n=p_id)
        ET.SubElement(w, "text").text = str(tok['word'])

    # Criar palavras L2 (Português)
    wds2 = ET.SubElement(sentence, "wds", lnum="L2")
    for i, tok in enumerate(tokens_l2, 1):
        p_id = f"1-{i}"
        id_map[tok['id']] = p_id
        w = ET.SubElement(wds2, "w", n=p_id)
        ET.SubElement(w, "text").text = str(tok['word'])

    # 2. Processar Alinhamentos
    # O Alpheios guarda os alinhamentos na chave 'alignments'
    alignments = data.get('alignments', [])
    for al in alignments:
        act = al.get('actions', {})
        origins = act.get('origin', [])
        targets = act.get('target', [])
        
        # Conectar palavras
        for o_id in origins:
            if o_id in id_map:
                xml_id = id_map[o_id]
                for w_node in sentence.findall(f".//w[@n='{xml_id}']"):
                    refs = w_node.find('refs')
                    if refs is None: refs = ET.SubElement(w_node, "refs", nrefs="")
                    atuais = refs.get('nrefs').split()
                    novos = [id_map[tid] for tid in targets if tid in id_map]
                    refs.set('nrefs', " ".join(sorted(list(set(atuais + novos)))))

        for t_id in targets:
            if t_id in id_map:
                xml_id = id_map[t_id]
                for w_node in sentence.findall(f".//w[@n='{xml_id}']"):
                    refs = w_node.find('refs')
                    if refs is None: refs = ET.SubElement(w_node, "refs", nrefs="")
                    atuais = refs.get('nrefs').split()
                    novos = [id_map[oid] for oid in origins if oid in id_map]
                    refs.set('nrefs', " ".join(sorted(list(set(atuais + novos)))))

    xml_str = ET.tostring(root, encoding='utf-8')
    return minidom.parseString(xml_str).toprettyxml(indent="    ")

# --- Streamlit ---
st.title("🏛️ Conversor Alpheios ➔ Perseids (V11 Universal)")
st.write("Esta versão usa 'aspiração' de dados para encontrar os tokens em qualquer estrutura.")

file = st.file_uploader("Suba o JSON do Alpheios", type="json")

if file:
    try:
        content = json.load(file)
        result = converter_para_perseids(content)
        if result:
            st.success("XML gerado com sucesso!")
            st.code(result, language="xml")
            st.download_button("Baixar XML", result, file_name="alinhamento.xml")
        else:
            st.error("Erro: O arquivo foi lido, mas nenhuma palavra foi encontrada nas seções de alinhamento.")
    except Exception as e:
        st.error(f"Erro inesperado: {e}")
