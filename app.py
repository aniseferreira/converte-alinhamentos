import streamlit as st
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Conversor Alpheios ➔ Perseids", layout="wide")

def find_tokens_list(obj):
    """
    Busca exaustiva pela lista de tokens. 
    Nos seus ficheiros, o caminho é origin -> segments -> [0] -> tokens
    """
    if isinstance(obj, dict):
        if "tokens" in obj and isinstance(obj["tokens"], list):
            return obj["tokens"]
        for v in obj.values():
            res = find_tokens_list(v)
            if res: return res
    elif isinstance(obj, list):
        for item in obj:
            res = find_tokens_list(item)
            if res: return res
    return None

def convert_to_xml(json_data):
    root = ET.Element("aligned-text", xmlns="http://alpheios.net/namespaces/aligned-text")
    ET.SubElement(root, "language", lnum="L1", **{"xml:lang": "grc"})
    ET.SubElement(root, "language", lnum="L2", **{"xml:lang": "por"})
    
    sentence_node = ET.SubElement(root, "sentence", n="1")
    id_map = {}

    def process_lang(lang_key, lnum):
        wds_node = ET.SubElement(sentence_node, "wds", lnum=lnum)
        section = json_data.get(lang_key, {})
        tokens = find_tokens_list(section)
        
        if not tokens:
            return False

        count = 1
        for tok in tokens:
            # Verifica se o token é um dicionário e tem os campos necessários
            if isinstance(tok, dict) and "id" in tok and "word" in tok:
                xml_id = f"1-{count}"
                id_map[tok["id"]] = xml_id
                
                w_node = ET.SubElement(wds_node, "w", n=xml_id)
                text_node = ET.SubElement(w_node, "text")
                text_node.text = str(tok["word"])
                count += 1
        return True

    if not process_lang('origin', 'L1') or not process_lang('target', 'L2'):
        return None

    # Processar Alinhamentos
    align_refs = {}
    for al in json_data.get('alignments', []):
        actions = al.get('actions', {})
        # O Alpheios usa 'origin' e 'target' dentro de 'actions'
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

    # Adicionar as tags <refs>
    for w_node in sentence_node.findall(".//w"):
        xml_id = w_node.get('n')
        # Localizar o ID original do JSON que gerou este xml_id
        orig_ids = [k for k, v in id_map.items() if v == xml_id]
        if orig_ids:
            oid = orig_ids[0]
            if oid in align_refs:
                unique_refs = sorted(list(set(align_refs[oid])))
                if unique_refs:
                    ET.SubElement(w_node, "refs", nrefs=" ".join(unique_refs))

    xml_str = ET.tostring(root, encoding='utf-8')
    return minidom.parseString(xml_str).toprettyxml(indent="    ")

st.title("🏛️ Conversor Alpheios para Perseids")

uploaded_file = st.file_uploader("Suba o JSON", type="json")

if uploaded_file:
    try:
        data = json.load(uploaded_file)
        xml_output = convert_to_xml(data)
        
        if xml_output:
            st.success("Conversão concluída!")
            st.code(xml_output, language="xml")
            st.download_button("Baixar XML", xml_output, file_name="alinhamento.xml")
        else:
            st.error("Não foi possível extrair os textos. Verifique se o JSON contém a chave 'origin' e 'target' com 'tokens'.")
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
