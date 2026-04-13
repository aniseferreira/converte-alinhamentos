import streamlit as st
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Conversor Alpheios Final", layout="wide")

def extrair_tokens_recursivo(obj):
    """
    Varre o JSON procurando por listas de tokens.
    Funciona para estruturas com ou sem 'alignedText'.
    """
    tokens_encontrados = []
    if isinstance(obj, dict):
        if "tokens" in obj and isinstance(obj["tokens"], list):
            for t in obj["tokens"]:
                tid = t.get('idWord') or t.get('id')
                word = t.get('word')
                if tid and word is not None:
                    tokens_encontrados.append({'id': tid, 'word': word})
        for v in obj.values():
            tokens_encontrados.extend(extrair_tokens_recursivo(v))
    elif isinstance(obj, list):
        for item in obj:
            tokens_encontrados.extend(extrair_tokens_recursivo(item))
    return tokens_encontrados

def convert_to_xml(json_data):
    root = ET.Element("aligned-text", xmlns="http://alpheios.net/namespaces/aligned-text")
    ET.SubElement(root, "language", lnum="L1", **{"xml:lang": "grc"})
    ET.SubElement(root, "language", lnum="L2", **{"xml:lang": "por"})
    
    sentence_node = ET.SubElement(root, "sentence", n="1")
    id_map = {} # Mapeia ID original (ex: 1-0-1) para ID XML (ex: 1-1)

    # 1. Processar Origem e Destino
    def processar(chave, lnum):
        dados_lingua = json_data.get(chave, {})
        tokens = extrair_tokens_recursivo(dados_lingua)
        
        if not tokens:
            return False
            
        wds_node = ET.SubElement(sentence_node, "wds", lnum=lnum)
        for i, tok in enumerate(tokens, 1):
            xml_id = f"1-{i}"
            id_map[tok['id']] = xml_id
            
            w_node = ET.SubElement(wds_node, "w", n=xml_id)
            text_node = ET.SubElement(w_node, "text")
            text_node.text = str(tok['word'])
        return True

    # Executa a extração
    ok_l1 = processar('origin', 'L1')
    ok_l2 = processar('target', 'L2')

    if not ok_l1 or not ok_l2:
        return None

    # 2. Processar Alinhamentos (Ações)
    alignments = json_data.get('alignments', [])
    for al in alignments:
        actions = al.get('actions', {})
        orig_ids = actions.get('origin', [])
        targ_ids = actions.get('target', [])
        
        # Mapeia IDs para ambos os lados
        todos_ids = orig_ids + targ_ids
        for source_id in todos_ids:
            if source_id in id_map:
                xml_id_ref = id_map[source_id]
                # Encontra o nó <w> no XML gerado
                for w in sentence_node.findall(f".//w[@n='{xml_id_ref}']"):
                    refs_node = w.find('refs')
                    if refs_node is None:
                        refs_node = ET.SubElement(w, "refs", nrefs="")
                    
                    # Determina quem são os alvos (se eu sou origin, meus alvos são target e vice-versa)
                    targets = targ_ids if source_id in orig_ids else orig_ids
                    
                    current_refs = refs_node.get('nrefs').split()
                    new_refs = [id_map[tid] for tid in targets if tid in id_map]
                    
                    # Atualiza sem duplicatas
                    final_refs = sorted(list(set(current_refs + new_refs)))
                    refs_node.set('nrefs', " ".join(final_refs))

    xml_str = ET.tostring(root, encoding='utf-8')
    return minidom.parseString(xml_str).toprettyxml(indent="    ")

# --- Interface Streamlit ---
st.title("🏛️ Conversor Alpheios ➔ Perseids (V7 - Ultra)")

uploaded_file = st.file_uploader("Suba seu arquivo JSON", type="json")

if uploaded_file:
    try:
        content = json.load(uploaded_file)
        # Tenta converter
        xml_result = convert_to_xml(content)
        
        if xml_result:
            st.success("Conversão realizada com sucesso!")
            st.code(xml_result, language="xml")
            st.download_button("Baixar XML", xml_result, file_name="alinhamento_perseids.xml")
        else:
            st.error("Erro: Não foi possível localizar os tokens de texto no arquivo. Verifique se as chaves 'origin' e 'target' contêm dados.")
    except Exception as e:
        st.error(f"Erro ao processar: {e}")
