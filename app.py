import streamlit as st
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Conversor Alpheios ➔ Perseids", layout="wide")

def extrair_tokens_alpheios(data_node):
    """Extrai tokens seguindo a hierarquia exata: alignedText > segments > tokens"""
    tokens_extraidos = []
    
    # Entra na subchave alignedText
    aligned_text = data_node.get('alignedText', {})
    # Pega a lista de segmentos
    segments = aligned_text.get('segments', [])
    
    if not segments:
        # Tenta um caminho alternativo caso a estrutura mude levemente
        segments = data_node.get('segments', [])

    for seg in segments:
        tokens = seg.get('tokens', [])
        for t in tokens:
            # Nos seus arquivos, a chave correta é idWord
            id_word = t.get('idWord')
            word_text = t.get('word')
            if id_word and word_text is not None:
                tokens_extraidos.append({'id': id_word, 'word': word_text})
    
    return tokens_extraidos

def gerar_xml_perseids(json_data):
    # Estrutura base do XML
    root = ET.Element("aligned-text", xmlns="http://alpheios.net/namespaces/aligned-text")
    ET.SubElement(root, "language", lnum="L1", **{"xml:lang": "grc"})
    ET.SubElement(root, "language", lnum="L2", **{"xml:lang": "por"})
    sentence_node = ET.SubElement(root, "sentence", n="1")
    
    id_map = {} # De '1-0-5' (Alpheios) para '1-5' (Perseids)

    # 1. Processar Grego (Origin) e Português (Target)
    tokens_grc = extrair_tokens_alpheios(json_data.get('origin', {}))
    tokens_por = extrair_tokens_alpheios(json_data.get('target', {}))

    if not tokens_grc or not tokens_por:
        return None

    # Criar palavras Grego (L1)
    wds_l1 = ET.SubElement(sentence_node, "wds", lnum="L1")
    for i, tok in enumerate(tokens_grc, 1):
        novo_id = f"1-{i}"
        id_map[tok['id']] = novo_id
        w = ET.SubElement(wds_l1, "w", n=novo_id)
        ET.SubElement(w, "text").text = str(tok['word'])

    # Criar palavras Português (L2)
    wds_l2 = ET.SubElement(sentence_node, "wds", lnum="L2")
    for i, tok in enumerate(tokens_por, 1):
        novo_id = f"1-{i}"
        id_map[tok['id']] = novo_id
        w = ET.SubElement(wds_l2, "w", n=novo_id)
        ET.SubElement(w, "text").text = str(tok['word'])

    # 2. Processar Alinhamentos (A seção 'alignments' na raiz)
    alignments = json_data.get('alignments', [])
    for align in alignments:
        actions = align.get('actions', {})
        orig_ids = actions.get('origin', [])
        targ_ids = actions.get('target', [])
        
        # Mapear refs para palavras de origem
        for o_id in orig_ids:
            if o_id in id_map:
                xml_id = id_map[o_id]
                for node in sentence_node.findall(f".//w[@n='{xml_id}']"):
                    refs = node.find('refs')
                    if refs is None: refs = ET.SubElement(node, "refs", nrefs="")
                    
                    atuais = refs.get('nrefs').split()
                    novos = [id_map[tid] for tid in targ_ids if tid in id_map]
                    refs.set('nrefs', " ".join(sorted(list(set(atuais + novos)))))

        # Mapear refs para palavras de destino
        for t_id in targ_ids:
            if t_id in id_map:
                xml_id = id_map[t_id]
                for node in sentence_node.findall(f".//w[@n='{xml_id}']"):
                    refs = node.find('refs')
                    if refs is None: refs = ET.SubElement(node, "refs", nrefs="")
                    
                    atuais = refs.get('nrefs').split()
                    novos = [id_map[oid] for oid in orig_ids if oid in id_map]
                    refs.set('nrefs', " ".join(sorted(list(set(atuais + novos)))))

    # Formatação Final
    xml_string = ET.tostring(root, encoding='utf-8')
    return minidom.parseString(xml_string).toprettyxml(indent="    ")

# Interface Streamlit
st.title("🏛️ Conversor Alpheios ➔ Perseids")
st.info("Especializado nos arquivos DL-Plat e Fabula.")

file = st.file_uploader("Suba o JSON original", type="json")

if file:
    try:
        conteudo = json.load(file)
        resultado_xml = gerar_xml_perseids(conteudo)
        
        if resultado_xml:
            st.success("Conversão realizada!")
            st.code(resultado_xml, language="xml")
            st.download_button("Baixar XML", resultado_xml, file_name="alinhamento_perseids.xml")
        else:
            st.error("Erro ao localizar tokens. Certifique-se de que o arquivo contém texto alinhado.")
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
