import { createContext, useContext, useEffect, useMemo, useState } from 'react'

const translations = {
  en: {
    workspace: 'Workspace', dashboard: 'Dashboard', newScan: 'New scan', documents: 'Documents', history: 'OCR history', settings: 'Settings',
    overview: 'Overview', scanDocument: 'Scan a document', searchDocuments: 'Search documents', language: 'Language', appearance: 'Appearance',
    lightMode: 'Light mode', darkMode: 'Dark mode', recentDocuments: 'Recent documents', viewAll: 'View all', documentLibrary: 'Document library',
    documentLibraryHint: 'Search, review, and manage every document in your workspace.', allDocuments: 'All documents', uploadDocument: 'Upload document',
    intelligentWorkspace: 'Intelligent document workspace', heroTitle: 'From image to insight, without the busywork.',
    heroText: 'Capture, understand, correct, and export important documents in one focused workspace.',
    documentsScanned: 'Documents scanned', processed: 'Successfully processed', failed: 'Needs attention', confidence: 'OCR confidence',
    noDocuments: 'No documents yet', noDocumentsHint: 'Start with a receipt, invoice, form, or printed page.', startScan: 'Start a scan',
    processing: 'Processing', completed: 'Completed', document: 'Document', status: 'Status', uploaded: 'Uploaded', textPreview: 'Text preview',
    noText: 'No text returned', delete: 'Delete', openDocument: 'Open document', localWorkspace: 'Local workspace',
    newDocument: 'New document', uploadTitle: 'Bring a document into focus.', uploadHint: 'Drop a clean photo or scan. We will prepare it for OCR and structured review.',
    chooseFile: 'Choose a file', supported: 'PNG or JPEG · up to 10 MB', ready: 'Ready to process', uploadAndProcess: 'Upload and process',
    imagePreview: 'Image preview', whatNext: 'What happens next', whatNextText: 'We assess quality, prepare the image, run OCR, and create an editable representation.',
    themeHint: 'Choose how DocuScan AI looks in this browser.', languageHint: 'Choose the language used by the interface. OCR languages are configured on the server.',
    saved: 'Saved', save: 'Save changes', search: 'Search', filter: 'Filter', allStatus: 'All statuses', clear: 'Clear',
  },
  hi: {
    workspace: 'वर्कस्पेस', dashboard: 'डैशबोर्ड', newScan: 'नया स्कैन', documents: 'दस्तावेज़', history: 'OCR इतिहास', settings: 'सेटिंग्स',
    overview: 'अवलोकन', scanDocument: 'दस्तावेज़ स्कैन करें', searchDocuments: 'दस्तावेज़ खोजें', language: 'भाषा', appearance: 'दिखावट',
    lightMode: 'लाइट मोड', darkMode: 'डार्क मोड', recentDocuments: 'हाल के दस्तावेज़', viewAll: 'सभी देखें', documentLibrary: 'दस्तावेज़ लाइब्रेरी',
    documentLibraryHint: 'अपने सभी दस्तावेज़ खोजें, देखें और प्रबंधित करें।', allDocuments: 'सभी दस्तावेज़', uploadDocument: 'दस्तावेज़ अपलोड करें',
    intelligentWorkspace: 'स्मार्ट दस्तावेज़ कार्यक्षेत्र', heroTitle: 'छवि से उपयोगी जानकारी तक, बिना अतिरिक्त काम के।',
    heroText: 'महत्वपूर्ण दस्तावेज़ों को एक जगह कैप्चर, समझें, सुधारें और एक्सपोर्ट करें।',
    documentsScanned: 'स्कैन किए दस्तावेज़', processed: 'सफलतापूर्वक प्रोसेस', failed: 'ध्यान आवश्यक', confidence: 'OCR विश्वास',
    noDocuments: 'अभी कोई दस्तावेज़ नहीं', noDocumentsHint: 'रसीद, बिल, फॉर्म या मुद्रित पेज से शुरू करें।', startScan: 'स्कैन शुरू करें',
    processing: 'प्रोसेस हो रहा है', completed: 'पूर्ण', document: 'दस्तावेज़', status: 'स्थिति', uploaded: 'अपलोड किया गया', textPreview: 'टेक्स्ट पूर्वावलोकन',
    noText: 'कोई टेक्स्ट नहीं मिला', delete: 'हटाएं', openDocument: 'दस्तावेज़ खोलें', localWorkspace: 'लोकल कार्यक्षेत्र',
    newDocument: 'नया दस्तावेज़', uploadTitle: 'अपने दस्तावेज़ को स्पष्ट बनाएं।', uploadHint: 'एक साफ फोटो या स्कैन डालें। हम इसे OCR और समीक्षा के लिए तैयार करेंगे।',
    chooseFile: 'फ़ाइल चुनें', supported: 'PNG या JPEG · 10 MB तक', ready: 'प्रोसेस के लिए तैयार', uploadAndProcess: 'अपलोड और प्रोसेस करें',
    imagePreview: 'छवि पूर्वावलोकन', whatNext: 'आगे क्या होगा', whatNextText: 'हम गुणवत्ता जांचते हैं, छवि तैयार करते हैं, OCR चलाते हैं और संपादन योग्य प्रतिनिधित्व बनाते हैं।',
    themeHint: 'इस ब्राउज़र में DocuScan AI का रूप चुनें।', languageHint: 'इंटरफ़ेस भाषा चुनें। OCR भाषाएं सर्वर पर सेट होती हैं।',
    saved: 'सहेजा गया', save: 'बदलाव सहेजें', search: 'खोजें', filter: 'फ़िल्टर', allStatus: 'सभी स्थितियां', clear: 'साफ करें',
  },
  ta: {
    workspace: 'பணியிடம்', dashboard: 'டாஷ்போர்டு', newScan: 'புதிய ஸ்கேன்', documents: 'ஆவணங்கள்', history: 'OCR வரலாறு', settings: 'அமைப்புகள்',
    overview: 'கண்ணோட்டம்', scanDocument: 'ஆவணத்தை ஸ்கேன் செய்க', searchDocuments: 'ஆவணங்களைத் தேடுக', language: 'மொழி', appearance: 'தோற்றம்',
    lightMode: 'ஒளி முறை', darkMode: 'இருள் முறை', recentDocuments: 'சமீபத்திய ஆவணங்கள்', viewAll: 'அனைத்தையும் காண்க', documentLibrary: 'ஆவண நூலகம்',
    documentLibraryHint: 'உங்கள் பணியிடத்தில் உள்ள ஆவணங்களைத் தேடி நிர்வகிக்கவும்.', allDocuments: 'அனைத்து ஆவணங்கள்', uploadDocument: 'ஆவணத்தை பதிவேற்றுக',
    intelligentWorkspace: 'நுண்ணறிவு ஆவண பணியிடம்', heroTitle: 'படத்திலிருந்து பயனுள்ள தகவலுக்கு.',
    heroText: 'முக்கிய ஆவணங்களை ஒரே பணியிடத்தில் பிடிக்கவும், புரிந்துகொள்ளவும், திருத்தவும் மற்றும் ஏற்றுமதி செய்யவும்.',
    documentsScanned: 'ஸ்கேன் செய்யப்பட்டவை', processed: 'வெற்றிகரமாக செயலாக்கப்பட்டது', failed: 'கவனம் தேவை', confidence: 'OCR நம்பிக்கை',
    noDocuments: 'இன்னும் ஆவணங்கள் இல்லை', noDocumentsHint: 'ரசீது, பில், படிவம் அல்லது அச்சிடப்பட்ட பக்கத்துடன் தொடங்குங்கள்.', startScan: 'ஸ்கேன் தொடங்கு',
    processing: 'செயலாக்கப்படுகிறது', completed: 'முடிந்தது', document: 'ஆவணம்', status: 'நிலை', uploaded: 'பதிவேற்றப்பட்டது', textPreview: 'உரை முன்னோட்டம்',
    noText: 'உரை கிடைக்கவில்லை', delete: 'நீக்கு', openDocument: 'ஆவணத்தைத் திற', localWorkspace: 'உள்ளூர் பணியிடம்',
    newDocument: 'புதிய ஆவணம்', uploadTitle: 'உங்கள் ஆவணத்தை தெளிவுபடுத்துங்கள்.', uploadHint: 'தெளிவான புகைப்படம் அல்லது ஸ்கேனை இழுத்து விடுங்கள்.',
    chooseFile: 'கோப்பைத் தேர்ந்தெடுக்கவும்', supported: 'PNG அல்லது JPEG · 10 MB வரை', ready: 'செயலாக்கத் தயார்', uploadAndProcess: 'பதிவேற்றி செயலாக்கு',
    imagePreview: 'பட முன்னோட்டம்', whatNext: 'அடுத்து என்ன', whatNextText: 'தரத்தை மதிப்பிட்டு, படத்தைத் தயாரித்து, OCR இயக்கி, திருத்தக்கூடிய வடிவத்தை உருவாக்குகிறோம்.',
    themeHint: 'இந்த உலாவியில் DocuScan AI தோற்றத்தைத் தேர்ந்தெடுக்கவும்.', languageHint: 'இடைமுக மொழியைத் தேர்ந்தெடுக்கவும். OCR மொழிகள் சேவையகத்தில் அமைக்கப்படுகின்றன.',
    saved: 'சேமிக்கப்பட்டது', save: 'மாற்றங்களை சேமி', search: 'தேடல்', filter: 'வடிகட்டி', allStatus: 'அனைத்து நிலைகள்', clear: 'அழி',
  },
  es: {
    workspace: 'Espacio de trabajo', dashboard: 'Panel', newScan: 'Nuevo escaneo', documents: 'Documentos', history: 'Historial OCR', settings: 'Ajustes',
    overview: 'Resumen', scanDocument: 'Escanear documento', searchDocuments: 'Buscar documentos', language: 'Idioma', appearance: 'Apariencia',
    lightMode: 'Modo claro', darkMode: 'Modo oscuro', recentDocuments: 'Documentos recientes', viewAll: 'Ver todo', documentLibrary: 'Biblioteca de documentos',
    documentLibraryHint: 'Busca, revisa y gestiona todos los documentos.', allDocuments: 'Todos los documentos', uploadDocument: 'Subir documento',
    intelligentWorkspace: 'Espacio inteligente de documentos', heroTitle: 'De imagen a información, sin trabajo extra.',
    heroText: 'Captura, comprende, corrige y exporta documentos importantes.', documentsScanned: 'Documentos escaneados', processed: 'Procesados', failed: 'Requiere atención', confidence: 'Confianza OCR',
    noDocuments: 'Aún no hay documentos', noDocumentsHint: 'Comienza con un recibo, factura, formulario o página.', startScan: 'Iniciar escaneo',
    processing: 'Procesando', completed: 'Completado', document: 'Documento', status: 'Estado', uploaded: 'Subido', textPreview: 'Vista previa',
    noText: 'No se devolvió texto', delete: 'Eliminar', openDocument: 'Abrir documento', localWorkspace: 'Espacio local',
    newDocument: 'Nuevo documento', uploadTitle: 'Enfoca tu documento.', uploadHint: 'Suelta una foto o escaneo nítido.', chooseFile: 'Elegir archivo',
    supported: 'PNG o JPEG · hasta 10 MB', ready: 'Listo para procesar', uploadAndProcess: 'Subir y procesar', imagePreview: 'Vista previa',
    whatNext: 'Qué sucede después', whatNextText: 'Evaluamos la calidad, preparamos la imagen, ejecutamos OCR y creamos una representación editable.',
    themeHint: 'Elige el aspecto de DocuScan AI en este navegador.', languageHint: 'Elige el idioma de la interfaz. Los idiomas OCR se configuran en el servidor.',
    saved: 'Guardado', save: 'Guardar cambios', search: 'Buscar', filter: 'Filtrar', allStatus: 'Todos los estados', clear: 'Limpiar',
  },
}

const languageOptions = [
  { code: 'en', label: 'English' }, { code: 'hi', label: 'हिन्दी' }, { code: 'ta', label: 'தமிழ்' }, { code: 'es', label: 'Español' },
]
const I18nContext = createContext(null)

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(() => localStorage.getItem('docuscan-language') || 'en')
  useEffect(() => { localStorage.setItem('docuscan-language', language); document.documentElement.lang = language }, [language])
  const value = useMemo(() => ({ language, setLanguage, languages: languageOptions, t: (key) => translations[language]?.[key] || translations.en[key] || key }), [language])
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n() { return useContext(I18nContext) }
