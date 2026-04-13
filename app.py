import streamlit as st
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Conversor Alpheios ➔ Perseids", layout="wide")

def extrair_tokens(data_section):
    """Navega na estrutura exata do Alpheios para coletar palavras."""
    tokens_list = []
    # O Alpheios coloca os dados reais dentro de alignedText -> segments
    aligned_text = data_section.get('alignedText', {})
    segments = aligned_text.get('segments', [])
    
    for seg in segments:
        for tok in seg.get('tokens', []):
            # Nos seus arquivos, a chave é 'idWord'
            tid = tok.get('idWord')
            word = tok.get('word')
            if tid and word is not None:
                tokens_list.append({'id': tid, 'word': word})
    return tokens_list

def convert_to_xml(data):
    # Cabeçalho do XML Perseids
    root = ET.Element("aligned-text", xmlns="http://alpheios.net/namespaces/aligned-text")
    ET.SubElement(root, "language", lnum="L1", **{"xml:lang": "grc"})
    ET.SubElement(root, "language", lnum="L2", **{"xml:lang": "por"})
    sentence_node = ET.SubElement(root, "sentence", n="1")
    
    id_map = {} # Traduz o ID do Alpheios (ex: 1-0-5) para o do Perseids (ex: 1-5)

    # 1. Processar Grego (Origin) e Português (Target)
    tokens_grc = extrair_tokens(data.get('origin', {}))
    tokens_por = extrair_tokens(data.get('target', {}))

    if not tokens_grc or not tokens_por:
        return None

    # Montar nós de palavras Grego (L1)
    wds1 = ET.SubElement(sentence_node, "wds", lnum="L1")
    for i, tok in enumerate(tokens_grc, 1):
        xml_id = f"1-{i}"
        id_map[tok['id']] = xml_id
        w = ET.SubElement(wds1, "w", n=xml_id)
        ET.SubElement(w, "text").text = str(tok['word'])

    # Montar nós de palavras Português (L2)
    wds2 = ET.SubElement(sentence_node, "wds", lnum="L2")
    for i, tok in enumerate(tokens_por, 1):
        xml_id = f"1-{i}"
        id_map[tok['id']] = xml_id
        w = ET.SubElement(wds2, "w", n=xml_id)
        ET.SubElement(w, "text").text = str(tok['word'])

    # 2. Mapear os Alinhamentos (Refs)
    # A seção 'alignments' fica na raiz do seu JSON
    alignments = data.get('alignments', [])
    for al in alignments:
        act = al.get('actions', {})
        orig_ids = act.get('origin', [])
        targ_ids = act.get('target', [])
        
        # Conecta Origem -> Destino
        for o_id in orig_ids:
            if o_id in id_map:
                target_refs = [id_map[tid] for tid in targ_ids if tid in id_map]
                if target_refs:
                    # Busca o nó <w> correspondente no XML para injetar a ref
                    for w in sentence_node.findall(f".//w[@n='{id_map[o_id]}']"):
                        ref_node = w.find('refs')
                        if ref_node is None: ref_node = ET.SubElement(w, "refs", nrefs="")
                        existing = ref_node.get('nrefs').split()
                        ref_node.set('nrefs', " ".join(sorted(list(set(existing + target_refs)))))

        # Conecta Destino -> Origem (Bidirecional)
        for t_id in targ_ids:
            if t_id in id_map:
                origin_refs = [id_map[oid] for oid in orig_ids if oid in id_map]
                if origin_refs:
                    for w in sentence_node.findall(f".//w[@n='{id_map[t_id]}']"):
                        ref_node = w.find('refs')
                        if ref_node is None: ref_node = ET.SubElement(w, "refs", nrefs="")
                        existing = ref_node.get('nrefs').split()
                        ref_node.set('nrefs', " ".join(sorted(list(set(existing + origin_refs)))))

    xml_str = ET.tostring(root, encoding='utf-8')
    return minidom.parseString(xml_str).toprettyxml(indent="    ")

# Streamlit UI
st.title("Conversor Alpheios ➔ Perseids")
file = st.file_uploader("Suba o JSON original do Alpheios", type="json")

if file:
    try:
        content = json.load(file)
        xml_result = convert_to_xml(content)
        if xml_result:
            st.success("Conversão bem-sucedida!")
            st.code(xml_result, language="xml")
            st.download_button("Baixar XML", xml_result, file_name="alinhamento.xml")
        else:
            st.error("Erro ao mapear tokens. O formato interno do JSON é diferente do esperado.")
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
