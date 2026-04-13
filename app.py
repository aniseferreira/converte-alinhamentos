import streamlit as st
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Conversor Alpheios para Perseids", layout="wide")

def convert_alpheios_to_perseids(json_content):
    data = json.loads(json_content)
    
    root = ET.Element("aligned-text", xmlns="http://alpheios.net/namespaces/aligned-text")
    ET.SubElement(root, "language", lnum="L1", **{"xml:lang": "grc"})
    ET.SubElement(root, "language", lnum="L2", **{"xml:lang": "por"})
    
    id_map = {}
    sentence_node = ET.SubElement(root, "sentence", n="1")

    # Função para extrair tokens baseada na estrutura real do seu JSON
    def build_sentence(parent, lang_data, lnum, sentence_n):
        wds = ET.SubElement(parent, "wds", lnum=lnum)
        token_count = 1
        # No seu JSON, a estrutura é data['origin']['segments']...
        for segment in lang_data['segments']:
            for token in segment['tokens']:
                xml_id = f"{sentence_n}-{token_count}"
                id_map[token['id']] = xml_id
                
                w = ET.SubElement(wds, "w", n=xml_id)
                text_node = ET.SubElement(w, "text")
                text_node.text = token['word']
                token_count += 1

    # Chamada corrigida acessando 'origin' e 'target' diretamente na raiz
    build_sentence(sentence_node, data['origin'], "L1", "1")
    build_sentence(sentence_node, data['target'], "L2", "1")

    # Mapear Alinhamentos
    align_refs = {}
    for alignment in data.get('alignments', []):
        # No seu JSON, o caminho é alignment['actions']['origin']
        actions = alignment.get('actions', {})
        origins = actions.get('origin', [])
        targets = actions.get('target', [])
        
        for o in origins:
            if o not in align_refs: align_refs[o] = []
            align_refs[o].extend([id_map[t] for t in targets if t in id_map])
            
        for t in targets:
            if t not in align_refs: align_refs[t] = []
            align_refs[t].extend([id_map[o] for o in origins if o in id_map])

    # Inserir as tags <refs>
    for w_node in sentence_node.findall(".//w"):
        xml_id = w_node.get('n')
        orig_json_id = [k for k, v in id_map.items() if v == xml_id]
        if orig_json_id and orig_json_id[0] in align_refs:
            refs = sorted(list(set(align_refs[orig_json_id[0]])))
            if refs:
                ET.SubElement(w_node, "refs", nrefs=" ".join(refs))

    xml_str = ET.tostring(root, encoding='utf-8')
    return minidom.parseString(xml_str).toprettyxml(indent="    ")

# Interface do Usuário
st.title("🏛️ Conversor de Alinhamento JSON ➔ XML")
st.subheader("Formato: Novo Alpheios Editor para Perseids/Alpheios")

uploaded_file = st.file_uploader("Suba o arquivo .json gerado pelo Alpheios", type="json")

if uploaded_file:
    json_text = uploaded_file.read().decode("utf-8")
    
    with st.spinner("Convertendo..."):
        try:
            xml_output = convert_alpheios_to_perseids(json_text)
            
            col1, col2 = st.columns(2)
            with col1:
                st.info("Prévia do XML gerado")
                st.code(xml_output, language="xml")
            
            with col2:
                st.success("Conversão concluída!")
                st.download_button(
                    label="Baixar Arquivo XML",
                    data=xml_output,
                    file_name="alinhamento_perseids.xml",
                    mime="text/xml"
                )
        except Exception as e:
            st.error(f"Erro ao processar: {e}")
