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

# Konfiguracja OpenAI z walidacją klucza
def initialize_openai_client():
    """Inicjalizuje klienta OpenAI z walidacją klucza"""
    try:
        if "OPENAI_API_KEY" not in st.secrets:
            st.error("❌ Brak klucza OpenAI w sekretach. Sprawdź konfigurację!")
            st.info("Dodaj klucz OPENAI_API_KEY w ustawieniach aplikacji (Settings → Secrets)")
            st.stop()
        
        client = OpenAI(api_key=st.secrets.OPENAI_API_KEY)
        return client
    except Exception as e:
        st.error(f"❌ Błąd inicjalizacji OpenAI: {e}")
        st.stop()

# Inicjalizacja klienta
client = initialize_openai_client()

def extract_text_from_excel(file):
    """Ekstraktuje tekst z pliku Excel"""
    try:
        df = pd.read_excel(file)
        text = ""
        for column in df.columns:
            text += f"{column}: "
            text += " ".join(df[column].astype(str).tolist())
            text += "\n"
        return text.strip()
    except Exception as e:
        st.error(f"❌ Błąd podczas czytania pliku Excel: {e}")
        return None

def extract_text_from_docx(file):
    """Ekstraktuje tekst z pliku Word"""
    try:
        doc = docx.Document(file)
        text = ""
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():  # Pomijaj puste paragrafy
                text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        st.error(f"❌ Błąd podczas czytania pliku Word: {e}")
        return None

def extract_text_from_pdf(file):
    """Ekstraktuje tekst z pliku PDF"""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page_num, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            if page_text.strip():  # Sprawdź czy strona zawiera tekst
                text += page_text + "\n"
        
        if not text.strip():
            st.warning("⚠️ Nie udało się wyekstraktować tekstu z PDF. Plik może zawierać tylko obrazy.")
            return None
        
        return text.strip()
    except Exception as e:
        st.error(f"❌ Błąd podczas czytania pliku PDF: {e}")
        return None

def detect_language(text):
    """Wykrywa język tekstu"""
    try:
        if len(text.strip()) < 10:
            st.warning("⚠️ Tekst jest zbyt krótki do niezawodnej detekcji języka")
            return "Nieznany"
        
        language_code = detect(text)
        language_names = {
            'pl': 'Polski',
            'en': 'Angielski', 
            'de': 'Niemiecki',
            'fr': 'Francuski',
            'es': 'Hiszpański',
            'it': 'Włoski',
            'ru': 'Rosyjski',
            'cs': 'Czeski',
            'sk': 'Słowacki'
        }
        return language_names.get(language_code, f'Język: {language_code}')
    except Exception as e:
        st.warning(f"⚠️ Błąd podczas detekcji języka: {e}")
        return "Nieznany"

def translate_text(text, target_language, source_language):
    """Tłumaczy tekst używając OpenAI"""
    try:
        # Sprawdź długość tekstu
        if len(text) > 15000:  # Ograniczenie dla GPT-4
            st.warning("⚠️ Tekst jest bardzo długi. Tłumaczenie może być skrócone.")
            text = text[:15000] + "..."
        
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
        - Zachowaj formatowanie (paragrafy, listy)
        
        Tekst do tłumaczenia:
        {text}
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": "Jesteś ekspertem ds. tłumaczeń biznesowych specjalizującym się w dokumentach finansowych i transakcyjnych. Wykonujesz tłumaczenia o charakterze formalnym i profesjonalnym."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            max_tokens=4000,
            temperature=0.2,  # Niższa temperatura dla większej precyzji
            top_p=1.0
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        st.error(f"❌ Błąd podczas tłumaczenia: {e}")
        if "insufficient_quota" in str(e):
            st.error("💳 Przekroczono limit API OpenAI. Sprawdź swoje konto.")
        elif "model_not_found" in str(e):
            st.error("🤖 Model GPT-4 niedostępny. Sprawdź dostęp do modelu.")
        return None

def validate_file_content(text, filename):
    """Waliduje zawartość wyekstraktowanego tekstu"""
    if not text or len(text.strip()) < 5:
        st.error(f"❌ Plik {filename} nie zawiera tekstu lub tekst jest zbyt krótki do tłumaczenia.")
        return False
    
    if len(text) > 50000:
        st.warning(f"⚠️ Plik {filename} jest bardzo duży ({len(text)} znaków). Tłumaczenie może zająć więcej czasu.")
    
    return True

def main():
    st.set_page_config(
        page_title="Translator Pro Business", 
        page_icon="🌐", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
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
        
        **Ograniczenia:**
        - Maks. rozmiar: 200MB
        - Maks. tekst: ~15,000 znaków
        """)
        
        st.markdown("---")
        st.markdown("**💡 Wskazówki:**")
        st.markdown("""
        - PDF: Upewnij się, że zawiera tekst (nie tylko obrazy)
        - Excel: Wszystkie arkusze będą przetłumaczone
        - Word: Zachowane zostanie formatowanie paragrafów
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
            file_size = len(uploaded_file.getvalue()) / (1024 * 1024)  # MB
            st.success(f"✅ Załadowano plik: {uploaded_file.name}")
            st.info(f"📊 Rozmiar pliku: {file_size:.2f} MB")
            
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
                
                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # Krok 1: Ekstraktuj tekst
                    status_text.text("📖 Ekstraktowanie tekstu...")
                    progress_bar.progress(25)
                    
                    file_extension = uploaded_file.name.split('.')[-1].lower()
                    
                    if file_extension == 'xlsx':
                        text = extract_text_from_excel(uploaded_file)
                    elif file_extension == 'docx':
                        text = extract_text_from_docx(uploaded_file)
                    elif file_extension == 'pdf':
                        text = extract_text_from_pdf(uploaded_file)
                    
                    if not text or not validate_file_content(text, uploaded_file.name):
                        progress_bar.empty()
                        status_text.empty()
                        st.stop()
                    
                    # Krok 2: Wykryj język
                    status_text.text("🔍 Wykrywanie języka...")
                    progress_bar.progress(50)
                    
                    detected_language = detect_language(text)
                    st.info(f"🔍 Wykryty język: {detected_language}")
                    
                    # Krok 3: Tłumacz tekst
                    status_text.text("🌐 Tłumaczenie w toku...")
                    progress_bar.progress(75)
                    
                    translated_text = translate_text(text, target_language, detected_language)
                    
                    if translated_text:
                        # Krok 4: Zakończenie
                        status_text.text("✅ Tłumaczenie zakończone!")
                        progress_bar.progress(100)
                        
                        # Przechowaj wyniki w session state
                        st.session_state.translated_text = translated_text
                        st.session_state.target_language = target_language
                        st.session_state.source_file = uploaded_file.name
                        st.session_state.detected_language = detected_language
                        st.session_state.original_text = text[:500] + "..." if len(text) > 500 else text
                        
                        st.success("✅ Tłumaczenie zakończone pomyślnie!")
                        
                        # Wyczyść progress
                        progress_bar.empty()
                        status_text.empty()
                    else:
                        progress_bar.empty()
                        status_text.empty()
                        st.error("❌ Tłumaczenie nie powiodło się.")
                        
                except Exception as e:
                    progress_bar.empty()
                    status_text.empty()
                    st.error(f"❌ Wystąpił nieoczekiwany błąd: {e}")
    
    # Wyświetlanie wyników
    if 'translated_text' in st.session_state:
        st.markdown("---")
        st.subheader("📝 Wyniki tłumaczenia")
        
        # Informacje o tłumaczeniu
        info_col1, info_col2, info_col3 = st.columns(3)
        
        with info_col1:
            st.metric("📄 Plik źródłowy", st.session_state.source_file)
        
        with info_col2:
            st.metric("🔍 Język wykryty", st.session_state.detected_language)
        
        with info_col3:
            st.metric("🎯 Język docelowy", st.session_state.target_language)
        
        # Główna sekcja wyników
        col3, col4 = st.columns([3, 1])
        
        with col3:
            # Tabs dla oryginalnego i przetłumaczonego tekstu
            tab1, tab2 = st.tabs(["🌐 Tłumaczenie", "📄 Oryginał (fragment)"])
            
            with tab1:
                st.text_area(
                    "Przetłumaczony tekst:",
                    value=st.session_state.translated_text,
                    height=400,
                    help="Możesz skopiować tekst lub pobrać go jako plik"
                )
            
            with tab2:
                st.text_area(
                    "Oryginalny tekst (fragment):",
                    value=st.session_state.original_text,
                    height=400,
                    disabled=True
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
            st.metric("Liczba słów", f"{word_count:,}")
            st.metric("Liczba znaków", f"{char_count:,}")
            
            # Przycisk czyszczenia
            if st.button("🗑️ Wyczyść wyniki", help="Usuń aktualne wyniki tłumaczenia"):
                for key in ['translated_text', 'target_language', 'source_file', 'detected_language', 'original_text']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

if __name__ == "__main__":
    main()
