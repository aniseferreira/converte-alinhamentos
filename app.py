import streamlit as st
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Conversor Alpheios ➔ Perseids", layout="wide")

def convert_to_xml(json_data):
    # Inicialização do XML
    root = ET.Element("aligned-text", xmlns="http://alpheios.net/namespaces/aligned-text")
    ET.SubElement(root, "language", lnum="L1", **{"xml:lang": "grc"})
    ET.SubElement(root, "language", lnum="L2", **{"xml:lang": "por"})
    
    sentence_node = ET.SubElement(root, "sentence", n="1")
    id_map = {}
    
    def extract_tokens(data_path):
        """Extrai tokens lidando com variações de estrutura do Alpheios."""
        tokens = []
        # Tenta encontrar a lista de segmentos
        segments = data_path.get('segments', [])
        if not segments and 'segment' in data_path:
            segments = [data_path['segment']]
            
        for seg in segments:
            tokens.extend(seg.get('tokens', []))
        return tokens

    def build_wds(parent, lang_key, lnum):
        wds_node = ET.SubElement(parent, "wds", lnum=lnum)
        lang_data = json_data.get(lang_key, {})
        tokens = extract_tokens(lang_data)
        
        for i, tok in enumerate(tokens, 1):
            xml_id = f"1-{i}"
            id_map[tok['id']] = xml_id
            w = ET.SubElement(wds_node, "w", n=xml_id)
            text = ET.SubElement(w, "text")
            text.text = tok.get('word', '')
            
    # Constrói as palavras para Grego (L1) e Português (L2)
    build_wds(sentence_node, 'origin', 'L1')
    build_wds(sentence_node, 'target', 'L2')

    # Processamento de Alinhamentos (Refs)
    align_refs = {}
    for al in json_data.get('alignments', []):
        actions = al.get('actions', {})
        orig_ids = actions.get('origin', [])
        targ_ids = actions.get('target', [])
        
        # Mapeia origem para destino e vice-versa
        for o in orig_ids:
            if o not in align_refs: align_refs[o] = []
            align_refs[o].extend([id_map[t] for t in targ_ids if t in id_map])
        for t in targ_ids:
            if t not in align_refs: align_refs[t] = []
            align_refs[t].extend([id_map[o] for o in orig_ids if o in id_map])

    # Insere as referências no XML
    for w_node in sentence_node.findall(".//w"):
        xml_id = w_node.get('n')
        # Localiza o ID original do JSON
        json_id = [k for k, v in id_map.items() if v == xml_id]
        if json_id and json_id[0] in align_refs:
            refs = sorted(list(set(align_refs[json_id[0]])))
            if refs:
                ET.SubElement(w_node, "refs", nrefs=" ".join(refs))

    xml_str = ET.tostring(root, encoding='utf-8')
    return minidom.parseString(xml_str).toprettyxml(indent="    ")

# Interface Streamlit
st.title("🏛️ Conversor de JSON do Novo Alpheios para XML do Alpheios-Perseids")
st.info("Arraste qualquer um dos seus arquivos JSON (Odisseia ou Fábula).")

uploaded_file = st.file_uploader("Arquivo JSON", type="json")

if uploaded_file:
    try:
        content = json.load(uploaded_file)
        result_xml = convert_to_xml(content)
        
        col1, col2 = st.columns(2)
        with col1:
            st.code(result_xml, language="xml")
        with col2:
            st.success("Conversão pronta!")
            st.download_button("Baixar XML", result_xml, file_name="alinhamento.xml")
    except Exception as e:
        st.error(f"Erro ao processar: {e}")
        st.write("Dica: Verifique se o arquivo é um export válido do Alpheios Alignment Editor.")
