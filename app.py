import streamlit as st
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Conversor Alinhamento Total", layout="wide")

def convert_to_xml(data):
    # Namespace e Raiz
    root = ET.Element("aligned-text", xmlns="http://alpheios.net/namespaces/aligned-text")
    ET.SubElement(root, "language", lnum="L1", **{"xml:lang": "grc"})
    ET.SubElement(root, "language", lnum="L2", **{"xml:lang": "por"})
    
    sentence_node = ET.SubElement(root, "sentence", n="1")
    id_map = {}

    def process_language(lang_key, lnum):
        wds_node = ET.SubElement(sentence_node, "wds", lnum=lnum)
        
        # Acesso robusto aos tokens: tenta diferentes caminhos comuns no JSON do Alpheios
        lang_data = data.get(lang_key, {})
        segments = lang_data.get('segments', [])
        
        tokens = []
        for seg in segments:
            tokens.extend(seg.get('tokens', []))
        
        # Se não encontrou em 'segments', tenta procurar na raiz do objeto de língua
        if not tokens:
            tokens = lang_data.get('tokens', [])

        for i, tok in enumerate(tokens, 1):
            xml_id = f"1-{i}"
            id_map[tok['id']] = xml_id
            
            w_node = ET.SubElement(wds_node, "w", n=xml_id)
            text_node = ET.SubElement(w_node, "text")
            text_node.text = str(tok.get('word', '')) # Garante que o texto entre aqui

    # 1. Criar as palavras (O texto DEVE aparecer aqui)
    process_language('origin', 'L1')
    process_language('target', 'L2')

    # 2. Criar os alinhamentos (as referências cruzadas)
    align_refs = {}
    for al in data.get('alignments', []):
        actions = al.get('actions', {})
        origins = actions.get('origin', [])
        targets = actions.get('target', [])
        
        for o in origins:
            if o in id_map:
                if o not in align_refs: align_refs[o] = []
                align_refs[o].extend([id_map[t] for t in targets if t in id_map])
        for t in targets:
            if t in id_map:
                if t not in align_refs: align_refs[t] = []
                align_refs[t].extend([id_map[o] for o in origins if o in id_map])

    # 3. Inserir as tags <refs> dentro de cada <w>
    for w_node in sentence_node.findall(".//w"):
        xml_id = w_node.get('n')
        # Busca o ID original do JSON para este nó XML
        json_id = [k for k, v in id_map.items() if v == xml_id]
        if json_id and json_id[0] in align_refs:
            unique_refs = sorted(list(set(align_refs[json_id[0]])))
            if unique_refs:
                ET.SubElement(w_node, "refs", nrefs=" ".join(unique_refs))

    xml_str = ET.tostring(root, encoding='utf-8')
    return minidom.parseString(xml_str).toprettyxml(indent="    ")

# Interface Streamlit
st.title("🏛️ Conversor de Alinhamento Alpheios(json) ➔ Perseids (xml) (Texto + Alinhamento)")

file = st.file_uploader("Suba o JSON", type="json")

if file:
    try:
        content = json.load(file)
        xml_result = convert_to_xml(content)
        
        if "<text>" not in xml_result:
            st.error("Atenção: O texto não foi detectado nos tokens. Verifique a estrutura do JSON.")
        
        st.code(xml_result, language="xml")
        st.download_button("Baixar XML", xml_result, file_name="alinhamento.xml")
    except Exception as e:
        st.error(f"Erro: {e}")
