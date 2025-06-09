import streamlit as st
import pandas as pd
import docx
import PyPDF2
from langdetect import detect, DetectorFactory
from openai import OpenAI
import io
import tempfile

# Ustawienie deterministycznej detekcji języka
DetectorFactory.seed = 0

# Konfiguracja OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def extract_text_from_excel(file):
    """Ekstraktuje tekst z pliku Excel"""
    try:
        df = pd.read_excel(file)
        # Konwertuje wszystkie wartości do string i łączy w jeden tekst
        text = ""
        for column in df.columns:
            text += f"{column}: "
            text += " ".join(df[column].astype(str).tolist())
            text += "\n"
        return text
    except Exception as e:
        st.error(f"Błąd podczas czytania pliku Excel: {e}")
        return None

def extract_text_from_docx(file):
    """Ekstraktuje tekst z pliku Word"""
    try:
        doc = docx.Document(file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        st.error(f"Błąd podczas czytania pliku Word: {e}")
        return None

def extract_text_from_pdf(file):
    """Ekstraktuje tekst z pliku PDF"""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Błąd podczas czytania pliku PDF: {e}")
        return None

def detect_language(text):
    """Wykrywa język tekstu"""
    try:
        language_code = detect(text)
        language_names = {
            'pl': 'Polski',
            'en': 'Angielski', 
            'de': 'Niemiecki',
            'fr': 'Francuski',
            'es': 'Hiszpański',
            'it': 'Włoski'
        }
        return language_names.get(language_code, f'Język: {language_code}')
    except Exception as e:
        st.error(f"Błąd podczas detekcji języka: {e}")
        return "Nieznany"

def translate_text(text, target_language, source_language):
    """Tłumaczy tekst używając OpenAI"""
    try:
        language_mapping = {
            'Polski': 'Polish',
            'Angielski': 'English',
            'Niemiecki': 'German'
        }
        
        target_lang = language_mapping[target_language]
        
        prompt = f"""
        Przetłumacz następujący tekst na język {target_lang}.
        
        WYMAGANIA STYLU:
        - Język ma być formalny, rzeczowy i neutralny
        - Odpowiedni dla dokumentów biznesowych
        - Specjalizacja: doradztwo transakcyjne i finansowo-biznesowe
        - Zachowaj terminologię profesjonalną
        - Utrzymaj strukturę dokumentu
        - Język raportowy, precyzyjny
        
        Tekst do tłumaczenia:
        {text}
        
        Przetłumaczony tekst:
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Jesteś ekspertem ds. tłumaczeń biznesowych specjalizującym się w dokumentach finansowych i transakcyjnych. Wykonujesz tłumaczenia o charakterze formalnym i profesjonalnym."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        st.error(f"Błąd podczas tłumaczenia: {e}")
        return None

def main():
    st.set_page_config(page_title="Translator Pro Business", page_icon="🌐", layout="wide")
    
    st.title("🌐 Translator Pro Business")
    st.markdown("### Profesjonalne tłumaczenie dokumentów biznesowych")
    st.markdown("*Specjalizacja: doradztwo transakcyjne i finansowo-biznesowe*")
    
    # Sidebar z instrukcjami
    with st.sidebar:
        st.header("📋 Instrukcje")
        st.markdown("""
        **Obsługiwane formaty:**
        - Excel (.xlsx)
        - Word (.docx) 
        - PDF (.pdf)
        
        **Dostępne języki:**
        - Polski
        - Angielski
        - Niemiecki
        
        **Styl tłumaczenia:**
        - Formalny i rzeczowy
        - Terminologia biznesowa
        - Język raportowy
        """)
    
    # Główny interfejs
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📄 Przesyłanie dokumentu")
        uploaded_file = st.file_uploader(
            "Wybierz dokument do tłumaczenia",
            type=['xlsx', 'docx', 'pdf'],
            help="Maksymalny rozmiar pliku: 200MB"
        )
        
        if uploaded_file is not None:
            st.success(f"✅ Załadowano plik: {uploaded_file.name}")
            
            # Wybór języka docelowego
            target_language = st.selectbox(
                "Wybierz język docelowy",
                options=['Polski', 'Angielski', 'Niemiecki'],
                help="Wybierz język, na który ma zostać przetłumaczony dokument"
            )
    
    with col2:
        st.subheader("🔄 Proces tłumaczenia")
        
        if uploaded_file is not None:
            if st.button("🚀 Rozpocznij tłumaczenie", type="primary"):
                
                with st.spinner("Przetwarzanie dokumentu..."):
                    # Ekstraktuj tekst w zależności od typu pliku
                    file_extension = uploaded_file.name.split('.')[-1].lower()
                    
                    if file_extension == 'xlsx':
                        text = extract_text_from_excel(uploaded_file)
                    elif file_extension == 'docx':
                        text = extract_text_from_docx(uploaded_file)
                    elif file_extension == 'pdf':
                        text = extract_text_from_pdf(uploaded_file)
                    
                    if text:
                        # Wykryj język
                        detected_language = detect_language(text)
                        st.info(f"🔍 Wykryty język: {detected_language}")
                        
                        # Tłumacz tekst
                        with st.spinner("Tłumaczenie w toku..."):
                            translated_text = translate_text(text, target_language, detected_language)
                        
                        if translated_text:
                            st.success("✅ Tłumaczenie zakończone!")
                            
                            # Przechowaj wyniki w session state
                            st.session_state.translated_text = translated_text
                            st.session_state.target_language = target_language
                            st.session_state.source_file = uploaded_file.name
    
    # Wyświetlanie wyników
    if 'translated_text' in st.session_state:
        st.markdown("---")
        st.subheader("📝 Wyniki tłumaczenia")
        
        col3, col4 = st.columns([3, 1])
        
        with col3:
            st.markdown(f"**Plik źródłowy:** {st.session_state.source_file}")
            st.markdown(f"**Język docelowy:** {st.session_state.target_language}")
            
            # Wyświetl przetłumaczony tekst
            st.text_area(
                "Przetłumaczony tekst:",
                value=st.session_state.translated_text,
                height=400,
                help="Możesz skopiować tekst lub pobrać go jako plik"
            )
        
        with col4:
            st.markdown("### 💾 Eksport")
            
            # Przycisk pobierania
            filename = f"translated_{st.session_state.source_file.split('.')[0]}_{st.session_state.target_language}.txt"
            
            st.download_button(
                label="⬇️ Pobierz tłumaczenie",
                data=st.session_state.translated_text,
                file_name=filename,
                mime="text/plain",
                help="Pobierz przetłumaczony tekst jako plik .txt"
            )
            
            # Statystyki
            word_count = len(st.session_state.translated_text.split())
            char_count = len(st.session_state.translated_text)
            
            st.markdown("### 📊 Statystyki")
            st.metric("Liczba słów", word_count)
            st.metric("Liczba znaków", char_count)

if __name__ == "__main__":
    main()
