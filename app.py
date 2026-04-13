import streamlit as st
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Conversor Alpheios Final", layout="wide")

def get_tokens_from_alpheios(data_part):
    """
    Busca os tokens no caminho específico: 
    data -> alignedText -> segments -> tokens
    Ou data -> segments -> tokens
    """
    # 1. Tenta acessar via alignedText (comum nos seus arquivos recentes)
    container = data_part.get('alignedText', data_part)
    
    # 2. Pega a lista de segmentos
    segments = container.get('segments', [])
    if isinstance(segments, dict): segments = [segments]
    
    all_tokens = []
    for seg in segments:
        tokens = seg.get('tokens', [])
        if isinstance(tokens, list):
            for t in tokens:
                # O Alpheios usa 'idWord' como identificador único nos seus JSONs
                tid = t.get('idWord') or t.get('id')
                word = t.get('word')
                if tid and word is not None:
                    all_tokens.append({'id': tid, 'word': word})
    return all_tokens

def convert_to_xml(json_data):
    root = ET.Element("aligned-text", xmlns="http://alpheios.net/namespaces/aligned-text")
    ET.SubElement(root, "language", lnum="L1", **{"xml:lang": "grc"})
    ET.SubElement(root, "language", lnum="L2", **{"xml:lang": "por"})
    
    sentence_node = ET.SubElement(root, "sentence", n="1")
    id_map = {} # De '1-0-1' para '1-1'

    # Localizar origin e target
    origin_part = json_data.get('origin', {})
    target_part = json_data.get('target', {})

    def process_lang(lang_data, lnum):
        tokens = get_tokens_from_alpheios(lang_data)
        if not tokens: return False
        
        wds_node = ET.SubElement(sentence_node, "wds", lnum=lnum)
        for i, tok in enumerate(tokens, 1):
            xml_id = f"1-{i}"
            id_map[tok['id']] = xml_id
            
            w_node = ET.SubElement(wds_node, "w", n=xml_id)
            text_node = ET.SubElement(w_node, "text")
            text_node.text = str(tok['word'])
        return True

    # 1. Extrair Textos
    if not process_lang(origin_part, 'L1') or not process_lang(target_part, 'L2'):
        return None

    # 2. Mapear Alinhamentos (Refs)
    # A seção 'alignments' costuma estar na raiz do JSON
    for al in json_data.get('alignments', []):
        actions = al.get('actions', {})
        origins = actions.get('origin', [])
        targets = actions.get('target', [])
        
        # Para cada palavra de origem, adiciona as referências de destino
        for o_id in origins:
            if o_id in id_map:
                xml_o = id_map[o_id]
                # Busca o nó <w> correspondente no XML
                for w in sentence_node.findall(f".//w[@n='{xml_o}']"):
                    refs = w.find('refs')
                    if refs is None: refs = ET.SubElement(w, "refs", nrefs="")
                    
                    # Atualiza a lista de nrefs
                    existing = refs.get('nrefs').split()
                    to_add = [id_map[t] for t in targets if t in id_map]
                    refs.set('nrefs', " ".join(sorted(list(set(existing + to_add)))))

        # Faz o inverso (Português para Grego)
        for t_id in targets:
            if t_id in id_map:
                xml_t = id_map[t_id]
                for w in sentence_node.findall(f".//w[@n='{xml_t}']"):
                    refs = w.find('refs')
                    if refs is None: refs = ET.SubElement(w, "refs", nrefs="")
                    existing = refs.get('nrefs').split()
                    to_add = [id_map[o] for o in origins if o in id_map]
                    refs.set('nrefs', " ".join(sorted(list(set(existing + to_add)))))

    xml_str = ET.tostring(root, encoding='utf-8')
    return minidom.parseString(xml_str).toprettyxml(indent="    ")

# Interface Streamlit
st.title("🏛️ Conversor Alpheios ➔ Perseids (Correção idWord)")

file = st.file_uploader("Suba o JSON (DL-Plat ou Fabula)", type="json")

if file:
    try:
        content = json.load(file)
        result = convert_to_xml(content)
        
        if result:
            st.success("Sucesso! Texto e alinhamentos encontrados.")
            st.code(result, language="xml")
            st.download_button("Baixar XML", result, file_name="alinhamento.xml")
        else:
            st.error("Erro: Não foi possível encontrar os tokens. Verifique se o JSON possui a chave 'alignedText'.")
    except Exception as e:
        st.error(f"Erro inesperado: {e}")
