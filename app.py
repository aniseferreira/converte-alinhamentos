import streamlit as st
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Conversor Alpheios ➔ Perseids", layout="wide")

def find_tokens(data):
    """
    Busca recursivamente pela lista de tokens dentro do JSON.
    Isso resolve o problema de mudanças na estrutura do Alpheios.
    """
    if isinstance(data, list):
        for item in data:
            result = find_tokens(item)
            if result: return result
    elif isinstance(data, dict):
        if "tokens" in data and isinstance(data["tokens"], list):
            return data["tokens"]
        for key, value in data.items():
            result = find_tokens(value)
            if result: return result
    return None

def convert_to_xml(json_data):
    # Namespace e Raiz do XML
    root = ET.Element("aligned-text", xmlns="http://alpheios.net/namespaces/aligned-text")
    ET.SubElement(root, "language", lnum="L1", **{"xml:lang": "grc"})
    ET.SubElement(root, "language", lnum="L2", **{"xml:lang": "por"})
    
    sentence_node = ET.SubElement(root, "sentence", n="1")
    id_map = {} # De: ID do JSON (ex: 1-0-1) Para: ID do XML (ex: 1-1)

    # 1. Processar L1 (Grego) e L2 (Português)
    def process_lang(lang_key, lnum):
        wds_node = ET.SubElement(sentence_node, "wds", lnum=lnum)
        lang_section = json_data.get(lang_key, {})
        
        # Usa a busca profunda para encontrar os tokens no JSON
        tokens = find_tokens(lang_section)
        
        if not tokens:
            return False

        for i, tok in enumerate(tokens, 1):
            xml_id = f"1-{i}"
            # O ID no JSON Alpheios é tok['id']
            id_map[tok['id']] = xml_id
            
            w_node = ET.SubElement(wds_node, "w", n=xml_id)
            text_node = ET.SubElement(w_node, "text")
            # Pega o conteúdo da chave 'word'
            text_node.text = str(tok.get('word', ''))
        return True

    success_l1 = process_lang('origin', 'L1')
    success_l2 = process_lang('target', 'L2')

    if not success_l1 or not success_l2:
        return None

    # 2. Processar Alinhamentos (Refs)
    align_refs = {}
    for al in json_data.get('alignments', []):
        actions = al.get('actions', {})
        origins = actions.get('origin', [])
        targets = actions.get('target', [])
        
        # Mapeia IDs de origem para destino e vice-versa
        for o in origins:
            if o in id_map:
                if o not in align_refs: align_refs[o] = []
                align_refs[o].extend([id_map[t] for t in targets if t in id_map])
        for t in targets:
            if t in id_map:
                if t not in align_refs: align_refs[t] = []
                align_refs[t].extend([id_map[o] for o in origins if o in id_map])

    # 3. Adicionar as tags <refs>
    for w_node in sentence_node.findall(".//w"):
        xml_id = w_node.get('n')
        # Encontra o ID original do JSON correspondente
        json_id_list = [k for k, v in id_map.items() if v == xml_id]
        if json_id_list:
            json_id = json_id_list[0]
            if json_id in align_refs:
                unique_refs = sorted(list(set(align_refs[json_id])))
                if unique_refs:
                    ET.SubElement(w_node, "refs", nrefs=" ".join(unique_refs))

    # Formata o XML para leitura humana
    xml_str = ET.tostring(root, encoding='utf-8')
    return minidom.parseString(xml_str).toprettyxml(indent="    ")

# --- Interface Streamlit ---
st.title("🏛️ Conversor Alpheios ➔ Perseids (V3 Final)")
st.markdown("Esta versão utiliza busca profunda para localizar o texto no JSON.")

uploaded_file = st.file_uploader("Suba seu arquivo .json", type="json")

if uploaded_file:
    try:
        content = json.load(uploaded_file)
        xml_output = convert_to_xml(content)
        
        if xml_output:
            st.success("Texto e alinhamentos convertidos com sucesso!")
            col1, col2 = st.columns([2, 1])
            with col1:
                st.code(xml_output, language="xml")
            with col2:
                st.download_button("Baixar XML", xml_output, file_name="alinhamento_perseids.xml")
        else:
            st.error("Erro Crítico: Não foi possível localizar a lista de tokens (palavras) dentro do arquivo JSON.")
            st.write("Verifique se este é um arquivo de exportação de ALINHAMENTO do Alpheios.")
            
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
