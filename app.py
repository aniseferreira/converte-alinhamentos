import streamlit as st
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Conversor Alpheios PRO", layout="wide")

def find_all_tokens(data_root):
    """Varre o JSON em busca de qualquer objeto que tenha 'idWord' e 'word'."""
    tokens = []
    if isinstance(data_root, dict):
        if 'idWord' in data_root and 'word' in data_root:
            return [data_root]
        for v in data_root.values():
            tokens.extend(find_all_tokens(v))
    elif isinstance(data_root, list):
        for item in data_root:
            tokens.extend(find_all_tokens(item))
    return tokens

def convert_alpheios_to_perseids(data):
    # Inicializa XML
    root = ET.Element("aligned-text", xmlns="http://alpheios.net/namespaces/aligned-text")
    ET.SubElement(root, "language", lnum="L1", **{"xml:lang": "grc"})
    ET.SubElement(root, "language", lnum="L2", **{"xml:lang": "por"})
    sentence_node = ET.SubElement(root, "sentence", n="1")
    
    # Busca tokens em origin e target
    all_tokens_origin = find_all_tokens(data.get('origin', {}))
    all_tokens_target = find_all_tokens(data.get('target', {}))
    
    if not all_tokens_origin or not all_tokens_target:
        return None

    id_map = {} # Mapeia ID do Alpheios (1-0-1) para Perseids (1-1)

    # Constrói WDS L1 (Grego)
    wds1 = ET.SubElement(sentence_node, "wds", lnum="L1")
    for i, tok in enumerate(all_tokens_origin, 1):
        p_id = f"1-{i}"
        id_map[tok['idWord']] = p_id
        w = ET.SubElement(wds1, "w", n=p_id)
        ET.SubElement(w, "text").text = str(tok['word'])

    # Constrói WDS L2 (Português)
    wds2 = ET.SubElement(sentence_node, "wds", lnum="L2")
    for i, tok in enumerate(all_tokens_target, 1):
        p_id = f"1-{i}"
        id_map[tok['idWord']] = p_id
        w = ET.SubElement(wds2, "w", n=p_id)
        ET.SubElement(w, "text").text = str(tok['word'])

    # Processa Alinhamentos
    alignments = data.get('alignments', [])
    for al in alignments:
        actions = al.get('actions', {})
        origins = actions.get('origin', [])
        targets = actions.get('target', [])
        
        # Cria as referências cruzadas
        for o_id in origins:
            if o_id in id_map:
                xml_id = id_map[o_id]
                w_node = sentence_node.find(f".//w[@n='{xml_id}']")
                if w_node is not None:
                    refs = w_node.find('refs')
                    if refs is None: refs = ET.SubElement(w_node, "refs", nrefs="")
                    current = refs.get('nrefs').split()
                    new = [id_map[tid] for tid in targets if tid in id_map]
                    refs.set('nrefs', " ".join(sorted(list(set(current + new)))))

        for t_id in targets:
            if t_id in id_map:
                xml_id = id_map[t_id]
                w_node = sentence_node.find(f".//w[@n='{xml_id}']")
                if w_node is not None:
                    refs = w_node.find('refs')
                    if refs is None: refs = ET.SubElement(w_node, "refs", nrefs="")
                    current = refs.get('nrefs').split()
                    new = [id_map[oid] for oid in origins if oid in id_map]
                    refs.set('nrefs', " ".join(sorted(list(set(current + new)))))

    xml_str = ET.tostring(root, encoding='utf-8')
    return minidom.parseString(xml_str).toprettyxml(indent="    ")

# Interface Streamlit
st.title("Conversor Alpheios JSON ➔ Perseids XML")

uploaded_file = st.file_uploader("Suba o arquivo JSON", type="json")

if uploaded_file:
    try:
        data = json.load(uploaded_file)
        result = convert_alpheios_to_perseids(data)
        
        if result:
            st.success("Conversão concluída com sucesso!")
            st.code(result, language="xml")
            st.download_button("Baixar XML", result, file_name="alinhamento.xml")
        else:
            st.error("Erro: Não foi possível extrair palavras do JSON. Verifique se é um export do Alpheios.")
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
