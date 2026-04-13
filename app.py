import streamlit as st
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Alpheios JSON to Perseids XML", layout="wide")

def convert_to_perseids_aligned(json_data):
    # Namespace e Raiz
    root = ET.Element("aligned-text", xmlns="http://alpheios.net/namespaces/aligned-text")
    ET.SubElement(root, "language", lnum="L1", **{"xml:lang": "grc"})
    ET.SubElement(root, "language", lnum="L2", **{"xml:lang": "por"})
    
    sentence_node = ET.SubElement(root, "sentence", n="1")
    id_map = {} # De: "1-0-1" Para: "1-1"

    # 1. Extração e Criação dos nós de palavras com Texto
    def build_word_nodes(parent, lang_key, lnum):
        wds = ET.SubElement(parent, "wds", lnum=lnum)
        lang_data = json_data.get(lang_key, {})
        
        # Lógica robusta para encontrar os tokens
        segments = lang_data.get('segments', [])
        if not segments and 'segment' in lang_data:
            segments = [lang_data['segment']]
            
        all_tokens = []
        for seg in segments:
            all_tokens.extend(seg.get('tokens', []))

        for i, tok in enumerate(all_tokens, 1):
            xml_id = f"1-{i}"
            id_map[tok['id']] = xml_id # Mapeia o ID complexo do JSON para o ID simples do XML
            
            w_node = ET.SubElement(wds, "w", n=xml_id)
            text_elem = ET.SubElement(w_node, "text")
            text_elem.text = tok.get('word', '')
        
        return all_tokens

    build_word_nodes(sentence_node, 'origin', 'L1')
    build_word_nodes(sentence_node, 'target', 'L2')

    # 2. Processamento dos Alinhamentos
    # Criamos um mapa de referências baseadas nos IDs do XML
    refs_map = {} 

    for al in json_data.get('alignments', []):
        actions = al.get('actions', {})
        origins = actions.get('origin', [])
        targets = actions.get('target', [])
        
        # Converte IDs do JSON para IDs do XML e armazena as relações
        for o in origins:
            xml_o = id_map.get(o)
            if xml_o:
                if xml_o not in refs_map: refs_map[xml_o] = []
                refs_map[xml_o].extend([id_map[t] for t in targets if t in id_map])

        for t in targets:
            xml_t = id_map.get(t)
            if xml_t:
                if xml_t not in refs_map: refs_map[xml_t] = []
                refs_map[xml_t].extend([id_map[o] for o in origins if o in id_map])

    # 3. Inserção das tags <refs> dentro de cada <w>
    for w_node in sentence_node.findall(".//w"):
        node_xml_id = w_node.get('n')
        if node_xml_id in refs_map:
            # Elimina duplicatas e ordena (ex: "1-5 1-4" vira "1-4 1-5")
            clean_refs = sorted(list(set(refs_map[node_xml_id])))
            if clean_refs:
                refs_elem = ET.SubElement(w_node, "refs", nrefs=" ".join(clean_refs))

    # Exportação formatada
    xml_str = ET.tostring(root, encoding='utf-8')
    return minidom.parseString(xml_str).toprettyxml(indent="    ")

# --- Interface Streamlit ---
st.title("🏛️ Conversor de Alinhamento do XML do Novo Alpheios para XML do Alpheios-Perseids (Texto + Conexões)")
st.markdown("Este conversor mantém o texto original e gera as referências de alinhamento para o Perseids.")

file = st.file_uploader("Suba seu arquivo JSON", type="json")

if file:
    try:
        json_content = json.load(file)
        final_xml = convert_to_perseids_aligned(json_content)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("Visualização do XML Alinhado")
            st.code(final_xml, language="xml")
        with col2:
            st.subheader("Ações")
            st.download_button(
                "Baixar XML para o Perseids", 
                final_xml, 
                file_name=f"alinhado_{file.name.split('.')[0]}.xml",
                mime="text/xml"
            )
            st.success("Texto e alinhamentos processados!")
    except Exception as e:
        st.error(f"Erro na conversão: {e}")
