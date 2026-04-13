import streamlit as st
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Conversor Alpheios Universal", layout="wide")

def deep_search(obj, key):
    """Busca uma chave em qualquer nível do JSON."""
    if key in obj: return obj[key]
    if isinstance(obj, dict):
        for v in obj.values():
            if isinstance(v, (dict, list)):
                item = deep_search(v, key)
                if item is not None: return item
    elif isinstance(obj, list):
        for v in obj:
            item = deep_search(v, key)
            if item is not None: return item
    return None

def extract_tokens(data_root):
    """Extrai tokens independente da profundidade."""
    # Tenta achar 'segments' dentro da parte de texto (origin ou target)
    segments = deep_search(data_root, 'segments')
    tokens_found = []
    
    if isinstance(segments, list):
        for seg in segments:
            if isinstance(seg, dict) and 'tokens' in seg:
                tokens_found.extend(seg['tokens'])
    elif isinstance(segments, dict) and 'tokens' in segments:
        tokens_found.extend(segments['tokens'])
        
    return tokens_found

def convert_to_xml(data):
    root = ET.Element("aligned-text", xmlns="http://alpheios.net/namespaces/aligned-text")
    ET.SubElement(root, "language", lnum="L1", **{"xml:lang": "grc"})
    ET.SubElement(root, "language", lnum="L2", **{"xml:lang": "por"})
    
    sentence_node = ET.SubElement(root, "sentence", n="1")
    id_map = {}

    # Localizar origin e target no JSON (pode estar na raiz ou dentro de um objeto)
    origin_data = data.get('origin') or deep_search(data, 'origin')
    target_data = data.get('target') or deep_search(data, 'target')
    alignments_data = data.get('alignments') or deep_search(data, 'alignments') or []

    def process_lang(lang_data, lnum):
        if not lang_data: return False
        wds_node = ET.SubElement(sentence_node, "wds", lnum=lnum)
        tokens = extract_tokens(lang_data)
        
        if not tokens: return False

        for i, tok in enumerate(tokens, 1):
            # O Alpheios usa 'idWord' ou 'id'
            t_id = tok.get('idWord') or tok.get('id')
            word = tok.get('word', '')
            
            xml_id = f"1-{i}"
            id_map[t_id] = xml_id
            
            w_node = ET.SubElement(wds_node, "w", n=xml_id)
            text_node = ET.SubElement(w_node, "text")
            text_node.text = str(word)
        return True

    if not process_lang(origin_data, 'L1') or not process_lang(target_data, 'L2'):
        return None

    # Processar Alinhamentos
    for al in alignments_data:
        actions = al.get('actions', {})
        origins = actions.get('origin', [])
        targets = actions.get('target', [])
        
        # Mapear refs nos nós XML já criados
        for o_id in origins:
            xml_o = id_map.get(o_id)
            if xml_o:
                # Localizar o nó <w> correspondente
                for w in sentence_node.findall(f".//w[@n='{xml_o}']"):
                    refs = w.find('refs')
                    if refs is None: refs = ET.SubElement(w, "refs", nrefs="")
                    
                    current_refs = refs.get('nrefs').split()
                    new_refs = [id_map[t] for t in targets if t in id_map]
                    refs.set('nrefs', " ".join(sorted(list(set(current_refs + new_refs)))))

        # Fazer o mesmo para o target (bidirecional)
        for t_id in targets:
            xml_t = id_map.get(t_id)
            if xml_t:
                for w in sentence_node.findall(f".//w[@n='{xml_t}']"):
                    refs = w.find('refs')
                    if refs is None: refs = ET.SubElement(w, "refs", nrefs="")
                    current_refs = refs.get('nrefs').split()
                    new_refs = [id_map[o] for o in origins if o in id_map]
                    refs.set('nrefs', " ".join(sorted(list(set(current_refs + new_refs)))))

    xml_str = ET.tostring(root, encoding='utf-8')
    return minidom.parseString(xml_str).toprettyxml(indent="    ")

st.title("🏛️ Conversor Alpheios ➔ Perseids (Versão Universal)")

file = st.file_uploader("Suba o JSON", type="json")

if file:
    try:
        content = json.load(file)
        xml_result = convert_to_xml(content)
        
        if xml_result:
            st.success("XML gerado com sucesso!")
            st.code(xml_result, language="xml")
            st.download_button("Baixar XML", xml_result, file_name="alinhamento.xml")
        else:
            st.error("Erro: Não foi possível localizar os dados de texto no arquivo.")
    except Exception as e:
        st.error(f"Erro fatal: {e}")
