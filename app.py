import streamlit as st
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Conversor Alpheios Final", layout="wide")

def coletar_tokens(obj):
    """Varre o JSON recursivamente para achar todos os objetos que são tokens."""
    tokens = []
    if isinstance(obj, dict):
        # Verifica se o dicionário atual é um token (tem palavra e ID)
        if 'word' in obj and ('idWord' in obj or 'id' in obj):
            tid = obj.get('idWord') or obj.get('id')
            return [{'id': tid, 'word': obj['word']}]
        # Se não for, continua mergulhando
        for v in obj.values():
            tokens.extend(coletar_tokens(v))
    elif isinstance(obj, list):
        for item in obj:
            tokens.extend(coletar_tokens(item))
    return tokens

def convert_to_xml(data):
    # Setup básico do XML do Perseids
    root = ET.Element("aligned-text", xmlns="http://alpheios.net/namespaces/aligned-text")
    ET.SubElement(root, "language", lnum="L1", **{"xml:lang": "grc"})
    ET.SubElement(root, "language", lnum="L2", **{"xml:lang": "por"})
    sentence_node = ET.SubElement(root, "sentence", n="1")
    
    id_map = {} # De '1-0-1' para '1-1'

    # 1. Extração robusta de L1 e L2
    # Procuramos especificamente dentro das seções de origem e destino
    tokens_l1 = coletar_tokens(data.get('origin', {}))
    tokens_l2 = coletar_tokens(data.get('target', {}))

    if not tokens_l1 or not tokens_l2:
        return None

    # Monta os nós de palavras para o Grego (L1)
    wds1 = ET.SubElement(sentence_node, "wds", lnum="L1")
    for i, tok in enumerate(tokens_l1, 1):
        xml_id = f"1-{i}"
        id_map[tok['id']] = xml_id
        w = ET.SubElement(wds1, "w", n=xml_id)
        ET.SubElement(w, "text").text = str(tok['word'])

    # Monta os nós de palavras para o Português (L2)
    wds2 = ET.SubElement(sentence_node, "wds", lnum="L2")
    for i, tok in enumerate(tokens_l2, 1):
        xml_id = f"1-{i}"
        id_map[tok['id']] = xml_id
        w = ET.SubElement(wds2, "w", n=xml_id)
        ET.SubElement(w, "text").text = str(tok['word'])

    # 2. Processar Alinhamentos
    # Percorre a lista de alinhamentos que fica na raiz do JSON
    alignments = data.get('alignments', [])
    for al in alignments:
        actions = al.get('actions', {})
        origins = actions.get('origin', [])
        targets = actions.get('target', [])
        
        # Cria as conexões nrefs
        for o_id in origins:
            if o_id in id_map:
                xml_o = id_map[o_id]
                # Localiza o nó <w> correspondente no XML
                for node in sentence_node.findall(f".//w[@n='{xml_o}']"):
                    refs = node.find('refs')
                    if refs is None: refs = ET.SubElement(node, "refs", nrefs="")
                    
                    existentes = refs.get('nrefs').split()
                    novos = [id_map[tid] for tid in targets if tid in id_map]
                    refs.set('nrefs', " ".join(sorted(list(set(existentes + novos)))))

        # Faz o mesmo para o lado do target
        for t_id in targets:
            if t_id in id_map:
                xml_t = id_map[t_id]
                for node in sentence_node.findall(f".//w[@n='{xml_t}']"):
                    refs = node.find('refs')
                    if refs is None: refs = ET.SubElement(node, "refs", nrefs="")
                    
                    existentes = refs.get('nrefs').split()
                    novos = [id_map[oid] for oid in origins if oid in id_map]
                    refs.set('nrefs', " ".join(sorted(list(set(existentes + novos)))))

    # Finaliza e formata o XML
    xml_str = ET.tostring(root, encoding='utf-8')
    return minidom.parseString(xml_str).toprettyxml(indent="    ")

# Interface Streamlit
st.title("🏛️ Conversor Alpheios ➔ Perseids (V8 Definitiva)")
st.write("Suba o arquivo .json original (o mesmo que deu erro antes).")

file = st.file_uploader("Arquivo JSON", type="json")

if file:
    try:
        content = json.load(file)
        # Tenta a conversão
        xml_output = convert_to_xml(content)
        
        if xml_output:
            st.success("Conversão concluída!")
            st.code(xml_output, language="xml")
            st.download_button("Baixar XML para Perseids", xml_output, file_name="alinhamento.xml")
        else:
            st.error("Erro: Não foi possível mapear as palavras. O arquivo pode estar vazio ou em um formato incompatível.")
    except Exception as e:
        st.error(f"Erro inesperado: {e}")
