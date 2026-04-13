import streamlit as st
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Conversor Alpheios ➔ Perseids V5", layout="wide")

def get_tokens_safe(data_part):
    """
    Busca os tokens navegando pela estrutura real: 
    data -> origin/target -> segments -> lista -> tokens
    """
    all_tokens = []
    
    # 1. Tenta acessar a lista de segmentos
    segments = data_part.get('segments', [])
    
    # Caso segments não seja uma lista (raro, mas acontece em certas versões)
    if isinstance(segments, dict):
        segments = [segments]

    for seg in segments:
        tokens = seg.get('tokens', [])
        if isinstance(tokens, list):
            for t in tokens:
                # Validamos se o token tem o formato mínimo esperado
                if isinstance(t, dict) and 'id' in t and 'word' in t:
                    all_tokens.append(t)
    
    return all_tokens

def convert_to_xml(json_data):
    root = ET.Element("aligned-text", xmlns="http://alpheios.net/namespaces/aligned-text")
    ET.SubElement(root, "language", lnum="L1", **{"xml:lang": "grc"})
    ET.SubElement(root, "language", lnum="L2", **{"xml:lang": "por"})
    
    sentence_node = ET.SubElement(root, "sentence", n="1")
    id_map = {}

    def process_lang(lang_key, lnum):
        wds_node = ET.SubElement(sentence_node, "wds", lnum=lnum)
        lang_data = json_data.get(lang_key, {})
        
        tokens = get_tokens_safe(lang_data)
        
        if not tokens:
            st.warning(f"Aviso: Nenhuma palavra encontrada para {lang_key}.")
            return False

        for i, tok in enumerate(tokens, 1):
            xml_id = f"1-{i}"
            id_map[tok['id']] = xml_id
            
            w_node = ET.SubElement(wds_node, "w", n=xml_id)
            text_node = ET.SubElement(w_node, "text")
            text_node.text = str(tok['word'])
        return True

    # Processamento das duas línguas
    success_l1 = process_lang('origin', 'L1')
    success_l2 = process_lang('target', 'L2')

    if not success_l1 or not success_l2:
        return None

    # Mapeamento de Alinhamentos
    align_refs = {}
    for al in json_data.get('alignments', []):
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

    # Inserção das tags <refs>
    for w_node in sentence_node.findall(".//w"):
        xml_id = w_node.get('n')
        orig_json_ids = [k for k, v in id_map.items() if v == xml_id]
        if orig_json_ids:
            oid = orig_json_ids[0]
            if oid in align_refs:
                unique_refs = sorted(list(set(align_refs[oid])))
                if unique_refs:
                    ET.SubElement(w_node, "refs", nrefs=" ".join(unique_refs))

    xml_str = ET.tostring(root, encoding='utf-8')
    return minidom.parseString(xml_str).toprettyxml(indent="    ")

# Interface
st.title("🏛️ Conversor Alpheios ➔ Perseids (Versão de Diagnóstico)")

file = st.file_uploader("Suba o JSON", type="json")

if file:
    try:
        content = json.load(file)
        
        # DEBUG: Mostra no Streamlit se as chaves existem
        st.write("### Diagnóstico do Arquivo:")
        st.write(f"- Chave 'origin' presente: {'origin' in content}")
        st.write(f"- Chave 'target' presente: {'target' in content}")
        st.write(f"- Chave 'alignments' presente: {'alignments' in content}")

        xml_result = convert_to_xml(content)
        
        if xml_result:
            st.success("XML gerado com sucesso!")
            st.code(xml_result, language="xml")
            st.download_button("Baixar XML", xml_result, file_name="alinhamento.xml")
        else:
            st.error("Erro: A estrutura de tokens dentro de 'segments' não foi encontrada.")
            
    except Exception as e:
        st.error(f"Erro fatal: {e}")
