import streamlit as st
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Conversor Alpheios Ultra-Robusto", layout="wide")

def extrair_tokens_de_qualquer_lugar(dados_lingua):
    """
    Busca tokens em todas as subestruturas conhecidas do Alpheios:
    alignedText, docSource ou a própria raiz da língua.
    """
    tokens_result = []
    
    # Lista de possíveis caminhos onde o Alpheios guarda os segmentos
    caminhos = [
        dados_lingua.get('alignedText', {}).get('segments', []),
        dados_lingua.get('docSource', {}).get('tokenization', {}).get('segments', []),
        dados_lingua.get('segments', [])
    ]
    
    for segments in caminhos:
        if isinstance(segments, list):
            for seg in segments:
                tokens = seg.get('tokens', [])
                if isinstance(tokens, list):
                    for t in tokens:
                        # Pega o ID (pode ser idWord ou id)
                        tid = t.get('idWord') or t.get('id')
                        word = t.get('word')
                        if tid and word is not None:
                            tokens_result.append({'id': tid, 'word': word})
        
        # Se já achamos tokens em um caminho, não precisamos olhar os outros
        if tokens_result:
            break
            
    return tokens_result

def converter_para_perseids(data):
    # Base do XML
    root = ET.Element("aligned-text", xmlns="http://alpheios.net/namespaces/aligned-text")
    ET.SubElement(root, "language", lnum="L1", **{"xml:lang": "grc"})
    ET.SubElement(root, "language", lnum="L2", **{"xml:lang": "por"})
    sentence = ET.SubElement(root, "sentence", n="1")
    
    id_map = {}

    # 1. Extrair L1 e L2
    orig_tokens = extrair_tokens_de_qualquer_lugar(data.get('origin', {}))
    targ_tokens = extrair_tokens_de_qualquer_lugar(data.get('target', {}))

    if not orig_tokens or not targ_tokens:
        return None

    # Criar WDS L1
    wds1 = ET.SubElement(sentence, "wds", lnum="L1")
    for i, tok in enumerate(orig_tokens, 1):
        xml_id = f"1-{i}"
        id_map[tok['id']] = xml_id
        w = ET.SubElement(wds1, "w", n=xml_id)
        ET.SubElement(w, "text").text = str(tok['word'])

    # Criar WDS L2
    wds2 = ET.SubElement(sentence, "wds", lnum="L2")
    for i, tok in enumerate(targ_tokens, 1):
        xml_id = f"1-{i}"
        id_map[tok['id']] = xml_id
        w = ET.SubElement(wds2, "w", n=xml_id)
        ET.SubElement(w, "text").text = str(tok['word'])

    # 2. Processar Alinhamentos
    alignments = data.get('alignments', [])
    for al in alignments:
        actions = al.get('actions', {})
        # Alpheios às vezes guarda os IDs direto em 'origin'/'target' ou dentro de 'words'
        o_ids = actions.get('origin', [])
        t_ids = actions.get('target', [])
        
        # Inserir referências nrefs
        for o_id in o_ids:
            if o_id in id_map:
                xml_o = id_map[o_id]
                for node in sentence.findall(f".//w[@n='{xml_o}']"):
                    refs = node.find('refs')
                    if refs is None: refs = ET.SubElement(node, "refs", nrefs="")
                    atuais = refs.get('nrefs').split()
                    novos = [id_map[tid] for tid in t_ids if tid in id_map]
                    refs.set('nrefs', " ".join(sorted(list(set(atuais + novos)))))

        for t_id in t_ids:
            if t_id in id_map:
                xml_t = id_map[t_id]
                for node in sentence.findall(f".//w[@n='{xml_t}']"):
                    refs = node.find('refs')
                    if refs is None: refs = ET.SubElement(node, "refs", nrefs="")
                    atuais = refs.get('nrefs').split()
                    novos = [id_map[oid] for oid in o_ids if oid in id_map]
                    refs.set('nrefs', " ".join(sorted(list(set(atuais + novos)))))

    xml_str = ET.tostring(root, encoding='utf-8')
    return minidom.parseString(xml_str).toprettyxml(indent="    ")

# UI
st.title("🏛️ Conversor Alpheios ➔ Perseids (V10)")
st.write("Esta versão foi ajustada para os caminhos internos específicos da Fábula e de Platão.")

file = st.file_uploader("Suba o JSON", type="json")

if file:
    try:
        content = json.load(file)
        result = converter_para_perseids(content)
        if result:
            st.success("XML Gerado!")
            st.code(result, language="xml")
            st.download_button("Baixar XML", result, file_name="alinhamento.xml")
        else:
            st.error("Erro técnico: O script não encontrou a lista de tokens nos caminhos esperados.")
    except Exception as e:
        st.error(f"Erro: {e}")
