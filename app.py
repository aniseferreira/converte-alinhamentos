import streamlit as st
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Conversor Alpheios ➔ Perseids", layout="wide")

def extract_tokens_from_json(data_part):
    """
    Extrai tokens especificamente da estrutura do Alpheios:
    lang -> segments -> [lista] -> tokens -> [lista]
    """
    tokens_list = []
    if "segments" in data_part:
        for segment in data_part["segments"]:
            if "tokens" in segment:
                for token in segment["tokens"]:
                    # Verifica se é um dicionário de token válido
                    if isinstance(token, dict) and "id" in token and "word" in token:
                        tokens_list.append(token)
    return tokens_list

def convert_to_xml(json_data):
    # Criar raiz do XML
    root = ET.Element("aligned-text", xmlns="http://alpheios.net/namespaces/aligned-text")
    ET.SubElement(root, "language", lnum="L1", **{"xml:lang": "grc"})
    ET.SubElement(root, "language", lnum="L2", **{"xml:lang": "por"})
    
    sentence_node = ET.SubElement(root, "sentence", n="1")
    id_map = {} # De ID Alpheios (ex: 1-0-1) para ID Perseids (ex: 1-1)

    # 1. Processar L1 (Origem) e L2 (Destino)
    def process_lang(lang_key, lnum):
        wds_node = ET.SubElement(sentence_node, "wds", lnum=lnum)
        lang_data = json_data.get(lang_key, {})
        tokens = extract_tokens_from_json(lang_data)
        
        if not tokens:
            return False

        for i, tok in enumerate(tokens, 1):
            xml_id = f"1-{i}"
            id_map[tok["id"]] = xml_id
            
            w_node = ET.SubElement(wds_node, "w", n=xml_id)
            text_node = ET.SubElement(w_node, "text")
            text_node.text = str(tok["word"])
        return True

    # Tenta processar as duas línguas
    has_l1 = process_lang("origin", "L1")
    has_l2 = process_lang("target", "L2")

    if not has_l1 or not has_l2:
        return None

    # 2. Mapear Alinhamentos
    align_refs = {}
    for al in json_data.get("alignments", []):
        actions = al.get("actions", {})
        origins = actions.get("origin", [])
        targets = actions.get("target", [])
        
        for o in origins:
            if o in id_map:
                if o not in align_refs: align_refs[o] = []
                # Adiciona todos os alinhamentos correspondentes
                for t in targets:
                    if t in id_map:
                        align_refs[o].append(id_map[t])
        
        for t in targets:
            if t in id_map:
                if t not in align_refs: align_refs[t] = []
                for o in origins:
                    if o in id_map:
                        align_refs[t].append(id_map[o])

    # 3. Adicionar tags <refs> ao XML
    for w_node in sentence_node.findall(".//w"):
        xml_id = w_node.get("n")
        # Encontra o ID original do JSON (ex: 1-0-5) que gerou este 1-1
        original_json_id = [k for k, v in id_map.items() if v == xml_id]
        
        if original_json_id:
            oid = original_json_id[0]
            if oid in align_refs:
                # Remove duplicatas e ordena as referências
                unique_refs = sorted(list(set(align_refs[oid])))
                if unique_refs:
                    ET.SubElement(w_node, "refs", nrefs=" ".join(unique_refs))

    # Formatar string XML
    xml_str = ET.tostring(root, encoding="utf-8")
    return minidom.parseString(xml_str).toprettyxml(indent="    ")

# --- Interface ---
st.title("🏛️ Conversor Alpheios ➔ Perseids (V4)")

file = st.file_uploader("Suba o JSON aqui", type="json")

if file:
    try:
        data = json.load(file)
        xml_result = convert_to_xml(data)
        
        if xml_result:
            st.success("Conversão realizada!")
            st.code(xml_result, language="xml")
            st.download_button("Baixar XML", xml_result, file_name="alinhamento.xml")
        else:
            st.error("Erro: Não foi possível extrair os textos. Verifique se o JSON contém 'origin' e 'target' com a estrutura de tokens correta.")
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
